# RUN.md — pt-truth, verbatim build+run on nibbles

Captured 2026-10-19 08:07:11 PDT on nibbles, unprivileged derekblair,
perf_event_paranoid=2. Commands verbatim, from clean.

## Nondeterministic fields (R3)
DETERMINISTIC / load-bearing: the ground-truth confirmation; fenced ok/wrong
(always 24/0); the coarse-vs-fine time-keyed outcome (coarse mis-attributes,
fine exact). NONDETERMINISTIC: absolute TSC values; exact per-delay time-keyed
wrong counts in coarse vary by +/-a few run to run (e.g. 21-24 wrong) with
scheduling/timing jitter; trace byte sizes; the mtemp workdir path.

## 0. Environment
```
$ gcc --version | head -1
gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
$ python3 --version
Python 3.12.3
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

## 2. Independent ground truth (no Intel PT): single-step the self-modified code
```
$ ./verify_singlestep 24
verify_singlestep: 24 versions, 24 single-stepped ret-points, ground truth CONFIRMED (EAX-at-ret == EXEC_TAG+i for all i)
$ echo exit=$?
exit=0
```

## 3. Capture + attribution head-to-head sweep + report (what `make` runs)
```
$ make        # .DEFAULT_GOAL := run
./verify_singlestep 24
verify_singlestep: 24 versions, 24 single-stepped ret-points, ground truth CONFIRMED (EAX-at-ret == EXEC_TAG+i for all i)
VERSIONS=24 ./run.sh > data.csv
python3 report.py data.csv
==========================================================================
pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed
==========================================================================
timing     delay  execs TSC+MTCres | fenced(ok/wrong) | time-keyed(ok/wrong)
----------------------------------------------------------------------------
coarse         0     24         24 |      24/0        |         0/24        
coarse       100     24         24 |      24/0        |         1/23        
coarse      1000     24         24 |      24/0        |         0/24        
coarse     10000     24         24 |      24/0        |         1/23        
coarse    100000     24         24 |      24/0        |         1/23        
coarse   1000000     24         24 |      24/0        |         1/23        
fine           0     24         24 |      24/0        |        24/0         
fine         100     24         24 |      24/0        |        24/0         
fine        1000     24         24 |      24/0        |        24/0         
fine       10000     24         24 |      24/0        |        24/0         
fine      100000     24         24 |      24/0        |        24/0         
fine     1000000     24         24 |      24/0        |        24/0         

==========================================================================
VERDICTS
==========================================================================
VERDICT PASS: PTW-fenced attribution is exact at every delay & timing (0 wrong)  [total fenced wrong across 12 runs = 0; no-preceding-fence = 0]
VERDICT PASS: capture is loss-free across the sweep (no OVF packets)  [total OVF packets across 12 runs = 0]
VERDICT PASS: COARSE timing: TSC+MTC time-keyed mis-attributes at EVERY delay, while PTW-fenced is exact  [coarse time-keyed wrong per delay = [24, 23, 24, 23, 23, 23]; fenced wrong = [0, 0, 0, 0, 0, 0]]
VERDICT PASS: FINE timing (CYC on): TSC+MTC time-keyed is exact -- so the PTW win is specifically at coarse timing; the fence needs NO timing packets either way  [fine time-keyed wrong per delay = [0, 0, 0, 0, 0, 0]]
VERDICT PASS: at coarse+delay0: PTW-fenced correct on all, time-keyed correct on almost none  [fenced 24/24 correct; time-keyed 0/24 correct]

Interpretation: the in-band executed PTWRITE fence pins each traced
execution to its exact self-modified version in packet order, with no
timestamps; the time-keyed method (perf/libipt-sb/wilvk) can only place
executions by PT timestamp, so when a patch and its execution fall within
the PT timestamp resolution it attributes the wrong version. Ground truth
is the EXEC payload the executed bytes produced, confirmed independently
of PT by verify_singlestep (EAX-at-ret == EXEC_TAG+i).

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0
```

## 4. Baseline (known, not the observable): PT silently misdecodes SMC
See ../../research/probes/pt-smc-misdecode/probe-output.txt (gdb+libipt show
the post-patch bytes for an execution that returned the pre-patch result).
