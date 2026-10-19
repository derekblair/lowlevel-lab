#!/usr/bin/env python3
"""sanitize.py — the ifetch-sanitizer (whole-program, program-driven).

A self-modifying AArch64 kernel is run through a small A64 interpreter whose
self-modified slot is fetched THROUGH the cache model (icache_model.Machine).
The interpreter decodes the STR / DC CVAU / IC IVAU / DSB / ISB the program
actually executes and applies them to the model; the verdict (fresh vs stale,
and which maintenance step is missing) therefore depends on the PROGRAM, not on
any recipe (REVIEW-04 B1). The barrier rule matches the Arm requirement and the
Linux implementation (B2); the architecture text is quoted below (B3); and the
model's coherent mode is checked against qemu-aarch64 on every kernel (B4).
ORDER MATTERS (round 2, B5): the required sequence is anchored after the latest
store to the slot, so flush-then-write, a second unmaintained patch, and a DC
issued before the STR are all diagnosed STALE with a named cause.

All staleness is MODEL output (R10); the same kernels run FRESH under
qemu-aarch64 (SMC-coherent). a64asm encoders are differential-tested vs
aarch64-linux-gnu-as. Python stdlib only.
"""
import struct
import subprocess
import sys
import tempfile
import os
import a64asm as A
from icache_model import Config, Machine

BASE = 0x400000
HDR = 128                     # ehdr(64) + phdr(56) + 8 pad: the code base is 64-B aligned,
CODEBASE = BASE + HDR         # so the model's line partition IS the address-aligned one
SLOT_OLD = 0x11
SLOT_NEW = 0x22
EXIT_NR = 93

# B3 — verbatim architecture / reference text (fetched as data; see
# research/raw and the REVIEW-04 evidence):
ARM_REF = """\
Arm CTR_EL0 (DDI 0487, AArch64-ctr_el0; Arm XML build 26/03/2024), verbatim:
  IDC=1: "Data cache clean to the Point of Unification is not required for
          instruction to data coherence."
  DIC=1: "Instruction cache invalidation to the Point of Unification is not
          required for data to instruction coherence."
  "If CTR_EL0.DIC is 1 then the value reported in [IDC] must also be 1."
Canonical modify-execute sequence (SECONDARY: DDI 0487G.a B2.2.5 as quoted by
  Rutland's LKML post and patent US11210222; not checked against the manual here):
  modifying PE: DC CVAU,Xn ; DSB ISH ; IC IVAU,Xn ; DSB ISH ; and each executing
  PE: ISB.
Linux arch/arm64/mm/cache.S caches_clean_inval_pou_macro: on ARM64_HAS_CACHE_IDC
  the DC loop is skipped but a 'dsb ishst' is STILL issued; on ARM64_HAS_CACHE_DIC
  the IC loop is skipped but an 'isb' is STILL issued. => the barriers are kept
  even when IDC/DIC excuse the cache op; that is the rule this model applies."""

A.svc = lambda: struct.pack("<I", 0xD4000001)   # SVC #0 (a64asm has no svc)


# ---- kernel construction ------------------------------------------------
# A kernel is an A64 program built from an ordered action list:
#   ('warm',) / ('run',)  BLR to the slot (movz x0,#imm ; ret)
#   ('store', imm)        STR the instruction word `movz x0,#imm` into the slot
#   ('dc'|'ic', delta)    DC CVAU / IC IVAU at slot+delta
#   ('dsb',) / ('isb',)
# The verdict is read back from the EXECUTED instructions, never from the list.
def _li(reg, val):                                     # fixed length: movz + movk
    return A.movz(reg, val & 0xFFFF) + A.movk(reg, (val >> 16) & 0xFFFF, 16)


def build_program(actions):
    slot = A.movz("x0", SLOT_OLD) + A.ret()            # movz x0,#OLD ; ret

    def entry(slot_vaddr):
        c = _li("x9", slot_vaddr)
        for a in actions:
            k = a[0]
            if k in ("warm", "run"):
                c += A.blr("x9")
            elif k == "store":
                c += _li("x10", int.from_bytes(A.movz("x0", a[1]), "little"))
                c += A.strw_imm("w10", "x9", 0)        # STR new instruction word (SMC)
            elif k in ("dc", "ic"):                    # always via x11: length is
                c += _li("x11", slot_vaddr + a[1])     # independent of the delta
                c += A.dc_cvau("x11") if k == "dc" else A.ic_ivau("x11")
            elif k == "dsb":
                c += A.dsb_ish()
            elif k == "isb":
                c += A.isb()
        return c + A.movz("x8", EXIT_NR) + A.svc()     # exit(x0)

    slot_vaddr = CODEBASE + len(entry(CODEBASE))       # entry length is value-independent
    return entry(slot_vaddr) + slot, 0, slot_vaddr


def build_kernel(maint):
    """warm; STR NEW; <maint steps on the slot's line>; run."""
    return build_program([("warm",), ("store", SLOT_NEW)]
                         + [(s, 0) if s in ("dc", "ic") else (s,) for s in maint]
                         + [("run",)])


def build_strided(stride, line=64, span=4):
    """The line-size class as a real (unrolled) JIT flush loop: DC then IC every
    `stride` bytes over `span` lines, starting one line below the slot's line.
    stride == line covers the slot's line; stride 128 -- a line size read from
    another core's CTR_EL0 -- skips it on a 64-B-line core."""
    def acts(lo):
        offs = list(range(lo, lo + span * line, stride))
        return ([("warm",), ("store", SLOT_NEW)] + [("dc", o) for o in offs] + [("dsb",)]
                + [("ic", o) for o in offs] + [("dsb",), ("isb",), ("run",)])
    _, _, slot = build_program(acts(-line))            # length does not depend on lo
    sl = slot - CODEBASE
    code, e, s2 = build_program(acts(-line - sl % line))   # lo = one line below the slot's line
    assert s2 == slot
    return code, e, s2


# ---- decoder for the subset ----
def decode(w):
    if (w & 0xFF800000) == 0xD2800000: return "movz", (w & 31, (w >> 5) & 0xFFFF, ((w >> 21) & 3) * 16)
    if (w & 0xFF800000) == 0xF2800000: return "movk", (w & 31, (w >> 5) & 0xFFFF, ((w >> 21) & 3) * 16)
    if (w & 0xFFC00000) == 0xB9000000: return "strw", (w & 31, (w >> 5) & 31, ((w >> 10) & 0xFFF) * 4)
    if (w & 0xFFFFFC1F) == 0xD63F0000: return "blr", ((w >> 5) & 31,)
    if (w & 0xFFFFFC1F) == 0xD65F0000: return "ret", ((w >> 5) & 31,)
    if w == 0xD4000001: return "svc", ()
    if (w & 0xFFFFFFE0) == 0xD50B7B20: return "dc", (w & 31,)     # DC CVAU, Xt
    if (w & 0xFFFFFFE0) == 0xD50B7520: return "ic", (w & 31,)     # IC IVAU, Xt
    # DSB ISH and DSB ISHST both count as the required DSB (N8). Linux uses ISHST
    # only on the IDC path; whether ISHST suffices after DC CVAU when IDC=0 is
    # not established here (UNVERIFIED either way) -- disclosed in README.
    if w in (0xD5033B9F, 0xD5033A9F): return "dsb", ()
    if w == 0xD5033FDF: return "isb", ()
    return "?", (w,)


# ---- interpreter: executes the kernel THROUGH the model ----
def interp(code, entry_off, slot_vaddr, cfg, coherent=False):
    m = Machine(code, cfg, coherent=coherent)
    slot_off = slot_vaddr - CODEBASE
    x = [0] * 32
    pc = CODEBASE + entry_off
    link = 0
    warmed = False
    for _ in range(2000):
        off = pc - CODEBASE
        w = int.from_bytes(code[off:off + 4], "little")
        op, d = decode(w)
        if pc == slot_vaddr:                   # executing the slot (movz x0,#imm ; ret)
            if not warmed:
                m.warm(slot_off)               # first run caches OLD
                warmed = True
            sw = m.fetch_word(slot_off)        # fetch THROUGH the model (old or new)
            sop, sd = decode(sw)
            x[0] = (sd[1] << sd[2]) if sop == "movz" else (sw & 0xFF)
            pc = link
            continue
        if op == "movz": x[d[0]] = d[1] << d[2]
        elif op == "movk": x[d[0]] = (x[d[0]] & ~(0xFFFF << d[2])) | (d[1] << d[2])
        elif op == "strw":
            addr = x[d[1]] + d[2]
            word = x[d[0]] & 0xFFFFFFFF
            for i in range(4):
                m.store(addr - CODEBASE + i, (word >> (8 * i)) & 0xFF)
        elif op == "dc": m.dc(x[d[0]] - CODEBASE)
        elif op == "ic": m.ic(x[d[0]] - CODEBASE)
        elif op == "dsb": m.dsb()
        elif op == "isb": m.isb()
        elif op == "blr": link = pc + 4; pc = x[d[0]]; continue
        elif op == "ret": pc = x[d[0]]; continue
        elif op == "svc": return x[0] & 0xFF, m
        else: raise RuntimeError(f"interp: unhandled {op} @ {pc:#x} {w:#010x}")
        pc += 4
    raise RuntimeError("interp ran away")


STEP_LABEL = {"dc": "DC CVAU (clean D-cache to PoU)", "dsb": "DSB (barrier)",
              "ic": "IC IVAU (invalidate I-cache to PoU)", "isb": "ISB (synchronize fetch)"}


# ---- qemu semantic oracle ----
def elf_wrap(code, entry_off):
    EHDR, PHDR = 64, 56
    total = HDR + len(code)
    e = struct.pack("<4sBBBBB7xHHIQQQIHHHHHH", b"\x7fELF", 2, 1, 1, 0, 0,
                    2, 183, 1, CODEBASE + entry_off, EHDR, 0, 0, EHDR, PHDR, 1, 0, 0, 0)
    p = struct.pack("<IIQQQQQQ", 1, 7, 0, BASE, BASE, total, total, 0x10000)  # RWX (self-modifies)
    return e + p + b"\0" * (HDR - EHDR - PHDR) + code


def run_qemu(code, entry_off):
    with tempfile.TemporaryDirectory() as d:          # N6: no per-call litter
        path = os.path.join(d, "k")
        with open(path, "wb") as fh:
            fh.write(elf_wrap(code, entry_off))
        os.chmod(path, 0o755)
        return subprocess.run(["qemu-aarch64", path], capture_output=True).returncode


KERNELS = {
    "correct":   ["dc", "dsb", "ic", "dsb", "isb"],
    "omit-DC":   ["dsb", "ic", "dsb", "isb"],
    "omit-DSB1": ["dc", "ic", "dsb", "isb"],
    "omit-IC":   ["dc", "dsb", "dsb", "isb"],
    "omit-DSB2": ["dc", "dsb", "ic", "isb"],
    "omit-ISB":  ["dc", "dsb", "ic", "dsb"],
    "none":      [],
}
SLOT_NEW2 = 0x33
FULL = [("dc", 0), ("dsb",), ("ic", 0), ("dsb",), ("isb",)]
# B5: store ORDERING relative to the maintenance (each must be STALE with a cause)
ORDERING = {
    "control":          [("warm",), ("store", SLOT_NEW)] + FULL + [("run",)],
    "flush-then-write": [("warm",)] + FULL + [("store", SLOT_NEW), ("run",)],
    "re-patch":         [("warm",), ("store", SLOT_NEW)] + FULL
                        + [("store", SLOT_NEW2), ("run",)],
    "dc-before-str":    [("warm",), ("dc", 0), ("store", SLOT_NEW), ("dsb",),
                         ("ic", 0), ("dsb",), ("isb",), ("run",)],
}
LATEST = {"re-patch": SLOT_NEW2}       # the last value each ordering kernel stores
CONFIGS = {   # only architecturally-valid combinations ({IDC=0,DIC=1} is impossible)
    "IDC=0,DIC=0": Config(idc=0, dic=0),
    "IDC=1,DIC=0": Config(idc=1, dic=0),
    "IDC=1,DIC=1": Config(idc=1, dic=1),
}


def main():
    print("=" * 78)
    print("ifetch-sanitizer (program-driven): which cache-maintenance step is missing")
    print("Staleness is MODEL output (R10); every kernel runs FRESH under qemu-aarch64.")
    print(ARM_REF)
    print("=" * 78)
    fail = 0

    def v(name, cond, detail=""):
        nonlocal fail
        if not cond:
            fail = 1
        print(f"VERDICT {'PASS' if cond else 'FAIL'}: {name}" + (f"  [{detail}]" if detail else ""))

    p, t, fails = A.selftest()
    v(f"encoder oracle: a64asm matches aarch64-linux-gnu-as ({p}/{t})", p == t, str(fails))

    # ---- B4 semantic oracle: model COHERENT mode == qemu on EVERY kernel ----
    print("\n-- semantic oracle: model(coherent) end-state vs qemu exit, every kernel --")
    every = [(k, build_kernel(m), SLOT_NEW) for k, m in KERNELS.items()]
    every += [(k, build_program(a), LATEST.get(k, SLOT_NEW)) for k, a in ORDERING.items()]
    every += [(f"stride-{s}", build_strided(s), SLOT_NEW) for s in (64, 128)]
    oracle_ok = True
    for kname, (code, eoff, slot), want in every:
        q = run_qemu(code, eoff)
        mc, _ = interp(code, eoff, slot, CONFIGS["IDC=0,DIC=0"], coherent=True)
        same = (q == want == mc)
        oracle_ok = oracle_ok and same
        print(f"  {kname:16} qemu={q:3}  model(coherent)={mc:3}  latest-stored={want:3}  "
              f"{'ok' if same else 'MISMATCH'}")
    v(f"B4 semantic oracle: model coherent-mode == qemu == latest stored word, all {len(every)} kernels",
      oracle_ok)

    # ---- B1 program-dependence: verdict must follow the executed instructions ----
    code_a, eoff_a, slot_a = build_kernel(["dsb", "dsb", "dsb", "dsb", "dsb"])
    xa, _ = interp(code_a, eoff_a, slot_a, CONFIGS["IDC=0,DIC=0"])
    v("B1(a): a kernel whose maintenance is only DSBs is diagnosed STALE (reads the program)",
      xa == SLOT_OLD, f"x0={xa}")
    code_c, eoff_c, slot_c = build_kernel(KERNELS["correct"])
    xc, _ = interp(code_c, eoff_c, slot_c, CONFIGS["IDC=0,DIC=0"])
    v("B1(c): the correct kernel is FRESH", xc == SLOT_NEW, f"x0={xc}")

    # ---- the diagnosis matrix ----
    print("\n-- diagnosis matrix: x0 after re-running the patched slot --")
    print(f"{'kernel':10}" + "".join(f"{c:>16}" for c in CONFIGS))
    res = {}
    for kname, maint in KERNELS.items():
        code, eoff, slot = build_kernel(maint)
        row = f"{kname:10}"
        for cname, cfg in CONFIGS.items():
            x0, mach = interp(code, eoff, slot, cfg)
            fresh, missing = mach.diagnose(slot - CODEBASE)
            res[(kname, cname)] = (x0, missing)
            row += f"{('NEW' if x0 == SLOT_NEW else 'OLD!' + (missing or '?')):>16}"
        print(row)

    v("correct sequence is FRESH in every valid config",
      all(res[("correct", c)][0] == SLOT_NEW for c in CONFIGS))
    for k, step in [("omit-DC", "dc"), ("omit-IC", "ic"), ("omit-ISB", "isb")]:
        x0, miss = res[(k, "IDC=0,DIC=0")]
        v(f"{k}: STALE under IDC=0,DIC=0 and the sanitizer names '{STEP_LABEL[step]}'",
          x0 == SLOT_OLD and miss == step, f"missing={miss} x0={x0}")
    v("omit-DC becomes FRESH under IDC=1 (DC excused) but omit-ISB stays STALE",
      res[("omit-DC", "IDC=1,DIC=0")][0] == SLOT_NEW and
      all(res[("omit-ISB", c)][0] == SLOT_OLD for c in CONFIGS),
      "IDC=1 excuses DC (barrier kept); ISB never excused")
    v("omit-IC becomes FRESH only under DIC=1 (=>IDC=1), else STALE",
      res[("omit-IC", "IDC=1,DIC=1")][0] == SLOT_NEW and
      res[("omit-IC", "IDC=0,DIC=0")][0] == SLOT_OLD and
      res[("omit-IC", "IDC=1,DIC=0")][0] == SLOT_OLD, "")
    v("omit-DSB1 names the step that is ABSENT: the DSB between DC and IC (N3)",
      all(res[("omit-DSB1", c)] == (SLOT_OLD, "dsb") for c in ("IDC=0,DIC=0", "IDC=1,DIC=0")),
      f"IDC=0,DIC=0 -> {res[('omit-DSB1', 'IDC=0,DIC=0')][1]}; "
      f"IDC=1,DIC=0 -> {res[('omit-DSB1', 'IDC=1,DIC=0')][1]} (the IC is present)")

    # ---- B5 store ordering: the sequence must come AFTER the latest store ----
    print("\n-- store ordering (B5): x0 / missing step, and the cause under IDC=0,DIC=0 --")
    print(f"{'kernel':18}" + "".join(f"{c:>16}" for c in CONFIGS) + "   cause (IDC=0,DIC=0)")
    ordr = {}
    for kname, acts in ORDERING.items():
        code, eoff, slot = build_program(acts)
        row = f"{kname:18}"
        for cname, cfg in CONFIGS.items():
            x0, mach = interp(code, eoff, slot, cfg)
            fresh, missing = mach.diagnose(slot - CODEBASE)
            ordr[(kname, cname)] = (x0, fresh, missing, mach.explain(slot - CODEBASE))
            tag = {SLOT_OLD: "OLD", SLOT_NEW: "NEW", SLOT_NEW2: "NEW2"}.get(x0, hex(x0))
            row += f"{tag + ('' if fresh else '!' + missing):>16}"
        print(row + "   " + ordr[(kname, "IDC=0,DIC=0")][3])
    c00 = "IDC=0,DIC=0"
    x0, fr, mi, why = ordr[("control", c00)]
    v("B5 control: STR then the full sequence then run is FRESH", fr and x0 == SLOT_NEW, f"x0={x0}")
    x0, fr, mi, why = ordr[("flush-then-write", c00)]
    v("B5 flush-then-write: maintenance BEFORE the store is STALE, cause named",
      not fr and x0 == SLOT_OLD and mi == "dc" and "BEFORE" in why, f"missing={mi}: {why}")
    x0, fr, mi, why = ordr[("re-patch", c00)]
    v("B5 re-patch: a second, unmaintained store is STALE (fetch sees the maintained NEW, not NEW2)",
      not fr and x0 == SLOT_NEW and mi == "dc", f"x0={x0:#x} missing={mi}: {why}")
    x0, fr, mi, why = ordr[("dc-before-str", c00)]
    v("B5 dc-before-str: a DC issued before the STR never cleans the new bytes -> STALE",
      not fr and x0 == SLOT_OLD and mi == "dc", f"missing={mi}: {why}")

    # ---- line-size class: a REAL strided flush loop in the program (N4) ----
    print("\n-- line-size mismatch: unrolled JIT flush loop, Iline=Dline=64, IDC=0,DIC=0 --")
    cfg = Config(idc=0, dic=0, iminline=64, dminline=64)
    stride = {}
    for s in (64, 128):
        code, e, slot = build_strided(s)
        x0, m = interp(code, e, slot, cfg)
        fresh, miss = m.diagnose(slot - CODEBASE)
        sl = slot - CODEBASE
        flushed = sorted({off - off % 64 for op, off in m.maint if op == "dc"})
        stride[s] = (x0, fresh, miss)
        print(f"  stride {s:3}: slot line +{sl - sl % 64:#x}; DC hit lines "
              f"{[hex(f) for f in flushed]} -> x0={x0} "
              f"({'NEW' if x0 == SLOT_NEW else 'OLD'}); missing: {miss}")
    v("line-size: a stride-128 flush (another core's line size) skips the slot's 64-B line -> STALE; stride 64 FRESH",
      stride[64] == (SLOT_NEW, True, None) and stride[128] == (SLOT_OLD, False, "dc"),
      "decided from the executed flush addresses, not a flag")

    print("\n" + ("ALL VERDICTS PASS" if fail == 0 else "SOME VERDICTS FAILED"))
    return fail


if __name__ == "__main__":
    sys.exit(main())
