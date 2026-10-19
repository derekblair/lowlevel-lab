#!/usr/bin/env python3
"""resync_survey.py — reviewer's independent resync-length survey for BUILD-05 (C09).

Not author code and not a fix: evidence for whether the build's headline
("median 1 instruction, ~80% within <=2", one 126-byte function) generalises.

usage: python3 -I resync_survey.py FILE[:label[:CAP]] ...
  CAP: analyse only .text, cut at the last instruction start <= CAP bytes.
  env SURVEY_MINSEC (default 32): skip smaller sections; SURVEY_MAXCHAIN (default 64).
Each FILE's code sections (objdump -d -w -z) are one region per section.
Boundaries = objdump's linear sweep: GROUND TRUTH for gcc-built .o files (no
inline data on x86-64), only a REFERENCE decode for stripped binaries.
Per-offset first-instruction length: one objdump call per section on a blob of
windows  section[k:k+15] + 16 x 0x90  (any insn <= 15 bytes, so the sweep
re-enters single-byte NOPs and lands on the next window start; checked against
per-offset objdump calls in windowed-decode-check.txt).
Resync, as in superset.py: from each non-boundary offset follow the chain
k -> k+len until it lands on a boundary; count instructions and bytes.
Chains that pass through an objdump '(bad)' are reported separately.
"""
import os, re, statistics as st, subprocess, sys, tempfile

LINEW = re.compile(r"^\s*([0-9a-f]+):\t((?:[0-9a-f]{2} )+)\s*\t?(.*)$")
SEC = re.compile(r"^Disassembly of section (\S+):")
W = 31
MINSEC = int(os.environ.get("SURVEY_MINSEC", "32"))      # skip smaller sections
MAXCHAIN = int(os.environ.get("SURVEY_MAXCHAIN", "64"))  # chain length cap


def sections(path):
    out = subprocess.run(["objdump", "-d", "-w", "-z", path], capture_output=True, text=True, check=True).stdout
    secs, cur = {}, None
    for ln in out.splitlines():
        m = SEC.match(ln)
        if m:
            cur = secs.setdefault(m.group(1), {"raw": bytearray(), "starts": [], "base": None}); continue
        m = LINEW.match(ln)
        if m and cur is not None:
            a = int(m.group(1), 16)
            if cur["base"] is None:
                cur["base"] = a
            if a - cur["base"] != len(cur["raw"]):   # gap (should not happen with -z)
                raise SystemExit(f"{path}: non-contiguous decode at {a:#x}")
            cur["starts"].append(a - cur["base"])
            cur["raw"] += bytes(int(x, 16) for x in m.group(2).split())
    return secs


def window_decode(raw):
    blob = b"".join(raw[k:k + 15].ljust(15, b"\x90") + b"\x90" * 16 for k in range(len(raw)))
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "w.bin"); open(f, "wb").write(blob)
        out = subprocess.run(["objdump", "-D", "-w", "-z", "-b", "binary", "-m", "i386:x86-64", f],
                             capture_output=True, text=True, check=True).stdout
    ln_, bad = {}, {}
    for ln in out.splitlines():
        m = LINEW.match(ln)
        if m:
            a = int(m.group(1), 16)
            if a % W == 0:
                ln_[a // W] = len(m.group(2).split()); bad[a // W] = "(bad)" in m.group(3) or m.group(3).startswith(".byte")
    return ln_, bad


def survey(raw, starts):
    N, B = len(raw), set(starts) | {len(raw)}
    L, bad = window_decode(raw)
    res = []
    for k in range(N):
        if k in B:
            continue
        pos, n, hit_bad = k, 0, False
        while pos < N and n < MAXCHAIN:
            hit_bad |= bad[pos]; pos += L[pos]; n += 1
            if pos in B:
                res.append((n, pos - k, hit_bad)); break
    return res, (N - len(set(starts))) - len(res)


def fmt(rs, never, tag):
    ins = sorted(r[0] for r in rs)
    if not ins:
        return f"{tag}: none"
    q = st.quantiles(ins, n=4) if len(ins) > 1 else [ins[0]] * 3
    le = lambda t: sum(x <= t for x in ins) / len(ins)
    return (f"{tag}: n={len(ins)} never={never} median={st.median(ins)} q1={q[0]} q3={q[2]} "
            f"P(<=1)={le(1):.2f} P(<=2)={le(2):.2f} P(<=3)={le(3):.2f} max={ins[-1]} "
            f"byte_median={st.median(sorted(r[1] for r in rs))}")


def main():
    pooled = {}
    for spec in sys.argv[1:]:
        path, _, rest = spec.partition(":")
        label, _, caps = rest.partition(":")
        label = label or "file"
        cap = int(caps) if caps else None   # FILE:label:CAP = .text only, cut at an insn start <= CAP
        for name, s in sections(path).items():
            if len(s["raw"]) < MINSEC:
                continue
            if cap is not None:
                if name != ".text":
                    continue
                cut = max(o for o in s["starts"] if o <= cap) if len(s["raw"]) > cap else len(s["raw"])
                s = {"raw": s["raw"][:cut], "starts": [o for o in s["starts"] if o < cut], "base": s["base"]}
            rs, never = survey(bytes(s["raw"]), s["starts"])
            print(f"{os.path.basename(path)} {name} [{label}] {len(s['raw'])}B insns={len(s['starts'])}")
            print("   " + fmt(rs, never, "all chains"))
            print("   " + fmt([r for r in rs if not r[2]], never, "chains w/o (bad)"))
            p = pooled.setdefault(label, ([], [0]))
            p[0].extend(rs); p[1][0] += never
    for label, (rs, nv) in pooled.items():
        print(f"POOLED [{label}] " + fmt(rs, nv[0], "all chains"))
        print(f"POOLED [{label}] " + fmt([r for r in rs if not r[2]], nv[0], "chains w/o (bad)"))


if __name__ == "__main__":
    main()
