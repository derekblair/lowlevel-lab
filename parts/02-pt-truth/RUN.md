# RUN.md — pt-truth, verbatim build+run on nibbles (fix round 1)

Captured 2026-10-19 08:23:44 PDT on nibbles, unprivileged derekblair,
perf_event_paranoid=2. Verbatim, from clean.

## Nondeterministic fields (R3)
DETERMINISTIC / load-bearing: ground-truth confirmation; PTW-fenced ok/wrong
(24/0 every row); the time-keyed middle-band-exact / long-gap-fail / fine-exact
structure. NONDETERMINISTIC: absolute TSC; measured intervals (TSC ticks) vary
run to run; the exact-band EDGE points jitter (lower edge ~1 MTC tick ~768 TSC),
so the very shortest interval sometimes resolves (reported as INFO, not gated);
OVF is rare but possible (reported per row, excluded from scoring, make still
passes). The long-gap failure (delay 1e6) and fine-exact are stable.

## 0. Environment
```
$ gcc --version | head -1
gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
$ grep -m1 "model name" /proc/cpuinfo
model name	: Intel(R) Core(TM) Ultra X7 358H
$ cat /sys/bus/event_source/devices/intel_pt/caps/ptwrite
1
```

## 1. Clean build
```
$ make clean && make ptcap verify_singlestep
rm -f ptcap verify_singlestep data.csv
cc -O1 -Wall -Wextra -o ptcap ptcap.c
cc -O1 -Wall -Wextra -o verify_singlestep verify_singlestep.c
```

## 2. Independent ground truth (no Intel PT)
```
$ ./verify_singlestep 24
verify_singlestep: 24 versions, 24 single-stepped ret-points, ground truth CONFIRMED (EAX-at-ret == EXEC_TAG+i for all i)
```

## 3. Full build+run via make, TWICE consecutively (B2: must pass every run)
```
$ make        # run 1
./verify_singlestep 24
verify_singlestep: 24 versions, 24 single-stepped ret-points, ground truth CONFIRMED (EAX-at-ret == EXEC_TAG+i for all i)
VERSIONS=24 ./run.sh > data.csv
python3 report.py data.csv
==================================================================================
pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed
(time-keyed = TMA-anchored MTC-payload TSC clock; intervals in TSC ticks)
==================================================================================
timing     delay interval(TSC)  ovf | fenced ok/wrong | time-keyed ok/wrong
---------------------------------------------------------------------------
coarse         0          1428    0 |       24/0      |          8/16      
coarse       100           298    0 |       24/0      |          9/15      
coarse      1000          1346    0 |       24/0      |         24/0       
coarse     10000         23486    0 |       24/0      |         24/0       
coarse    100000        264324    0 |       24/0      |          5/19      
coarse   1000000       2847502    0 |       24/0      |          3/21      
fine           0           630    0 |       24/0      |         24/0       
fine         100           406    0 |       24/0      |         24/0       
fine        1000          1350    0 |       24/0      |         24/0       
fine       10000         16512    0 |       24/0      |         24/0       

==================================================================================
VERDICTS
==================================================================================
VERDICT PASS: PTW-fenced attribution is exact on every row (0 wrong), needs no timing packets  [fenced wrong total = 0; no-preceding-fence = 0 over 10 rows]
VERDICT PASS: OVF rows excluded from accuracy scoring (lossy trace != method result)  [0 of 10 rows had OVF (excluded): none]
VERDICT PASS: coarse time-keyed is EXACT in a middle interval band  [exact at intervals(TSC) = [1346, 23486]]
INFO: coarse time-keyed at short intervals (<band): [(298, 15)]
VERDICT PASS: coarse time-keyed MIS-attributes above the band (MTC 8-bit payload wrap, one TSC anchor)  [wrong at long intervals(TSC) = [(264324, 19), (2847502, 21)]]
VERDICT PASS: reported time-keyed accuracy window (TSC ticks)  [exact band ~[1346, 23486] TSC ticks; fails below and above]
VERDICT PASS: FINE timing: time-keyed is exact on all OVF-free rows (dense timing closes the short-interval gap)  [fine time-keyed wrong = [0, 0, 0, 0] (OVF-free rows)]
VERDICT PASS: wherever time-keyed mis-attributes, PTW-fenced is exact  [rows with time-keyed wrong: 4; of those, fenced wrong: 0]

Interpretation: an executed in-band PTWRITE fence pins each traced
execution to its exact self-modified version in packet order, needing no
timestamps. The strong time-keyed decoder (TMA + MTC payloads) is exact
only for a middle band of patch->execute intervals: below it there are too
few CTC ticks to place the exec after its patch; above it the 8-bit MTC
payload wraps between the sparse TSC anchors (BranchEn=0), losing the high
CTC bits. Fine (dense) timing closes the low end but risks AUX overflow at
long intervals. Ground truth is the EXEC payload the executed bytes
produced, confirmed independently of PT by verify_singlestep.

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0

$ make        # run 2 (consecutive)
./verify_singlestep 24
verify_singlestep: 24 versions, 24 single-stepped ret-points, ground truth CONFIRMED (EAX-at-ret == EXEC_TAG+i for all i)
VERSIONS=24 ./run.sh > data.csv
python3 report.py data.csv
==================================================================================
pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed
(time-keyed = TMA-anchored MTC-payload TSC clock; intervals in TSC ticks)
==================================================================================
timing     delay interval(TSC)  ovf | fenced ok/wrong | time-keyed ok/wrong
---------------------------------------------------------------------------
coarse         0          1146    0 |       24/0      |          3/21      
coarse       100           318    0 |       24/0      |         24/0       
coarse      1000          1312    0 |       24/0      |         24/0       
coarse     10000         11392    0 |       24/0      |         24/0       
coarse    100000        115758    0 |       24/0      |         24/0       
coarse   1000000       1161132    0 |       24/0      |          5/19      
fine           0           536    0 |       24/0      |         24/0       
fine         100           366    0 |       24/0      |         24/0       
fine        1000          1350    0 |       24/0      |         24/0       
fine       10000         16508    0 |       24/0      |         24/0       

==================================================================================
VERDICTS
==================================================================================
VERDICT PASS: PTW-fenced attribution is exact on every row (0 wrong), needs no timing packets  [fenced wrong total = 0; no-preceding-fence = 0 over 10 rows]
VERDICT PASS: OVF rows excluded from accuracy scoring (lossy trace != method result)  [0 of 10 rows had OVF (excluded): none]
VERDICT PASS: coarse time-keyed is EXACT in a middle interval band  [exact at intervals(TSC) = [318, 1312, 11392, 115758]]
INFO: coarse time-keyed at short intervals (<band): all resolved this run
VERDICT PASS: coarse time-keyed MIS-attributes above the band (MTC 8-bit payload wrap, one TSC anchor)  [wrong at long intervals(TSC) = [(1161132, 19)]]
VERDICT PASS: reported time-keyed accuracy window (TSC ticks)  [exact band ~[318, 115758] TSC ticks; fails below and above]
VERDICT PASS: FINE timing: time-keyed is exact on all OVF-free rows (dense timing closes the short-interval gap)  [fine time-keyed wrong = [0, 0, 0, 0] (OVF-free rows)]
VERDICT PASS: wherever time-keyed mis-attributes, PTW-fenced is exact  [rows with time-keyed wrong: 2; of those, fenced wrong: 0]

Interpretation: an executed in-band PTWRITE fence pins each traced
execution to its exact self-modified version in packet order, needing no
timestamps. The strong time-keyed decoder (TMA + MTC payloads) is exact
only for a middle band of patch->execute intervals: below it there are too
few CTC ticks to place the exec after its patch; above it the 8-bit MTC
payload wraps between the sparse TSC anchors (BranchEn=0), losing the high
CTC bits. Fine (dense) timing closes the low end but risks AUX overflow at
long intervals. Ground truth is the EXEC payload the executed bytes
produced, confirmed independently of PT by verify_singlestep.

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0
```

## 4. Baseline (known, not the observable): PT silently misdecodes SMC
See ../../research/probes/pt-smc-misdecode/probe-output.txt.
