# RUN.md — x86-lattice, verbatim build+run on nibbles

Captured 2026-10-19 09:11:28 PDT on nibbles, user derekblair.

## Determinism
The self-built target is compiled fresh each run (gcc -O2); its exact bytes
can vary with the gcc version, so the resync numbers are reported as
median/fraction, not a fixed vector. The VERDICTs (true-boundary agreement,
resync median <=3, viz embeds data) are stable. objdump is the authority.

## Environment
```
$ python3 --version
Python 3.12.3
$ gcc --version|head -1
gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
$ objdump --version|head -1
GNU objdump (GNU Binutils for Ubuntu) 2.42
```

## make (build target, superset-decode at every offset, resync stats, viz, VERDICTs)
```
$ make
python3 superset.py
============================================================================
x86-64 superset-decode lattice + resync statistics
(authoritative per-offset decode = objdump; lendec agreement reported)
Linn & Debray CCS 2003 §3.1: errors "resynchronize quite quickly - often
 within just one or two instructions" -- quantified here on real x86-64.
============================================================================

self-built work() [-O2, 126B, ground truth = symbols]
  lendec vs objdump on TRUE boundaries (real instrs): 38/38; on ALL offsets: 105/126 (83%); undecodable-by-lendec: 21 (all deferred to objdump, which powers the lattice/stats)
  misaligned starts that resync: 88; never-resync: 0
  resync length: median 1.0 instrs, max 5; within ≤2 instrs: 81%  (bytes: median 3.0)

/usr/bin/true .text head [163B, reference-decode (stripped caveat)]
  lendec vs objdump on TRUE boundaries (real instrs): 45/48; on ALL offsets: 128/161 (79%); undecodable-by-lendec: 24 (all deferred to objdump, which powers the lattice/stats)
  misaligned starts that resync: 111; never-resync: 2
  resync length: median 2 instrs, max 10; within ≤2 instrs: 68%  (bytes: median 5)

wrote lattice.html (machine-checkable: data embedded in <script id=data>)
VERDICT PASS: lendec sizes EVERY compiler-intended instruction correctly (true boundaries)  [true-boundary agreement 38/38; all-offset 105/126 (83% -- misaligned bytes hit opcodes outside lendec's scoped table; those offsets defer to objdump)]
VERDICT PASS: most misaligned decodes RESYNC (few or none run off forever)  [resync=88 never=0]
VERDICT PASS: resync is quick: median ≤ 3 instructions (quantifies Linn & Debray §3.1)  [median=1.0 insns, ≤2-instr fraction=0.81]
VERDICT PASS: the HTML lattice embeds the data for checking (C09-5)  [lattice.html]
VERDICT PASS: real /usr/bin/true region also analysed and resynchronises  [resync=111]

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0
```

## The lattice visualization
make writes lattice.html (self-contained: inline CSS + data in <script id=data>,
no external refs). Render headless, e.g.:
  firefox --headless --screenshot=lattice.png file://$PWD/lattice.html
