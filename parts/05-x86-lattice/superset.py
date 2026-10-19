#!/usr/bin/env python3
"""superset.py — x86-64 superset-decode lattice + resynchronisation statistics.

Decode a code region at EVERY byte offset, draw the overlapping-instruction
lattice, and measure how quickly misaligned decode streams RESYNCHRONISE with
the compiler-intended stream. This quantifies, on a CORPUS of modern x86-64
binaries, the qualitative claim of Linn & Debray (CCS 2003 §3.1 "Self-Repairing
Disassembly": "disassembly errors usually resynchronize quite quickly - often
within just one or two instructions"), restated by Andriesse et al. (USENIX Sec
2016 §3) as "within two or three instructions". We report the real distribution
so the reader can see which holds, and render the lattice (REVIEW-01 §6.2).

AUTHORITY = objdump.  Every per-offset length comes from `objdump -D -w -z`
(REVIEW-05-build B1: without `-w`, objdump wraps instruction bytes at 7 per line
and a from-scratch line parser mistakes the continuation line for a new
instruction; without `-z` it elides zero runs). Two guards make the authority
trustworthy by construction:
  * a parser SELF-CHECK: the linear decode's instruction lengths are contiguous
    and sum to the region size;
  * a WINDOWED per-offset decode (one objdump call per region: the region is
    expanded into 15-byte windows each followed by 16 x 0x90, so any <=15-byte
    x86 instruction decodes fully and the sweep realigns on the NOPs at the next
    window) is cross-checked against the linear decode at every true boundary.

`(bad)` POLICY (REVIEW-05-build B1): an offset objdump prints as `(bad)` is
stepped by the byte count objdump assigns it and FLAGGED; every resync chain
records whether it passed through a `(bad)`, and ALL statistics are reported
twice -- over all chains, and over only chains that never touch a `(bad)`.

ANALYSIS ONLY (C09-2): reads binaries read-only, compiles one fixed benign C
file, never generates or transforms code.  Python stdlib + system objdump/gcc.
"""
import json
import os
import re
import statistics as st
import subprocess
import sys
import tempfile

import lendec

OBJDUMP = "objdump"
MACHINE = ["-b", "binary", "-m", "i386:x86-64"]
# With -w there is exactly one line per instruction: "  <addr>:\t<bytes>\t<text>".
LINE = re.compile(r"^\s*([0-9a-f]+):\t([0-9a-f ]+?)\t(.*)$")
WINDOW = 15          # max x86-64 instruction length
PAD = 16             # 0x90 NOPs after each window -> clean realignment


def _is_bad(text):
    """objdump's undecodable output: `(bad)`, or `.byte` (a truncated tail)."""
    return "(bad)" in text or text.startswith(".byte")


# --------------------------------------------------------------------------
# objdump: linear decode (the intended / reference stream) and the self-check
# --------------------------------------------------------------------------
def linear_decode(raw):
    """Linear `objdump -D -w -z` of raw bytes. Returns (insns, bounds) where
    insns is a list of (off, length, is_bad, text) covering raw contiguously,
    and bounds is the set of instruction-start offsets plus len(raw).
    SELF-CHECK (B1): lengths are contiguous and sum to len(raw)."""
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "r.bin")
        with open(f, "wb") as fh:
            fh.write(raw)
        out = subprocess.run([OBJDUMP, "-D", *MACHINE, "-w", "-z", f],
                             capture_output=True, text=True, check=True).stdout
    insns = []
    for ln in out.splitlines():
        m = LINE.match(ln)
        if not m:
            continue
        off = int(m.group(1), 16)
        nby = len(m.group(2).split())
        insns.append((off, nby, _is_bad(m.group(3).strip()), m.group(3).strip()))
    # self-check: contiguous and total == region size
    pos = 0
    for off, nby, _, _ in insns:
        if off != pos:
            raise AssertionError(f"linear decode gap: expected {pos}, got {off}")
        pos += nby
    if pos != len(raw):
        raise AssertionError(f"linear decode covers {pos}, region is {len(raw)}")
    bounds = {off for off, _, _, _ in insns}
    bounds.add(len(raw))
    return insns, bounds


def superset_lengths(raw):
    """Per-offset first-instruction length at EVERY offset, in ONE objdump call
    (REVIEW-05-build perf hint). Returns (olen, obad): lists of length len(raw);
    olen[k] is the authoritative length of the instruction decoded at offset k,
    obad[k] True iff objdump prints it `(bad)`."""
    N = len(raw)
    stride = WINDOW + PAD
    blob = b"".join(raw[k:k + WINDOW].ljust(WINDOW, b"\x90") + b"\x90" * PAD
                    for k in range(N))
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "w.bin")
        with open(f, "wb") as fh:
            fh.write(blob)
        out = subprocess.run([OBJDUMP, "-D", *MACHINE, "-w", "-z", f],
                             capture_output=True, text=True, check=True).stdout
    olen = [None] * N
    obad = [False] * N
    for ln in out.splitlines():
        m = LINE.match(ln)
        if not m:
            continue
        a = int(m.group(1), 16)
        if a % stride:            # only the first instruction of each window
            continue
        k = a // stride
        if k < N:
            olen[k] = len(m.group(2).split())
            obad[k] = _is_bad(m.group(3).strip())
    # A decode that would end past the region consumed padding, not program
    # bytes: it is not an instruction of this region. Chains reaching it run off
    # the end (never resync); the lattice does not draw it.
    return olen, obad


# --------------------------------------------------------------------------
# resync: follow each misaligned decode to the compiler-intended stream
# --------------------------------------------------------------------------
def resync_chains(raw, bounds, olen, obad):
    """For each misaligned start (offset not a true boundary) follow
    k -> k+olen[k] -> ... until it lands on a true boundary (RESYNC) or runs off
    the region (NEVER). Record bytes, instruction count, and whether the chain
    passed through a `(bad)`. Returns (resyncs, never) lists of dicts."""
    N = len(raw)
    resyncs, never = [], []
    for k in range(N):
        if k in bounds or olen[k] is None:
            continue
        pos, insns, hit_bad = k, 0, False
        while pos < N and olen[pos] is not None and insns <= N:
            if obad[pos]:
                hit_bad = True
            pos += olen[pos]
            insns += 1
            if pos in bounds:
                resyncs.append({"start": k, "bytes": pos - k,
                                "insns": insns, "bad": hit_bad})
                break
        else:
            never.append({"start": k, "bad": hit_bad})
    return resyncs, never


def diststats(vals):
    if not vals:
        return None
    v = sorted(vals)
    n = len(v)
    q = st.quantiles(v, n=4) if n >= 2 else [v[0], v[0], v[0]]
    return {
        "n": n, "median": st.median(v), "q1": q[0], "q3": q[2], "max": v[-1],
        "p1": sum(1 for x in v if x <= 1) / n,
        "p2": sum(1 for x in v if x <= 2) / n,
        "p3": sum(1 for x in v if x <= 3) / n,
    }


def lendec_categories(offsets, olen, obad, dlen):
    """The REVIEW-05 categories for lendec vs objdump over `offsets`."""
    c = {"AGREE": 0, "WRONG": 0, "LENDEC-NONE": 0, "BAD-ACCEPTED": 0, "BAD-REJECTED": 0}
    for k in offsets:
        if obad[k]:
            c["BAD-REJECTED" if dlen[k] is None else "BAD-ACCEPTED"] += 1
        elif dlen[k] is None:
            c["LENDEC-NONE"] += 1
        elif dlen[k] == olen[k]:
            c["AGREE"] += 1
        else:
            c["WRONG"] += 1
    return c


def analyze(raw, label, ground_truth, funcs=None):
    """Full analysis of one region. Guards (B1): the linear decode is contiguous
    (raises otherwise); the windowed per-offset decode is cross-checked against
    it at every true boundary; for ground truth, every function entry from the
    symbol table must be a boundary of the sweep, and the sweep must be clean."""
    N = len(raw)
    insns, bounds = linear_decode(raw)
    linlen = {off: nby for off, nby, _, _ in insns}
    olen, obad = superset_lengths(raw)
    xchk = sorted(linlen)
    xok = sum(1 for b in xchk if olen[b] == linlen[b])
    sweep_bad = sum(1 for _, _, b, _ in insns if b)
    sym_missing = sorted(f for f, off in (funcs or {}).items() if off not in bounds)

    # lendec differential test (C09-3): offsets whose objdump decode ends inside
    # the region (a decode past the end consumed padding, not program bytes)
    inside = [k for k in range(N) if olen[k] is not None and k + olen[k] <= N]
    past = N - len(inside)
    ins = set(inside)
    dlen = [lendec.decode_len(raw, k)[0] for k in range(N)]
    cat_true = lendec_categories([b for b in xchk if b in ins], olen, obad, dlen)
    cat_all = lendec_categories(inside, olen, obad, dlen)

    resyncs, never = resync_chains(raw, bounds, olen, obad)
    clean = [r for r in resyncs if not r["bad"]]
    return {
        "label": label, "ground_truth": ground_truth, "N": N,
        "nbounds": len(bounds) - 1, "nbad": sum(obad), "past_end": past,
        "xchk": len(xchk), "xok": xok, "sweep_bad": sweep_bad,
        "nfuncs": len(funcs or {}), "sym_missing": sym_missing,
        "cat_true": cat_true, "cat_all": cat_all,
        "resyncs": resyncs, "never": never,
        "all_stats": diststats([r["insns"] for r in resyncs]),
        "clean_stats": diststats([r["insns"] for r in clean]),
        "byte_stats": diststats([r["bytes"] for r in resyncs]),
        "never_all": len(never), "never_clean": sum(1 for x in never if not x["bad"]),
        "olen": olen, "obad": obad, "dlen": dlen, "bounds": sorted(bounds), "_raw": raw,
    }


# --------------------------------------------------------------------------
# region sources
# --------------------------------------------------------------------------
GROUND_SRC = r"""
#include <stdint.h>
#include <string.h>
/* A spread of gcc -O2 forms: imm64/movabs, SSE, a jump table, bit ops, a
   memcpy, a leaf. Compiled with symbols so the intended boundaries are known
   (C09-4 ground truth). Benign; never executed by this tool. */
long work(int *a, int n, int k) {
    long s = 0;
    for (int i = 0; i < n; i++) {
        int v = a[i];
        if (v & 1) s += (long)v * k; else s -= (v >> 2) + 7;
        if (v > 1000) s ^= 0xdeadbeefULL;
        a[i] = (int)(s + i);
    }
    return s * 2654435761u + k;
}
double sse(double x, double y, int n) {
    double s = 0.0;
    for (int i = 0; i < n; i++) s += x * y + (double)i / 3.0;
    return s / (x + 1.0);
}
int jt(int c, int x) {
    switch (c) {
    case 0: return x + 1;   case 1: return x * 3;
    case 2: return x << 2;  case 3: return x - 9;
    case 4: return x ^ 0x5a5a; case 5: return x / 7;
    default: return ~x;
    }
}
unsigned long bits(unsigned long v) {
    v ^= v >> 33; v *= 0xff51afd7ed558ccdUL; v ^= v >> 29;
    v *= 0xc4ceb9fe1a85ec53UL; v ^= v >> 32; return v;
}
void cpy(char *d, const char *s, unsigned long n) { memcpy(d, s, n); }
int leaf(int a, int b) { return a * b + (a ^ b); }
long poly(long *p, int n) {
    long acc = 1;
    for (int i = 0; i < n; i++) acc = acc * p[i] + (p[i] >> 1) - 17;
    return acc;
}
int cls(int x) { return x < 0 ? -1 : (x == 0 ? 0 : (x < 100 ? 1 : 2)); }
"""
# Ground-truth corpus: the inline functions above plus every C source of this
# repo (own code, in the clone), each compiled -O2 with symbols. Never run.
HERE = os.path.dirname(os.path.abspath(__file__))
GT_SOURCES = ["<inline gt.c>",
              "../01-smc-observatory/smcobs.c",
              "../02-pt-truth/ptcap.c",
              "../02-pt-truth/verify_singlestep.c",
              "../../research/probes/hybrid-undefined-flags/rule.c",
              "../../research/probes/hybrid-undefined-flags/uflags.c",
              "../../research/probes/hybrid-undefined-flags/refine.c",
              "../../research/probes/pt-smc-misdecode/smc.c"]
HEADLINE_FN = "work"               # the region drawn as the lattice

# reference-decode arm: present members of this list; each capped to keep `make`
# fast and bounded. "Reference decode" = objdump's linear sweep of raw .text; it
# is NOT true ground truth for a stripped binary (C09-4 caveat).
REF_CANDIDATES = ["/usr/bin/true", "/usr/bin/cat", "/usr/bin/wc",
                  "/usr/bin/sort", "/usr/bin/ls"]
REF_CAP = 48 * 1024


def compile_ground(tmp):
    """Compile each ground-truth source -O2 with symbols into `tmp`.
    Returns [(label, objfile)] for those that compile; others are reported."""
    objs = []
    for src in GT_SOURCES:
        if src.startswith("<"):
            c = os.path.join(tmp, "gt.c")
            with open(c, "w") as fh:
                fh.write(GROUND_SRC)
            label = "gt.c"
        else:
            c = os.path.normpath(os.path.join(HERE, src))
            label = os.path.basename(c)
            if not os.path.exists(c):
                print(f"  (ground truth: {src} not present, skipped)")
                continue
        o = os.path.join(tmp, label + ".o")
        r = subprocess.run(["gcc", "-O2", "-c", "-D_GNU_SOURCE",
                            "-fno-asynchronous-unwind-tables", c, "-o", o],
                           capture_output=True, text=True)
        if r.returncode:
            print(f"  (ground truth: {label} did not compile, skipped)")
            continue
        objs.append((label, o))
    return objs


def text_bytes(path, cap):
    """The first <= `cap` bytes of an ELF's .text, CUT AT AN INSTRUCTION BOUNDARY
    of the linear sweep, so the cap never truncates the last instruction (a
    truncated tail made the windowed and linear decodes disagree)."""
    out = subprocess.run(["readelf", "-SW", path], capture_output=True, text=True).stdout
    for ln in out.splitlines():
        p = ln.replace("]", " ").replace("[", " ").split()
        if len(p) >= 6 and p[1] == ".text":
            off, size = int(p[4], 16), int(p[5], 16)
            with open(path, "rb") as fh:
                fh.seek(off)
                raw = fh.read(min(size, cap + WINDOW + 1))
            if size <= cap:
                return raw
            insns, _ = linear_decode(raw)
            cut = max(o for o, _, _, _ in insns if o <= cap)
            return raw[:cut]
    return b""


def objdump_len_at(raw, k):
    """Per-offset helper: the objdump -w -z length of the instruction decoded at
    offset k (the same 15-byte window superset_lengths uses for every offset),
    or None if that decode would end past the region (it consumed padding)."""
    L = superset_lengths(raw[k:k + WINDOW])[0][0]
    return L if L is not None and k + L <= len(raw) else None


def region_from_symbol_elf(path, maxbytes=160):
    """The first <= maxbytes of an ELF's .text, cut at an instruction boundary,
    with its objdump -w -z linear-sweep boundaries (a REFERENCE decode, C09-4)."""
    raw = text_bytes(path, maxbytes)
    return raw, linear_decode(raw)[1]


def object_sections(objfile):
    """Every code section of a self-built object, from ONE `objdump -d -w -z`
    pass: list of (section, raw bytes, {function: offset}). The function
    offsets come from the symbol labels and are an INDEPENDENT check on the
    section's linear sweep (every entry must be one of its boundaries)."""
    out = subprocess.run([OBJDUMP, "-d", "-w", "-z", objfile],
                         capture_output=True, text=True, check=True).stdout
    secs, cur = [], None
    for ln in out.splitlines():
        s = re.match(r"^Disassembly of section (\S+):$", ln)
        if s:
            cur = [s.group(1), bytearray(), {}, None]
            secs.append(cur)
            continue
        lab = re.match(r"^([0-9a-f]+) <([^>]+)>:$", ln)
        if lab and cur is not None:
            a = int(lab.group(1), 16)
            if cur[3] is None:
                cur[3] = a
            cur[2][lab.group(2)] = a - cur[3]
            continue
        m = LINE.match(ln)
        if m and cur is not None:
            if cur[3] is None:
                cur[3] = int(m.group(1), 16)
            cur[1] += bytes(int(x, 16) for x in m.group(2).split())
    return [(name, bytes(raw), funcs) for name, raw, funcs, _ in secs if raw]


# --------------------------------------------------------------------------
# visualization: a real overlapping-instruction lattice (B3)
# --------------------------------------------------------------------------
def emit_lattice(r, allres, path):
    """SVG lattice for region r: nodes = byte offsets on a baseline; edges =
    k -> k+olen[k] drawn as arcs (the superset of all decodes). The true stream
    is highlighted; misaligned chains arc below and visibly merge onto the true
    stream at their resync point; the resync histogram is plotted. Per-offset
    data is embedded in <script id=data> so the picture is re-derivable."""
    N = r["N"]
    bset = set(r["bounds"])
    olen, obad, dlen = r["olen"], r["obad"], r["dlen"]
    PX = 11                       # px per byte
    W = N * PX + 80
    TOP = 120                     # baseline; arcs span TOP-70 .. TOP+70
    H = 440                       # histogram band sits below the arcs
    x = lambda k: 40 + k * PX

    edges = []
    for k in range(N):
        L = olen[k]
        if L is None or k + L > N:            # a decode past the region end is not drawn
            continue
        x0, x1 = x(k), x(k + L)
        up = k in bset            # true-stream edges arc UP, misaligned arc DOWN
        cls = "bad" if obad[k] else ("true" if up else "mis")
        r_ = (x1 - x0) / 2
        cy = TOP
        sweep = 1 if up else 0
        # merge marker: a misaligned edge that lands exactly on a true boundary
        merge = (not up) and ((k + L) in bset)
        edges.append((x0, x1, cy, r_, sweep, cls, merge, k, L))

    seg = []
    for x0, x1, cy, r_, sweep, cls, merge, k, L in edges:
        seg.append(f'<path class="e {cls}" d="M{x0},{cy} A{r_:.1f},'
                   f'{min(r_, 70):.1f} 0 0,{sweep} {x1},{cy}"/>')
        if merge:
            seg.append(f'<circle class="merge" cx="{x1}" cy="{cy}" r="3"/>')
    # true-stream node ticks
    ticks = "".join(f'<line class="tick" x1="{x(b)}" y1="{TOP-4}" '
                    f'x2="{x(b)}" y2="{TOP+4}"/>' for b in r["bounds"] if b <= N)

    # example misaligned chains, followed edge by edge to their merge point:
    # the longest resync, plus one 2-insn and one 3-insn chain
    rs = r["resyncs"]
    ex = (sorted(rs, key=lambda c: -c["insns"])[:1]
          + [c for c in rs if c["insns"] == 2][:1]
          + [c for c in rs if c["insns"] == 3][:1])
    chain_svg = []
    for c in ex:
        pos = c["start"]
        while pos < N and pos not in bset and olen[pos]:
            L = olen[pos]
            x0, x1 = x(pos), x(pos + L)
            rr = (x1 - x0) / 2
            chain_svg.append(f'<path class="e chain" d="M{x0},{TOP} A{rr:.1f},'
                             f'{min(rr, 70):.1f} 0 0,0 {x1},{TOP}"/>')
            pos += L
        chain_svg.append(f'<circle class="start" cx="{x(c["start"])}" cy="{TOP}" r="3.5"/>')

    # resync histogram (instructions-to-resync), all chains
    hist = {}
    for rr in r["resyncs"]:
        hist[rr["insns"]] = hist.get(rr["insns"], 0) + 1
    hmax = max(hist.values()) if hist else 1
    bw, bx, by = 26, 60, H - 28
    bars = []
    for i, key in enumerate(sorted(hist)):
        hh = int(140 * hist[key] / hmax)
        bars.append(f'<rect class="bar" x="{bx + i*bw}" y="{by-hh}" width="{bw-6}" '
                    f'height="{hh}"/><text class="hl" x="{bx + i*bw + (bw-6)/2}" '
                    f'y="{by+14}">{key}</text><text class="hl" x="{bx + i*bw + (bw-6)/2}" '
                    f'y="{by-hh-4}">{hist[key]}</text>')

    # embedded, re-derivable per-offset data
    per = [{"off": k, "hex": raw_hex(r, k), "objlen": olen[k],
            "declen": dlen[k], "bad": bool(obad[k]), "boundary": k in bset}
           for k in range(N)]
    data = {"label": r["label"], "N": N, "per_offset": per,
            "geom": {"px_per_byte": PX, "left": 40},       # x(k) = left + k * px
            "resync_insn_hist": {str(k): v for k, v in sorted(hist.items())},
            "corpus": allres}

    css = ("body{font:13px system-ui;background:#0b0d12;color:#e6e8ee;margin:20px}"
           "svg{background:#0f1218;border:1px solid #222;max-width:100%}"
           ".e{fill:none;stroke-width:1.4;opacity:.55}"
           ".true{stroke:#3fb950;stroke-width:2.4;opacity:1}"      # true-stream edges
           ".mis{stroke:#6e7681}"                                   # misaligned edges
           ".bad{stroke:#f85149;stroke-dasharray:3 2}"             # (bad) edges
           ".merge{fill:#d29922}"                                   # resync / merge point
           ".chain{stroke:#a371f7;stroke-width:2.2;opacity:1}"     # example chain
           ".start{fill:#a371f7}"                                   # example chain start
           ".tick{stroke:#3fb950;stroke-width:2}"
           ".bar{fill:#58a6ff}.hl{fill:#8b949e;font-size:10px;text-anchor:middle}"
           "code{color:#7ee787}h1{font-size:18px}h2{font-size:14px;margin:16px 0 4px}")
    html = [
        "<!doctype html><meta charset=utf-8><title>x86 superset lattice</title>",
        f"<style>{css}</style>",
        "<h1>x86-64 superset-decode lattice</h1>",
        f"<p>Region: <code>{r['label']}</code>. Each vertical tick is a "
        "compiler-intended instruction boundary. Each arc is one decoded "
        "instruction <code>k &rarr; k+len(k)</code>:</p>",
        '<p><b style="color:#3fb950">&#9180; green (up)</b> = the true stream; '
        '<b style="color:#6e7681">&#9181; grey (down)</b> = a misaligned decode; '
        '<b style="color:#f85149">red dashed</b> = objdump <code>(bad)</code>; '
        '<b style="color:#d29922">&#9679;</b> = a misaligned arc landing on a '
        "true boundary (resync / merge point); "
        '<b style="color:#a371f7">purple</b> = example misaligned chains '
        "(the longest, one 2-insn, one 3-insn) followed arc by arc from their "
        "start dot to the merge point where they rejoin the ticks.</p>",
        f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
        f'<line class="tick" x1="40" y1="{TOP}" x2="{N*PX+40}" y2="{TOP}" '
        'style="stroke:#30363d;stroke-width:1"/>',
        ticks, "".join(seg), "".join(chain_svg),
        f'<text class="hl" x="60" y="{TOP+108}" style="text-anchor:start">'
        'resync length (instructions to rejoin the true stream) &rarr; count</text>',
        "".join(bars),
        "</svg>",
        f"<h2>illustration region (the headline is the corpus below) &mdash; {r['label']}</h2>",
        f"<p>{_fmt_stats(r)}</p>",
        "<h2>corpus</h2>",
        _corpus_table(allres),
        f'<script id=data type=application/json>{json.dumps(data)}</script>',
    ]
    with open(path, "w") as fh:
        fh.write("\n".join(html))


def raw_hex(r, k):
    L = r["olen"][k] or 1
    return " ".join("%02x" % b for b in r["_raw"][k:k + L])


def _fmt_stats(r):
    a, c = r["all_stats"], r["clean_stats"]
    if not a:
        return "no resync data"
    return (f"all chains: n={a['n']}, median={_g(a['median'])} insns, "
            f"P(&le;2)={a['p2']*100:.0f}%, max={a['max']}; "
            f"(bad)-free chains: n={c['n']}, median={_g(c['median'])}, "
            f"P(&le;2)={c['p2']*100:.0f}% &nbsp;|&nbsp; never-resync "
            f"{r['never_all']} (all), {r['never_clean']} ((bad)-free)")


def _corpus_table(allres):
    rows = ['<table border=0 cellpadding=4><tr><td>region</td><td>kind</td>'
            '<td>n</td><td>median</td><td>P(&le;1)</td><td>P(&le;2)</td>'
            '<td>P(&le;3)</td><td>max</td><td>(bad)-free median / P(&le;2)</td></tr>']
    for a in allres:
        s, cl = a["all"], a["clean"]
        if not s:
            continue
        kind = "ground truth" if a["ground_truth"] else "reference"
        clean = f'{_g(cl["median"])} / {cl["p2"]*100:.0f}%' if cl else "-"
        rows.append(
            f'<tr><td><code>{a["label"]}</code></td><td>{kind}</td><td>{s["n"]}</td>'
            f'<td>{_g(s["median"])}</td><td>{s["p1"]*100:.0f}%</td><td>{s["p2"]*100:.0f}%</td>'
            f'<td>{s["p3"]*100:.0f}%</td><td>{s["max"]}</td><td>{clean}</td></tr>')
    rows.append("</table>")
    return "".join(rows)


# --------------------------------------------------------------------------
def _pool(results, clean):
    vals = []
    for r in results:
        vals += [x["insns"] for x in r["resyncs"] if (not clean or not x["bad"])]
    return diststats(vals)


def _summize(r):
    """Compact corpus row for embedding + the printed table."""
    return {"label": r["label"], "ground_truth": r["ground_truth"],
            "all": r["all_stats"], "clean": r["clean_stats"],
            "never": r["never_all"], "never_clean": r["never_clean"]}


def _merge(label, parts):
    """Aggregate an object's analysed code sections into one corpus row."""
    rs = [x for p in parts for x in p["resyncs"]]
    nv = [x for p in parts for x in p["never"]]
    return {"label": label, "ground_truth": True, "N": sum(p["N"] for p in parts),
            "resyncs": rs, "never": nv,
            "all_stats": diststats([x["insns"] for x in rs]),
            "clean_stats": diststats([x["insns"] for x in rs if not x["bad"]]),
            "never_all": len(nv), "never_clean": sum(1 for x in nv if not x["bad"])}


def _g(x):
    return f"{x:g}"


def _row(r):
    s, c = r["all_stats"], r["clean_stats"]
    if not s:
        return f"  {r['label']:<34} (no misaligned starts)"
    cl = f"{_g(c['median'])} / {c['p2']*100:.0f}%" if c else "-"
    return (f"  {r['label']:<34}{s['n']:>7}{_g(s['median']):>5}{_g(s['q1']):>5}{_g(s['q3']):>5}"
            f"{s['p1']*100:>5.0f}%{s['p2']*100:>5.0f}%{s['p3']*100:>5.0f}%{s['max']:>5}"
            f"{r['never_all']:>6}   {cl:>10}")


def main():
    print("=" * 78)
    print("x86-64 superset-decode lattice + resync statistics  (authority: objdump -w -z)")
    print('Linn & Debray CCS\'03 §3.1: errors "resynchronize ... within just one or')
    print(' two instructions"; Andriesse et al. 2016 §3 restates it as "two or three".')
    print(" Measured here over a corpus, with and without chains through a (bad).")
    print("=" * 78)
    fail = 0

    def v(name, cond, detail=""):
        nonlocal fail
        if not cond:
            fail = 1
        print(f"VERDICT {'PASS' if cond else 'FAIL'}: {name}" + (f"  [{detail}]" if detail else ""))

    # ---- ground-truth arm: self-built -O2 objects with symbols, by section ----
    gt_regions, gt_rows, excluded, headline, nfuncs = [], [], [], None, 0
    with tempfile.TemporaryDirectory(prefix="latt-gt-") as tmp:
        for olabel, obj in compile_ground(tmp):
            parts = []
            for sec, raw, funcs in object_sections(obj):
                a = analyze(raw, f"{olabel}:{sec}", True, funcs)
                if a["sweep_bad"] or a["sym_missing"]:
                    excluded.append((a["label"], a["sweep_bad"], a["sym_missing"]))
                    continue
                parts.append(a)
                nfuncs += a["nfuncs"]
                if olabel == "gt.c" and sec == ".text" and HEADLINE_FN in funcs:
                    s = funcs[HEADLINE_FN]
                    e = min([x for x in funcs.values() if x > s] or [len(raw)])
                    headline = analyze(raw[s:e], f"gt.c:{HEADLINE_FN}() [{e - s}B]",
                                       True, {HEADLINE_FN: 0})
            if parts:
                gt_regions += parts
                gt_rows.append(_merge(f"{olabel} [{sum(p['N'] for p in parts)}B "
                                      f"{len(parts)}sec {sum(p['nfuncs'] for p in parts)}fn]",
                                      parts))

    # ---- reference-decode arm: present /usr/bin binaries ---------------------
    ref_rows = []
    for path in REF_CANDIDATES:
        if not os.path.exists(path):
            continue
        raw = text_bytes(path, REF_CAP)
        if raw:
            ref_rows.append(analyze(raw, f"{os.path.basename(path)} [{len(raw)}B .text]", False))

    # ---- report --------------------------------------------------------------
    hdr = (f"  {'region':<34}{'n':>7}{'med':>5}{'Q1':>5}{'Q3':>5}{'P<=1':>6}{'P<=2':>6}"
           f"{'P<=3':>6}{'max':>5}{'never':>6}   {'(bad)-free med/P<=2':>10}")
    print("\nGROUND TRUTH — self-built gcc -O2 objects with symbols (every code section;"
          "\n  sweep clean and every function entry confirmed by the symbol table):")
    print(hdr)
    for r in gt_rows:
        print(_row(r))
    for lab, nb, miss in excluded:
        print(f"  (excluded {lab}: sweep (bad)/.byte={nb}, unconfirmed entries={miss})")
    print("\nREFERENCE DECODE — /usr/bin .text (linear sweep = reference boundaries, NOT"
          "\n  ground truth for a stripped binary; capped at an instruction boundary):")
    print(hdr)
    for r in ref_rows:
        print(_row(r))

    gt_all, gt_clean = _pool(gt_regions, False), _pool(gt_regions, True)
    ref_all, ref_clean = _pool(ref_rows, False), _pool(ref_rows, True)
    gt_never = sum(r["never_all"] for r in gt_regions)
    ref_never = sum(r["never_all"] for r in ref_rows)
    print("\npooled (instructions to resync; (bad)-free = chains that never touch a (bad)):")
    for nm, s, c, nv in [("GROUND TRUTH", gt_all, gt_clean, gt_never),
                         ("REFERENCE", ref_all, ref_clean, ref_never)]:
        print(f"  {nm:<13} n={s['n']:>6} median={_g(s['median'])} Q1={_g(s['q1'])} "
              f"Q3={_g(s['q3'])} P<=1={s['p1']*100:.0f}% P<=2={s['p2']*100:.0f}% "
              f"P<=3={s['p3']*100:.0f}% max={s['max']} never={nv}")
        print(f"  {'':<13} (bad)-free: n={c['n']} median={_g(c['median'])} "
              f"P<=1={c['p1']*100:.0f}% P<=2={c['p2']*100:.0f}% P<=3={c['p3']*100:.0f}% "
              f"max={c['max']}")

    # ---- lendec differential (C09-3), pooled ground truth --------------------
    def catsum(key, regs):
        tot = {}
        for r in regs:
            for k, n in r[key].items():
                tot[k] = tot.get(k, 0) + n
        return tot
    ct, ca = catsum("cat_true", gt_regions), catsum("cat_all", gt_regions)
    print(f"\nlendec vs objdump, ground truth (offsets whose decode ends inside the region):"
          f"\n  at true boundaries: {ct}\n  at every offset:    {ca}")

    # ---- authority self-checks (B1) -----------------------------------------
    allregs = gt_regions + ref_rows
    xok, xcmp = sum(r["xok"] for r in allregs), sum(r["xchk"] for r in allregs)

    # ---- lattice -------------------------------------------------------------
    emit_lattice(headline, [_summize(r) for r in gt_rows + ref_rows], "lattice.html")
    print(f"\nwrote lattice.html: SVG lattice of {headline['label']} + histogram; "
          "per-offset data and corpus stats in <script id=data>")

    # ---- verdicts ------------------------------------------------------------
    v("authority: windowed per-offset length == linear objdump -w -z decode at every true boundary",
      xcmp and xok == xcmp,
      f"{xok}/{xcmp} over {len(allregs)} regions; every linear decode contiguous, summing to its region")
    v("ground truth: every section's sweep is clean and every function entry is a sweep boundary",
      not excluded and nfuncs >= 30,
      f"{len(gt_regions)} sections, {nfuncs} function entries confirmed by the symbol table, "
      f"{len(excluded)} excluded")
    v("lendec never mis-sizes a compiler-intended instruction, and sizes >= 95% of them",
      ct.get("WRONG", 1) == 0 and ct.get("AGREE", 0) >= 0.95 * sum(ct.values()),
      f"true boundaries: AGREE {ct.get('AGREE')} WRONG {ct.get('WRONG')} "
      f"NONE {ct.get('LENDEC-NONE')} of {sum(ct.values())}")
    v("the corpus is not an anecdote: >= 2000 ground-truth chains from >= 5 objects; >= 3 reference binaries",
      gt_all["n"] >= 2000 and len(gt_rows) >= 5 and len(ref_rows) >= 3,
      f"ground truth n={gt_all['n']} from {len(gt_rows)} objects; reference n={ref_all['n']} "
      f"from {len(ref_rows)} binaries")
    CLAIMS(v, gt_all, gt_clean, ref_all, ref_clean)
    ok_html, why = _check_lattice("lattice.html", headline, [_summize(r) for r in gt_rows + ref_rows])
    v("lattice.html is a real lattice: arcs + merge markers + histogram + re-derivable data (C09-5, B3)",
      ok_html, why)

    print("\n" + ("ALL VERDICTS PASS" if fail == 0 else "SOME VERDICTS FAILED"))
    return fail


def CLAIMS(v, gt_all, gt_clean, ref_all, ref_clean):
    """The corpus headline as five falsifiable statements. They were formulated
    FROM this measurement (README says so); the VERDICTs pin them, so a change of
    toolchain, corpus or method that alters a finding is caught."""
    v("claim 1: Linn & Debray's 'one or two' describes the TYPICAL chain (ground-truth median is 1 or 2)",
      gt_all["median"] in (1, 2), f"median {_g(gt_all['median'])} over n={gt_all['n']}")
    v("claim 2: ...but it is not a bound: >= 10% of ground-truth chains need 3+ instructions",
      1 - gt_all["p2"] >= 0.10, f"P(>2) = {(1 - gt_all['p2'])*100:.0f}%, max {gt_all['max']}")
    v("claim 3: Andriesse et al.'s 'two or three' covers >= 75% of ground-truth chains",
      gt_all["p3"] >= 0.75, f"P(<=3) = {gt_all['p3']*100:.0f}%")
    v("claim 4: the (bad) policy is the hinge: (bad)-free median < all-chain median, in BOTH arms",
      gt_clean["median"] < gt_all["median"] and ref_clean["median"] < ref_all["median"],
      f"ground truth {_g(gt_all['median'])} -> {_g(gt_clean['median'])}; "
      f"reference {_g(ref_all['median'])} -> {_g(ref_clean['median'])}")
    v("claim 5: /usr/bin's heavier tail is (bad)-driven: (bad)-free P<=2 within 5 points of ground truth",
      ref_all["p2"] < gt_all["p2"] and abs(ref_clean["p2"] - gt_clean["p2"]) <= 0.05,
      f"all chains: reference {ref_all['p2']*100:.0f}% vs ground truth {gt_all['p2']*100:.0f}%; "
      f"(bad)-free: {ref_clean['p2']*100:.0f}% vs {gt_clean['p2']*100:.0f}%")


def _check_lattice(path, r, corpus):
    """Machine-check the emitted lattice (B3, N5): RE-DERIVE the drawing from the
    embedded per-offset data alone and require it to match what was drawn."""
    try:
        html = open(path, encoding="utf-8").read()
    except OSError as e:
        return False, str(e)
    m = re.search(r'<script id=data type=application/json>(.*?)</script>', html, re.S)
    if not m:
        return False, "no embedded data block"
    d = json.loads(m.group(1))
    per = d.get("per_offset", [])
    N = len(per)
    if N != r["N"] or not all(set(p) >= {"off", "hex", "objlen", "declen", "bad", "boundary"}
                              for p in per):
        return False, f"per-offset data malformed ({N} entries, region {r['N']})"
    bset = {p["off"] for p in per if p["boundary"]} | {N}
    olen = [p["objlen"] for p in per]
    edges = [k for k in range(N) if olen[k] and k + olen[k] <= N]
    merges = [k for k in edges if k not in bset and k + olen[k] in bset]
    hist = {}
    for k in range(N):                         # resync chains, from the data only
        if k in bset or not olen[k]:
            continue
        pos, n = k, 0
        while pos < N and olen[pos]:
            pos += olen[pos]
            n += 1
            if pos in bset:
                hist[str(n)] = hist.get(str(n), 0) + 1
                break
    # GEOMETRY (N6): every drawn arc must map back, through the embedded x(k) =
    # left + k*px, to exactly one decode (k, k+objlen[k]) of the right class.
    g = d.get("geom", {})
    px, left = g.get("px_per_byte"), g.get("left")
    want = {(k, k + olen[k], "bad" if per[k]["bad"] else
             ("true" if per[k]["boundary"] else "mis")) for k in edges}
    drawn = []
    for cls, x0, x1 in re.findall(r'<path class="e (true|mis|bad)" d="M(\d+),\d+ '
                                  r'A[\d.]+,[\d.]+ 0 0,[01] (\d+),\d+"/>', html):
        k0, r0 = divmod(int(x0) - left, px) if px else (None, 1)
        k1, r1 = divmod(int(x1) - left, px) if px else (None, 1)
        drawn.append((k0, k1, cls) if r0 == 0 and r1 == 0 else None)
    geom_ok = len(drawn) == len(want) and set(drawn) == want
    drawn_merges = html.count('class="merge"')
    nbars = html.count('<rect class="bar"')
    ok = (geom_ok and drawn_merges == len(merges)
          and hist == d.get("resync_insn_hist") and nbars == len(hist)
          and d.get("corpus") == json.loads(json.dumps(corpus)))
    return ok, (f"re-derived from data: arcs {len(want)} (drawn {len(drawn)}, every endpoint "
                f"and class matches={geom_ok}), merges {len(merges)} (drawn {drawn_merges}), "
                f"histogram {len(hist)} bars (drawn {nbars}, data match="
                f"{hist == d.get('resync_insn_hist')}), corpus stats embedded="
                f"{d.get('corpus') == json.loads(json.dumps(corpus))}")


if __name__ == "__main__":
    sys.exit(main())
