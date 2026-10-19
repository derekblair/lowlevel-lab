#!/usr/bin/env python3
"""patched_kernel.py — round-2 continuation of round 1's code_vs_recipe.py (a)/(b):
take the author's `correct` kernel BYTES, overwrite every DC CVAU / IC IVAU / ISB
word with DSB ISH (no builder involved), and run the fix-round interp on it.
Expected now: STALE. Also the `none` kernel. usage: python3 -I patched_kernel.py CLONE_PART_DIR"""
import sys
sys.path.insert(0, sys.argv[1])
import sanitize as S
from icache_model import Config
code, e, slot = S.build_kernel(S.KERNELS["correct"])
code = bytearray(code); DSB = (0xD5033B9F).to_bytes(4, "little"); n = 0
for off in range(0, len(code) - 4, 4):
    op, _ = S.decode(int.from_bytes(code[off:off + 4], "little"))
    if op in ("dc", "ic", "isb"):
        code[off:off + 4] = DSB; n += 1
ops = [S.decode(int.from_bytes(code[o:o + 4], "little"))[0] for o in range(0, len(code), 4)]
x0, m = S.interp(bytes(code), e, slot, Config(0, 0))
print(f"(a') correct kernel with {n} DC/IC/ISB words overwritten by DSB ISH (remaining dc/ic/isb: "
      f"{sum(o in ('dc', 'ic', 'isb') for o in ops)}): x0={x0} -> {'STALE' if x0 == S.SLOT_OLD else 'FRESH'}; missing={m.diagnose(slot - S.CODEBASE)[1]}")
code_n, en, sn = S.build_kernel(S.KERNELS["none"])
xn, mn = S.interp(code_n, en, sn, Config(0, 0))
print(f"(b') none kernel: x0={xn} -> {'STALE' if xn == S.SLOT_OLD else 'FRESH'}; missing={mn.diagnose(sn - S.CODEBASE)[1]}")
