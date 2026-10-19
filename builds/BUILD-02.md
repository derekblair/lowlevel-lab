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

## Fix round 1 (REVIEW-02-build, CHANGES REQUESTED @21475a8)

Both blockers fixed. The corrected result is **stronger and more honest** than
round 1's, exactly as the reviewer predicted.

- **B1 (time-keyed baseline was a strawman by implementation) — FIXED.** Round 1
  computed the time-keyed clock by **counting MTC packets** × a fixed period;
  in coarse mode the hardware *skips* MTC periods, so that clock fell behind and
  every exec looked like it preceded its patch (→ "coarse fails everywhere",
  false). `attribute.py` now reconstructs the TSC-domain clock the way a real
  sideband decoder does: **anchor CTC at the TSC+TMA pair, advance from each
  MTC's payload** (CTC[period+7:period], 8-bit wrap), convert via CPUID.15H.
  Cross-checked against the reviewer's independent `payload_timekeyed.py` (same
  algorithm, agreeing results). The honest result: time-keyed is **exact in a
  middle band of patch→execute intervals (~10³–10⁵ TSC ticks)** and
  mis-attributes **below** it (too few CTC ticks) and **above** it (the 8-bit MTC
  payload wraps between the sparse BranchEn=0 TSC anchors — the delay-10⁶
  long-gap regime). Intervals are now reported in **TSC ticks** (ptcap logs the
  patch and exec rdtsc). VERDICT 3/4, README "The result"/"Interpretation" and
  this file rewritten to match. "fine is exact" and "the fence needs no timing
  packets" are kept — both still true. (b) The band edges and the short-interval
  point are reported; the long-gap failure is the stable blocking verdict.
- **B2 (`make` not reproducible: OVF 6/8 runs) — FIXED.** Root cause: fine mode
  with CYC floods the AUX ring at long delays. Fix: (1) AUX ring 4→8 MiB; (2)
  fine delays capped at 10⁴ (the long-gap regime is a *coarse* phenomenon, so
  nothing is lost); (3) OVF is now treated as data — reported per row and
  **excluded from time-keyed accuracy scoring**, so a stray overflow never fails
  `make`. Verified **5/5 consecutive clean `make` runs PASS, 0 OVF**; RUN.md §3
  shows 2 consecutive runs; RUN.md's nondeterminism section declares OVF and the
  jittery band edges.

Nits: N1 framer PTW IP-bit handling corrected (IP bit ⇒ a separate FUP follows,
not bytes inside the PTW packet) + README qualifier; N2 the unused `truth.csv`
(intended-version) dropped — ground truth is the EXEC payloads + verify_singlestep;
N3 README order corrected to patch→fence→spin→exec; N4 the `mfence/lfence`
removed and the comment corrected (the indirect call to new code is what
satisfies the SDM rule); N5 README states the BranchEn=0 scope; N6 interpretation
text rewritten (resolved by B1).

Re-verified: clean warning-free build; 5/5 `make` runs PASS; ground truth
CONFIRMED; reproduced under `env -i`.

## Post-clearance correction (REVIEW-02 round 2: APPROVE @cc7e74d, nits a–d)

Applying nit **(d)**, pinning the captures, **changed a cleared claim**, so I
am re-opening this gate for review rather than folding it in silently.

- **What changed.** With every capture pinned per core class (CPU 0 Cougar Cove
  P, CPU 4 Darkmont E, CPU 12 Darkmont LP-E), the coarse time-keyed **long-gap
  failure is Darkmont-only**. On Cougar Cove it stays exact out to ~1×10⁷ TSC,
  >45× the predicted edge, in 3/3 runs. The cleared runs were unpinned, so their
  long-gap captures evidently landed on Darkmont cores.
- **Mechanism, from the packets.** `attribute.py` now records MTC/TSC counts
  per capture. At the longest gap (BranchEn=0, `mtc_period` 3):

  | class | MTC per capture | TSC per capture |
  |---|---|---|
  | Cougar Cove | ≈2.7–3.4×10⁵ (one per MTC period) | ~300 |
  | Darkmont E, LP-E | ~250–400 (sporadic) | 1 |

  So the 8-bit payload wraps unobserved only on Darkmont. A VERDICT checks the
  ≥100× gap.
- **(c) prediction, now a VERDICT.** The upper edge is 2^(mtc_period+8) CTC ×
  TSC/CTC (CPUID.15H 192/2) = **196,608 TSC**. On Darkmont it falls between
  LP-E's last exact rows (1.6–1.8×10⁵) and E's first failing rows
  (2.2–2.8×10⁵). The VERDICT requires agreement within 2×.
- **(a)** The two can't-fail checks are now INFO lines. VERDICT 3 is renamed to
  "exact over an interval band".
- **(b)** README: the fine cap at 10⁴ loses no result. Before the cap, fine mode
  was 24/0 at delays 10⁵ and 10⁶ too (`review/evidence/build-02/
  payload-vs-count.txt`); the cap only removes OVF risk.
- **(d)** `run.sh` pins each sweep with `taskset -c` (override with `PT_CPUS`)
  and tags each CSV row with its CPU. `report.py` gives per-class tables and
  VERDICTs.

Also: `run.sh`'s `mktemp -d` workdir is now removed on exit unless `WORK` is
given. This is the same litter class as P4/C09's N6.

**Unchanged:** PTW-fenced is exact on every row of every class; fine timing is
exact on every class. The N2 claim stands. It is now stated per core class,
with a predicted edge and the mechanism measured. *[Corrected at REVIEW-02
round 3, B3: this line originally also said "time-keyed fails at short
intervals everywhere". That is false for Cougar Cove, which is exact down to
about one MTC period. See the round-2 correction below.]*

Re-verified: 3/3 consecutive `make` runs under `env -i`, each covering all
three classes, give 10/10 VERDICTs PASS. RUN.md re-captured.

## Post-clearance correction, round 2 (REVIEW-02 round 3: CHANGES REQUESTED @71bb650 — B3, N7, N8)

- **B3 (the short-interval failure was over-generalized) — FIXED.** Time-keyed
  does **not** fail at short intervals on every class:
  - **Cougar Cove:** exact at every tested interval ≥ 2 MTC periods, from
    ~2×10³ TSC up to the longest gap.
  - **Darkmont:** fails at the shortest interval in every run, and at long gaps.

  Corrected in README (the result section, the claim paragraph and the fence
  advantages), AGENTS.md, this file's "Unchanged" line (marked in place), and
  `report.py` (docstring, VERDICTs, Interpretation). The fence's accuracy
  advantage is now stated as Darkmont at short and long gaps, and P only near
  or below one MTC period. (b) and (c) hold on every class.
- **P's lower edge, measured rather than asserted.** The reviewer asked me to
  either reach a P lower edge or say it wasn't reached. My first re-capture
  happened to put P rows below one MTC period, and some failed. So I added a
  dedicated short-delay probe on CPU 0 (RUN.md §5, verbatim, 5 repeats):
  - the 8 of 20 coarse rows that mis-attribute (1–4 of 24) all have median
    intervals below ~1.2 periods (298–914 TSC);
  - every row at ≥ 970 TSC is exact;
  - all 20 fine rows are exact, including 4 below one coarse period.

  So P's lower edge sits at about one MTC period, the resolution of a clock
  that ticks every period. Because `interval` is a *median* of 24 per-exec
  intervals, P's VERDICT requires exactness only from **2 periods** (1,536 TSC)
  up. That margin is physical, not fitted: the worst failing median observed
  is 914. Rows below it are INFO.
- **N7 — FIXED, and measured in my own pipeline.** `attribute.py` now records,
  per capture, the number of consecutive MTC payload steps that are 0 mod 256
  (Δ0), and the trace bytes.
  - Darkmont at the longest gap: 43–77% Δ0 across today's pinned runs (chance
    level 1/256).
  - Cougar Cove: zero Δ0; every step is +1.

  The text now says "about one per payload wrap (Δ0 dominates)", not
  "sporadic". The mechanism VERDICT requires P's zero Δ0 and Darkmont's ≥ 10%
  share (~25× chance). My first threshold (≥ 50%) was set from too few runs:
  E measured 43–50% when its long gap was shorter, so I re-anchored it to the
  chance level rather than to observations.
- **N8 — FIXED.** The onset VERDICT detail now states how far below and above
  the edge the bracketing rows lie, and which side is tight within 2× in that
  run. E usually brackets from the failure side, LP-E often from the exact
  side.
- **Price, now reported:** at the longest gap Cougar Cove's trace is ~230–340×
  larger than Darkmont's (the reviewer measured ~475× in their runs). This is
  INFO in the report and stated in the README.

Re-verified: 3/3 consecutive `make` runs under `env -i`, each covering all
three classes, give 12/12 VERDICTs PASS; the §5 probe is appended verbatim.
RUN.md re-captured.

## Post-clearance nit N9 (REVIEW-02 round 4: APPROVE @abd11f4)

- **N9 — FIXED.** The gated "Darkmont mis-attributes at the shortest tested
  interval" could rest on one execution: the reviewer saw LP-E's shortest row
  land at 852 TSC with 1/24 wrong. The coarse sweep now includes delays **25
  and 50**, which put each class's shortest row well below one MTC period.
  - In RUN.md the Darkmont shortest rows are E at 192–318 TSC (3–15 wrong) and
    LP-E at 248–536 (7–14 wrong); three extra pre-capture runs gave 4–15
    wrong.
  - RUN.md's determinism note now says this row's count varies but stays clear
    of zero.
  - For P the extra rows only feed the INFO edge report; P's gated check starts
    at 2 periods.
- README numbers re-synced to the re-captured RUN.md. The N8 sentence is
  generalized: which bracket side is tight depends on where each run's 10⁵
  step lands; this capture had E bracketing from the exact side.

Re-verified: 3/3 `make` under `env -i`, 12/12 VERDICTs PASS each; the §5
probe is preserved verbatim.
