#!/usr/bin/env python3
import sys
"""superset.py — x86-64 superset-decode lattice + resynchronisation statistics.

Decode a code region at EVERY byte offset, draw the overlapping-instruction
lattice, and measure how quickly misaligned decode streams RESYNCHRONISE with
the compiler-intended stream. This quantifies, on modern x86-64 binaries, the
qualitative claim of Linn & Debray (CCS 2003 §3.1 "Self-Repairing Disassembly":
"disassembly errors usually resynchronize quite quickly - often within just one
or two instructions"), and renders the lattice (REVIEW-01 §6.2).

The authoritative per-offset decode is OBJDUMP (so the lattice is correct by
construction, C09-3); a from-scratch length decoder (lendec.py) is ALSO run at
every offset and its agreement rate vs objdump is reported. ANALYSIS ONLY: this
reads binaries read-only and never generates or transforms code (C09-2).

Python stdlib only; uses the system `objdump` and `gcc`.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import lendec

OBJDUMP = "objdump"
LINE = re.compile(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)")


def build_target():
    """Compile a small program with symbols (-O2). Ground truth = objdump's
    disassembly of a named function (C09-4: a binary the project builds itself,
    with symbols, so .text extent and the intended boundaries are known)."""
    src = r"""
    #include <stdint.h>
    int work(int *a, int n, int k) {
        int s = 0;
        for (int i = 0; i < n; i++) {
            int v = a[i];
            if (v & 1) s += v * k; else s -= (v >> 2) + 7;
            if (v > 1000) s ^= 0xdeadbeef;
            a[i] = s + i;
        }
        return s * 2654435761u + k;
    }
    """
    d = tempfile.mkdtemp()
    c = os.path.join(d, "t.c")
    o = os.path.join(d, "t.o")
    open(c, "w").write(src)
    subprocess.run(["gcc", "-O2", "-c", "-fno-asynchronous-unwind-tables", c, "-o", o],
                   check=True, capture_output=True)
    return o, "work"


def region_from_symbol(objfile, sym):
    """Return (raw_bytes, true_boundaries set) for function `sym` from objdump."""
    out = subprocess.run([OBJDUMP, "-d", "--no-show-raw-insn", objfile],
                         capture_output=True, text=True, check=True).stdout
    full = subprocess.run([OBJDUMP, "-d", objfile], capture_output=True,
                          text=True, check=True).stdout
    raw = bytearray()
    bounds = set()
    in_fn = False
    base = None
    for ln in full.splitlines():
        if re.match(r"^[0-9a-f]+ <%s>:" % re.escape(sym), ln):
            in_fn = True
            base = int(ln.split()[0], 16)
            continue
        if in_fn:
            if ln.strip() == "" or re.match(r"^[0-9a-f]+ <", ln):
                break
            m = LINE.match(ln)
            if not m:
                continue
            addr = int(m.group(1), 16)
            by = bytes(int(x, 16) for x in m.group(2).split())
            bounds.add(addr - base)
            raw += by
    bounds.add(len(raw))
    return bytes(raw), bounds


def objdump_len_at(raw, k):
    """Authoritative length of the first instruction when decoding from offset k."""
    d = tempfile.mkdtemp()
    f = os.path.join(d, "r.bin")
    open(f, "wb").write(raw)
    out = subprocess.run([OBJDUMP, "-D", "-b", "binary", "-m", "i386:x86-64",
                          "--start-address=%d" % k, f], capture_output=True,
                         text=True, check=True).stdout
    for ln in out.splitlines():
        m = LINE.match(ln)
        if m and int(m.group(1), 16) == k:
            nby = len(m.group(2).split())
            # (bad) or data objdump may emit 1-byte ".byte"; treat as length 1
            return nby
    return None


def analyze(raw, bounds, label):
    N = len(raw)
    # authoritative per-offset decode length (objdump), once per offset
    olen = [objdump_len_at(raw, k) for k in range(N)]
    # from-scratch decoder length, per offset (for the agreement check)
    dlen = []
    for k in range(N):
        L, _ = lendec.decode_len(raw, k)
        dlen.append(L)

    # lendec agreement vs objdump (C09-3), split: on the compiler-intended
    # boundaries (real instructions) vs on ALL offsets (incl. arbitrary
    # misaligned bytes, which hit opcodes outside lendec's scoped table).
    comparable = [k for k in range(N) if olen[k] is not None]
    agree = sum(1 for k in comparable if dlen[k] == olen[k])
    undec = sum(1 for k in range(N) if dlen[k] is None)
    bcmp = [k for k in bounds if k < N and olen[k] is not None]
    bagree = sum(1 for k in bcmp if dlen[k] == olen[k])

    # resync: from each misaligned start k (not a true boundary), follow the
    # authoritative (objdump) decode chain until it lands on a TRUE boundary.
    # resync length in bytes and in instructions (C09-4 definition).
    resyncs = []           # (start, bytes_to_resync, insns_to_resync)
    never = 0
    for k in range(N):
        if k in bounds or olen[k] is None:
            continue
        pos, insns = k, 0
        while pos < N and olen[pos] is not None and insns < N:
            pos += olen[pos]
            insns += 1
            if pos in bounds:
                resyncs.append((k, pos - k, insns))
                break
        else:
            never += 1
    return {
        "label": label, "N": N, "nbounds": len(bounds),
        "agree": agree, "comparable": len(comparable), "undec": undec,
        "bagree": bagree, "bcmp": len(bcmp),
        "resyncs": resyncs, "never": never,
        "olen": olen, "dlen": dlen, "bounds": sorted(bounds),
    }


def stats(resyncs):
    import statistics as st
    by_insn = sorted(r[2] for r in resyncs)
    by_byte = sorted(r[1] for r in resyncs)
    if not by_insn:
        return {}
    return {
        "n": len(by_insn),
        "insn_median": st.median(by_insn), "insn_max": by_insn[-1],
        "insn_le2_frac": sum(1 for x in by_insn if x <= 2) / len(by_insn),
        "byte_median": st.median(by_byte), "byte_max": by_byte[-1],
    }


def emit_html(results, path):
    blocks = []
    for r in results:
        bset = set(r["bounds"])
        cells = []
        for k in range(r["N"]):
            cls = "bound" if k in bset else ("undec" if r["olen"][k] is None else "mis")
            cells.append(f'<i class="{cls}" title="off {k} objlen={r["olen"][k]} declen={r["dlen"][k]}"></i>')
        s = stats(r["resyncs"])
        blocks.append({"label": r["label"], "cells": "".join(cells), "stats": s,
                       "resync_hist": _hist([x[2] for x in r["resyncs"]])})
    data = json.dumps([{"label": b["label"], "stats": b["stats"],
                        "resync_insn_hist": b["resync_hist"]} for b in blocks])
    html = ["<!doctype html><meta charset=utf-8><title>x86 superset lattice</title>",
            "<style>body{font:14px system-ui;background:#0b0d12;color:#e6e8ee;margin:24px}",
            "i{display:inline-block;width:9px;height:14px;margin:1px}",
            ".bound{background:#3fb950}.mis{background:#30363d}.undec{background:#f85149}",
            "h2{margin:18px 0 6px}code{color:#7ee787}</style>",
            "<h1>x86-64 superset-decode lattice</h1>",
            "<p>Each cell = one byte offset. ",
            "<i class=bound></i> true (compiler-intended) instruction boundary; ",
            "<i class=mis></i> a byte that starts a misaligned decode; ",
            "<i class=undec></i> undecodable-by-lendec. Data embedded below for checking.</p>"]
    for b in blocks:
        s = b["stats"]
        html.append(f"<h2>{b['label']}</h2><div>{b['cells']}</div>")
        if s:
            html.append(f"<p>resync: n={s['n']} median={s['insn_median']} insns "
                        f"(≤2 insns: {s['insn_le2_frac']*100:.0f}%), max={s['insn_max']} insns; "
                        f"byte median={s['byte_median']}, max={s['byte_max']}</p>")
    html.append(f"<script id=data type=application/json>{data}</script>")
    open(path, "w").write("\n".join(html))


def _hist(xs):
    h = {}
    for x in xs:
        h[x] = h.get(x, 0) + 1
    return dict(sorted(h.items()))


def main():
    print("=" * 76)
    print("x86-64 superset-decode lattice + resync statistics")
    print("(authoritative per-offset decode = objdump; lendec agreement reported)")
    print('Linn & Debray CCS 2003 §3.1: errors "resynchronize quite quickly - often')
    print(' within just one or two instructions" -- quantified here on real x86-64.')
    print("=" * 76)
    fail = 0

    def v(name, cond, detail=""):
        nonlocal fail
        if not cond:
            fail = 1
        print(f"VERDICT {'PASS' if cond else 'FAIL'}: {name}" + (f"  [{detail}]" if detail else ""))

    results = []
    # C09-4 ground truth: a self-built -O2 function with symbols.
    obj, sym = build_target()
    raw, bounds = region_from_symbol(obj, sym)
    r1 = analyze(raw, bounds, f"self-built work() [-O2, {len(raw)}B, ground truth = symbols]")
    results.append(r1)
    # a real /usr/bin binary (reference decode caveat, C09-4).
    usr = "/usr/bin/true"
    ur, ub = region_from_symbol_elf(usr)
    r2 = analyze(ur, ub, f"/usr/bin/true .text head [{len(ur)}B, reference-decode (stripped caveat)]")
    results.append(r2)

    for r in results:
        s = stats(r["resyncs"])
        print(f"\n{r['label']}")
        print(f"  lendec vs objdump on TRUE boundaries (real instrs): {r['bagree']}/{r['bcmp']}; "
              f"on ALL offsets: {r['agree']}/{r['comparable']} "
              f"({100*r['agree']//max(r['comparable'],1)}%); undecodable-by-lendec: {r['undec']} "
              f"(all deferred to objdump, which powers the lattice/stats)")
        print(f"  misaligned starts that resync: {len(r['resyncs'])}; never-resync: {r['never']}")
        if s:
            print(f"  resync length: median {s['insn_median']} instrs, max {s['insn_max']}; "
                  f"within ≤2 instrs: {100*s['insn_le2_frac']:.0f}%  (bytes: median {s['byte_median']})")

    emit_html(results, "lattice.html")
    print("\nwrote lattice.html (machine-checkable: data embedded in <script id=data>)")

    # ---- verdicts ----
    r1s = stats(r1["resyncs"])
    v("lendec sizes EVERY compiler-intended instruction correctly (true boundaries)",
      r1["bcmp"] and r1["bagree"] == r1["bcmp"],
      f"true-boundary agreement {r1['bagree']}/{r1['bcmp']}; all-offset "
      f"{r1['agree']}/{r1['comparable']} ({100*r1['agree']//max(r1['comparable'],1)}% -- misaligned "
      f"bytes hit opcodes outside lendec's scoped table; those offsets defer to objdump)")
    v("most misaligned decodes RESYNC (few or none run off forever)",
      r1["resyncs"] and r1["never"] <= max(1, len(r1["resyncs"]) // 20),
      f"resync={len(r1['resyncs'])} never={r1['never']}")
    v("resync is quick: median ≤ 3 instructions (quantifies Linn & Debray §3.1)",
      r1s and r1s["insn_median"] <= 3,
      f"median={r1s.get('insn_median')} insns, ≤2-instr fraction={r1s.get('insn_le2_frac',0):.2f}")
    v("the HTML lattice embeds the data for checking (C09-5)",
      os.path.exists("lattice.html") and b"<script id=data" in open("lattice.html", "rb").read(),
      "lattice.html")
    # also confirm the real-binary analysis ran and resynced
    v("real /usr/bin/true region also analysed and resynchronises",
      r2["resyncs"] and (not stats(r2["resyncs"]) or stats(r2["resyncs"])["insn_median"] <= 5),
      f"resync={len(r2['resyncs'])}")

    print("\n" + ("ALL VERDICTS PASS" if fail == 0 else "SOME VERDICTS FAILED"))
    return fail


def region_from_symbol_elf(path, maxbytes=160):
    """Grab the first ~maxbytes of an ELF's .text as a raw region + the objdump
    linear-sweep boundaries (the 'reference decode', not true ground truth for a
    stripped binary -- C09-4 caveat)."""
    out = subprocess.run([OBJDUMP, "-d", "-j", ".text", path], capture_output=True,
                         text=True, check=True).stdout
    raw = bytearray()
    bounds = set()
    base = None
    for ln in out.splitlines():
        m = LINE.match(ln)
        if not m:
            continue
        addr = int(m.group(1), 16)
        if base is None:
            base = addr
        by = bytes(int(x, 16) for x in m.group(2).split())
        if addr - base >= maxbytes:
            break
        bounds.add(addr - base)
        raw += by
    bounds.add(len(raw))
    return bytes(raw), bounds


if __name__ == "__main__":
    sys.exit(main())
