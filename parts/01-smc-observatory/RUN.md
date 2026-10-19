# RUN.md — smc-observatory, verbatim build+run on nibbles

Captured 2026-10-19 07:42:56 PDT on nibbles, unprivileged user derekblair,
perf_event_paranoid=2. Commands run exactly as shown, from clean. No paraphrase.

## Nondeterministic fields (R3)
Load-bearing and DETERMINISTIC across repeats: the sweep `clears_per_iter`
values (0 / ~1 / ~2) and hence the detection-window boundaries and all 10
VERDICTs. NONDETERMINISTIC (vary run to run, not asserted byte-exactly):
`tsc_per_iter` everywhere (frequency/thermal); the in-window clears shortfall
below 2.0/1.0 (2-42 counts/2e5, see README precision note); the `xcore`
clears-per-million medians (scheduling-dependent). torn counts are expected 0.

## 0. Environment (informational)
```
$ gcc --version | head -1
gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
$ python3 --version
Python 3.12.3
$ grep -m1 "model name" /proc/cpuinfo; nproc
model name	: Intel(R) Core(TM) Ultra X7 358H
16
```

## 1. Clean build
```
$ make clean && make smcobs
rm -f smcobs data.csv
cc -O2 -Wall -Wextra -pthread -o smcobs smcobs.c
```

## 2. Smoke test (reproduces the reviewer c02-probe reference)
```
$ make smoke
sweep,0,P,cpu_core,0,8,smc,1.9999,702.1,0
sweep,0,P,cpu_core,0,64,smc,0.0000,5.0,0
sweep,5,E,cpu_atom,0,512,smc,1.0000,151.7,0
sweep,5,E,cpu_atom,0,1024,smc,0.0000,5.9,0
sweep,13,LP-E,cpu_atom,0,512,smc,0.9999,268.3,0
```
Reference (review/evidence/presearch/c02-probe/sweep.txt): P same-line=2.000,
next-line=0; E/LP-E same-1KiB=1.000, next-1KiB=0. Reproduced (P prints ~1.9999
from the small variable shortfall; VERDICT 8 compares at the reference %.3f).

## 3. Torn-fetch probe is non-vacuous (REVIEW-01-build B1 fix)
mov eax,imm32 straddles a 64B line; writer changes BOTH halves with ordered
aligned 2-byte stores so memory never holds 0x11114444. An executor reading
0x11114444 (or any non-{A,B,0x33332222} value) is a genuine torn fetch.
```
$ ./smcobs torn 0 5     # writer P-core, executor E-core
torn,5,E,0,P,-,0,5000000,0
$ ./smcobs torn 4 0     # writer E-core, executor P-core
torn,0,P,4,E,-,0,5000000,0
# CSV: torn,exec_cpu,exec_cls,writer_cpu,writer_cls,-,TORN+other,legit,TORN_exact
# field 7 (TORN+other) = 0 here: no torn fetch observed on this part (OBSERVED,
# not guaranteed); field 8 legit = 5000000 confirms the classifier counted reads.
```

## 4. Full sweep + report (this is what `make` runs by default, B2 fix)
```
$ make        # .DEFAULT_GOAL := run  -> builds, sweeps, reports
CPUS="0 5 13" REPEATS=5 ./run.sh > data.csv
python3 -I report.py data.csv
========================================================================
SMC machine-clear detection window — median clears/iteration vs store offset
(~2.0 = P-core nuke, ~1.0 = Darkmont nuke, 0 = no clear; code is 6 bytes)
========================================================================

placement: code at byte 0 (line 0, 1KiB-subpage 0)
  store@ |     8    32    63    64   128   256   512  1023  1024  1536  2047  2048  4096  8192
  --------------------------------------------------------------------------------------------
      P |  2.00  2.00  2.00  0.00  0.00  0.00  0.00  0.00  0.00  0.00  0.00  0.00  0.00  0.00
      E |  1.00  1.00  1.00  1.00  1.00  1.00  1.00  1.00  0.00  0.00  0.00  0.00  0.00  0.00
   LP-E |  1.00  1.00  1.00  1.00  1.00  1.00  1.00  1.00  0.00  0.00  0.00  0.00  0.00  0.00
  (worst per-cell spread max-min over A repeats: 0.00 clears/iter)

placement: code at byte 1536 (line 24, 1KiB-subpage 1)
  store@ |     8   512  1023  1024  1472  1543  1600  2000  2047  2048  3072
  --------------------------------------------------------------------------
      P |  0.00  0.00  0.00  0.00  0.00  2.00  0.00  0.00  0.00  0.00  0.00
      E |  0.00  0.00  0.00  1.00  1.00  1.00  1.00  1.00  1.00  0.00  0.00
   LP-E |  0.00  0.00  0.00  1.00  1.00  1.00  1.00  1.00  1.00  0.00  0.00
  (worst per-cell spread max-min over B repeats: 0.00 clears/iter)

========================================================================
VERDICTS (grep-able)
========================================================================
VERDICT PASS: P: SMC clears ONLY within a 64-byte window of the executing code  [in-window median min=2.00 (want>=0.9); out-window median max=0.00 (want=0)]
VERDICT PASS: E: SMC clears ONLY within a 1024-byte window of the executing code  [in-window median min=1.00 (want>=0.9); out-window median max=0.00 (want=0)]
VERDICT PASS: LP-E: SMC clears ONLY within a 1024-byte window of the executing code  [in-window median min=1.00 (want>=0.9); out-window median max=0.00 (want=0)]
VERDICT PASS: P and Darkmont granularities DIFFER (store@512: P quiet, E clears)  [P@512=0.00, E@512=1.00]
VERDICT PASS: Intel 248966 3.6.8.1 1KiB-subpage rule matches Darkmont (E/LP-E)  [E@1023=1.00 (same subpage, clears), E@1024=0.00 (next subpage, quiet)]
VERDICT PASS: ...and does NOT describe Cougar Cove (P window is tighter, 64B)  [P@63=2.00 (same line), P@64=0.00 (next line)]
VERDICT PASS: detection window tracks the CODE's subpage, not the page base (placement B)  [E code@1536: store@8=0.00, store@2000=1.00, store@2048=0.00]
VERDICT PASS: in-window clears/iter: P==2.000, Darkmont==1.000 at reviewer %.3f precision  [P@8=1.9999->%.3f=2.0, E@512=1.0000, LP-E@512=1.0000; raw delta = ~2 counts/200k = ENABLE/DISABLE boundary, direction+magnitude exact]

cross-modifying code (executor counts, clears per 1e6 executes):
  exec=E    writer=P    SMC   median=0.0 (n=5)
  exec=E    writer=P    XMC   median=114523.4 (n=5)
  exec=LP-E writer=P    SMC   median=0.0 (n=5)
  exec=LP-E writer=P    XMC   median=37304.8 (n=5)
  exec=P    writer=E    SMC   median=119154.6 (n=5)
  exec=P    writer=P    SMC   median=147297.8 (n=5)
VERDICT PASS: cross-core mod: Darkmont books XMC (SMC~=0), P books SMC (no XMC counter)  [E executor SMC=0.0/1e6 XMC=114523.4/1e6; P executor SMC=147297.8/1e6]

torn-fetch probe (reads that were neither old nor new value):
  exec=E    writer=P    torn=0 over 5 runs
  exec=LP-E writer=P    torn=0 over 5 runs
  exec=P    writer=E    torn=0 over 5 runs
VERDICT PASS: no torn instruction fetch observed on this part (OBSERVED, not guaranteed)  [total torn reads=0]

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0
```
