#!/usr/bin/env python3
"""lendec_sample.py — reviewer's C09-3 every-offset differential test of the
author's lendec.py on REVIEWER-CHOSEN regions (REVIEW-01 §6.2: "I'll pick the
sample at the gate").

usage: python3 -I lendec_sample.py CLONE_PART_DIR ELF:START:LEN [ELF:START:LEN ...]
Oracle per offset = review/tools/objdump_lengths.decode_at (objdump -d -w,
--start-address=A --stop-address=A+16, on the real ELF). lendec gets the region
bytes plus 15 trailing bytes, so both see the same lookahead.
Categories per offset: AGREE | LENDEC-NONE (honest undecodable) |
WRONG (both give a length, they differ, objdump valid: a SILENT error) |
BAD-ACCEPTED (objdump says (bad), lendec returns a length) | BAD-REJECTED.
Reference instruction starts = objdump -d -w linear sweep of the region.
"""
import os, re, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "tools"))
from objdump_lengths import decode_at, LINE  # reviewer oracle


def region_bytes(elf, start, n):
    out = subprocess.run(["objdump", "-d", "-w", f"--start-address={start:#x}",
                          f"--stop-address={start + n + 15:#x}", elf],
                         capture_output=True, text=True, check=True).stdout
    raw, starts = bytearray(), set()
    for ln in out.splitlines():
        m = LINE.match(ln)
        if m:
            a = int(m.group(1), 16)
            if a < start + n:
                starts.add(a - start)
            raw += bytes(int(x, 16) for x in m.group(2).split())
    return bytes(raw), starts


def main():
    sys.path.insert(0, sys.argv[1])
    import lendec  # author module (read in full; pure function, no I/O)
    tot = {}
    for spec in sys.argv[2:]:
        elf, s, n = spec.split(":"); s, n = int(s, 0), int(n, 0)
        buf, starts = region_bytes(elf, s, n)
        cats, wrong = {}, []
        for k in range(n):
            ol, hexb, asm = decode_at(elf, s + k)
            dl, why = lendec.decode_len(buf, k)
            bad = "(bad)" in asm or asm.startswith(".byte")  # incl. "lock (bad)", "ljmp (bad)"
            if bad:
                c = "BAD-REJECTED" if dl is None else "BAD-ACCEPTED"
            elif dl is None:
                c = "LENDEC-NONE"
            elif dl == ol:
                c = "AGREE"
            else:
                c = "WRONG"; wrong.append((k, dl, ol, hexb, asm, k in starts))
            cats[c] = cats.get(c, 0) + 1
            tot[c] = tot.get(c, 0) + 1
        ts = [k for k in starts]
        tagree = sum(1 for k in ts if lendec.decode_len(buf, k)[0] == decode_at(elf, s + k)[0])
        print(f"{elf}:{s:#x}+{n}: offsets={n} {dict(sorted(cats.items()))}; "
              f"reference instruction starts sized correctly: {tagree}/{len(ts)}")
        for k, dl, ol, hexb, asm, st in wrong:
            print(f"   WRONG off+{k} ({s + k:#x}) lendec={dl} objdump={ol} {hexb} {asm}"
                  f"{'   <-- a REAL instruction start' if st else ''}")
    print("TOTAL", dict(sorted(tot.items())))


if __name__ == "__main__":
    main()
