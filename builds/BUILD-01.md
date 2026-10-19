# BUILD-01 — smc-observatory (P1)

Author lane. Build of concept P1 (C02), KEEP at N3 per REVIEW-01 §2.1.
Part dir: `parts/01-smc-observatory/`.

## What was built

A benign own-process microbenchmark (`smcobs.c`, ~230 lines C) + a sweep driver
(`run.sh`) + a stdlib aggregator (`report.py`) that map self-modifying-code
machine-clear behaviour on this hybrid x86 part by core class:
- a **distance sweep** of `MACHINE_CLEARS.SMC` vs the store's offset from the
  executing code, at sub-page resolution, for two code placements (aligned at
  offset 0; shifted into the 2nd 1-KiB subpage at 1536), across the three core
  classes P (cpu0) / E (cpu5) / LP-E (cpu13);
- a **cross-modifying-code** experiment (writer thread + executor thread,
  counting SMC and the Darkmont-only XMC on the executor);
- a **torn-fetch** probe (instruction straddling a 64-byte boundary).

## The finding

SMC machine-clear **detection granularity is per core class**:
- **Cougar Cove (P): one 64-byte cache line.**
- **Darkmont (E and LP-E): one 1-KiB subpage** — matching Intel 248966
  §3.6.8.1 (Pentium-4-era rule), which thus still describes the efficiency
  cores and not the performance cores.
The window tracks the code's own line/subpage (not the page base), and the
in-window clear magnitude is 2/iteration on P, 1/iteration on Darkmont.

## How verified

- **Independent oracle:** reproduces the reviewer's reference probe
  (`review/evidence/presearch/c02-probe/sweep.txt`) exactly — P@same-line=2,
  P@next-line=0; E/LP-E@same-1KiB=1, @next-1KiB=0 (see RUN.md §2–3).
- **Machine-checkable:** `report.py` emits 10 grep-able `VERDICT` lines and
  exits non-zero unless all pass; the captured run shows `ALL VERDICTS PASS`
  / `report_exit=0` (RUN.md §3).
- **Clean-env reproduction:** built and run under `env -i HOME=… PATH=/usr/local/bin:/usr/bin:/bin
  LANG=C.UTF-8` with empty stderr (pre-checked; the reviewer will redo this in
  a fresh clone per REVIEW-00 §2.2).
- **Determinism:** clear counts are identical across all 5 repeats per point;
  timings vary and are used only as order-of-magnitude context (§1.18).

## REVIEW-01 BUILD-01 conditions — status

- **P1-1** sub-page sweep (power-of-two offsets + same-line, aligned +
  shifted placement, §3.6.8.1 tested explicitly): **done** (two placement
  tables, VERDICTs for both boundaries).
- **P1-2** three classes P(0–3)/E(4–11)/LP-E(12–15) reported separately:
  **done** (never "E=4–15").
- **P1-3** §1.18 discipline (median+spread, ≥5 runs, pinned, tolerance);
  clears match reference, timings to order of magnitude; P=2-vs-E=1 explained-
  or-flagged: **done** (flagged; precision note in README; the ~2-count boundary
  loss is documented, VERDICT 8 compares at the reference's %.3f precision).
- **P1-4** safety, own-process only, no channel: **done** (README + AGENTS).
- **P1-5** XMC asymmetry (Darkmont only): **done** (VERDICT + xcore table).
- **P1-6** torn-fetch stated as observed-not-guaranteed: **done**.
- Botacin SAP cited (README + novelty log): **done**.

## Known weak spots (the reviewer will find these; stated plainly)

- **P=2-clears-per-iteration is unexplained.** Direction and magnitude are
  stable and match the reference, but *why* Cougar Cove books two nukes per
  modify-execute iteration (vs Darkmont's one) is not established — flagged, not
  explained.
- **Model-specific constants.** Event encodings and the exact 64 B / 1 KiB
  numbers are Panther Lake (family 6 model 0xCC). On another Intel model the
  event codes in `event_config()` would need updating; the sweep method is
  portable but the numbers are not claimed to be.
- **Timings are noisy.** `tsc/iter` swings with frequency/thermal state (e.g.
  LP-E first-touch spikes); only the clear *counts* are load-bearing.
- **Representative-CPU sampling.** The default samples one CPU per class
  (0/5/13). The reviewer reproduced the probe across 0/2/3, 4/9/11, 12/15; the
  class generalisation rests on that + the shared-PMU/topology evidence, not on
  sweeping all 16 here (kept fast + reproducible, P1 risk note).
- **Cross-modifying magnitudes** (clears per 1e6 executes) are reported for
  context; they depend on the writer/executor scheduling and are not pinned to
  a tolerance (the SMC *granularity* is the claim, not the XMC rate).

## Files

`parts/01-smc-observatory/`: AGENTS.md, README.md, RUN.md, Makefile, smcobs.c,
run.sh, report.py (+ generated data.csv, smcobs — `make clean`-able).
