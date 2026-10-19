# part 01 — smc-observatory (AGENTS.md)

Part of **lowlevel-lab** (see ../../AGENTS.md). Author-lane build P1 of the
5-concept mission. Benign SMC machine-clear cartography on a hybrid x86 CPU.

- **What:** `smcobs.c` (C, one measurement per invocation), `run.sh` (sweep
  driver), `report.py` (stdlib aggregation + grep-able VERDICTs), `Makefile`.
  `README.md` explains it; `RUN.md` is the verbatim build+run evidence.
- **Build/run:** `make` (build + full sweep + report). `make smoke` for the
  5-point reviewer-reference check. Present tools only (gcc, make, python3
  stdlib, `perf_event_open` for own task at paranoid=2). No root, no installs.
- **Novel observable:** SMC machine-clear detection granularity differs by core
  class — Cougar Cove (P) = 64-byte line; Darkmont (E/LP-E) = 1-KiB subpage
  (Intel 248966 §3.6.8.1). Proven by the `VERDICT PASS` lines in RUN.md §3.
- **Oracle:** clear-counts reproduce the reviewer's independent reference
  (`review/evidence/presearch/c02-probe/`) exactly at its print precision.
- **Safety:** own-process only; the cross-modifying experiment is two threads of
  this process reporting clear counts, never a transmission channel. No foreign
  process is touched; no network; no writes outside this dir.
- **Scope of validity:** event codes + exact granularities are Panther Lake
  (family 6 model 0xCC); method generalises, numbers are this part's.
- **Artifacts:** `data.csv` is a generated sweep capture (reproducible via
  `make run`); `smcobs` is a build output. Both are `make clean`-able and not
  build inputs.
