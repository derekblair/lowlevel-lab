#!/usr/bin/env python3
"""build_fixpoint.py — construct a 2-cycle cross-ISA machine-code quine relay.

Emits stage0 = stage_X, a freestanding **x86-64** ELF. Run it and it writes a
freestanding **AArch64** ELF (stage1 = stage_A) to stdout; run that (under
qemu-aarch64) and it writes stage_X back, **byte-for-byte**. So

    stage_X --(run native)-->  stage_A --(run under qemu)-->  stage_X'
    sha256(stage_X) == sha256(stage_X')

The fixed point (REVIEW-01 §6.1 C12-5): a single shared payload
    P = header_X || code_X || header_A || code_A
is carried verbatim by BOTH stages. Each stage file is  header_i || code_i || P.
code_X emits  header_A || code_A || P ( = stage_A );  code_A emits
header_X || code_X || P ( = stage_X ). Each stage therefore emits the OTHER
ISA's header+code **as data read out of P** and never executes it (C12-3: a
relay, not a polyglot). Each stage does only write(1,…) + exit (C12-2).

All machine code is hand-emitted here with fixed-width instructions, so code
lengths do not depend on the immediate values and the layout closes in one pass.
Python stdlib only; no assembler needed to BUILD (the Makefile uses
aarch64-linux-gnu-objdump only to DISASSEMBLE the AArch64 stage as evidence).
"""
import struct
import sys

V = 0x200000          # load vaddr for both stages. 64 KiB-aligned: qemu-aarch64's
ALIGN = 0x1000       # loader expects the guest's 64 KiB page alignment (a 0x1000
#                       align at 0x200000 is silently rejected by qemu); x86 is
#                       happy with the stronger alignment too.
EHDR = 64
PHDR = 56
HDR = EHDR + PHDR     # 120: ELF header + one program header
EM_X86_64 = 62
EM_AARCH64 = 183


def elf_header(machine, total_size):
    """A minimal ET_EXEC with one RWX PT_LOAD covering the whole file at V."""
    e = struct.pack("<4sBBBBB7xHHIQQQIHHHHHH",
                    b"\x7fELF", 2, 1, 1, 0, 0,   # ident: ELF64, LSB, v1, SysV
                    2,              # e_type = ET_EXEC
                    machine,        # e_machine
                    1,              # e_version
                    V + HDR,        # e_entry = start of code
                    EHDR,           # e_phoff
                    0,              # e_shoff
                    0,              # e_flags
                    EHDR,           # e_ehsize
                    PHDR,           # e_phentsize
                    1,              # e_phnum
                    0, 0, 0)        # shentsize, shnum, shstrndx
    p = struct.pack("<IIQQQQQQ",
                    1,              # p_type = PT_LOAD
                    5,              # p_flags = R|X (W^X; stages never write own memory)
                    0,              # p_offset
                    V,              # p_vaddr
                    V,              # p_paddr
                    total_size,     # p_filesz
                    total_size,     # p_memsz
                    ALIGN)          # p_align (64 KiB; qemu-aarch64 loader needs it)
    assert len(e) == EHDR and len(p) == PHDR
    return e + p


# ---- x86-64 code emitters (fixed width) ----
def x_mov_edi_1():  return bytes([0xbf, 1, 0, 0, 0])            # mov edi,1  (fd)
def x_mov_eax(v):   return bytes([0xb8]) + struct.pack("<I", v)  # mov eax,imm32
def x_movabs_rsi(v):return bytes([0x48, 0xbe]) + struct.pack("<Q", v)  # movabs rsi,imm64
def x_mov_edx(v):   return bytes([0xba]) + struct.pack("<I", v)  # mov edx,imm32
def x_syscall():    return bytes([0x0f, 0x05])
def x_xor_edi():    return bytes([0x31, 0xff])                   # xor edi,edi

def x_write(buf_vaddr, length):
    return x_mov_eax(1) + x_movabs_rsi(buf_vaddr) + x_mov_edx(length) + x_syscall()

def x_code(hdrA, codeA, Paddr, Plen, lcode):
    c = x_mov_edi_1()
    c += x_write(hdrA, HDR)          # write(1, header_A, 120)
    c += x_write(codeA, lcode)       # write(1, code_A, La)
    c += x_write(Paddr, Plen)        # write(1, P, |P|)
    c += x_mov_eax(60) + x_xor_edi() + x_syscall()   # exit(0)
    return c


# ---- AArch64 code emitters (fixed width: movz+movk for every value) ----
def a_movz(rd, imm16, shift):  # movz xrd, #imm16, lsl #shift
    return struct.pack("<I", 0xd2800000 | (shift // 16) << 21 | (imm16 & 0xffff) << 5 | rd)
def a_movk(rd, imm16, shift):  # movk xrd, #imm16, lsl #shift
    return struct.pack("<I", 0xf2800000 | (shift // 16) << 21 | (imm16 & 0xffff) << 5 | rd)
def a_set(rd, val):            # rd <- val (val < 2^32), fixed 2 instructions
    return a_movz(rd, val & 0xffff, 0) + a_movk(rd, (val >> 16) & 0xffff, 16)
def a_svc0():
    return struct.pack("<I", 0xd4000001)   # svc #0

def a_write(buf_vaddr, length):
    # x0 is BOTH arg0 (fd) and the syscall return value, so reset x0=1 before
    # every write (svc clobbered it with the previous byte count).
    return a_set(0, 1) + a_set(1, buf_vaddr) + a_set(2, length) + a_svc0()

def a_code(hdrX, codeX, Paddr, Plen, lcode):
    c = a_set(8, 64)                 # x8=write (x8 is preserved across svc)
    c += a_write(hdrX, HDR)          # write(1, header_X, 120)
    c += a_write(codeX, lcode)       # write(1, code_X, Lx)
    c += a_write(Paddr, Plen)        # write(1, P, |P|)
    c += a_set(8, 93) + a_set(0, 0) + a_svc0()   # x8=exit, x0=0, svc
    return c


# code lengths are constant (fixed-width ops); compute once with dummy args.
Lx = len(x_code(0, 0, 0, 0, 0))
La = len(a_code(0, 0, 0, 0, 0))

# Layout. P = header_X || code_X || header_A || code_A (carried by both stages).
#   stage_X = header_X || code_X || P   (size TX)
#   stage_A = header_A || code_A || P   (size TA)
LP = 2 * HDR + Lx + La
TX = HDR + Lx + LP        # 360 + 2*Lx + La
TA = HDR + La + LP        # 360 + Lx + 2*La
# offsets inside P:
off_hX, off_cX, off_hA, off_cA = 0, HDR, HDR + Lx, 2 * HDR + Lx
# where P sits (vaddr) in each stage:
Pvx = V + HDR + Lx        # P's vaddr inside stage_X
Pva = V + HDR + La        # P's vaddr inside stage_A

# code_X (runs in stage_X) emits stage_A = header_A || code_A || P:
code_X = x_code(Pvx + off_hA, Pvx + off_cA, Pvx, LP, La)
# code_A (runs in stage_A) emits stage_X = header_X || code_X || P:
code_A = a_code(Pva + off_hX, Pva + off_cX, Pva, LP, Lx)
assert len(code_X) == Lx and len(code_A) == La, (len(code_X), Lx, len(code_A), La)

header_X = elf_header(EM_X86_64, TX)
header_A = elf_header(EM_AARCH64, TA)
P = header_X + code_X + header_A + code_A
assert len(P) == LP

stage_X = header_X + code_X + P
stage_A = header_A + code_A + P
assert len(stage_X) == TX and len(stage_A) == TA
TOTAL = TX   # stage0 is stage_X


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "stage0"
    with open(out, "wb") as f:
        f.write(stage_X)
    # also drop the expected AArch64 stage for reference / disassembly
    with open(out + ".expected_stageA", "wb") as f:
        f.write(stage_A)
    sys.stderr.write(
        f"built {out}: x86-64 stage_X, {TX} bytes "
        f"(HDR={HDR} code_X={Lx} code_A={La} payload={LP}); "
        f"stage_A would be {TA} bytes; entry=V+{HDR:#x}\n")
