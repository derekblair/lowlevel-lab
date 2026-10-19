#!/usr/bin/env python3
"""a64asm.py — a tiny AArch64 assembler for the ifetch-sanitizer's kernels.

It covers only the instruction subset the self-modifying-code kernels use
(REVIEW-01 §2.4 P4-5: keep the subset scoped). Each encoder is a pure function
returning 4 little-endian bytes. `selftest()` differential-tests every encoder
against the system `aarch64-linux-gnu-as` + `objdump` (REVIEW-01 §2.4 P4-2 /
R6): the independent oracle is GNU binutils, not this file.

Encodings follow the Arm ARM (DDI 0487). Python stdlib only.
"""
import struct
import subprocess
import sys
import tempfile
import os

X = {f"x{i}": i for i in range(31)}
X["xzr"] = 31
X["sp"] = 31


def _w(word):
    return struct.pack("<I", word & 0xFFFFFFFF)


def movz(rd, imm16, shift=0):
    return _w(0xD2800000 | (shift // 16) << 21 | (imm16 & 0xFFFF) << 5 | X[rd])


def movk(rd, imm16, shift=0):
    return _w(0xF2800000 | (shift // 16) << 21 | (imm16 & 0xFFFF) << 5 | X[rd])


def add_imm(rd, rn, imm12):
    return _w(0x91000000 | (imm12 & 0xFFF) << 10 | X[rn] << 5 | X[rd])


def sub_imm(rd, rn, imm12):
    return _w(0xD1000000 | (imm12 & 0xFFF) << 10 | X[rn] << 5 | X[rd])


def str_imm(rt, rn, off):           # STR Xt, [Xn, #off]  (64-bit, scaled /8)
    return _w(0xF9000000 | ((off // 8) & 0xFFF) << 10 | X[rn] << 5 | X[rt])


def ldr_imm(rt, rn, off):           # LDR Xt, [Xn, #off]
    return _w(0xF9400000 | ((off // 8) & 0xFFF) << 10 | X[rn] << 5 | X[rt])


def strw_imm(rt, rn, off):          # STR Wt, [Xn, #off]  (32-bit, scaled /4)
    return _w(0xB9000000 | ((off // 4) & 0xFFF) << 10 | X[rn] << 5 | X[rt])


def ret(rn="x30"):
    return _w(0xD65F0000 | X[rn] << 5)


def br(rn):
    return _w(0xD61F0000 | X[rn] << 5)


def blr(rn):
    return _w(0xD63F0000 | X[rn] << 5)


def cbz(rt, off):                   # CBZ Xt, #off  (off in bytes, /4, signed imm19)
    imm19 = (off // 4) & 0x7FFFF
    return _w(0xB4000000 | imm19 << 5 | X[rt])


def b(off):                         # B #off (off bytes, /4, signed imm26)
    imm26 = (off // 4) & 0x3FFFFFF
    return _w(0x14000000 | imm26)


def nop():
    return _w(0xD503201F)


def dc_cvau(rt):                    # DC CVAU, Xt  = SYS #3,c7,c11,#1
    return _w(0xD50B7B20 | X[rt])


def ic_ivau(rt):                    # IC IVAU, Xt  = SYS #3,c7,c5,#1
    return _w(0xD50B7520 | X[rt])


def dsb_ish():                      # DSB ISH
    return _w(0xD5033B9F)


def dsb_ishst():                    # DSB ISHST
    return _w(0xD5033A9F)


def isb():                          # ISB (SY)
    return _w(0xD5033FDF)


# (mnemonic for objdump, encoder, args) — the differential-test table.
_CASES = [
    ("movz x0, #0x1234", lambda: movz("x0", 0x1234)),
    ("movz x5, #0xbeef, lsl #16", lambda: movz("x5", 0xBEEF, 16)),
    ("movk x3, #0xabcd, lsl #32", lambda: movk("x3", 0xABCD, 32)),
    ("add x1, x2, #0x40", lambda: add_imm("x1", "x2", 0x40)),
    ("sub x7, x7, #0x1", lambda: sub_imm("x7", "x7", 1)),
    ("str x4, [x5, #16]", lambda: str_imm("x4", "x5", 16)),
    ("ldr x6, [x7, #8]", lambda: ldr_imm("x6", "x7", 8)),
    ("str w4, [x5, #4]", lambda: strw_imm("w4", "x5", 4)),
    ("ret", lambda: ret()),
    ("br x9", lambda: br("x9")),
    ("blr x10", lambda: blr("x10")),
    ("cbz x0, .+8", lambda: cbz("x0", 8)),
    ("b .+16", lambda: b(16)),
    ("nop", lambda: nop()),
    ("dc cvau, x8", lambda: dc_cvau("x8")),
    ("ic ivau, x8", lambda: ic_ivau("x8")),
    ("dsb ish", lambda: dsb_ish()),
    ("dsb ishst", lambda: dsb_ishst()),
    ("isb", lambda: isb()),
    ("movz x9, #0x0", lambda: movz("x9", 0)),
    ("add x0, x0, #0xff0", lambda: add_imm("x0", "x0", 0xFF0)),
    ("ldr x0, [x0, #0]", lambda: ldr_imm("x0", "x0", 0)),
]

# strw_imm uses Wt names; map them for the encoder (same register index).
X.update({f"w{i}": i for i in range(31)})


def _as_encode(asm_line):
    """Assemble one instruction with the system assembler; return 4 bytes."""
    d = tempfile.mkdtemp()
    s = os.path.join(d, "t.s")
    o = os.path.join(d, "t.o")
    with open(s, "w") as f:
        f.write(".text\n" + asm_line + "\n")
    subprocess.run(["aarch64-linux-gnu-as", s, "-o", o], check=True,
                   capture_output=True)
    out = subprocess.run(["aarch64-linux-gnu-objdump", "-d", o],
                         check=True, capture_output=True, text=True).stdout
    for ln in out.splitlines():
        parts = ln.split("\t")
        if len(parts) >= 2 and parts[0].strip().endswith(":"):
            hexpart = parts[1].strip().replace(" ", "")
            if len(hexpart) == 8:
                return bytes.fromhex(hexpart)[::-1]  # objdump prints big-endian nibbles of a LE word... handle below
    raise RuntimeError(f"could not assemble {asm_line!r}:\n{out}")


def selftest():
    """Differential-test every encoder against aarch64-linux-gnu-as. Returns
    (passed, total, failures[])."""
    passed = 0
    failures = []
    for mnem, enc in _CASES:
        mine = enc()
        try:
            ref = _as_encode(mnem)
        except Exception as e:  # noqa
            failures.append((mnem, mine.hex(), f"as-error: {e}"))
            continue
        if mine == ref:
            passed += 1
        else:
            failures.append((mnem, mine.hex(), ref.hex()))
    return passed, len(_CASES), failures


if __name__ == "__main__":
    p, t, fails = selftest()
    for mnem, mine, ref in fails:
        print(f"MISMATCH {mnem!r}: mine={mine} ref={ref}")
    print(f"a64asm differential test vs aarch64-linux-gnu-as: {p}/{t} encoders match")
    sys.exit(0 if p == t else 1)
