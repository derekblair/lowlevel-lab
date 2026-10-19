#!/usr/bin/env python3
"""round3_tests.py — reviewer's NEW probes of the fix-round-2 (anchored) model.
usage: python3 -I round3_tests.py CLONE_PART_DIR
Reviewer-built kernels (own builder; author encoders + interp + Machine, read-only).
Each row: kernel | config | architectural expectation | model x0 / missing / explain | qemu."""
import sys
sys.path.insert(0, sys.argv[1])
import sanitize as S
from icache_model import Config
A = S.A
OLD, NEW, NEW2 = S.SLOT_OLD, S.SLOT_NEW, 0x33


def li(reg, val):
    return A.movz(reg, val & 0xFFFF) + A.movk(reg, (val >> 16) & 0xFFFF, 16)


def build(actions):
    """('warm'|'run'|'dsb'|'isb'), ('store', imm16[, delta]), ('dc'|'ic', delta)"""
    def entry(slot):
        c = li("x9", slot)
        for a in actions:
            k = a[0]
            if k in ("warm", "run"): c += A.blr("x9")
            elif k == "store":
                c += li("x10", int.from_bytes(A.movz("x0", a[1]), "little"))
                d = a[2] if len(a) > 2 else 0
                c += li("x12", slot + d) + A.strw_imm("w10", "x12", 0)
            elif k in ("dc", "ic"):
                c += li("x11", slot + a[1]) + (A.dc_cvau("x11") if k == "dc" else A.ic_ivau("x11"))
            elif k == "dsb": c += A.dsb_ish()
            elif k == "isb": c += A.isb()
        return c + A.movz("x8", S.EXIT_NR) + A.svc()
    slot = S.CODEBASE + len(entry(S.CODEBASE))
    code = entry(slot) + A.movz("x0", OLD) + A.ret() + b"\0" * 4096   # room for far stores
    return code, 0, slot


def run(acts, cfg):
    code, e, slot = build(acts)
    x0, m = S.interp(code, e, slot, cfg)
    fresh, miss = m.diagnose(slot - S.CODEBASE)
    q = S.run_qemu(code, e)
    xc, _ = S.interp(code, e, slot, cfg, coherent=True)
    tag = {OLD: "OLD", NEW: "NEW", NEW2: "NEW2"}.get(x0, hex(x0))
    return tag, fresh, miss, m.explain(slot - S.CODEBASE), q, xc, slot


C00 = Config(0, 0, 64, 64)
C10 = Config(1, 0, 64, 64)
C11 = Config(1, 1, 64, 64)
FULL = [("dc", 0), ("dsb",), ("ic", 0), ("dsb",), ("isb",)]
W, P = [("warm",)], [("store", NEW)]
cases = [
    ("P1 unrelated store (+2048, other line) after full maint", C00, "FRESH", W + P + FULL + [("store", NEW2, 2048), ("run",)]),
    ("P2 same-line other-word store (+8) after full maint", C00, "FRESH (slot word maintained)", W + P + FULL + [("store", NEW2, 8), ("run",)]),
    ("P4 ISB before the IC's DSB: DC;DSB;IC;ISB;DSB", C00, "STALE (ISB must follow DSB2)", W + P + [("dc", 0), ("dsb",), ("ic", 0), ("isb",), ("dsb",), ("run",)]),
    ("P5 interim run before ISB, then ISB, run", C00, "final FRESH", W + P + [("dc", 0), ("dsb",), ("ic", 0), ("dsb",), ("run",), ("isb",), ("run",)]),
    ("P6 IC before DC: IC;DSB;DC;DSB;ISB", C00, "STALE (IC must follow the clean)", W + P + [("ic", 0), ("dsb",), ("dc", 0), ("dsb",), ("isb",), ("run",)]),
    ("P7 full maintenance twice", C00, "FRESH", W + P + FULL + FULL + [("run",)]),
    ("P8 never warmed: STR; full; run", C00, "FRESH", P + FULL + [("run",)]),
    ("P9 never warmed, no maintenance: STR; run", C00, "STALE (not guaranteed)", P + [("run",)]),
    ("P10 IDC=DIC=1: STR; DSB; ISB", C11, "FRESH (Linux IDC+DIC path)", W + P + [("dsb",), ("isb",), ("run",)]),
    ("P11 IDC=DIC=1: STR; ISB; DSB", C11, "STALE (ISB before the DSB)", W + P + [("isb",), ("dsb",), ("run",)]),
    ("P12 IDC=1,DIC=0: STR; DSB; IC; DSB; ISB", C10, "FRESH (Linux IDC path)", W + P + [("dsb",), ("ic", 0), ("dsb",), ("isb",), ("run",)]),
    ("P13 IDC=1,DIC=0: STR; IC; DSB; ISB (no DSB before IC)", C10, "STALE (dsb missing before IC)", W + P + [("ic", 0), ("dsb",), ("isb",), ("run",)]),
    ("P14 DC/IC on a different address in the slot's line (+32)", C00, "FRESH (same 64-B line)", W + P + [("dc", 32), ("dsb",), ("ic", 32), ("dsb",), ("isb",), ("run",)]),
    ("P15 re-patch then full maint again (NEW2 maintained)", C00, "FRESH with NEW2", W + P + FULL + [("store", NEW2)] + FULL + [("run",)]),
]
print(f"{'probe':58} {'cfg':12} {'architecture':32} | model x0 fresh/missing | explain | qemu | coherent")
for name, cfg, expect, acts in cases:
    tag, fr, mi, why, q, xc, slot = run(acts, cfg)
    print(f"{name:58} {cfg.name():12} {expect:32} | {tag} {'fresh' if fr else 'STALE!' + str(mi)} | {why} | qemu={q} | coh={xc}")

# P3: I-line smaller than the D-line (IminLine=32 B, DminLine=64 B): a JIT that
# strides IC by the D-line size (64) skips every other 32-B I-line. The slot is
# pushed into an ODD 32-B I-line by k leading DSBs (4 B each; they precede the
# store, so the anchored rule ignores them); the flush region starts on the
# 64-B line below the slot's D-line, so stride-64 IC addresses hit only EVEN
# 32-B I-lines.
print("\nP3 Iline=32 < Dline=64, IDC=0,DIC=0: DC stride 64; IC stride 64 vs 32, slot in an ODD 32-B I-line")
cfg = Config(0, 0, dminline=64, iminline=32)
for istride in (64, 32):
    def acts(k, lo):
        d_offs = list(range(lo, lo + 256, 64)); i_offs = list(range(lo, lo + 256, istride))
        return ([("dsb",)] * k + W + P + [("dc", o) for o in d_offs] + [("dsb",)]
                + [("ic", o) for o in i_offs] + [("dsb",), ("isb",), ("run",)])
    for k in range(16):                       # slot offset = f(k) only (li is fixed-length)
        code, e, slot = build(acts(k, 0)); so = slot - S.CODEBASE
        if (so // 32) % 2 == 1:
            break
    lo = -(so % 64) - 64                      # 64-B aligned, one D-line below the slot's
    code, e, slot2 = build(acts(k, lo)); assert slot2 == slot
    hit = sorted({(so + o) - (so + o) % 32 for o in range(lo, lo + 256, istride)})
    tag, fr, mi, why, q, xc, _ = run(acts(k, lo), cfg)
    print(f"   IC stride {istride:2}: slot @+{so:#x} in 32-B I-line +{so - so % 32:#x} ({'odd' if (so // 32) % 2 else 'even'}); "
          f"IC lines hit {[hex(h) for h in hit]} -> {tag} {'fresh' if fr else 'STALE!' + str(mi)} | {why} | qemu={q}")
