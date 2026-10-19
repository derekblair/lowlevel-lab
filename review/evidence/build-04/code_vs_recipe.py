#!/usr/bin/env python3
"""Reviewer test for BUILD-04: does the sanitizer's verdict depend on the PROGRAM, or only on the
recipe list build_kernel() was given? Uses the author's own sanitize.py functions unmodified.
usage: code_vs_recipe.py PARTDIR"""
import sys
sys.path.insert(0, sys.argv[1])
import sanitize as S
cfg = S.CONFIGS[next(k for k in S.CONFIGS if "IDC=0" in k and "DIC=0" in k)]
SUB = None  # set below to DSB ISH (the interpreter cannot decode NOP)
def verdict(code, trace, slot):
    x0 = S.interp(code, 0, slot, cfg, trace, True)
    return "FRESH" if x0 == S.SLOT_NEW else "STALE"

# (a) correct kernel's machine code with every maintenance instruction replaced by NOP,
#     but the original recipe trace passed in
code, _, _, trace, slot = S.build_kernel(S.KERNELS["correct"])
words = [code[i:i+4] for i in range(0, len(code), 4)]
maint = {S.A.dc_cvau("x9"), S.A.ic_ivau("x9"), S.A.dsb_ish(), S.A.isb()}
SUB = S.A.dsb_ish()
stripped = b"".join(SUB if (w in maint and w != SUB) else w for w in words)
n_nopped = sum(1 for w in words if w in maint and w != SUB)
print(f"(a) 'correct' code with its {n_nopped} DC/IC/ISB replaced by DSB ISH (no DC, no IC, no ISB left) + 'correct' recipe -> {verdict(stripped, trace, slot)}")
# (b) the 'none' kernel's code (no maintenance at all) + the 'correct' recipe trace
code_none, _, _, _, slot_n = S.build_kernel(S.KERNELS["none"])
print(f"(b) 'none' kernel code + 'correct' recipe            -> {verdict(code_none, trace, slot_n)}")
# (c) the 'correct' kernel's code + an EMPTY recipe trace
print(f"(c) 'correct' kernel code + empty recipe             -> {verdict(code, [], slot)}")
# (d) does the program's code even reach the cache model? (Machine is imported but never built)
import inspect
print("(d) icache_model.Machine instantiated anywhere in sanitize.py:",
      "Machine(" in inspect.getsource(S))
