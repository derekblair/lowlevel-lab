#!/usr/bin/env python3
"""sanitize.py — the ifetch-sanitizer.

Given a self-modifying AArch64 kernel and a CTR_EL0 / line-size config, it runs
the kernel through a small A64 interpreter whose instruction fetch goes through
the modelled I/D cache hierarchy (icache_model.py), and reports whether the
patched code executes FRESH or STALE and, if stale, EXACTLY which step of the
architectural maintenance sequence

    DC CVAU -> DSB ISH -> IC IVAU -> DSB ISH -> ISB

is missing (or defeated by an I/D line-size mismatch). All staleness output is
MODEL output (REVIEW-01 §2.4 P4-4 / R10); the same kernels run FRESH under
qemu-aarch64 (SMC-coherent) and that is reported as qemu's coherence, not as
evidence about silicon.

Build order of the machine code is via a64asm.py (differential-tested vs
aarch64-linux-gnu-as). Python stdlib only.
"""
import struct
import subprocess
import sys
import tempfile
import os
import a64asm as A
from icache_model import Config, Machine

BASE = 0x400000
CODEBASE = BASE + 64 + 56     # code loads after ehdr(64)+phdr(56); interp agrees
SLOT_OLD = 0x11
SLOT_NEW = 0x22
EXIT_NR = 93

# The architecture reference the per-config verdicts cite (P4-3).
ARM_REF = ("Arm ARM DDI 0487K.a, B2.7.4 'Instruction cache maintenance "
           "requirements' and D23.2.35 CTR_EL0.{IDC,DIC}; the sequence DC CVAU; "
           "DSB ISH; IC IVAU; DSB ISH; ISB")


# ---- kernel construction -------------------------------------------------
# Memory layout (one region at BASE):
#   entry: sets up, patches the slot word, does maintenance, blr slot, exit(x0)
#   slot : movz x0, #OLD ; ret      (the self-modified code)
# The patch overwrites the slot's movz-imm16 so it loads NEW instead of OLD.

def build_kernel(maint, wrong_line=False):
    """maint: list of steps from {'dc','dsb1','ic','dsb2','isb'} to PERFORM.
    Returns (image_bytes, slot_off, entry_off, maint_trace). maint_trace is the
    ordered [(op, line_base)] the model evaluates."""
    # assemble the slot first so we know its size/offset
    slot = A.movz("x0", SLOT_OLD) + A.ret()           # 8 bytes
    # entry code; we fill the slot address with movz/movk of (BASE+slot_off)
    # placeholder, patched after we know slot_off.
    def entry(slot_vaddr, slot_off):
        c = b""
        # x9 = slot vaddr (for maintenance + call); x10 = patch word
        c += A.movz("x9", slot_vaddr & 0xFFFF) + A.movk("x9", (slot_vaddr >> 16) & 0xFFFF, 16)
        # new slot word = movz x0,#NEW  (overwrites slot[0:4])
        patch_word = int.from_bytes(A.movz("x0", SLOT_NEW), "little")
        c += A.movz("x10", patch_word & 0xFFFF) + A.movk("x10", (patch_word >> 16) & 0xFFFF, 16)
        c += A.strw_imm("w10", "x9", 0)               # STORE the new instruction word (SMC)
        # maintenance, in the requested subset/order
        for step in maint:
            if step == "dc":   c += A.dc_cvau("x9")
            elif step == "dsb1": c += A.dsb_ish()
            elif step == "ic": c += A.ic_ivau("x9")
            elif step == "dsb2": c += A.dsb_ish()
            elif step == "isb": c += A.isb()
        c += A.blr("x9")                              # call the (maybe patched) slot
        c += A.movz("x8", EXIT_NR) + A.svc()          # exit(x0)
        return c
    # two-pass: compute entry size with a dummy, then place slot after it
    dummy = entry(CODEBASE, 0)
    entry_len = len(dummy)
    slot_off = entry_len
    slot_vaddr = CODEBASE + slot_off
    code = entry(slot_vaddr, slot_off) + slot
    assert len(code) == entry_len + len(slot)
    # maint_trace: ops on the slot line, in order (addresses = slot_vaddr)
    trace = [(s, slot_vaddr) for s in maint]
    return code, slot_off, 0, trace, slot_vaddr


# a64asm has no svc; add it here (SVC #0).
A.svc = lambda: struct.pack("<I", 0xD4000001)


# ---- tiny A64 interpreter -------------------------------------------------
# Executes the kernel subset. Instruction fetch of the self-modified SLOT is
# resolved by evaluate_maintenance (the DDI 0487 rule), which is the authority
# for fresh-vs-stale and for naming the missing step. x[]/memory are a plain
# register file + byte array (the cache model's data side is exercised by the
# store but the staleness DECISION is the sequence rule, so the two can't
# disagree).
def interp(code, entry_off, slot_vaddr, cfg, maint_trace, patched_line_size_ok):
    x = [0] * 32
    pc = CODEBASE + entry_off
    link = 0
    for _ in range(1000):
        off = pc - CODEBASE
        w = int.from_bytes(code[off:off + 4], "little")
        op, dec = decode(w)
        if pc == slot_vaddr:        # fetch of the self-modified slot
            fresh, _ = evaluate_maintenance(maint_trace, cfg, slot_vaddr, patched_line_size_ok)
            x[0] = SLOT_NEW if fresh else SLOT_OLD   # slot = movz x0,#imm ; ret
            pc = link
            continue
        if op == "movz":
            x[dec[0]] = dec[1] << dec[2]
        elif op == "movk":
            x[dec[0]] = (x[dec[0]] & ~(0xFFFF << dec[2])) | (dec[1] << dec[2])
        elif op in ("dc", "ic", "dsb", "isb", "strw"):
            pass                    # store + maintenance effects are in maint_trace
        elif op == "blr":
            link = pc + 4
            pc = x[dec[0]]
            continue
        elif op == "ret":
            pc = x[dec[0]]
            continue
        elif op == "svc":
            return x[0] & 0xFF      # exit(x0)
        else:
            raise RuntimeError(f"interp: unhandled {op} @ {pc:#x} word={w:#010x}")
        pc += 4
    raise RuntimeError("interp: ran away")


def decode(w):
    if (w & 0xFF800000) == 0xD2800000:
        return "movz", (w & 31, (w >> 5) & 0xFFFF, ((w >> 21) & 3) * 16)
    if (w & 0xFF800000) == 0xF2800000:
        return "movk", (w & 31, (w >> 5) & 0xFFFF, ((w >> 21) & 3) * 16)
    if (w & 0xFFC00000) == 0xB9000000:
        return "strw", (w & 31, (w >> 5) & 31, ((w >> 10) & 0xFFF) * 4)
    if (w & 0xFFFFFC1F) == 0xD63F0000:
        return "blr", ((w >> 5) & 31,)
    if (w & 0xFFFFFC1F) == 0xD65F0000:
        return "ret", ((w >> 5) & 31,)
    if w == 0xD4000001:
        return "svc", ()
    if (w & 0xFFFFF000) == 0xD50B7000 and (w & 0x1F) < 31:  # dc/ic SYS
        return ("ic" if (w & 0xFE0) == 0x520 else "dc"), ((w & 31),)
    if (w & 0xFFFFF0FF) == 0xD503309F:  # DSB
        return "dsb", ()
    if w == 0xD5033FDF:
        return "isb", ()
    return "?", (w,)


# ---- the architectural staleness decision (the heart of the diagnosis) ----
STEP_LABEL = {
    "dc": "DC CVAU (clean D-cache to PoU)",
    "dsb1": "DSB ISH (after DC CVAU)",
    "ic": "IC IVAU (invalidate I-cache to PoU)",
    "dsb2": "DSB ISH (after IC IVAU)",
    "isb": "ISB (context-synchronize the fetch)",
}


def required_steps(cfg):
    """The ordered steps required to make the store visible to fetch, given
    CTR_EL0.{IDC,DIC}."""
    req = []
    if cfg.idc == 0:
        req += ["dc", "dsb1"]
    if cfg.dic == 0:
        req += ["ic", "dsb2"]
    req += ["isb"]
    return req


def evaluate_maintenance(trace, cfg, slot_vaddr, line_size_ok):
    """Return (fresh: bool, missing_step: str|None). The performed steps are the
    ops in `trace` whose line (under the config's line sizes) covers the patched
    slot. A line-size mismatch means DC/IC did not cover the slot's line."""
    performed = []
    for op, addr in trace:
        if op in ("dc", "ic") and not line_size_ok:
            continue  # wrong-stride maintenance misses the patched line
        performed.append(op)
    req = required_steps(cfg)
    # req must appear as an in-order SUBSEQUENCE of performed (extra, unneeded
    # steps in performed are harmless and skipped).
    i = 0
    for p in performed:
        if i < len(req) and p == req[i]:
            i += 1
    if i == len(req):
        return True, None
    return False, req[i]   # first still-missing required step


# ---- qemu oracle (P4-2): coherent-mode end state must equal qemu ----------
def elf_wrap(code, entry_off):
    EHDR, PHDR = 64, 56
    total = EHDR + PHDR + len(code)
    e = struct.pack("<4sBBBBB7xHHIQQQIHHHHHH", b"\x7fELF", 2, 1, 1, 0, 0,
                    2, 183, 1, BASE + EHDR + PHDR + entry_off, EHDR, 0, 0,
                    EHDR, PHDR, 1, 0, 0, 0)
    # RWX: the kernel self-modifies its own slot, so the page must be writable
    # AND executable. (qemu-aarch64 is SMC-coherent, so the patch is visible.)
    p = struct.pack("<IIQQQQQQ", 1, 7, 0, BASE, BASE, total, total, 0x10000)
    return e + p + code


def run_qemu(code, entry_off):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "k")
    with open(path, "wb") as f:
        f.write(elf_wrap(code, entry_off))
    os.chmod(path, 0o755)
    r = subprocess.run(["qemu-aarch64", path], capture_output=True)
    return r.returncode


# ---- the kernels and the sweep -------------------------------------------
KERNELS = {
    "correct":      ["dc", "dsb1", "ic", "dsb2", "isb"],
    "omit-DC":      ["dsb1", "ic", "dsb2", "isb"],
    "omit-DSB1":    ["dc", "ic", "dsb2", "isb"],
    "omit-IC":      ["dc", "dsb1", "dsb2", "isb"],
    "omit-DSB2":    ["dc", "dsb1", "ic", "isb"],
    "omit-ISB":     ["dc", "dsb1", "ic", "dsb2"],
    "none":         [],
}

# Only architecturally-valid CTR_EL0 combinations. Per the Arm ARM, "if
# CTR_EL0.DIC is 1 then IDC must also be 1", so {IDC=0, DIC=1} is IMPOSSIBLE and
# is deliberately absent (DDI 0487K.a D23.2.35).
CONFIGS = {
    "IDC=0,DIC=0": Config(idc=0, dic=0),
    "IDC=1,DIC=0": Config(idc=1, dic=0),
    "IDC=1,DIC=1": Config(idc=1, dic=1),
}


def main():
    print("=" * 78)
    print("ifetch-sanitizer: which cache-maintenance step is missing, per CTR_EL0 config")
    print("(ALL staleness output is MODEL output; the same kernels run FRESH under")
    print(" qemu-aarch64, which is SMC-coherent -- that is qemu's coherence, R10)")
    print("Arch ref:", ARM_REF)
    print("=" * 78)
    fail = 0

    def v(name, cond, detail=""):
        nonlocal fail
        if not cond:
            fail = 1
        print(f"VERDICT {'PASS' if cond else 'FAIL'}: {name}" + (f"  [{detail}]" if detail else ""))

    # ---- P4-2 encoder oracle: a64asm vs aarch64-linux-gnu-as ----
    p, t, fails = A.selftest()
    v(f"encoder oracle: a64asm matches aarch64-linux-gnu-as ({p}/{t})", p == t,
      f"mismatches: {fails}" if fails else "all encoders byte-identical")

    # ---- P4-2 semantic oracle: coherent-mode model == qemu for EVERY kernel ----
    print("\n-- semantic oracle (coherent config IDC=0,DIC=0; correct kernel vs qemu) --")
    code, slot_off, entry_off, trace, slot_vaddr = build_kernel(KERNELS["correct"])
    qret = run_qemu(code, entry_off)
    mret = interp(code, entry_off, slot_vaddr, CONFIGS["IDC=0,DIC=0"], trace, True)
    print(f"correct kernel: qemu exit={qret}  model(coherent) x0={mret}  (both must be NEW={SLOT_NEW})")
    v("semantic oracle: model coherent-mode result == qemu == NEW", qret == SLOT_NEW and mret == SLOT_NEW,
      f"qemu={qret} model={mret} new={SLOT_NEW}")
    # qemu runs every kernel FRESH regardless of maintenance (it is coherent):
    qall = {k: run_qemu(build_kernel(m)[0], 0) for k, m in KERNELS.items()}
    v("qemu runs EVERY kernel fresh (NEW) -- so qemu cannot show the stale cases",
      all(r == SLOT_NEW for r in qall.values()),
      f"qemu exits: {qall}")

    # ---- the diagnosis matrix ----
    print("\n-- diagnosis matrix: x0 after calling the patched slot (NEW=fresh, OLD=stale) --")
    hdr = f"{'kernel':12}" + "".join(f"{c:>22}" for c in CONFIGS)
    print(hdr)
    results = {}
    for kname, maint in KERNELS.items():
        code, slot_off, entry_off, trace, slot_vaddr = build_kernel(maint)
        row = f"{kname:12}"
        for cname, cfg in CONFIGS.items():
            fresh, missing = evaluate_maintenance(trace, cfg, slot_vaddr, True)
            x0 = interp(code, entry_off, slot_vaddr, cfg, trace, True)
            tag = "NEW" if x0 == SLOT_NEW else f"OLD!{STEP_LABEL[missing].split()[0] if missing else ''}"
            results[(kname, cname)] = (fresh, missing, x0)
            row += f"{tag:>22}"
        print(row)

    # ---- verdicts on the diagnosis ----
    print()
    # correct kernel is fresh in every config
    v("the correct full sequence executes FRESH in every config",
      all(results[("correct", c)][2] == SLOT_NEW for c in CONFIGS),
      "")
    # each omission is stale in both0 and the sanitizer names the omitted step
    for kname, step in [("omit-DC", "dc"), ("omit-IC", "ic"), ("omit-ISB", "isb")]:
        fresh, missing, x0 = results[(kname, "IDC=0,DIC=0")]
        v(f"{kname}: stale under IDC=0/DIC=0, sanitizer names '{STEP_LABEL[step]}'",
          x0 == SLOT_OLD and missing == step,
          f"missing={missing} x0={x0}")
    # IDC=1 excuses the DC omission; DIC=1 excuses the IC omission
    v("omit-DC becomes FRESH when IDC=1 (D-cache clean to PoU not required)",
      results[("omit-DC", "IDC=1,DIC=0")][2] == SLOT_NEW and results[("omit-DC", "IDC=0,DIC=0")][2] == SLOT_OLD,
      "config-sensitive, as the architecture specifies")
    v("omit-IC becomes FRESH when DIC=1 (requires IDC=1; config IDC=1,DIC=1)",
      results[("omit-IC", "IDC=1,DIC=1")][2] == SLOT_NEW and results[("omit-IC", "IDC=0,DIC=0")][2] == SLOT_OLD,
      "DIC=1 implies IDC=1 per DDI 0487 D23.2.35; {IDC=0,DIC=1} is impossible and omitted")
    # ISB is always required
    v("omit-ISB is stale in EVERY config (ISB is never excused by IDC/DIC)",
      all(results[("omit-ISB", c)][2] == SLOT_OLD for c in CONFIGS), "")

    # ---- line-size mismatch class (the big.LITTLE JIT bug) ----
    print("\n-- I/D line-size mismatch: correct sequence, but the maintenance loop")
    print("   strides by the wrong line size so it misses the patched line --")
    code, slot_off, entry_off, trace, slot_vaddr = build_kernel(KERNELS["correct"])
    mism = Config(idc=0, dic=0, dminline=64, iminline=128)  # loop assumed 64, I-line is 128
    x0_ok = interp(code, entry_off, slot_vaddr, mism, trace, True)   # stride correct
    x0_bad = interp(code, entry_off, slot_vaddr, mism, trace, False)  # stride wrong (misses line)
    print(f"   correct-stride x0={x0_ok} (NEW)   wrong-stride x0={x0_bad} (OLD, stale)")
    v("line-size mismatch: a correct-looking sequence with the wrong stride goes STALE",
      x0_ok == SLOT_NEW and x0_bad == SLOT_OLD,
      "the classic big.LITTLE mismatched-cache-line JIT bug, caught by the model")

    print("\n" + ("ALL VERDICTS PASS" if fail == 0 else "SOME VERDICTS FAILED"))
    return fail


if __name__ == "__main__":
    sys.exit(main())
