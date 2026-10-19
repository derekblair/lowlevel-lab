# RUN.md — pt-truth, verbatim build+run on nibbles (post-clearance correction, cleared at round 4; + N9)

Captured 2026-10-19 12:31:23 PDT on nibbles, unprivileged derekblair,
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
and trace bytes; OVF is rare (reported per row, excluded from scoring). The wrong-count on
Darkmont's shortest row varies (it is a count out of 24 executions near the clock's
resolution); the coarse delays 25/50 keep that row well below one MTC period so the count
stays clear of zero (N9). Each sweep is pinned: CPU 0 = Cougar Cove P, 4 = Darkmont E,
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
================================================================================================
pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed
(time-keyed = TMA-anchored MTC-payload TSC clock; intervals in TSC ticks;
 each sweep pinned to one CPU: P = Cougar Cove, E / LP-E = Darkmont)
================================================================================================
class timing     delay interval(TSC)  ovf     MTC  MTCd0   TSC    bytes | fenced ok/wrong | time-keyed ok/wrong
---------------------------------------------------------------------------------------------------------------
P     coarse         0          1526    0     102      0     1      752 |       24/0      |         24/0       
P     coarse        25           936    0      64      0     1      736 |       24/0      |         22/2       
P     coarse        50           542    0      81      0     1      768 |       24/0      |         24/0       
P     coarse       100           586    0      89      0     1      784 |       24/0      |         24/0       
P     coarse      1000          2046    0     273      0     1     1216 |       24/0      |         24/0       
P     coarse     10000        153502    0    4080      0     5     9136 |       24/0      |         24/0       
P     coarse    100000       1604898    0   50372      0    52   105216 |       24/0      |         24/0       
P     coarse   1000000       5899414    0  186558      0   190   387504 |       24/0      |         24/0       
P     fine           0           806    0     443      0     2     2496 |       24/0      |         24/0       
P     fine         100           356    0     457      0     2     2608 |       24/0      |         24/0       
P     fine        1000          5438    0    2958      0     7    12976 |       24/0      |         24/0       
P     fine       10000         83826    0   21306      0    44    89040 |       24/0      |         24/0       
E     coarse         0           554    0      33      0     1      528 |       24/0      |         16/8       
E     coarse        25           540    0      33      0     1      528 |       24/0      |          9/15      
E     coarse        50           444    0      37      0     1      536 |       24/0      |         13/11      
E     coarse       100           318    0      27      0     1      516 |       24/0      |         14/10      
E     coarse      1000          2932    0      52      0     1      568 |       24/0      |         24/0       
E     coarse     10000         25054    0      55      0     1      572 |       24/0      |         24/0       
E     coarse    100000        123204    0      65      0     1      600 |       24/0      |         24/0       
E     coarse   1000000       2053464    0     300    212     1     1092 |       24/0      |          1/23      
E     fine           0           520    0     410      0     2     2208 |       24/0      |         24/0       
E     fine         100           548    0     696      0     2     3328 |       24/0      |         24/0       
E     fine        1000          1310    0     624      0     2     3064 |       24/0      |         24/0       
E     fine       10000         22586    0    6197      0    13    25800 |       24/0      |         24/0       
LP-E  coarse         0           612    0      41      0     1      544 |       24/0      |         17/7       
LP-E  coarse        25           624    0      47      0     1      556 |       24/0      |         21/3       
LP-E  coarse        50           536    0      32      0     1      528 |       24/0      |         11/13      
LP-E  coarse       100           870    0      48      0     1      560 |       24/0      |         23/1       
LP-E  coarse      1000          1626    0      46      0     1      556 |       24/0      |         24/0       
LP-E  coarse     10000         20912    0      52      0     1      568 |       24/0      |         24/0       
LP-E  coarse    100000        205662    0      76      1     1      616 |       24/0      |         14/10      
LP-E  coarse   1000000       1760024    0     274    192     1     1028 |       24/0      |          1/23      
LP-E  fine           0           906    0     840      0     2     3904 |       24/0      |         24/0       
LP-E  fine         100           374    0     494      0     2     2544 |       24/0      |         24/0       
LP-E  fine        1000          1524    0     775      0     2     3672 |       24/0      |         24/0       
LP-E  fine       10000         13022    0    3657      0     8    15484 |       24/0      |         24/0       

================================================================================================
VERDICTS
================================================================================================
VERDICT PASS: PTW-fenced attribution is exact on every row of every core class, needs no timing packets  [fenced wrong total = 0; no-preceding-fence = 0 over 36 rows, classes ['P', 'E', 'LP-E']]
INFO: OVF rows excluded from time-keyed scoring (lossy trace != method result): 0 of 36: none
INFO: one MTC period = 2^3 CTC x TSC/CTC = 768 TSC; one 8-bit payload wrap (predicted long-gap edge) = 2^(3+8) CTC x 192/2 = 196608 TSC
VERDICT PASS: P: coarse time-keyed is exact at EVERY tested interval >= 2 MTC periods (clear of its one-period resolution edge), incl. every long gap  [4/4 rows exact, intervals 2046..5899414 TSC (one MTC period = 768)]
INFO: P below 2 MTC periods (around its lower edge, ~1 period): [(542, 0), (586, 0), (936, 2), (1526, 0)]
VERDICT PASS: P: NO long-gap mis-attribution: exact at the longest interval, >= 10x the predicted wrap edge (an MTC every period, so the payload never wraps unseen)  [longest coarse interval 5899414 TSC (= 30x the edge 196608): time-keyed wrong=0]
VERDICT PASS: E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [2932, 25054, 123204]]
VERDICT PASS: E: coarse time-keyed MIS-attributes at the shortest tested interval  [shortest interval 318 TSC: wrong 10/24; all short failures (<band): [(318, 10), (444, 11), (540, 15), (554, 8)]]
VERDICT PASS: E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 123204 (= 1.6x below the edge) <= 2x196608; smallest long-gap failure 2053464 (= 10.44x the edge) >= 196608/2; within 2x of the edge on: exact side]
VERDICT PASS: LP-E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [1626, 20912]]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at the shortest tested interval  [shortest interval 536 TSC: wrong 13/24; all short failures (<band): [(536, 13), (612, 7), (624, 3), (870, 1)]]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 20912 (= 9.4x below the edge) <= 2x196608; smallest long-gap failure 205662 (= 1.05x the edge) >= 196608/2; within 2x of the edge on: failure side]
VERDICT PASS: mechanism: at the longest gap Cougar Cove carries >= 100x Darkmont's MTCs with no delta-0 payload steps, while >= 10% of Darkmont's MTC steps are a whole payload wrap (delta 0 mod 256, ~25x the 1/256 chance level)  [MTC per capture: P 186558; E 300; LP-E 274; delta-0 share: E 71%; LP-E 70%; P delta-0 0 of 186557]
INFO: the price of Cougar Cove's exactness at the longest gap: trace volume P 387504 B vs E 1092 B (355x), LP-E 1028 B (377x)
VERDICT PASS: FINE timing: time-keyed is exact on all OVF-free rows of every class (dense timing closes Darkmont's short-interval gap; P had none)  [fine time-keyed wrong = [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('E', 0), ('E', 0), ('E', 0), ('E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0)]]
VERDICT PASS: wherever time-keyed mis-attributes, PTW-fenced is exact  [rows with time-keyed wrong: 12; of those, fenced wrong: 0]

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
P     coarse         0           894    0      58      0     1      736 |       24/0      |         23/1       
P     coarse        25           848    0      57      0     1      736 |       24/0      |         24/0       
P     coarse        50           336    0      49      0     1      736 |       24/0      |         21/3       
P     coarse       100           326    0      45      0     1      736 |       24/0      |         18/6       
P     coarse      1000          1122    0      95      0     1      816 |       24/0      |         24/0       
P     coarse     10000         76334    0    2212      0     3     5216 |       24/0      |         24/0       
P     coarse    100000        112878    0    9013      0    11    19424 |       24/0      |         24/0       
P     coarse   1000000       4024748    0  133620      0   136   277728 |       24/0      |         24/0       
P     fine           0           804    0     464      0     2     2592 |       24/0      |         24/0       
P     fine         100           554    0     657      0     2     3376 |       24/0      |         24/0       
P     fine        1000          3314    0    2169      0     5     9680 |       24/0      |         24/0       
P     fine       10000        105548    0   26706      0    55   111456 |       24/0      |         24/0       
E     coarse         0           662    0      28      0     1      520 |       24/0      |          8/16      
E     coarse        25           228    0      27      0     1      516 |       24/0      |         21/3       
E     coarse        50           416    0      38      0     1      540 |       24/0      |         16/8       
E     coarse       100           298    0      28      0     1      520 |       24/0      |         13/11      
E     coarse      1000          2706    0      50      0     1      564 |       24/0      |         24/0       
E     coarse     10000         11734    0      44      0     1      552 |       24/0      |         24/0       
E     coarse    100000        123366    0      63      0     1      596 |       24/0      |         24/0       
E     coarse   1000000       2053338    0     296    208     1     1084 |       24/0      |          1/23      
E     fine           0           520    0     413      0     2     2228 |       24/0      |         24/0       
E     fine         100           428    0     755      0     2     3576 |       24/0      |         24/0       
E     fine        1000          1312    0     610      0     2     3012 |       24/0      |         24/0       
E     fine       10000         20218    0    5746      0    12    23988 |       24/0      |         24/0       
LP-E  coarse         0           572    0      42      0     1      548 |       24/0      |         20/4       
LP-E  coarse        25           594    0      43      0     1      548 |       24/0      |         18/6       
LP-E  coarse        50           276    0      33      0     1      528 |       24/0      |         17/7       
LP-E  coarse       100           560    0      39      0     1      540 |       24/0      |         19/5       
LP-E  coarse      1000          2556    0      49      0     1      560 |       24/0      |         24/0       
LP-E  coarse     10000         12998    0      48      0     1      560 |       24/0      |         24/0       
LP-E  coarse    100000        217728    0      77      3     1      620 |       24/0      |          1/23      
LP-E  coarse   1000000       1503670    0     244    153     1      996 |       24/0      |          1/23      
LP-E  fine           0           814    0    1016      0     3     4664 |       24/0      |         24/0       
LP-E  fine         100           864    0     949      0     3     4400 |       24/0      |         24/0       
LP-E  fine        1000          2320    0    1221      0     3     5476 |       24/0      |         24/0       
LP-E  fine       10000         22638    0    6285      0    13    26152 |       24/0      |         24/0       

================================================================================================
VERDICTS
================================================================================================
VERDICT PASS: PTW-fenced attribution is exact on every row of every core class, needs no timing packets  [fenced wrong total = 0; no-preceding-fence = 0 over 36 rows, classes ['P', 'E', 'LP-E']]
INFO: OVF rows excluded from time-keyed scoring (lossy trace != method result): 0 of 36: none
INFO: one MTC period = 2^3 CTC x TSC/CTC = 768 TSC; one 8-bit payload wrap (predicted long-gap edge) = 2^(3+8) CTC x 192/2 = 196608 TSC
VERDICT PASS: P: coarse time-keyed is exact at EVERY tested interval >= 2 MTC periods (clear of its one-period resolution edge), incl. every long gap  [3/3 rows exact, intervals 76334..4024748 TSC (one MTC period = 768)]
INFO: P below 2 MTC periods (around its lower edge, ~1 period): [(326, 6), (336, 3), (848, 0), (894, 1), (1122, 0)]
VERDICT PASS: P: NO long-gap mis-attribution: exact at the longest interval, >= 10x the predicted wrap edge (an MTC every period, so the payload never wraps unseen)  [longest coarse interval 4024748 TSC (= 20x the edge 196608): time-keyed wrong=0]
VERDICT PASS: E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [2706, 11734, 123366]]
VERDICT PASS: E: coarse time-keyed MIS-attributes at the shortest tested interval  [shortest interval 228 TSC: wrong 3/24; all short failures (<band): [(228, 3), (298, 11), (416, 8), (662, 16)]]
VERDICT PASS: E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 123366 (= 1.6x below the edge) <= 2x196608; smallest long-gap failure 2053338 (= 10.44x the edge) >= 196608/2; within 2x of the edge on: exact side]
VERDICT PASS: LP-E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [2556, 12998]]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at the shortest tested interval  [shortest interval 276 TSC: wrong 7/24; all short failures (<band): [(276, 7), (560, 5), (572, 4), (594, 6)]]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 12998 (= 15.1x below the edge) <= 2x196608; smallest long-gap failure 217728 (= 1.11x the edge) >= 196608/2; within 2x of the edge on: failure side]
VERDICT PASS: mechanism: at the longest gap Cougar Cove carries >= 100x Darkmont's MTCs with no delta-0 payload steps, while >= 10% of Darkmont's MTC steps are a whole payload wrap (delta 0 mod 256, ~25x the 1/256 chance level)  [MTC per capture: P 133620; E 296; LP-E 244; delta-0 share: E 71%; LP-E 63%; P delta-0 0 of 133619]
INFO: the price of Cougar Cove's exactness at the longest gap: trace volume P 277728 B vs E 1084 B (256x), LP-E 996 B (279x)
VERDICT PASS: FINE timing: time-keyed is exact on all OVF-free rows of every class (dense timing closes Darkmont's short-interval gap; P had none)  [fine time-keyed wrong = [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('E', 0), ('E', 0), ('E', 0), ('E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0)]]
VERDICT PASS: wherever time-keyed mis-attributes, PTW-fenced is exact  [rows with time-keyed wrong: 14; of those, fenced wrong: 0]

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
P     coarse         0          1024    0      71      0     1      736 |       24/0      |         24/0       
P     coarse        25           742    0      53      0     1      736 |       24/0      |         23/1       
P     coarse        50           274    0      41      0     1      704 |       24/0      |         20/4       
P     coarse       100           312    0      47      0     1      736 |       24/0      |          8/16      
P     coarse      1000          8330    0     257      0     1     1184 |       24/0      |         24/0       
P     coarse     10000         76738    0    2169      0     3     5120 |       24/0      |         24/0       
P     coarse    100000        613110    0   13377      0    14    28352 |       24/0      |         24/0       
P     coarse   1000000       3649366    0  114547      0   117   238160 |       24/0      |         24/0       
P     fine           0           726    0     391      0     2     2352 |       24/0      |         24/0       
P     fine         100           716    0     934      0     3     4576 |       24/0      |         24/0       
P     fine        1000          2092    0    1517      0     4     6992 |       24/0      |         24/0       
P     fine       10000        133300    0   26789      0    55   111520 |       24/0      |         24/0       
E     coarse         0           714    0      30      0     1      524 |       24/0      |         13/11      
E     coarse        25           192    0      23      0     1      508 |       24/0      |          9/15      
E     coarse        50           376    0      35      0     1      532 |       24/0      |         11/13      
E     coarse       100           308    0      28      0     1      520 |       24/0      |          5/19      
E     coarse      1000          1348    0      43      0     1      548 |       24/0      |         24/0       
E     coarse     10000         25050    0      53      0     1      568 |       24/0      |         24/0       
E     coarse    100000        112156    0      61      0     2      608 |       24/0      |         24/0       
E     coarse   1000000       1827596    0     277    180     1     1068 |       24/0      |          1/23      
E     fine           0           522    0     420      0     2     2244 |       24/0      |         24/0       
E     fine         100           516    0     630      0     2     3068 |       24/0      |         24/0       
E     fine        1000          2754    0    1720      0     4     7500 |       24/0      |         24/0       
E     fine       10000         20018    0    5526      0    12    23104 |       24/0      |         24/0       
LP-E  coarse         0           572    0      39      0     1      540 |       24/0      |         16/8       
LP-E  coarse        25           360    0      34      0     1      532 |       24/0      |         10/14      
LP-E  coarse        50           248    0      29      0     1      520 |       24/0      |         10/14      
LP-E  coarse       100           920    0      49      0     1      560 |       24/0      |         24/0       
LP-E  coarse      1000          1508    0      46      0     1      556 |       24/0      |         24/0       
LP-E  coarse     10000         12576    0      51      0     1      568 |       24/0      |         24/0       
LP-E  coarse    100000        123410    0      60      0     1      584 |       24/0      |         24/0       
LP-E  coarse   1000000       1231688    0     196    125     2      884 |       24/0      |          2/22      
LP-E  fine           0           592    0     617      0     2     3032 |       24/0      |         24/0       
LP-E  fine         100           358    0     480      0     2     2488 |       24/0      |         24/0       
LP-E  fine        1000          1524    0     826      0     2     3880 |       24/0      |         24/0       
LP-E  fine       10000         13182    0    4046      0     9    17084 |       24/0      |         24/0       

================================================================================================
VERDICTS
================================================================================================
VERDICT PASS: PTW-fenced attribution is exact on every row of every core class, needs no timing packets  [fenced wrong total = 0; no-preceding-fence = 0 over 36 rows, classes ['P', 'E', 'LP-E']]
INFO: OVF rows excluded from time-keyed scoring (lossy trace != method result): 0 of 36: none
INFO: one MTC period = 2^3 CTC x TSC/CTC = 768 TSC; one 8-bit payload wrap (predicted long-gap edge) = 2^(3+8) CTC x 192/2 = 196608 TSC
VERDICT PASS: P: coarse time-keyed is exact at EVERY tested interval >= 2 MTC periods (clear of its one-period resolution edge), incl. every long gap  [4/4 rows exact, intervals 8330..3649366 TSC (one MTC period = 768)]
INFO: P below 2 MTC periods (around its lower edge, ~1 period): [(274, 4), (312, 16), (742, 1), (1024, 0)]
VERDICT PASS: P: NO long-gap mis-attribution: exact at the longest interval, >= 10x the predicted wrap edge (an MTC every period, so the payload never wraps unseen)  [longest coarse interval 3649366 TSC (= 19x the edge 196608): time-keyed wrong=0]
VERDICT PASS: E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [1348, 25050, 112156]]
VERDICT PASS: E: coarse time-keyed MIS-attributes at the shortest tested interval  [shortest interval 192 TSC: wrong 15/24; all short failures (<band): [(192, 15), (308, 19), (376, 13), (714, 11)]]
VERDICT PASS: E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 112156 (= 1.8x below the edge) <= 2x196608; smallest long-gap failure 1827596 (= 9.30x the edge) >= 196608/2; within 2x of the edge on: exact side]
VERDICT PASS: LP-E: coarse time-keyed is exact over an interval band  [exact at intervals(TSC) = [920, 1508, 12576, 123410]]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at the shortest tested interval  [shortest interval 248 TSC: wrong 14/24; all short failures (<band): [(248, 14), (360, 14), (572, 8)]]
VERDICT PASS: LP-E: coarse time-keyed MIS-attributes at long gaps, onset at the predicted MTC-payload wrap (within 2x)  [largest exact 123410 (= 1.6x below the edge) <= 2x196608; smallest long-gap failure 1231688 (= 6.26x the edge) >= 196608/2; within 2x of the edge on: exact side]
VERDICT PASS: mechanism: at the longest gap Cougar Cove carries >= 100x Darkmont's MTCs with no delta-0 payload steps, while >= 10% of Darkmont's MTC steps are a whole payload wrap (delta 0 mod 256, ~25x the 1/256 chance level)  [MTC per capture: P 114547; E 277; LP-E 196; delta-0 share: E 65%; LP-E 64%; P delta-0 0 of 114546]
INFO: the price of Cougar Cove's exactness at the longest gap: trace volume P 238160 B vs E 1068 B (223x), LP-E 884 B (269x)
VERDICT PASS: FINE timing: time-keyed is exact on all OVF-free rows of every class (dense timing closes Darkmont's short-interval gap; P had none)  [fine time-keyed wrong = [('P', 0), ('P', 0), ('P', 0), ('P', 0), ('E', 0), ('E', 0), ('E', 0), ('E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0), ('LP-E', 0)]]
VERDICT PASS: wherever time-keyed mis-attributes, PTW-fenced is exact  [rows with time-keyed wrong: 12; of those, fenced wrong: 0]

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
