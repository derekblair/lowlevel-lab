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
CODEBASE = BASE + 64 + 56     # code loads after ehdr+phdr; interp uses the same base
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
Canonical modify-execute sequence (DDI 0487G.a B2.2.5, per Rutland/US11210222):
  modifying PE: DC CVAU,Xn ; DSB ISH ; IC IVAU,Xn ; DSB ISH ; and each executing
  PE: ISB.
Linux arch/arm64/mm/cache.S caches_clean_inval_pou_macro: on ARM64_HAS_CACHE_IDC
  the DC loop is skipped but a 'dsb ishst' is STILL issued; on ARM64_HAS_CACHE_DIC
  the IC loop is skipped but an 'isb' is STILL issued. => the barriers are kept
  even when IDC/DIC excuse the cache op; that is the rule this model applies."""

A.svc = lambda: struct.pack("<I", 0xD4000001)   # SVC #0 (a64asm has no svc)


# ---- kernel construction ------------------------------------------------
# A kernel is an A64 program: warm the slot (run it once -> caches OLD), patch
# it (STR a new movz word), run the chosen maintenance instructions, then run
# the slot again. `maint` selects which real instructions the kernel contains;
# the verdict is read back from those EXECUTED instructions, not from `maint`.
def build_kernel(maint, flush_off=0):
    slot = A.movz("x0", SLOT_OLD) + A.ret()            # movz x0,#OLD ; ret

    def entry(slot_vaddr):
        c = A.movz("x9", slot_vaddr & 0xFFFF) + A.movk("x9", (slot_vaddr >> 16) & 0xFFFF, 16)
        c += A.blr("x9")                               # warm: run slot once (caches OLD)
        patch_word = int.from_bytes(A.movz("x0", SLOT_NEW), "little")
        c += A.movz("x10", patch_word & 0xFFFF) + A.movk("x10", (patch_word >> 16) & 0xFFFF, 16)
        c += A.strw_imm("w10", "x9", 0)                # STR new instruction word (SMC)
        if flush_off:                                  # maintenance targets x11 = slot + wrong stride
            fa = slot_vaddr + flush_off
            c += A.movz("x11", fa & 0xFFFF) + A.movk("x11", (fa >> 16) & 0xFFFF, 16)
            maddr = "x11"
        else:
            maddr = "x9"
        for step in maint:
            if step == "dc":    c += A.dc_cvau(maddr)
            elif step == "dsb": c += A.dsb_ish()
            elif step == "ic":  c += A.ic_ivau(maddr)
            elif step == "isb": c += A.isb()
        c += A.blr("x9")                               # re-run slot -> NEW or OLD
        c += A.movz("x8", EXIT_NR) + A.svc()           # exit(x0)
        return c

    entry_len = len(entry(CODEBASE))
    slot_vaddr = CODEBASE + entry_len
    code = entry(slot_vaddr) + slot
    return code, 0, slot_vaddr      # entry is at offset 0; slot follows at entry_len


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
    total = EHDR + PHDR + len(code)
    e = struct.pack("<4sBBBBB7xHHIQQQIHHHHHH", b"\x7fELF", 2, 1, 1, 0, 0,
                    2, 183, 1, CODEBASE + entry_off, EHDR, 0, 0, EHDR, PHDR, 1, 0, 0, 0)
    p = struct.pack("<IIQQQQQQ", 1, 7, 0, BASE, BASE, total, total, 0x10000)  # RWX (self-modifies)
    return e + p + code


def run_qemu(code, entry_off):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "k")
    open(path, "wb").write(elf_wrap(code, entry_off))
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
    oracle_ok = True
    for kname, maint in KERNELS.items():
        code, eoff, slot = build_kernel(maint)
        q = run_qemu(code, eoff)
        mc, _ = interp(code, eoff, slot, CONFIGS["IDC=0,DIC=0"], coherent=True)
        same = (q == SLOT_NEW == mc)
        oracle_ok = oracle_ok and same
        print(f"  {kname:9} qemu={q:3}  model(coherent)={mc:3}  {'ok' if same else 'MISMATCH'}")
    v("B4 semantic oracle: model coherent-mode == qemu == NEW for every kernel", oracle_ok)

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

    # ---- B1 line-size class: a REAL wrong flush stride in the program ----
    print("\n-- line-size mismatch: a kernel that flushes the WRONG line (stride bug) --")
    cfg = Config(idc=0, dic=0, iminline=64, dminline=64)
    good, eg, sg = build_kernel(KERNELS["correct"], flush_off=0)   # flush the slot's line
    bad, eb, sb = build_kernel(KERNELS["correct"], flush_off=64)   # flush one line too far
    xg, _ = interp(good, eg, sg, cfg)
    xb, mb = interp(bad, eb, sb, cfg)
    fb, missb = mb.diagnose(sb - CODEBASE)
    print(f"  correct stride  -> x0={xg} ({'NEW' if xg == SLOT_NEW else 'OLD'})")
    print(f"  wrong stride    -> x0={xb} ({'NEW' if xb == SLOT_NEW else 'OLD'}); first missing: {missb}")
    v("line-size: the program's flush misses the slot's line -> STALE, from the actual addresses",
      xg == SLOT_NEW and xb == SLOT_OLD and missb in ("dc", "ic"),
      "wrong stride detected from the executed flush addresses, not a flag")

    print("\n" + ("ALL VERDICTS PASS" if fail == 0 else "SOME VERDICTS FAILED"))
    return fail


if __name__ == "__main__":
    sys.exit(main())
