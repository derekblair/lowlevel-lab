# RUN.md — x86-lattice, verbatim build+run on nibbles (fix round 1)

Captured 2026-10-19 10:10:05 PDT on nibbles, user derekblair, under `env -i` (HOME, PATH=/usr/local/bin:/usr/bin:/bin, LANG=C.UTF-8).

## Determinism
Deterministic for a given toolchain and set of /usr/bin binaries: the ground-truth
corpus is compiled fresh each run (gcc -O2) and the reference arm reads this system's
binaries, so exact counts are specific to this machine (gcc and binutils versions below).
objdump is the authority; every VERDICT below is computed from this run.

## Environment
```
$ python3 --version
Python 3.12.3
$ gcc --version|head -1
gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
$ objdump --version|head -1
GNU objdump (GNU Binutils for Ubuntu) 2.42
```

## make (compile ground-truth corpus, superset-decode every offset, resync stats, lattice, VERDICTs)
```
$ make
python3 superset.py
==============================================================================
x86-64 superset-decode lattice + resync statistics  (authority: objdump -w -z)
Linn & Debray CCS'03 §3.1: errors "resynchronize ... within just one or
 two instructions"; Andriesse et al. 2016 §3 restates it as "two or three".
 Measured here over a corpus, with and without chains through a (bad).
==============================================================================

GROUND TRUTH — self-built gcc -O2 objects with symbols (every code section;
  sweep clean and every function entry confirmed by the symbol table):
  region                                  n  med   Q1   Q3  P<=1  P<=2  P<=3  max never   (bad)-free med/P<=2
  gt.c [550B 1sec 8fn]                  391    2    1    3   48%   73%   86%   12     0      1 / 80%
  smcobs.c [3150B 3sec 10fn]           2395    2    1    3   47%   70%   82%   13     5      1 / 75%
  ptcap.c [1532B 2sec 2fn]             1171    2    1    3   49%   73%   85%   10     2      1 / 78%
  verify_singlestep.c [922B 3sec 3fn]    702    2    1    3   42%   66%   80%   10     7      2 / 70%
  rule.c [1292B 2sec 5fn]               976    1    1    3   52%   74%   85%   14     2      1 / 80%
  uflags.c [1324B 3sec 18fn]            944    1    1    3   57%   75%   85%   11     4      1 / 77%
  refine.c [2270B 2sec 13fn]           1724    2    1    3   49%   69%   80%   12     2      1 / 75%
  smc.c [137B 2sec 2fn]                  97    2    1    4   43%   62%   73%    7     2      2 / 65%

REFERENCE DECODE — /usr/bin .text (linear sweep = reference boundaries, NOT
  ground truth for a stripped binary; capped at an instruction boundary):
  region                                  n  med   Q1   Q3  P<=1  P<=2  P<=3  max never   (bad)-free med/P<=2
  true [10786B .text]                  8279    2    1    5   34%   51%   63%   47     8      1 / 78%
  cat [15746B .text]                  12107    2    1    5   35%   52%   65%   47     7      1 / 79%
  wc [27586B .text]                   21366    2    1    5   34%   51%   63%  101     8      1 / 74%
  sort [49144B .text]                 37450    2    1    4   37%   56%   69%   44     5      1 / 78%
  ls [49149B .text]                   36682    2    1    4   40%   60%   72%   55     3      1 / 76%

pooled (instructions to resync; (bad)-free = chains that never touch a (bad)):
  GROUND TRUTH  n=  8400 median=2 Q1=1 Q3=3 P<=1=49% P<=2=71% P<=3=83% max=14 never=24
                (bad)-free: n=7425 median=1 P<=1=54% P<=2=76% P<=3=87% max=13
  REFERENCE     n=115884 median=2 Q1=1 Q3=4 P<=1=37% P<=2=56% P<=3=68% max=101 never=31
                (bad)-free: n=73379 median=1 P<=1=54% P<=2=77% P<=3=88% max=19

lendec vs objdump, ground truth (offsets whose decode ends inside the region):
  at true boundaries: {'AGREE': 2715, 'WRONG': 0, 'LENDEC-NONE': 38, 'BAD-ACCEPTED': 0, 'BAD-REJECTED': 0}
  at every offset:    {'AGREE': 9816, 'WRONG': 0, 'LENDEC-NONE': 856, 'BAD-ACCEPTED': 191, 'BAD-REJECTED': 302}

wrote lattice.html: SVG lattice of gt.c:work() [128B] + histogram; per-offset data and corpus stats in <script id=data>
VERDICT PASS: authority: windowed per-offset length == linear objdump -w -z decode at every true boundary  [39249/39249 over 23 regions; every linear decode contiguous, summing to its region]
VERDICT PASS: ground truth: every section's sweep is clean and every function entry is a sweep boundary  [18 sections, 61 function entries confirmed by the symbol table, 0 excluded]
VERDICT PASS: lendec never mis-sizes a compiler-intended instruction, and sizes >= 95% of them  [true boundaries: AGREE 2715 WRONG 0 NONE 38 of 2753]
VERDICT PASS: the corpus is not an anecdote: >= 2000 ground-truth chains from >= 5 objects; >= 3 reference binaries  [ground truth n=8400 from 8 objects; reference n=115884 from 5 binaries]
VERDICT PASS: claim 1: Linn & Debray's 'one or two' describes the TYPICAL chain (ground-truth median is 1 or 2)  [median 2 over n=8400]
VERDICT PASS: claim 2: ...but it is not a bound: >= 10% of ground-truth chains need 3+ instructions  [P(>2) = 29%, max 14]
VERDICT PASS: claim 3: Andriesse et al.'s 'two or three' covers >= 75% of ground-truth chains  [P(<=3) = 83%]
VERDICT PASS: claim 4: the (bad) policy is the hinge: (bad)-free median < all-chain median, in BOTH arms  [ground truth 2 -> 1; reference 2 -> 1]
VERDICT PASS: claim 5: /usr/bin's heavier tail is (bad)-driven: (bad)-free P<=2 within 5 points of ground truth  [all chains: reference 56% vs ground truth 71%; (bad)-free: 77% vs 76%]
VERDICT PASS: lattice.html is a real lattice: arcs + merge markers + histogram + re-derivable data (C09-5, B3)  [re-derived from data: arcs 127 (drawn 127), merges 52 (drawn 52), histogram 4 bars (drawn 4, data match=True), corpus stats embedded=True]

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0
```

## The lattice visualization
lattice.html is self-contained (inline CSS + SVG; per-offset data and corpus stats in
<script id=data>; no external refs). Rendered headless with a throwaway profile:
```
$ firefox --headless --no-remote --profile <tmp> --window-size=1500,1100 --screenshot lattice.png file://$PWD/lattice.html
exit=0  png_bytes=215006
$ grep -c "src=\|href=" lattice.html   # external references
0
```
