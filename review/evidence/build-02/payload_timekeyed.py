#!/usr/bin/env python3
"""Reviewer check for BUILD-02 (REVIEW-01 §9: time-keyed baseline must be the
STRONGEST available). Same captures, same attribution rule as attribute.py
(latest patch rdtsc <= exec time), but the PT clock is reconstructed from the
MTC *payloads* (CTC[N+7:N]) anchored at the TSC+TMA pair -- as a real decoder
does -- instead of counting MTC packets. usage: payload_timekeyed.py PARTDIR WORKDIR
"""
import sys
sys.path.insert(0, sys.argv[1])
import ptdecode, attribute

def clocked_execs(buf, period, numer, denom):
    tsc0 = None; ctc = None; base_ctc = None; out = []
    for off, k, p in ptdecode.iter_packets(buf):
        if k == "tsc":
            tsc0 = p
        elif k == "tma" and tsc0 is not None:
            ctc = p[0]; base_ctc = ctc; base_tsc = tsc0
        elif k == "mtc" and ctc is not None:
            lo, width = period, 8
            old = (ctc >> lo) & 0xff
            new = p & 0xff
            step = (new - old) & 0xff              # periods elapsed (mod 256)
            ctc = (ctc & ~((0xff << lo))) | (new << lo)
            if new < old:                          # bits [N+7:N] wrapped
                ctc += 1 << (lo + width)
            ctc &= ~((1 << lo) - 1)                # MTC marks a period boundary
        elif k == "ptw" and (p & 0xFFFF0000) == ptdecode.EXEC_TAG:
            t = None if ctc is None else base_tsc + (ctc - base_ctc) * numer // denom
            out.append((p & 0xFFFF, t))
    return out

part, work = sys.argv[1], sys.argv[2]
for timing in ("coarse", "fine"):
    for d in (0, 100, 1000, 10000, 100000, 1000000):
        o = f"{work}/{timing}-{d}"
        sb = {k: int(v) for ln in open(f"{o}/sideband.txt") for tok in ln.split() if "=" in tok
              for k, v in [tok.split("=", 1)] if v.lstrip("-").isdigit()}
        buf = open(f"{o}/trace.pt", "rb").read()
        patches = attribute.read_patchlog(f"{o}/patchlog.csv")
        ex = clocked_execs(buf, sb["mtc_period"], sb["cpuid15_ebx_numer"], sb["cpuid15_eax_denom"])
        ok = sum(1 for v, t in ex if t is not None and max([pv for pv, pt in patches if pt <= t], default=None) == v)
        theirs = attribute.attribute(o)["timekeyed"]
        print(f"{timing:6} delay={d:<8} execs={len(ex):>2}  author count-based time-keyed ok/wrong={theirs[0]}/{theirs[1]:<3}"
              f"  reviewer PAYLOAD-based time-keyed ok/wrong={ok}/{len(ex)-ok}")
