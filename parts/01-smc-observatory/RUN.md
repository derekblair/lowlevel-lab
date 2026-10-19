# RUN.md — smc-observatory, verbatim build+run on nibbles

Captured 2026-10-19 07:30:46 PDT on nibbles. Commands run exactly
as shown, from a clean state. No paraphrase. perf_event_paranoid=2, unprivileged user derekblair.

## 0. Environment (informational)
```
$ gcc --version | head -1
gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
$ python3 --version
Python 3.12.3
$ grep -m1 "model name" /proc/cpuinfo; nproc
model name	: Intel(R) Core(TM) Ultra X7 358H
16
$ cat /proc/sys/kernel/perf_event_paranoid
2
```

## 1. Clean build
```
$ make clean && make smcobs
rm -f smcobs data.csv
cc -O2 -Wall -Wextra -pthread -o smcobs smcobs.c
$ echo exit=$?
exit=0
```

## 2. Smoke test (must reproduce the reviewer c02-probe reference)
```
$ make smoke
sweep,0,P,cpu_core,0,8,smc,1.9999,710.7,0
sweep,0,P,cpu_core,0,64,smc,0.0000,4.9,0
sweep,5,E,cpu_atom,0,512,smc,1.0000,149.2,0
sweep,5,E,cpu_atom,0,1024,smc,0.0000,5.8,0
sweep,13,LP-E,cpu_atom,0,512,smc,0.9999,270.3,0
```
Reference (review/evidence/presearch/c02-probe/sweep.txt): P@same-line=2.000,
P@next-line=0; E/LP-E@same-1KiB=1.000, @next-1KiB=0. Reproduced above
(P prints 1.9999 = 399998/200000; the reviewer probe printed %.3f -> "2.000";
same measurement, see VERDICT 8 and the README "Precision" note).

## 3. Full sweep + report
```
$ CPUS="0 5 13" REPEATS=5 ./run.sh > data.csv; echo run_exit=$?
run_exit=0
$ wc -l data.csv
423 data.csv
$ python3 -I report.py data.csv; echo report_exit=$?
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

placement: code at byte 1536 (line 24, 1KiB-subpage 1)
  store@ |     8   512  1023  1024  1472  1543  1600  2000  2047  2048  3072
  --------------------------------------------------------------------------
      P |  0.00  0.00  0.00  0.00  0.00  2.00  0.00  0.00  0.00  0.00  0.00
      E |  0.00  0.00  0.00  1.00  1.00  1.00  1.00  1.00  1.00  0.00  0.00
   LP-E |  0.00  0.00  0.00  1.00  1.00  1.00  1.00  1.00  1.00  0.00  0.00

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
  exec=E    writer=P    XMC   median=113314.2 (n=5)
  exec=LP-E writer=P    SMC   median=0.0 (n=5)
  exec=LP-E writer=P    XMC   median=36710.6 (n=5)
  exec=P    writer=E    SMC   median=207992.8 (n=5)
  exec=P    writer=P    SMC   median=143105.6 (n=5)
VERDICT PASS: XMC counter present on Darkmont executor (asymmetric observability)  [P-core cross-modifying clears fold into SMC/COUNT; only Darkmont exposes XMC]

torn-fetch probe (reads that were neither old nor new value):
  exec=E    writer=P    torn=0 over 5 runs
  exec=LP-E writer=P    torn=0 over 5 runs
  exec=P    writer=E    torn=0 over 5 runs
VERDICT PASS: no torn instruction fetch observed on this part (OBSERVED, not guaranteed)  [total torn reads=0]

ALL VERDICTS PASS
report_exit=0
```
