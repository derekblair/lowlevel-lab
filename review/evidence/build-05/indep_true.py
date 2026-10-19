#!/usr/bin/env python3
"""indep_true.py — reviewer check of superset.py's /usr/bin/true secondary sample.

usage: python3 -I indep_true.py CLONE_PART_DIR [ELF] [MAXBYTES]
Compares the author's region_from_symbol_elf() (objdump -d, default 7-byte line
wrap) with a -w parse (one line per instruction), and the author's per-offset
objdump_len_at() with a -w decode, then recomputes the resync stats.
"""
import os, re, statistics as st, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indep_lattice import LINEW, wide_decode, resync, summ  # reviewer's own helpers


def text_head_wide(path, maxbytes):
    out = subprocess.run(["objdump", "-d", "-w", "-j", ".text", path],
                         capture_output=True, text=True, check=True).stdout
    raw, bounds, base, asm = bytearray(), set(), None, {}
    for ln in out.splitlines():
        m = LINEW.match(ln)
        if not m:
            continue
        a = int(m.group(1), 16)
        base = a if base is None else base
        if a - base >= maxbytes:
            break
        bounds.add(a - base); asm[a - base] = m.group(3).strip()
        raw += bytes(int(x, 16) for x in m.group(2).split())
    bounds.add(len(raw))
    return bytes(raw), bounds, asm, base


def main():
    part = sys.argv[1]
    elf = sys.argv[2] if len(sys.argv) > 2 else "/usr/bin/true"
    mx = int(sys.argv[3]) if len(sys.argv) > 3 else 160
    sys.path.insert(0, part)
    import superset
    a_raw, a_b = superset.region_from_symbol_elf(elf, mx)
    raw, b, asm, base = text_head_wide(elf, mx)
    print(f"{elf} .text @ {base:#x}, maxbytes={mx}: author N={len(a_raw)} bounds={len(a_b)}; "
          f"-w N={len(raw)} bounds={len(b)}; same bytes: {a_raw == raw}")
    print(f"  author 'true boundaries' NOT instruction starts (-w): {sorted(a_b - b)}")
    for k in sorted(a_b - b):
        start = max(x for x in b if x < k)
        print(f"    off {k}: inside the {asm.get(start, '?')!r} at off {start} "
              f"({len(bytes(raw[start:min(y for y in b if y > start)]))} bytes)")
    print(f"  instruction starts missing from author's set: {sorted(b - a_b)}")
    N = len(raw)
    al = [superset.objdump_len_at(raw, k) for k in range(N)]
    wl = [wide_decode(raw, k)[0] for k in range(N)]
    d = [k for k in range(N) if al[k] != wl[k]]
    print(f"  per-offset length author vs -w: {N - len(d)}/{N} agree; differ at {[(k, al[k], wl[k]) for k in d]}")
    import lendec
    tb = [k for k in sorted(b) if k < N]
    ld = {k: lendec.decode_len(raw, k)[0] for k in range(N)}
    print(f"  lendec vs -w on REAL instruction starts: {sum(ld[k] == wl[k] for k in tb)}/{len(tb)}; "
          f"misses: {[(k, ld[k], wl[k], asm[k]) for k in tb if ld[k] != wl[k]]}")
    print("  author's resync (author bounds+lengths): " + summ(*resync(len(a_raw), a_b, [superset.objdump_len_at(a_raw, k) for k in range(len(a_raw))])))
    print("  corrected (-w bounds+lengths):            " + summ(*resync(N, b, wl)))


if __name__ == "__main__":
    main()
