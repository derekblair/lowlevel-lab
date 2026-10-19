# RUN.md — pt-truth, verbatim build+run on nibbles (post-clearance: pinned per core class)

Captured 2026-10-19 10:19:54 PDT on nibbles, unprivileged derekblair,
perf_event_paranoid=2, under `env -i`. Verbatim, from clean.

## Nondeterministic fields (R3)
DETERMINISTIC / load-bearing: ground-truth confirmation; PTW-fenced ok/wrong (24/0 every
row, every core class); per class, the time-keyed structure: exact over an interval band;
on Darkmont (E, LP-E) a long-gap failure starting at the predicted 196,608-TSC MTC-payload
wrap; on Cougar Cove (P) no long-gap failure; fine-exact; and the MTC-density gap between
classes. NONDETERMINISTIC: absolute TSC; measured intervals (TSC ticks) and MTC/TSC packet
counts vary run to run; the band's lower edge jitters (~1 MTC tick ~768 TSC), so the
shortest interval sometimes resolves (INFO, not gated); OVF is rare (reported per row,
excluded from scoring). Each sweep is pinned: CPU 0 = Cougar Cove P, 4 = Darkmont E,
12 = Darkmont LP-E.

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

## 3. Full build+run via make, THREE times consecutively (each pinned per core class)
```
$ make        # run 1
./verify_singlestep 24
verify_singlestep: 24 versions, 24 single-stepped ret-points, ground truth CONFIRMED (EAX-at-ret == EXEC_TAG+i for all i)
VERSIONS=24 ./run.sh > data.csv
python3 report.py data.csv
======================================================================================
pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed
(time-keyed = TMA-anchored MTC-payload TSC clock; intervals in TSC ticks;
 each sweep pinned to one CPU: P = Cougar Cove, E / LP-E = Darkmont)
======================================================================================
class timing     delay interval(TSC)  ovf     MTC   TSC | fenced ok/wrong | time-keyed ok/wrong
-----------------------------------------------------------------------------------------------
P     coarse         0          2346    0     238     1 |       24/0      |         24/0       
P     coarse       100          1100    0     162     1 |       24/0      |         24/0       
P     coarse      1000         23924    0     756     2 |       24/0      |         24/0       
P     coarse     10000        247062    0    7930     9 |       24/0      |         24/0       
P     coarse    100000        302644    0   30343    32 |       24/0      |         24/0       
P     coarse   1000000       7151048    0  246991   252 |       24/0      |         24/0       
P     fine           0          2408    0    1452     4 |       24/0      |         24/0       
P     fine         100           994    0    1269     3 |       24/0      |         24/0       
P     fine        1000         23542    0    5426    12 |       24/0      |         24/0       
P     fine       10000         30836    0   26548    54 |       24/0      |         24/0       
E     coarse         0          1478    0      32     1 |       24/0      |          6/18      
E     coarse       100           654    0      40     1 |       24/0      |         14/10      
E     coarse      1000          2886    0      50     1 |       24/0      |         24/0       
E     coarse     10000         25040    0      55     1 |       24/0      |         24/0       
E     coarse    100000        246736    0      80     1 |       24/0      |          2/22      
E     coarse   1000000       2496844    0     361     1 |       24/0      |          1/23      
E     fine           0          1150    0    1070     3 |       24/0      |         24/0       
E     fine         100           666    0     990     3 |       24/0      |         24/0       
E     fine        1000          3130    0    1832     4 |       24/0      |         24/0       
E     fine       10000         25654    0    7190    15 |       24/0      |         24/0       
LP-E  coarse         0           778    0      47     1 |       24/0      |         23/1       
LP-E  coarse       100           520    0      37     1 |       24/0      |         17/7       
LP-E  coarse      1000          2036    0      49     1 |       24/0      |         24/0       
LP-E  coarse     10000         17148    0      52     1 |       24/0      |         24/0       
LP-E  coarse    100000        168302    0      69     1 |       24/0      |         24/0       
LP-E  coarse   1000000       1693270    0     258     1 |       24/0      |          1/23      
LP-E  fine           0           782    0     931     3 |       24/0      |         24/0       
LP-E  fine         100           548    0     733     2 |       24/0      |         24/0       
LP-E  fine        1000          2068    0    1090     3 |       24/0      |         24/0       
LP-E  fine       10000         17188    0    4911    11 |       24/0      |         24/0       

======================================================================================
VERDICTS
======================================================================================
VERDICT PASS: PTW-fenced attribution is exact on every row of every core class, needs no timing packets  [fenced wrong total = 0; no-preceding-fence = 0 over 30 rows, classes ['P', 'E', 'LP-E']]
INFO: OVF rows excluded from time-keyed scoring (lossy trace != method result): 0 of 30: none
INFO: predicted MTC-payload wrap edge = 2^(mtc_period+8) CTC x TSC/CTC = 2^(3+8) x 192/2 = 196608 TSC ticks
VERDICT PASS: P: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [1100, 2346, 23924, 247062, 302644, 7151048]]
INFO: P: coarse time-keyed at short intervals (<band): all resolved this run
VERDICT PASS: P: NO long-gap mis-attribution: exact at the longest interval, >= 10x the predicted wrap edge (MTC every period, so the payload never wraps unseen)  [longest coarse interval 7151048 TSC: time-keyed wrong=0; predicted edge 196608]
VERDICT PASS: E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [2886, 25040]]
INFO: E: coarse time-keyed at short intervals (<band): [(654, 10), (1478, 18)]
VERDICT PASS: E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 25040 <= 2x196608; smallest long-gap failure 246736 >= 196608/2; wrong at long intervals = [(246736, 22), (2496844, 23)]]
VERDICT PASS: LP-E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [2036, 17148, 168302]]
INFO: LP-E: coarse time-keyed at short intervals (<band): [(520, 7), (778, 1)]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 168302 <= 2x196608; smallest long-gap failure 1693270 >= 196608/2; wrong at long intervals = [(1693270, 23)]]
VERDICT PASS: mechanism: at the longest gap Cougar Cove's trace carries >= 100x the MTC packets of each Darkmont class (BranchEn=0)  [MTC packets per capture: P 246991; E 361; LP-E 258 (TSC packets: P 252; E 1; LP-E 1)]
VERDICT PASS: FINE timing: time-keyed is exact on all OVF-free rows of every class (dense timing closes the short-interval gap)  [fine time-keyed wrong = [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('E', 0), ('E', 0), ('E', 0), ('E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0)]]
VERDICT PASS: wherever time-keyed mis-attributes, PTW-fenced is exact  [rows with time-keyed wrong: 7; of those, fenced wrong: 0]

Interpretation: an executed in-band PTWRITE fence pins each traced
execution to its exact self-modified version in packet order, needing no
timestamps, on every core class. The strong time-keyed decoder (TMA + MTC
payloads) is exact only over an interval band. Below it there are too few
CTC ticks to place the exec after its patch. Above it, on Darkmont (E,
LP-E), the BranchEn=0 trace carries only sporadic MTC packets and a single
TSC, so the 8-bit MTC payload wraps unobserved and the high CTC bits are
lost, starting at the predicted 2^(mtc_period+8) CTC edge. On Cougar Cove
(P) the trace carries an MTC every period, so the payload never wraps unseen
and long gaps stay exact. Fine (dense) timing closes the low end. Ground
truth is the EXEC payload the executed bytes produced, confirmed
independently of PT by verify_singlestep.

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0

$ make        # run 2
./verify_singlestep 24
verify_singlestep: 24 versions, 24 single-stepped ret-points, ground truth CONFIRMED (EAX-at-ret == EXEC_TAG+i for all i)
VERSIONS=24 ./run.sh > data.csv
python3 report.py data.csv
======================================================================================
pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed
(time-keyed = TMA-anchored MTC-payload TSC clock; intervals in TSC ticks;
 each sweep pinned to one CPU: P = Cougar Cove, E / LP-E = Darkmont)
======================================================================================
class timing     delay interval(TSC)  ovf     MTC   TSC | fenced ok/wrong | time-keyed ok/wrong
-----------------------------------------------------------------------------------------------
P     coarse         0          2386    0     161     1 |       24/0      |         24/0       
P     coarse       100          1022    0     161     1 |       24/0      |         24/0       
P     coarse      1000         26900    0    1073     3 |       24/0      |         24/0       
P     coarse     10000        249000    0    8167     9 |       24/0      |         24/0       
P     coarse    100000       2474150    0   60574    63 |       24/0      |         24/0       
P     coarse   1000000       5226452    0  216484   221 |       24/0      |         24/0       
P     fine           0          2350    0    2395     6 |       24/0      |         24/0       
P     fine         100          2116    0    1382     4 |       24/0      |         24/0       
P     fine        1000          3744    0    3865     9 |       24/0      |         24/0       
P     fine       10000         40064    0   27676    57 |       24/0      |         24/0       
E     coarse         0          1142    0      30     1 |       24/0      |          6/18      
E     coarse       100           660    0      44     1 |       24/0      |         18/6       
E     coarse      1000          2922    0      52     1 |       24/0      |         24/0       
E     coarse     10000         25084    0      53     1 |       24/0      |         24/0       
E     coarse    100000        247324    0      82     1 |       24/0      |          5/19      
E     coarse   1000000       2494902    0     360     1 |       24/0      |          1/23      
E     fine           0          1142    0    1116     3 |       24/0      |         24/0       
E     fine         100           896    0     972     3 |       24/0      |         24/0       
E     fine        1000          2884    0    1535     4 |       24/0      |         24/0       
E     fine       10000         25642    0    7209    15 |       24/0      |         24/0       
LP-E  coarse         0           778    0      44     1 |       24/0      |         21/3       
LP-E  coarse       100           524    0      38     1 |       24/0      |         17/7       
LP-E  coarse      1000          2062    0      51     1 |       24/0      |         24/0       
LP-E  coarse     10000         17158    0      51     1 |       24/0      |         24/0       
LP-E  coarse    100000        168350    0      71     1 |       24/0      |         24/0       
LP-E  coarse   1000000       1689298    0     259     2 |       24/0      |          2/22      
LP-E  fine           0           778    0     903     3 |       24/0      |         24/0       
LP-E  fine         100           520    0     724     2 |       24/0      |         24/0       
LP-E  fine        1000          2066    0    1079     3 |       24/0      |         24/0       
LP-E  fine       10000         17180    0    5300    11 |       24/0      |         24/0       

======================================================================================
VERDICTS
======================================================================================
VERDICT PASS: PTW-fenced attribution is exact on every row of every core class, needs no timing packets  [fenced wrong total = 0; no-preceding-fence = 0 over 30 rows, classes ['P', 'E', 'LP-E']]
INFO: OVF rows excluded from time-keyed scoring (lossy trace != method result): 0 of 30: none
INFO: predicted MTC-payload wrap edge = 2^(mtc_period+8) CTC x TSC/CTC = 2^(3+8) x 192/2 = 196608 TSC ticks
VERDICT PASS: P: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [1022, 2386, 26900, 249000, 2474150, 5226452]]
INFO: P: coarse time-keyed at short intervals (<band): all resolved this run
VERDICT PASS: P: NO long-gap mis-attribution: exact at the longest interval, >= 10x the predicted wrap edge (MTC every period, so the payload never wraps unseen)  [longest coarse interval 5226452 TSC: time-keyed wrong=0; predicted edge 196608]
VERDICT PASS: E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [2922, 25084]]
INFO: E: coarse time-keyed at short intervals (<band): [(660, 6), (1142, 18)]
VERDICT PASS: E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 25084 <= 2x196608; smallest long-gap failure 247324 >= 196608/2; wrong at long intervals = [(247324, 19), (2494902, 23)]]
VERDICT PASS: LP-E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [2062, 17158, 168350]]
INFO: LP-E: coarse time-keyed at short intervals (<band): [(524, 7), (778, 3)]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 168350 <= 2x196608; smallest long-gap failure 1689298 >= 196608/2; wrong at long intervals = [(1689298, 22)]]
VERDICT PASS: mechanism: at the longest gap Cougar Cove's trace carries >= 100x the MTC packets of each Darkmont class (BranchEn=0)  [MTC packets per capture: P 216484; E 360; LP-E 259 (TSC packets: P 221; E 1; LP-E 2)]
VERDICT PASS: FINE timing: time-keyed is exact on all OVF-free rows of every class (dense timing closes the short-interval gap)  [fine time-keyed wrong = [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('E', 0), ('E', 0), ('E', 0), ('E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0)]]
VERDICT PASS: wherever time-keyed mis-attributes, PTW-fenced is exact  [rows with time-keyed wrong: 7; of those, fenced wrong: 0]

Interpretation: an executed in-band PTWRITE fence pins each traced
execution to its exact self-modified version in packet order, needing no
timestamps, on every core class. The strong time-keyed decoder (TMA + MTC
payloads) is exact only over an interval band. Below it there are too few
CTC ticks to place the exec after its patch. Above it, on Darkmont (E,
LP-E), the BranchEn=0 trace carries only sporadic MTC packets and a single
TSC, so the 8-bit MTC payload wraps unobserved and the high CTC bits are
lost, starting at the predicted 2^(mtc_period+8) CTC edge. On Cougar Cove
(P) the trace carries an MTC every period, so the payload never wraps unseen
and long gaps stay exact. Fine (dense) timing closes the low end. Ground
truth is the EXEC payload the executed bytes produced, confirmed
independently of PT by verify_singlestep.

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0

$ make        # run 3
./verify_singlestep 24
verify_singlestep: 24 versions, 24 single-stepped ret-points, ground truth CONFIRMED (EAX-at-ret == EXEC_TAG+i for all i)
VERSIONS=24 ./run.sh > data.csv
python3 report.py data.csv
======================================================================================
pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed
(time-keyed = TMA-anchored MTC-payload TSC clock; intervals in TSC ticks;
 each sweep pinned to one CPU: P = Cougar Cove, E / LP-E = Darkmont)
======================================================================================
class timing     delay interval(TSC)  ovf     MTC   TSC | fenced ok/wrong | time-keyed ok/wrong
-----------------------------------------------------------------------------------------------
P     coarse         0          2212    0     149     1 |       24/0      |         24/0       
P     coarse       100          1064    0     148     1 |       24/0      |         24/0       
P     coarse      1000         20610    0     746     3 |       24/0      |         24/0       
P     coarse     10000         25384    0    1373     2 |       24/0      |         24/0       
P     coarse    100000        271048    0   29888    31 |       24/0      |         24/0       
P     coarse   1000000      11920706    0  329370   335 |       24/0      |         24/0       
P     fine           0          2360    0    1397     4 |       24/0      |         24/0       
P     fine         100          2192    0    1374     4 |       24/0      |         24/0       
P     fine        1000          4650    0    3526     8 |       24/0      |         24/0       
P     fine       10000        249534    0   50852   104 |       24/0      |         24/0       
E     coarse         0          1488    0      35     1 |       24/0      |          8/16      
E     coarse       100           660    0      42     1 |       24/0      |         16/8       
E     coarse      1000          2884    0      51     1 |       24/0      |         24/0       
E     coarse     10000         25182    0      54     1 |       24/0      |         24/0       
E     coarse    100000        247232    0      81     1 |       24/0      |          3/21      
E     coarse   1000000       2485248    0     355     1 |       24/0      |          1/23      
E     fine           0          1150    0    1009     3 |       24/0      |         24/0       
E     fine         100           672    0     862     2 |       24/0      |         24/0       
E     fine        1000          2900    0    1505     4 |       24/0      |         24/0       
E     fine       10000         25634    0    7162    15 |       24/0      |         24/0       
LP-E  coarse         0           744    0      49     1 |       24/0      |         22/2       
LP-E  coarse       100           538    0      37     1 |       24/0      |         16/8       
LP-E  coarse      1000          2112    0      50     1 |       24/0      |         24/0       
LP-E  coarse     10000         17994    0      51     1 |       24/0      |         24/0       
LP-E  coarse    100000        188664    0      74     1 |       24/0      |         24/0       
LP-E  coarse   1000000       1330234    0     226     1 |       24/0      |          1/23      
LP-E  fine           0           552    0     729     2 |       24/0      |         24/0       
LP-E  fine         100           506    0     717     2 |       24/0      |         24/0       
LP-E  fine        1000          1740    0     917     3 |       24/0      |         24/0       
LP-E  fine       10000         13564    0    4049     9 |       24/0      |         24/0       

======================================================================================
VERDICTS
======================================================================================
VERDICT PASS: PTW-fenced attribution is exact on every row of every core class, needs no timing packets  [fenced wrong total = 0; no-preceding-fence = 0 over 30 rows, classes ['P', 'E', 'LP-E']]
INFO: OVF rows excluded from time-keyed scoring (lossy trace != method result): 0 of 30: none
INFO: predicted MTC-payload wrap edge = 2^(mtc_period+8) CTC x TSC/CTC = 2^(3+8) x 192/2 = 196608 TSC ticks
VERDICT PASS: P: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [1064, 2212, 20610, 25384, 271048, 11920706]]
INFO: P: coarse time-keyed at short intervals (<band): all resolved this run
VERDICT PASS: P: NO long-gap mis-attribution: exact at the longest interval, >= 10x the predicted wrap edge (MTC every period, so the payload never wraps unseen)  [longest coarse interval 11920706 TSC: time-keyed wrong=0; predicted edge 196608]
VERDICT PASS: E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [2884, 25182]]
INFO: E: coarse time-keyed at short intervals (<band): [(660, 8), (1488, 16)]
VERDICT PASS: E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 25182 <= 2x196608; smallest long-gap failure 247232 >= 196608/2; wrong at long intervals = [(247232, 21), (2485248, 23)]]
VERDICT PASS: LP-E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [2112, 17994, 188664]]
INFO: LP-E: coarse time-keyed at short intervals (<band): [(538, 8), (744, 2)]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 188664 <= 2x196608; smallest long-gap failure 1330234 >= 196608/2; wrong at long intervals = [(1330234, 23)]]
VERDICT PASS: mechanism: at the longest gap Cougar Cove's trace carries >= 100x the MTC packets of each Darkmont class (BranchEn=0)  [MTC packets per capture: P 329370; E 355; LP-E 226 (TSC packets: P 335; E 1; LP-E 1)]
VERDICT PASS: FINE timing: time-keyed is exact on all OVF-free rows of every class (dense timing closes the short-interval gap)  [fine time-keyed wrong = [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('E', 0), ('E', 0), ('E', 0), ('E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0)]]
VERDICT PASS: wherever time-keyed mis-attributes, PTW-fenced is exact  [rows with time-keyed wrong: 7; of those, fenced wrong: 0]

Interpretation: an executed in-band PTWRITE fence pins each traced
execution to its exact self-modified version in packet order, needing no
timestamps, on every core class. The strong time-keyed decoder (TMA + MTC
payloads) is exact only over an interval band. Below it there are too few
CTC ticks to place the exec after its patch. Above it, on Darkmont (E,
LP-E), the BranchEn=0 trace carries only sporadic MTC packets and a single
TSC, so the 8-bit MTC payload wraps unobserved and the high CTC bits are
lost, starting at the predicted 2^(mtc_period+8) CTC edge. On Cougar Cove
(P) the trace carries an MTC every period, so the payload never wraps unseen
and long gaps stay exact. Fine (dense) timing closes the low end. Ground
truth is the EXEC payload the executed bytes produced, confirmed
independently of PT by verify_singlestep.

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0
```

## 4. Baseline (known, not the observable): PT silently misdecodes SMC
See ../../research/probes/pt-smc-misdecode/probe-output.txt.
