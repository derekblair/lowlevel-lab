# smc-observatory

A benign, own-process microbenchmark that **maps the self-modifying-code (SMC)
machine-clear behaviour of a hybrid x86 CPU by core class**. On this Intel
Panther Lake part it shows a concrete, reproducible fact:

> The CPU flushes the pipeline when you execute code you just wrote — but the
> **distance** over which it watches for that write is a **different size on
> each kind of core**. On a **Performance core (Cougar Cove)** the window is a
> single **64-byte cache line**. On an **Efficiency core (Darkmont, both the
> E and the low-power LP-E clusters)** it is a **1-KiB subpage** — 16× wider.

That 1-KiB figure is the Pentium-4-era guidance in Intel's Optimization
Reference Manual (248966) §3.6.8.1 ("avoid writing to a code page in the same
1-KByte subpage that is being executed"). It still describes the efficiency
cores and does **not** describe the performance cores.

## Why this is novel (see ../../research/NOVELTY-LOG.md, C02 / P1)

SMC penalties are usually quoted as folklore ("~an SMC nuke costs ~X cycles,
avoid it"). The adjacent published work measures something else:
- **SMaCk** (ASPLOS'25) and **Botacin, Zanata & Grégio — "SMC-Aware Processor
  (SAP)"** (J. Computer Virology & Hacking Techniques; repo
  `marcusbotacin/Self-Modifying-Code`) study SMC for *security* (an L1i cache
  attack; architectural-impact simulation) on a **single core class**, with no
  write-distance sweep and no hybrid comparison.
- **libLISA** (OOPSLA'24) compares P vs E *instruction semantics*, not SMC cost.

No public tool maps SMC **machine-clear cost and detection granularity as a
function of write↔execute distance, per core class, on one hybrid die**, nor
uses the Darkmont-only `MACHINE_CLEARS.XMC` counter. That map is the
contribution. (Prior art is disclosed in the novelty log; this is N3.)

## Novel observable (what a run proves — RUN.md line references)

Run it and read the two tables + the `VERDICT` lines in `RUN.md` §3:
- **The per-class granularity split** — the `placement: code at byte 0` table:
  row `P` is non-zero only for store offsets `< 64`; rows `E`/`LP-E` are
  non-zero for offsets `< 1024`. (`VERDICT PASS: P … 64-byte window`,
  `… E … 1024-byte window`, `… LP-E … 1024-byte window`.)
- **They genuinely differ** — a store 512 bytes from the code makes a Darkmont
  core nuke but leaves a Cougar Cove core silent (`VERDICT PASS: P and
  Darkmont granularities DIFFER`).
- **It is §3.6.8.1 for Darkmont, tighter for Cougar Cove** (`VERDICT PASS:
  Intel 248966 3.6.8.1 … matches Darkmont`, `… does NOT describe Cougar Cove`).
- **The window tracks the code, not the page** — the `code at byte 1536` table
  shows the Darkmont window move to the second 1-KiB subpage
  (`VERDICT PASS: detection window tracks the CODE's subpage`).
- **Magnitude matches the reviewer's independent reference** — P nukes twice
  per modify-execute iteration, Darkmont once (`VERDICT PASS: in-window
  clears/iter: P==2.000, Darkmont==1.000`).
- **Cross-modifying code** shows the asymmetric `XMC` counter (Darkmont only)
  and **torn-fetch** shows 0 torn reads on this part (stated as observed, not
  guaranteed).

## How to run

```
make           # builds smcobs, runs the full sweep, prints the report
# or, step by step:
make smcobs    # gcc -O2 -pthread -o smcobs smcobs.c
make smoke     # 5 points that must match the reviewer c02-probe reference
./run.sh > data.csv          # full sweep: 3 classes x 2 placements x offsets x 5 runs + xcore + torn
python3 -I report.py data.csv  # medians, tables, grep-able VERDICT lines; exit 0 iff all pass
```
Override the sampled CPUs / repeat count: `CPUS="0 5 13" REPEATS=5 ./run.sh`.
CPUs 0–3 are P (Cougar Cove), 4–11 are E (Darkmont), 12–15 are LP-E (Darkmont,
no L3); the defaults pick one representative per class, matching the reviewer's
reference so clear-counts compare directly.

## Requirements (R8)

- `gcc` + `-pthread` (glibc), `make`, `python3` (stdlib only — no numpy/pandas).
- Linux `perf_event_open` for **own task**, which `perf_event_paranoid=2`
  permits; no root, no `perf` binary, no PAPI, no `taskset` (affinity is a
  `sched_setaffinity(2)` call inside `smcobs`).
- An Intel hybrid CPU with `cpu_core` + `cpu_atom` PMUs. The event encodings
  (`MACHINE_CLEARS.SMC/.XMC/COUNT`) are hard-coded for family 6 model 0xCC
  (Panther Lake) from Intel perfmon `PTL/`; on another model the event codes
  would need updating (the code documents them).
- Nothing else: no network, no writes outside this directory, no other process
  is read or written.

## Precision note (REVIEW-00 §1.18)

Clears/iteration is reported from `count / NITER` with `NITER=200000`. In-window
the count is **2 (P) / 1 (Darkmont) per iteration minus a small, variable
shortfall** — measured (by the reviewer's `deficit_probe.c`, 54 runs) at **2–42
counts per 2×10⁵ iterations, varying run to run, not removed by a warm-up**, so
the **cause is not established** (interrupts landing inside the loop are one
untested candidate; it is *not* a fixed counter-boundary artefact — an earlier
version of this note claimed that and was wrong). The shortfall is why P prints
e.g. `1.9999` rather than `2.0000`. It is always < ~100 counts, so VERDICT 8's
3-decimal comparison against the reviewer reference is robust to it, and nothing
load-bearing changes. Timings (`tsc/iter`) vary with frequency/thermal state and
are order-of-magnitude context only; the **clear counts** are the load-bearing
numbers (the detection-window boundaries are identical across all repeats).

## A teaching detail: the sweep's store is *silent*

In the distance sweep the store writes `0xcc` onto the page's existing `0xcc`
`int3` fill — the byte does not change — yet the machine clears still fire. So
**SMC detection here is address-based, not value-based**: the core nukes because
an address it is fetching was *written*, regardless of whether the bytes
changed. (The cross-modifying and torn probes do change bytes; only the sweep is
silent.)

## Limits / honesty

- **x86-specific, this-model-specific.** The event codes and the exact
  granularities are for Panther Lake (family 6 model 0xCC). The *method*
  generalises; the *numbers* are this part's.
- **Own-process only, by design (safety).** The cross-modifying experiment uses
  two threads of this one process and reports machine-clear counts; it is not,
  and must not be turned into, a covert/side channel. No code outside this
  process is read, written, or executed.
- **Torn-fetch is a negative result** ("none observed under these conditions"),
  not a guarantee; unsynchronised cross-modifying code is architecturally
  unpredictable.
- The P=2 / Darkmont=1 clears-per-iteration difference is **reported and
  flagged**; the exact microarchitectural reason (why Cougar Cove books two
  nukes per modify-execute) is not established here.
