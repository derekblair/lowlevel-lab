#!/usr/bin/env python3
"""round2_tests.py — reviewer's BUILD-04 round-2 tests against the fix-round
sanitizer (author modules imported READ-ONLY from the gate-commit clone).

usage: python3 -I round2_tests.py CLONE_PART_DIR

Kernels here are built by the REVIEWER (own builder below, author encoders),
so the verdict under test is the author's interp()+Machine reading programs it
has never seen. Each line: test | architectural expectation | model result.
"""
import inspect, struct, sys

sys.path.insert(0, sys.argv[1])
import sanitize as S            # also installs A.svc
from icache_model import Config, Machine
A = S.A
OLD, NEW, NEW2 = S.SLOT_OLD, S.SLOT_NEW, 0x33


def li(reg, val):               # load a 32-bit immediate
    return A.movz(reg, val & 0xFFFF) + A.movk(reg, (val >> 16) & 0xFFFF, 16)


def word(insn):
    return int.from_bytes(insn, "little")


def build(actions):
    """actions: list of ('warm'|'run'|'dsb'|'isb'), ('store', imm16),
    ('dc'|'ic', byte_offset_from_slot)."""
    def entry(slot):
        c = li("x9", slot)
        for a in actions:
            k = a[0]
            if k in ("warm", "run"): c += A.blr("x9")
            elif k == "store":       c += li("x10", word(A.movz("x0", a[1]))) + A.strw_imm("w10", "x9", 0)
            elif k == "dc":          c += li("x11", slot + a[1]) + A.dc_cvau("x11")
            elif k == "ic":          c += li("x11", slot + a[1]) + A.ic_ivau("x11")
            elif k == "dsb":         c += A.dsb_ish()
            elif k == "isb":         c += A.isb()
        return c + A.movz("x8", S.EXIT_NR) + A.svc()
    n = len(entry(S.CODEBASE))
    slot = S.CODEBASE + n
    return entry(slot) + A.movz("x0", OLD) + A.ret(), 0, slot


def run(actions, cfg):
    code, e, slot = build(actions)
    x0, m = S.interp(code, e, slot, cfg)
    fresh, miss = m.diagnose(slot - S.CODEBASE)
    q = S.run_qemu(code, e)
    tag = {OLD: "OLD(stale)", NEW: "NEW", NEW2: "NEW2"}.get(x0, hex(x0))
    return tag, miss, q, slot


C00 = Config(idc=0, dic=0, iminline=64, dminline=64)
FULL = [("dc", 0), ("dsb",), ("ic", 0), ("dsb",), ("isb",)]
tests = [
    ("T0 control: warm; STR; DC;DSB;IC;DSB;ISB; run", "fresh",
     [("warm",), ("store", NEW)] + FULL + [("run",)]),
    ("T1 maintenance BEFORE the store: warm; DC;DSB;IC;DSB;ISB; STR; run", "NOT guaranteed (needs maintenance after STR)",
     [("warm",)] + FULL + [("store", NEW), ("run",)]),
    ("T2 second patch unmaintained: warm; STR NEW; full maint; STR NEW2; run", "NEW2 NOT guaranteed (2nd STR unmaintained)",
     [("warm",), ("store", NEW)] + FULL + [("store", NEW2), ("run",)]),
    ("T3 DC before the store, rest after: warm; DC; STR; DSB;IC;DSB;ISB; run", "NOT guaranteed (new bytes never cleaned, IDC=0)",
     [("warm",), ("dc", 0), ("store", NEW), ("dsb",), ("ic", 0), ("dsb",), ("isb",), ("run",)]),
    ("T4 omit DSB1 (DC; IC; DSB; ISB): which step is named?", "stale; the missing step is the DSB between DC and IC",
     [("warm",), ("store", NEW), ("dc", 0), ("ic", 0), ("dsb",), ("isb",), ("run",)]),
]
print(f"interp signature: {inspect.signature(S.interp)}  (no recipe argument: {'maint' not in str(inspect.signature(S.interp))})")
print(f"{'test':72} | {'architecture':48} | model x0 / first-missing | qemu")
for name, expect, acts in tests:
    tag, miss, q, slot = run(acts, C00)
    print(f"{name:72} | {expect:48} | {tag} / {miss} | qemu={q}")

# T5: wrong-stride flush loop, unrolled (the interpreter has no branches).
# HW line = 64 B. The program strides by 128 (a line size read on another core).
# Region = [slot_line-64, slot_line+192): stride 128 hits slot_line-64, slot_line+64,
# skipping the slot's own line. Stride 64 covers it.
print("\nT5 line-size mismatch as a real strided flush (unrolled loop), IDC=0,DIC=0, Iline=Dline=64:")
for stride in (64, 128):
    def acts_for(slot_mod):
        lo = -64 - slot_mod            # start one line below the slot's line
        offs = list(range(lo, lo + 256, stride))
        return ([("warm",), ("store", NEW)] + [("dc", o) for o in offs] + [("dsb",)] +
                [("ic", o) for o in offs] + [("dsb",), ("isb",), ("run",)])
    # the slot's offset within its 64-B line depends on the code length; solve by fixpoint
    mod = 0
    for _ in range(4):
        code, e, slot = build(acts_for(mod))
        mod = (slot - S.CODEBASE) % 64
    tag, miss, q, slot = run(acts_for(mod), C00)
    print(f"   stride {stride:3}: slot @+{slot - S.CODEBASE:#x} (line +{(slot - S.CODEBASE) // 64 * 64:#x}) -> {tag} / missing={miss} | qemu={q}")
