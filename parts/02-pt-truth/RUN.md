# RUN.md — pt-truth, verbatim build+run on nibbles (post-clearance correction, round 2: per core class)

Captured 2026-10-19 12:25:16 PDT on nibbles, unprivileged derekblair,
perf_event_paranoid=2, under `env -i`. Verbatim, from clean.

## Nondeterministic fields (R3)
DETERMINISTIC / load-bearing: ground-truth confirmation; PTW-fenced ok/wrong (24/0 every
row, every core class); per class, the time-keyed structure. Darkmont (E, LP-E) is exact
over a band, fails at the shortest tested interval, and fails at long gaps from the
predicted 196,608-TSC MTC-payload wrap. Cougar Cove (P) is exact at every interval >= 2 MTC
periods (1,536 TSC), including every long gap; its lower edge is about one MTC period (§5).
Also load-bearing: fine-exact, and the MTC-density / delta-0 mechanism at the longest gap.
NONDETERMINISTIC: absolute TSC; measured intervals (P's vary widely run to run, so which
P rows land near its lower edge is reported as INFO); MTC/TSC packet counts, delta-0 shares
and trace bytes; OVF is rare (reported per row, excluded from scoring). Each sweep is
pinned: CPU 0 = Cougar Cove P, 4 = Darkmont E, 12 = Darkmont LP-E.

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
================================================================================================
pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed
(time-keyed = TMA-anchored MTC-payload TSC clock; intervals in TSC ticks;
 each sweep pinned to one CPU: P = Cougar Cove, E / LP-E = Darkmont)
================================================================================================
class timing     delay interval(TSC)  ovf     MTC  MTCd0   TSC    bytes | fenced ok/wrong | time-keyed ok/wrong
---------------------------------------------------------------------------------------------------------------
P     coarse         0          2560    0     169      0     1      944 |       24/0      |         24/0       
P     coarse       100           624    0      96      0     1      816 |       24/0      |         24/0       
P     coarse      1000         15870    0     558      0     1     1744 |       24/0      |         24/0       
P     coarse     10000        142258    0    3806      0     5     8544 |       24/0      |         24/0       
P     coarse    100000       1340544    0   36941      0    38    77200 |       24/0      |         24/0       
P     coarse   1000000       5092076    0  160239      0   163   332912 |       24/0      |         24/0       
P     fine           0           848    0     454      0     2     2576 |       24/0      |         24/0       
P     fine         100           424    0     508      0     2     2720 |       24/0      |         24/0       
P     fine        1000         17550    0    4884      0    11    20912 |       24/0      |         24/0       
P     fine       10000         75104    0   16425      0    34    68800 |       24/0      |         24/0       
E     coarse         0           538    0      28      0     1      520 |       24/0      |         14/10      
E     coarse       100           350    0      30      0     1      524 |       24/0      |         13/11      
E     coarse      1000          3088    0      52      0     1      568 |       24/0      |         24/0       
E     coarse     10000         11382    0      44      0     1      552 |       24/0      |         24/0       
E     coarse    100000        246774    0      79      6     1      624 |       24/0      |          3/21      
E     coarse   1000000       1409318    0     238    144     1      988 |       24/0      |          1/23      
E     fine           0          1226    0    1014      0     3     4620 |       24/0      |         24/0       
E     fine         100           410    0     374      0     1     2020 |       24/0      |         24/0       
E     fine        1000          2404    0    1228      0     3     5496 |       24/0      |         24/0       
E     fine       10000         11402    0    3336      0     7    14148 |       24/0      |         24/0       
LP-E  coarse         0           948    0      33      0     1      528 |       24/0      |          6/18      
LP-E  coarse       100           548    0      38      0     1      540 |       24/0      |         16/8       
LP-E  coarse      1000          1568    0      46      0     1      556 |       24/0      |         24/0       
LP-E  coarse     10000         22490    0      53      0     1      568 |       24/0      |         24/0       
LP-E  coarse    100000        231594    0      79      4     1      624 |       24/0      |          5/19      
LP-E  coarse   1000000       1848220    0     284    199     1     1052 |       24/0      |          1/23      
LP-E  fine           0           712    0     814      0     2     3816 |       24/0      |         24/0       
LP-E  fine         100           892    0    1054      0     3     4788 |       24/0      |         24/0       
LP-E  fine        1000          2738    0    1384      0     3     6116 |       24/0      |         24/0       
LP-E  fine       10000         20196    0    5859      0    12    24440 |       24/0      |         24/0       

================================================================================================
VERDICTS
================================================================================================
VERDICT PASS: PTW-fenced attribution is exact on every row of every core class, needs no timing packets  [fenced wrong total = 0; no-preceding-fence = 0 over 30 rows, classes ['P', 'E', 'LP-E']]
INFO: OVF rows excluded from time-keyed scoring (lossy trace != method result): 0 of 30: none
INFO: one MTC period = 2^3 CTC x TSC/CTC = 768 TSC; one 8-bit payload wrap (predicted long-gap edge) = 2^(3+8) CTC x 192/2 = 196608 TSC
VERDICT PASS: P: coarse time-keyed is exact at EVERY tested interval >= 2 MTC periods (clear of its one-period resolution edge), incl. every long gap  [5/5 rows exact, intervals 2560..5092076 TSC (one MTC period = 768)]
INFO: P below 2 MTC periods (around its lower edge, ~1 period): [(624, 0)]
VERDICT PASS: P: NO long-gap mis-attribution: exact at the longest interval, >= 10x the predicted wrap edge (an MTC every period, so the payload never wraps unseen)  [longest coarse interval 5092076 TSC (= 26x the edge 196608): time-keyed wrong=0]
VERDICT PASS: E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [3088, 11382]]
VERDICT PASS: E: coarse time-keyed MIS-attributes at the shortest tested interval  [shortest interval 350 TSC: wrong 11/24; all short failures (<band): [(350, 11), (538, 10)]]
VERDICT PASS: E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 11382 (= 17.3x below the edge) <= 2x196608; smallest long-gap failure 246774 (= 1.26x the edge) >= 196608/2; within 2x of the edge on: failure side]
VERDICT PASS: LP-E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [1568, 22490]]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at the shortest tested interval  [shortest interval 548 TSC: wrong 8/24; all short failures (<band): [(548, 8), (948, 18)]]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 22490 (= 8.7x below the edge) <= 2x196608; smallest long-gap failure 231594 (= 1.18x the edge) >= 196608/2; within 2x of the edge on: failure side]
VERDICT PASS: mechanism: at the longest gap Cougar Cove carries >= 100x Darkmont's MTCs with no delta-0 payload steps, while >= 10% of Darkmont's MTC steps are a whole payload wrap (delta 0 mod 256, ~25x the 1/256 chance level)  [MTC per capture: P 160239; E 238; LP-E 284; delta-0 share: E 61%; LP-E 70%; P delta-0 0 of 160238]
INFO: the price of Cougar Cove's exactness at the longest gap: trace volume P 332912 B vs E 988 B (337x), LP-E 1052 B (316x)
VERDICT PASS: FINE timing: time-keyed is exact on all OVF-free rows of every class (dense timing closes Darkmont's short-interval gap; P had none)  [fine time-keyed wrong = [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('E', 0), ('E', 0), ('E', 0), ('E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0)]]
VERDICT PASS: wherever time-keyed mis-attributes, PTW-fenced is exact  [rows with time-keyed wrong: 8; of those, fenced wrong: 0]

Interpretation, per core class:
* PTW-fenced: an executed in-band PTWRITE fence pins each traced execution to
  its exact self-modified version in packet order, with no timestamps, on every
  core class and at every tested interval.
* Darkmont (E, LP-E): with BranchEn=0, the trace carries few MTCs, and at long
  gaps they arrive about one per 8-bit payload wrap (delta 0 dominates). So the
  payload clock fails at short intervals (too coarse to place the exec after
  its patch) and at long gaps from the predicted 2^(mtc_period+8) CTC edge (the
  wraps it cannot see). Dense (fine) timing closes the short-interval gap.
* Cougar Cove (P): the trace carries an MTC every period, so time-keyed resolves
  one MTC period: its lower edge sits at about one period. It is exact at every
  tested interval >= 2 periods, including every long gap, at the price of a much
  larger trace.
* So the fence buys accuracy on Darkmont at short and long gaps, and on P only
  near or below one MTC period. On every class it needs no timing packets and
  does not depend on how densely the core emits them.
Ground truth is the EXEC payload the executed bytes produced, confirmed
independently of PT by verify_singlestep.

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0

$ make        # run 2
./verify_singlestep 24
verify_singlestep: 24 versions, 24 single-stepped ret-points, ground truth CONFIRMED (EAX-at-ret == EXEC_TAG+i for all i)
VERSIONS=24 ./run.sh > data.csv
python3 report.py data.csv
================================================================================================
pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed
(time-keyed = TMA-anchored MTC-payload TSC clock; intervals in TSC ticks;
 each sweep pinned to one CPU: P = Cougar Cove, E / LP-E = Darkmont)
================================================================================================
class timing     delay interval(TSC)  ovf     MTC  MTCd0   TSC    bytes | fenced ok/wrong | time-keyed ok/wrong
---------------------------------------------------------------------------------------------------------------
P     coarse         0          2038    0     186      0     1      912 |       24/0      |         24/0       
P     coarse       100           674    0      97      0     1      800 |       24/0      |         24/0       
P     coarse      1000          1270    0     159      0     1      976 |       24/0      |         24/0       
P     coarse     10000          8864    0     685      0     1     2016 |       24/0      |         24/0       
P     coarse    100000        765572    0   20627      0    22    43408 |       24/0      |         24/0       
P     coarse   1000000       3810636    0  119006      0   121   247456 |       24/0      |         24/0       
P     fine           0           748    0     407      0     2     2368 |       24/0      |         24/0       
P     fine         100          1618    0    1035      0     3     4976 |       24/0      |         24/0       
P     fine        1000          1148    0    1210      0     3     5680 |       24/0      |         24/0       
P     fine       10000        153344    0   25899      0    53   107872 |       24/0      |         24/0       
E     coarse         0           660    0      27      0     1      516 |       24/0      |         13/11      
E     coarse       100           546    0      40      0     1      544 |       24/0      |         20/4       
E     coarse      1000          1666    0      46      0     1      556 |       24/0      |         24/0       
E     coarse     10000         25054    0      52      0     1      568 |       24/0      |         24/0       
E     coarse    100000        115648    0      57      0     1      576 |       24/0      |         24/0       
E     coarse   1000000       1847630    0     291    191     1     1096 |       24/0      |          1/23      
E     fine           0           536    0     410      0     2     2204 |       24/0      |         24/0       
E     fine         100           426    0     525      0     2     2656 |       24/0      |         24/0       
E     fine        1000          1420    0     626      0     2     3076 |       24/0      |         24/0       
E     fine       10000         12140    0    3473      0     8    14748 |       24/0      |         24/0       
LP-E  coarse         0           570    0      40      0     1      544 |       24/0      |         18/6       
LP-E  coarse       100           902    0      49      0     1      564 |       24/0      |         23/1       
LP-E  coarse      1000          2212    0      50      0     1      564 |       24/0      |         24/0       
LP-E  coarse     10000         19194    0      51      0     1      564 |       24/0      |         24/0       
LP-E  coarse    100000        185114    0      73      0     1      608 |       24/0      |         24/0       
LP-E  coarse   1000000       1457598    0     235    148     1      960 |       24/0      |          1/23      
LP-E  fine           0           572    0     608      0     2     2996 |       24/0      |         24/0       
LP-E  fine         100           360    0     618      0     2     3044 |       24/0      |         24/0       
LP-E  fine        1000          1514    0     782      0     2     3700 |       24/0      |         24/0       
LP-E  fine       10000         12674    0    3755      0     8    15868 |       24/0      |         24/0       

================================================================================================
VERDICTS
================================================================================================
VERDICT PASS: PTW-fenced attribution is exact on every row of every core class, needs no timing packets  [fenced wrong total = 0; no-preceding-fence = 0 over 30 rows, classes ['P', 'E', 'LP-E']]
INFO: OVF rows excluded from time-keyed scoring (lossy trace != method result): 0 of 30: none
INFO: one MTC period = 2^3 CTC x TSC/CTC = 768 TSC; one 8-bit payload wrap (predicted long-gap edge) = 2^(3+8) CTC x 192/2 = 196608 TSC
VERDICT PASS: P: coarse time-keyed is exact at EVERY tested interval >= 2 MTC periods (clear of its one-period resolution edge), incl. every long gap  [4/4 rows exact, intervals 2038..3810636 TSC (one MTC period = 768)]
INFO: P below 2 MTC periods (around its lower edge, ~1 period): [(674, 0), (1270, 0)]
VERDICT PASS: P: NO long-gap mis-attribution: exact at the longest interval, >= 10x the predicted wrap edge (an MTC every period, so the payload never wraps unseen)  [longest coarse interval 3810636 TSC (= 19x the edge 196608): time-keyed wrong=0]
VERDICT PASS: E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [1666, 25054, 115648]]
VERDICT PASS: E: coarse time-keyed MIS-attributes at the shortest tested interval  [shortest interval 546 TSC: wrong 4/24; all short failures (<band): [(546, 4), (660, 11)]]
VERDICT PASS: E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 115648 (= 1.7x below the edge) <= 2x196608; smallest long-gap failure 1847630 (= 9.40x the edge) >= 196608/2; within 2x of the edge on: exact side]
VERDICT PASS: LP-E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [2212, 19194, 185114]]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at the shortest tested interval  [shortest interval 570 TSC: wrong 6/24; all short failures (<band): [(570, 6), (902, 1)]]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 185114 (= 1.1x below the edge) <= 2x196608; smallest long-gap failure 1457598 (= 7.41x the edge) >= 196608/2; within 2x of the edge on: exact side]
VERDICT PASS: mechanism: at the longest gap Cougar Cove carries >= 100x Darkmont's MTCs with no delta-0 payload steps, while >= 10% of Darkmont's MTC steps are a whole payload wrap (delta 0 mod 256, ~25x the 1/256 chance level)  [MTC per capture: P 119006; E 291; LP-E 235; delta-0 share: E 66%; LP-E 63%; P delta-0 0 of 119005]
INFO: the price of Cougar Cove's exactness at the longest gap: trace volume P 247456 B vs E 1096 B (226x), LP-E 960 B (258x)
VERDICT PASS: FINE timing: time-keyed is exact on all OVF-free rows of every class (dense timing closes Darkmont's short-interval gap; P had none)  [fine time-keyed wrong = [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('E', 0), ('E', 0), ('E', 0), ('E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0)]]
VERDICT PASS: wherever time-keyed mis-attributes, PTW-fenced is exact  [rows with time-keyed wrong: 6; of those, fenced wrong: 0]

Interpretation, per core class:
* PTW-fenced: an executed in-band PTWRITE fence pins each traced execution to
  its exact self-modified version in packet order, with no timestamps, on every
  core class and at every tested interval.
* Darkmont (E, LP-E): with BranchEn=0, the trace carries few MTCs, and at long
  gaps they arrive about one per 8-bit payload wrap (delta 0 dominates). So the
  payload clock fails at short intervals (too coarse to place the exec after
  its patch) and at long gaps from the predicted 2^(mtc_period+8) CTC edge (the
  wraps it cannot see). Dense (fine) timing closes the short-interval gap.
* Cougar Cove (P): the trace carries an MTC every period, so time-keyed resolves
  one MTC period: its lower edge sits at about one period. It is exact at every
  tested interval >= 2 periods, including every long gap, at the price of a much
  larger trace.
* So the fence buys accuracy on Darkmont at short and long gaps, and on P only
  near or below one MTC period. On every class it needs no timing packets and
  does not depend on how densely the core emits them.
Ground truth is the EXEC payload the executed bytes produced, confirmed
independently of PT by verify_singlestep.

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0

$ make        # run 3
./verify_singlestep 24
verify_singlestep: 24 versions, 24 single-stepped ret-points, ground truth CONFIRMED (EAX-at-ret == EXEC_TAG+i for all i)
VERSIONS=24 ./run.sh > data.csv
python3 report.py data.csv
================================================================================================
pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed
(time-keyed = TMA-anchored MTC-payload TSC clock; intervals in TSC ticks;
 each sweep pinned to one CPU: P = Cougar Cove, E / LP-E = Darkmont)
================================================================================================
class timing     delay interval(TSC)  ovf     MTC  MTCd0   TSC    bytes | fenced ok/wrong | time-keyed ok/wrong
---------------------------------------------------------------------------------------------------------------
P     coarse         0          1270    0      84      0     1      752 |       24/0      |         24/0       
P     coarse       100           604    0      91      0     1      784 |       24/0      |         24/0       
P     coarse      1000         12898    0     438      0     1     1520 |       24/0      |         24/0       
P     coarse     10000         54350    0    2781      0     4     6432 |       24/0      |         24/0       
P     coarse    100000        161180    0   12097      0    13    25728 |       24/0      |         24/0       
P     coarse   1000000       4643794    0  162981      0   166   338656 |       24/0      |         24/0       
P     fine           0           704    0     420      0     2     2448 |       24/0      |         24/0       
P     fine         100          1428    0    1291      0     3     6000 |       24/0      |         24/0       
P     fine        1000         12394    0    2917      0     7    12784 |       24/0      |         24/0       
P     fine       10000        111762    0   23716      0    49    98976 |       24/0      |         24/0       
E     coarse         0           860    0      30      0     1      524 |       24/0      |          9/15      
E     coarse       100           428    0      36      0     1      536 |       24/0      |         17/7       
E     coarse      1000          2544    0      49      0     1      560 |       24/0      |         24/0       
E     coarse     10000         13418    0      49      0     1      560 |       24/0      |         24/0       
E     coarse    100000        231332    0      79      5     1      624 |       24/0      |          2/22      
E     coarse   1000000       1157098    0     227     98     2     1064 |       24/0      |          4/20      
E     fine           0           778    0     728      0     2     3464 |       24/0      |         24/0       
E     fine         100           656    0     874      0     2     4020 |       24/0      |         24/0       
E     fine        1000          2400    0    1241      0     3     5552 |       24/0      |         24/0       
E     fine       10000         19712    0    5580      0    12    23332 |       24/0      |         24/0       
LP-E  coarse         0           594    0      35      0     1      532 |       24/0      |         11/13      
LP-E  coarse       100           884    0      49      0     1      560 |       24/0      |         24/0       
LP-E  coarse      1000          1482    0      46      0     1      556 |       24/0      |         24/0       
LP-E  coarse     10000         12664    0      49      0     1      560 |       24/0      |         24/0       
LP-E  coarse    100000        123384    0      59      0     1      580 |       24/0      |         24/0       
LP-E  coarse   1000000       1766546    0     282    197     1     1056 |       24/0      |          1/23      
LP-E  fine           0           950    0     712      0     2     3400 |       24/0      |         24/0       
LP-E  fine         100           358    0     464      0     2     2428 |       24/0      |         24/0       
LP-E  fine        1000          2622    0    1461      6     4     6452 |       24/0      |         24/0       
LP-E  fine       10000         18994    0    5724      0    12    23900 |       24/0      |         24/0       

================================================================================================
VERDICTS
================================================================================================
VERDICT PASS: PTW-fenced attribution is exact on every row of every core class, needs no timing packets  [fenced wrong total = 0; no-preceding-fence = 0 over 30 rows, classes ['P', 'E', 'LP-E']]
INFO: OVF rows excluded from time-keyed scoring (lossy trace != method result): 0 of 30: none
INFO: one MTC period = 2^3 CTC x TSC/CTC = 768 TSC; one 8-bit payload wrap (predicted long-gap edge) = 2^(3+8) CTC x 192/2 = 196608 TSC
VERDICT PASS: P: coarse time-keyed is exact at EVERY tested interval >= 2 MTC periods (clear of its one-period resolution edge), incl. every long gap  [4/4 rows exact, intervals 12898..4643794 TSC (one MTC period = 768)]
INFO: P below 2 MTC periods (around its lower edge, ~1 period): [(604, 0), (1270, 0)]
VERDICT PASS: P: NO long-gap mis-attribution: exact at the longest interval, >= 10x the predicted wrap edge (an MTC every period, so the payload never wraps unseen)  [longest coarse interval 4643794 TSC (= 24x the edge 196608): time-keyed wrong=0]
VERDICT PASS: E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [2544, 13418]]
VERDICT PASS: E: coarse time-keyed MIS-attributes at the shortest tested interval  [shortest interval 428 TSC: wrong 7/24; all short failures (<band): [(428, 7), (860, 15)]]
VERDICT PASS: E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 13418 (= 14.7x below the edge) <= 2x196608; smallest long-gap failure 231332 (= 1.18x the edge) >= 196608/2; within 2x of the edge on: failure side]
VERDICT PASS: LP-E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [884, 1482, 12664, 123384]]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at the shortest tested interval  [shortest interval 594 TSC: wrong 13/24; all short failures (<band): [(594, 13)]]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 123384 (= 1.6x below the edge) <= 2x196608; smallest long-gap failure 1766546 (= 8.99x the edge) >= 196608/2; within 2x of the edge on: exact side]
VERDICT PASS: mechanism: at the longest gap Cougar Cove carries >= 100x Darkmont's MTCs with no delta-0 payload steps, while >= 10% of Darkmont's MTC steps are a whole payload wrap (delta 0 mod 256, ~25x the 1/256 chance level)  [MTC per capture: P 162981; E 227; LP-E 282; delta-0 share: E 43%; LP-E 70%; P delta-0 0 of 162980]
INFO: the price of Cougar Cove's exactness at the longest gap: trace volume P 338656 B vs E 1064 B (318x), LP-E 1056 B (321x)
VERDICT PASS: FINE timing: time-keyed is exact on all OVF-free rows of every class (dense timing closes Darkmont's short-interval gap; P had none)  [fine time-keyed wrong = [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('E', 0), ('E', 0), ('E', 0), ('E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0)]]
VERDICT PASS: wherever time-keyed mis-attributes, PTW-fenced is exact  [rows with time-keyed wrong: 6; of those, fenced wrong: 0]

Interpretation, per core class:
* PTW-fenced: an executed in-band PTWRITE fence pins each traced execution to
  its exact self-modified version in packet order, with no timestamps, on every
  core class and at every tested interval.
* Darkmont (E, LP-E): with BranchEn=0, the trace carries few MTCs, and at long
  gaps they arrive about one per 8-bit payload wrap (delta 0 dominates). So the
  payload clock fails at short intervals (too coarse to place the exec after
  its patch) and at long gaps from the predicted 2^(mtc_period+8) CTC edge (the
  wraps it cannot see). Dense (fine) timing closes the short-interval gap.
* Cougar Cove (P): the trace carries an MTC every period, so time-keyed resolves
  one MTC period: its lower edge sits at about one period. It is exact at every
  tested interval >= 2 periods, including every long gap, at the price of a much
  larger trace.
* So the fence buys accuracy on Darkmont at short and long gaps, and on P only
  near or below one MTC period. On every class it needs no timing packets and
  does not depend on how densely the core emits them.
Ground truth is the EXEC payload the executed bytes produced, confirmed
independently of PT by verify_singlestep.

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0
```

## 4. Baseline (known, not the observable): PT silently misdecodes SMC
See ../../research/probes/pt-smc-misdecode/probe-output.txt.

## 5. Cougar Cove's lower edge: short-delay probe on CPU 0, 5 repeats (verbatim)
One MTC period = 768 TSC (coarse, mtc_period 3). The fine sweep runs at its default delays.
CSV columns: timing,delay,execs,median_interval_tsc,fenced_ok,fenced_wrong,fenced_nofence,
tk_ok,tk_wrong,ovf,mtc_pkts,tsc_pkts,mtc_delta0,trace_bytes,cpu
```
$ PT_CPUS=0 COARSE_DELAYS="0 25 50 100" ./run.sh | grep -v '^#'   # repeat 1
coarse,0,24,2764,24,0,0,24,0,0,197,1,0,1024,0
coarse,25,24,2442,24,0,0,24,0,0,168,1,0,944,0
coarse,50,24,894,24,0,0,24,0,0,138,1,0,832,0
coarse,100,24,982,24,0,0,24,0,0,144,1,0,864,0
fine,0,24,2360,24,0,0,24,0,0,1376,4,0,6448,0
fine,100,24,1920,24,0,0,24,0,0,1368,4,0,6400,0
fine,1000,24,15532,24,0,0,24,0,0,4390,10,0,18864,0
fine,10000,24,32048,24,0,0,24,0,0,17532,36,0,73264,0
$ PT_CPUS=0 COARSE_DELAYS="0 25 50 100" ./run.sh | grep -v '^#'   # repeat 2
coarse,0,24,2218,24,0,0,24,0,0,148,1,0,864,0
coarse,25,24,2448,24,0,0,24,0,0,164,1,0,928,0
coarse,50,24,970,24,0,0,24,0,0,135,1,0,816,0
coarse,100,24,1704,24,0,0,24,0,0,151,1,0,896,0
fine,0,24,2380,24,0,0,24,0,0,1321,3,0,6176,0
fine,100,24,998,24,0,0,24,0,0,1256,3,0,5888,0
fine,1000,24,4952,24,0,0,24,0,0,3791,8,0,16368,0
fine,10000,24,227040,24,0,0,24,0,0,46184,94,0,191696,0
$ PT_CPUS=0 COARSE_DELAYS="0 25 50 100" ./run.sh | grep -v '^#'   # repeat 3
coarse,0,24,914,24,0,0,23,1,0,60,1,0,736,0
coarse,25,24,1764,24,0,0,24,0,0,121,1,0,800,0
coarse,50,24,546,24,0,0,24,0,0,92,1,0,784,0
coarse,100,24,378,24,0,0,21,3,0,50,1,0,736,0
fine,0,24,710,24,0,0,24,0,0,383,2,0,2304,0
fine,100,24,318,24,0,0,24,0,0,409,2,0,2448,0
fine,1000,24,10176,24,0,0,24,0,0,2998,7,0,13104,0
fine,10000,24,11014,24,0,0,24,0,0,7529,16,0,31872,0
$ PT_CPUS=0 COARSE_DELAYS="0 25 50 100" ./run.sh | grep -v '^#'   # repeat 4
coarse,0,24,806,24,0,0,23,1,0,52,1,0,736,0
coarse,25,24,822,24,0,0,23,1,0,58,1,0,736,0
coarse,50,24,392,24,0,0,22,2,0,60,1,0,752,0
coarse,100,24,2152,24,0,0,24,0,0,160,1,0,944,0
fine,0,24,1200,24,0,0,24,0,0,663,2,0,3392,0
fine,100,24,340,24,0,0,24,0,0,401,2,0,2400,0
fine,1000,24,1262,24,0,0,24,0,0,1412,4,0,6560,0
fine,10000,24,10744,24,0,0,24,0,0,5308,12,0,22704,0
$ PT_CPUS=0 COARSE_DELAYS="0 25 50 100" ./run.sh | grep -v '^#'   # repeat 5
coarse,0,24,782,24,0,0,22,2,0,51,1,0,736,0
coarse,25,24,730,24,0,0,24,0,0,51,1,0,720,0
coarse,50,24,298,24,0,0,21,3,0,46,1,0,736,0
coarse,100,24,334,24,0,0,20,4,0,53,1,0,736,0
fine,0,24,804,24,0,0,24,0,0,433,2,0,2464,0
fine,100,24,498,24,0,0,24,0,0,582,2,0,3120,0
fine,1000,24,2432,24,0,0,24,0,0,2374,6,0,10496,0
fine,10000,24,126186,24,0,0,24,0,0,20329,42,0,84800,0
```
