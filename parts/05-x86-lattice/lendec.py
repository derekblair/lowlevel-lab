#!/usr/bin/env python3
"""lendec.py — a from-scratch x86-64 instruction LENGTH decoder.

It returns the byte length of the instruction starting at a given offset (it
does not name the instruction). It is the fast decoder a superset disassembler
needs; its correctness is not assumed — `superset.py` differential-tests it at
EVERY byte offset against `objdump` and reports the agreement rate
(REVIEW-01 §6.2 C09-3). This decoder is ANALYSIS ONLY: it never emits or
transforms code (C09-2).

Covers the common 64-bit encodings gcc/clang emit. Offsets it cannot decode
return None (reported as "undecodable", handled explicitly by the caller).
Python stdlib only.
"""

LEGACY_PREFIXES = {0xF0, 0xF2, 0xF3, 0x2E, 0x36, 0x3E, 0x26, 0x64, 0x65, 0x66, 0x67}

# One-byte opcode map: opcode -> (has_modrm, imm_bytes) where imm_bytes may be
# 'z' (2 under 0x66 else 4), 'v' (operand-size), 'b' (1), 'p' (far ptr), or an int.
# None entry => not handled (undecodable). This is the common subset.
OP1 = {}


def _fill_op1():
    for base in (0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38):  # ALU r/m,r families
        OP1[base + 0] = (True, 0); OP1[base + 1] = (True, 0)
        OP1[base + 2] = (True, 0); OP1[base + 3] = (True, 0)
        OP1[base + 4] = (False, 1); OP1[base + 5] = (False, 'z')
    for r in range(0x50, 0x60):   # push/pop r64
        OP1[r] = (False, 0)
    OP1[0x63] = (True, 0)          # movslq
    OP1[0x68] = (False, 'z'); OP1[0x69] = (True, 'z')   # push imm; imul r,rm,imm
    OP1[0x6A] = (False, 1); OP1[0x6B] = (True, 1)
    for jcc in range(0x70, 0x80):  # jcc short
        OP1[jcc] = (False, 1)
    OP1[0x80] = (True, 1); OP1[0x81] = (True, 'z'); OP1[0x83] = (True, 1)  # grp1
    OP1[0x84] = (True, 0); OP1[0x85] = (True, 0)       # test
    OP1[0x86] = (True, 0); OP1[0x87] = (True, 0)       # xchg
    for o in (0x88, 0x89, 0x8A, 0x8B):                 # mov r/m,r etc
        OP1[o] = (True, 0)
    OP1[0x8D] = (True, 0)          # lea
    OP1[0x8F] = (True, 0)          # pop r/m
    OP1[0x90] = (False, 0)         # nop / xchg
    for o in range(0x91, 0x98):
        OP1[o] = (False, 0)
    OP1[0x98] = (False, 0); OP1[0x99] = (False, 0)     # cwde/cdqe, cdq/cqo
    OP1[0x9C] = (False, 0); OP1[0x9D] = (False, 0)     # pushf/popf
    OP1[0xA8] = (False, 1); OP1[0xA9] = (False, 'z')   # test al/eax, imm
    for r in range(0xB0, 0xB8):    # mov r8, imm8
        OP1[r] = (False, 1)
    for r in range(0xB8, 0xC0):    # mov r32/64, imm (imm is 'v': 8 if REX.W)
        OP1[r] = (False, 'v')
    OP1[0xC0] = (True, 1); OP1[0xC1] = (True, 1)       # shift grp2, imm8
    OP1[0xC2] = (False, 2); OP1[0xC3] = (False, 0)     # ret imm16 / ret
    OP1[0xC6] = (True, 1); OP1[0xC7] = (True, 'z')     # mov r/m, imm
    OP1[0xC9] = (False, 0); OP1[0xCB] = (False, 0)     # leave / retf
    OP1[0xD0] = (True, 0); OP1[0xD1] = (True, 0)       # shift by 1
    OP1[0xD2] = (True, 0); OP1[0xD3] = (True, 0)       # shift by cl
    OP1[0xE8] = (False, 'z'); OP1[0xE9] = (False, 'z')  # call/jmp rel32
    OP1[0xEB] = (False, 1)         # jmp rel8
    OP1[0xF4] = (False, 0)         # hlt
    OP1[0xF6] = (True, '/')        # grp3 (imm depends on /reg): handled specially
    OP1[0xF7] = (True, '/')
    OP1[0xFE] = (True, 0); OP1[0xFF] = (True, 0)       # inc/dec, call/jmp/push r/m


_fill_op1()

# Two-byte (0F xx) opcodes actually used by gcc output; has_modrm, imm.
OP2 = {}


def _fill_op2():
    for o in (0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x28, 0x29, 0x2A,
              0x2C, 0x2D, 0x2E, 0x2F, 0x51, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
              0x5A, 0x5C, 0x5D, 0x5E, 0x5F, 0x6E, 0x6F, 0x7E, 0x7F, 0xD6,
              0xEF, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
              0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0xB6, 0xB7, 0xBE, 0xBF, 0xAF,
              0xA3, 0xAB, 0xB0, 0xB1, 0xBC, 0xBD, 0x1E, 0x1F, 0x05, 0x0B):
        OP2[o] = (True, 0)
    for jcc in range(0x80, 0x90):  # jcc near rel32
        OP2[jcc] = (False, 'z')
    for setcc in range(0x90, 0xA0):
        OP2[setcc] = (True, 0)
    OP2[0x1F] = (True, 0)           # multi-byte nop
    OP2[0x70] = (True, 1); OP2[0x71] = (True, 1); OP2[0x72] = (True, 1); OP2[0x73] = (True, 1)
    OP2[0xC2] = (True, 1)           # cmpps imm8
    OP2[0x3A] = None; OP2[0x38] = None   # 3-byte escape handled in decode()


_fill_op2()


def _imm_len(code, modrm_present, imm, opsz, addrsz, reg_field):
    if imm == 0:
        return 0
    if imm == 'b':
        return 1
    if imm == 'z':
        return 2 if opsz == 2 else 4
    if imm == 'v':
        return opsz
    if imm == '/':
        # grp3 F6/F7: /0 and /1 (test) have an immediate; others don't
        return (1 if reg_field in (0, 1) else 0) if code == 0xF6 else \
               ((2 if opsz == 2 else 4) if reg_field in (0, 1) else 0)
    return imm


def decode_len(buf, off):
    """Return (length, info) for the instruction at buf[off], or (None, reason)."""
    i = off
    n = len(buf)
    opsz = 4          # default operand size (ignoring 0x66)
    addrsz = 8
    rex_w = 0
    seen = 0
    # prefixes
    while i < n and buf[i] in LEGACY_PREFIXES:
        if buf[i] == 0x66:
            opsz = 2
        if buf[i] == 0x67:
            addrsz = 4
        i += 1
        seen += 1
        if seen > 14:
            return None, "too many prefixes"
    if i >= n:
        return None, "truncated"
    # REX
    if 0x40 <= buf[i] <= 0x4F:
        rex_w = (buf[i] >> 3) & 1
        i += 1
        if i >= n:
            return None, "truncated after rex"
    if rex_w:
        opsz = 8
    op = buf[i]
    i += 1
    two = False
    three = 0
    if op == 0x0F:
        if i >= n:
            return None, "truncated 0f"
        op2 = buf[i]
        i += 1
        if op2 in (0x38, 0x3A):   # 3-byte
            if i >= n:
                return None, "truncated 3byte"
            three = op2
            op3 = buf[i]
            i += 1
            has_modrm, imm = True, (1 if three == 0x3A else 0)
        else:
            ent = OP2.get(op2)
            if ent is None:
                return None, f"unhandled 0f {op2:#x}"
            has_modrm, imm = ent
            two = True
            reg_field = 0
    else:
        ent = OP1.get(op)
        if ent is None:
            return None, f"unhandled op {op:#x}"
        has_modrm, imm = ent
    reg_field = 0
    # ModRM + SIB + displacement
    if has_modrm:
        if i >= n:
            return None, "truncated modrm"
        modrm = buf[i]
        i += 1
        mod = modrm >> 6
        reg_field = (modrm >> 3) & 7
        rm = modrm & 7
        if mod != 3 and rm == 4:          # SIB
            if i >= n:
                return None, "truncated sib"
            sib = buf[i]
            i += 1
            base = sib & 7
            if mod == 0 and base == 5:
                i += 4                     # disp32
            elif mod == 1:
                i += 1
            elif mod == 2:
                i += 4
        else:
            if mod == 0 and rm == 5:
                i += 4                     # rip-relative disp32
            elif mod == 1:
                i += 1
            elif mod == 2:
                i += 4
    # immediate
    il = _imm_len(op, has_modrm, imm, opsz, addrsz, reg_field)
    i += il
    if i > n:
        return None, "runs past end"
    return i - off, ("op", op)
