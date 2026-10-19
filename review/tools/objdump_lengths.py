#!/usr/bin/env python3
"""objdump_lengths.py — reviewer's every-offset x86-64 decode oracle (for BUILD-05).

usage: python3 -I review/tools/objdump_lengths.py BINARY START END [STEP]
  START/END are virtual addresses (hex like 0x1040 or decimal).

For each address A in [START, END) (every byte by default), asks GNU objdump to
decode the single instruction that STARTS at A
(`objdump -d --start-address=A --stop-address=A+16`, first insn only), and prints one TSV line:
    <addr-hex> <length> <bytes-hex> <mnemonic/operands or "(bad)">
This is the ground truth an author-written superset/length decoder must match
at every offset of the sampled region (REVIEW-01 §6.2 C09-3).
"""
import re
import subprocess
import sys

LINE = re.compile(r"^\s*([0-9a-f]+):\t((?:[0-9a-f]{2} )+)\s*\t?(.*)$")


def decode_at(binary, addr):
    out = subprocess.run(
        # stop at A+16, not A+1: objdump stops *reading bytes* at --stop-address,
        # so A+1 truncates every multi-byte instruction to `.byte` (found by
        # self-test). 16 > the x86 maximum instruction length (15).
        ["objdump", "-d", "-w",
         f"--start-address={addr:#x}", f"--stop-address={addr + 16:#x}", binary],
        capture_output=True, text=True, check=True).stdout
    for ln in out.splitlines():
        m = LINE.match(ln)
        if m and int(m.group(1), 16) == addr:
            raw = m.group(2).split()
            return len(raw), "".join(raw), m.group(3).strip() or "(bad)"
    return 0, "", "(no decode)"


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    binary = sys.argv[1]
    start, end = int(sys.argv[2], 0), int(sys.argv[3], 0)
    step = int(sys.argv[4], 0) if len(sys.argv) > 4 else 1
    for a in range(start, end, step):
        n, hexb, asm = decode_at(binary, a)
        print(f"{a:#x}\t{n}\t{hexb}\t{asm}")


if __name__ == "__main__":
    main()
