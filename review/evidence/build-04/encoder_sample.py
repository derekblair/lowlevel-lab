#!/usr/bin/env python3
"""Reviewer's encoder differential test for BUILD-04 (REVIEW-01 §6/P4-2: sample chosen by the
reviewer, not the author's _CASES). Seeded random instances of every form a64asm.py supports,
encoded by the author's a64asm and by GNU aarch64-linux-gnu-as; compared word-for-word.
usage: encoder_sample.py PARTDIR SEED N"""
import os, random, subprocess, sys, tempfile
sys.path.insert(0, sys.argv[1]); import a64asm as A
r = random.Random(int(sys.argv[2])); N = int(sys.argv[3])
R = lambda: f"x{r.randrange(0, 31)}"
RS = lambda: r.choice([R(), "sp"])
forms = [
 lambda: (lambda d, i, s: (f"movz {d}, #{i:#x}, lsl #{s}", A.movz(d, i, s)))(R(), r.randrange(65536), r.choice([0, 16, 32, 48])),
 lambda: (lambda d, i, s: (f"movk {d}, #{i:#x}, lsl #{s}", A.movk(d, i, s)))(R(), r.randrange(65536), r.choice([0, 16, 32, 48])),
 lambda: (lambda d, n, i: (f"add {d}, {n}, #{i}", A.add_imm(d, n, i)))(RS(), RS(), r.randrange(4096)),
 lambda: (lambda d, n, i: (f"sub {d}, {n}, #{i}", A.sub_imm(d, n, i)))(RS(), RS(), r.randrange(4096)),
 lambda: (lambda t, n, o: (f"str {t}, [{n}, #{o}]", A.str_imm(t, n, o)))(R(), RS(), 8 * r.randrange(4096)),
 lambda: (lambda t, n, o: (f"ldr {t}, [{n}, #{o}]", A.ldr_imm(t, n, o)))(R(), RS(), 8 * r.randrange(4096)),
 lambda: (lambda t, n, o: (f"str w{t[1:]}, [{n}, #{o}]", A.strw_imm(f"w{t[1:]}", n, o)))(R(), RS(), 4 * r.randrange(4096)),
 lambda: (lambda n: (f"ret {n}", A.ret(n)))(R()),
 lambda: (lambda n: (f"br {n}", A.br(n)))(R()),
 lambda: (lambda n: (f"blr {n}", A.blr(n)))(R()),
 lambda: (lambda t, o: (f"cbz {t}, .{o:+d}", A.cbz(t, o)))(R(), 4 * r.randrange(-(1 << 18), 1 << 18)),
 lambda: (lambda o: (f"b .{o:+d}", A.b(o)))(4 * r.randrange(-(1 << 25), 1 << 25)),
 lambda: ("nop", A.nop()),
 lambda: (lambda t: (f"dc cvau, {t}", A.dc_cvau(t)))(R()),
 lambda: (lambda t: (f"ic ivau, {t}", A.ic_ivau(t)))(R()),
 lambda: ("dsb ish", A.dsb_ish()), lambda: ("dsb ishst", A.dsb_ishst()), lambda: ("isb", A.isb()),
]
picks = [r.choice(forms)() for _ in range(N)]
with tempfile.TemporaryDirectory() as d:
    s, o = os.path.join(d, "t.s"), os.path.join(d, "t.o")
    open(s, "w").write(".text\n" + "\n".join(a for a, _ in picks) + "\n")
    subprocess.run(["aarch64-linux-gnu-as", s, "-o", o], check=True)
    dump = subprocess.run(["aarch64-linux-gnu-objdump", "-d", o], check=True, capture_output=True, text=True).stdout
ref = [bytes.fromhex(ln.split("\t")[1].strip())[::-1] for ln in dump.splitlines() if ln.startswith("  ") and ":\t" in ln]
assert len(ref) == N
bad = [(a, m.hex(), g.hex()) for (a, m), g in zip(picks, ref) if m != g]
for a, m, g in bad: print(f"MISMATCH {a!r}: a64asm={m} gnu-as={g}")
print(f"seed={sys.argv[2]} N={N}: {N-len(bad)}/{N} a64asm encodings byte-identical to aarch64-linux-gnu-as")
