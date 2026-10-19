# BUILD-02 — pt-truth (P2)

Author lane. Build of concept P2 (C03), RESHAPE to N2 per REVIEW-01 §2.2.
Part dir: `parts/02-pt-truth/`. Built with proceed-in-parallel granted at
REVIEW-01-build §22 (both P1 blockers were local).

## What was built

A **version-attribution head-to-head** (REVIEW-01-build P2-3) for Intel-PT
decoding of self-modifying code:
- `ptcap.c` traces its own code with PT + PTWRITE (branch tracing deliberately
  off), cycling a mutable region through N versions; each version logs its patch
  `rdtsc`, emits an in-band `PTWRITE(FENCE+i)`, then executes
  `mov eax,EXEC+i; ptwrite eax; ret` so the EXEC PTW payload is hardware ground
  truth of which version ran. A tunable spin sweeps the patch→execute interval;
  coarse/fine select PT timing density.
- `ptdecode.py` — a from-scratch, self-checking PT **packet framer** (stdlib),
  enough to recover PTW payloads + TSC/MTC in order (not an instruction walk).
- `attribute.py` runs **time-keyed** (TSC+MTC in the TSC domain, via the
  CPUID.15H ratio `ptcap` records — the strongest baseline) and **ptw-fenced**
  (packet order) decoders, scoring both against the EXEC-payload ground truth.
- `verify_singlestep.c` — **independent** ground truth (no PT): TF single-steps
  the same target and confirms EAX-at-`ret` == `EXEC_TAG+i` (P2-4).

## The result

- **PTW-fenced: exact at every delay and timing** (24/24, 0 wrong, 0 dropped),
  using no timing packets.
- **Coarse PT timing: TSC+MTC time-keyed mis-attributes at every delay**
  (≈23–24/24 wrong) — stale timestamps from an untraced interval.
- **Fine PT timing (CYC on): time-keyed is exact** — stated plainly; the PTW
  win is at coarse timing and in needing no timing packets.
- Ground truth confirmed independently of PT by single-step.

All 5 report VERDICTs PASS (exit 0), captured in RUN.md §3; ground truth
CONFIRMED in §2; clean build warning-free; reproduced under `env -i`.

## REVIEW-01 P2 conditions — status

- **P2-1** (NOVELTY-LOG C03 dispositions: wilvk/asm-test incl. the 1-hit miss,
  perf TEXT_POKE, libipt sideband correction, FlowJIT, DRAKVUF; drop N3):
  done at Gate 1 (commit 73fabee); README restates the surviving delta.
- **P2-2** (README/SHORTLIST novelty rewritten to the surviving in-band-PTWRITE-
  fence delta, citing items 1–5): done.
- **P2-3** (head-to-head time-keyed vs PTW-fenced on one capture, scored vs
  ground truth; report the patch→execute interval below which time-keyed
  mis-attributes, at stated MTC/CYC settings; "if time-keyed is exact at
  cycle-accurate settings, say so"): done — coarse mis-attributes at all tested
  intervals, fine (cycle-accurate/CYC) is exact and we say so.
- **P2-4** (ground-truth oracle independent of the PT path; TF/ptrace route):
  done — `verify_singlestep` (TF single-step, no perf).
- **P2-5** (C22 TNT barcode stays a bonus, not a scoring criterion): honored —
  not built here.

## Known weak spots (stated plainly)

- **CYC enabled but not decoded** in fine mode (variable-length packets), so
  fine time-keyed accuracy is a *lower bound*. It only understates time-keyed,
  never the PTW advantage, and fine time-keyed already comes out exact.
- **Packet-level framer, not a general PT instruction decoder.** It self-checks
  by consuming the whole buffer and recovering every PTW on these traces; it is
  not a libipt replacement and is not claimed to frame arbitrary PT.
- **Coarse never "recovers" in the tested delay range** (unlike my Gate-1
  sketch of a single recovery threshold): an untraced spin emits too few MTCs,
  so more delay doesn't add resolution. The honest result is the coarse-fails /
  fine-exact split, not a single-number threshold.
- Model-specific config constants (family 6 model 0xCC): `mtc_period` 5 is
  rejected here; PTW header bytes `02 32`/`02 12`. Documented in `ptcap.c`.
- Per-delay coarse wrong counts jitter by a few runs to run; the split is stable.

## Files

`parts/02-pt-truth/`: AGENTS.md, README.md, RUN.md, Makefile, ptcap.c,
verify_singlestep.c, ptdecode.py, attribute.py, run.sh (+ generated data.csv,
ptcap, verify_singlestep — `make clean`-able).
