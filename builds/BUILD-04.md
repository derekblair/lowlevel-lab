# BUILD-04 — ifetch-sanitizer (P4, reshaped C01)

Author lane. Build of P4 (C01 reshaped), KEEP at N2 (REVIEW-01 §2.4). The
mission's ARM64 build. Part dir: `parts/04-ifetch-sanitizer/`.

## What was built

A whole-program sanitizer for missing AArch64 instruction-cache maintenance in
self-modifying/JIT code. `a64asm.py` (A64 encoder, differential-tested vs the
system assembler) builds the kernels; `icache_model.py` models the I/D cache
hierarchy parameterised by `CTR_EL0.{IDC,DIC}` and line sizes; `sanitize.py`
interprets each self-modifying kernel and reports, per config, whether the
patched code runs fresh or stale and **which maintenance step is missing**.

## The result

The diagnosis matrix is architecturally exact (RUN.md): the full
`DC CVAU → DSB ISH → IC IVAU → DSB ISH → ISB` sequence runs FRESH in every
config; each omission runs STALE and the sanitizer names the omitted step;
`IDC=1` excuses the DC step, `DIC=1` excuses the IC step, `ISB` is never excused;
and a correct sequence with the **wrong line-size stride** (big.LITTLE JIT bug)
goes STALE. All 11 VERDICTs PASS (exit 0).

## How verified

- **P4-2 encoder oracle:** 22/22 a64asm encoders byte-identical to
  `aarch64-linux-gnu-as` (`a64asm.py` selftest). Reviewer may add instructions
  to `_CASES` at the gate.
- **P4-2 semantic oracle:** the `correct` kernel's coherent-mode model end-state
  (`x0`=0x22=NEW) equals its `qemu-aarch64` exit code; qemu runs **every** kernel
  fresh (it is SMC-coherent), so qemu cannot exhibit the stale cases — those are
  model output (R10).
- **P4-3 architecture citation + herdtools7 cross-check:** every rule cites
  DDI 0487K.a B2.7.4 + CTR_EL0.{IDC,DIC}; the herdtools7
  `SM.udf+dc.cvau+dsb.ish-ic.vau-dsb.ish-isb` litmus test (fetched as data,
  herd/herdtools7 @12690a83da, saved under research/raw/) encodes the same
  conclusion — full sequence ⇒ new instruction runs, stale forbidden.
- **P4-4 labelling (R10):** README/AGENTS/report state all staleness is model
  output and "runs fine under qemu" = qemu's coherence, not silicon.
- **Clean-env:** built + run under `env -i` (11 VERDICT PASS, exit 0).

## Known weak spots (stated plainly)

- **Model, not silicon.** No ARM hardware here; staleness is the model's output,
  corroborated by qemu only in the coherent case. It encodes the DDI 0487 rule,
  not a cycle-level cache simulator.
- **Single-thread (SM-style)** kernels (match herdtools7 `SM.*`); cross-thread
  `MP.*` ifetch is out of scope (v2).
- **Sequence rule modelled as an ordered subsequence** with IDC/DIC skips and a
  wrong-stride = line-not-covered abstraction; it is the architectural
  requirement, not a per-line cache-state simulation. (goliajp models cache
  state but only the I-side; this models the whole sequence + diagnosis instead.)
- **Scoped A64 subset (P4-5)**: assembler/interpreter cover only the kernels'
  instructions, not general A64.
- herd7 itself is not installed (can't be); the cross-check rests on the fetched
  litmus test + its assertion, not a herd7 run.

## Files

`parts/04-ifetch-sanitizer/`: AGENTS.md, README.md, RUN.md, Makefile, a64asm.py,
icache_model.py, sanitize.py. Evidence: research/raw/repos/herd__herdtools7-ifetch/.

## Fidelity fix (pre-review, from REVIEW-03-build prep note)

The reviewer's BUILD-04 prep verified from the Arm ARM that **{IDC=0, DIC=1} is
architecturally impossible** ("if CTR_EL0.DIC is 1 then IDC must also be 1",
DDI 0487K.a D23.2.35). My initial CONFIGS included that impossible combination.
Removed it: the matrix now sweeps only the three valid configs
{IDC=0,DIC=0}, {IDC=1,DIC=0}, {IDC=1,DIC=1}, and a comment + the "omit-IC fresh
when DIC=1" verdict both note that DIC=1 implies IDC=1. All 11 VERDICTs still
PASS. The impossibility is cited where the configs are defined.

## Fix round 1 (REVIEW-04-build, CHANGES REQUESTED @6530c51)

All four blockers fixed; the sanitizer is now genuinely program-driven.

- **B1 (verdict read a recipe, not the program) — FIXED.** `interp` now executes
  each kernel **through** `icache_model.Machine`: it decodes the actual
  `STR/DC CVAU/IC IVAU/DSB/ISB` it runs and applies them to the model, warms the
  slot (caches the OLD word), patches with a real `STR`, and **re-fetches the
  slot through `Machine.fetch_word`** (fresh ⇒ patched word, else the pre-patch
  snapshot). The recipe-as-verdict is gone. New test B1(a): a kernel whose
  maintenance is replaced by only `DSB`s is now diagnosed **STALE** (was FRESH).
  The line-size class is a **real wrong flush address** in the program
  (`flush_off`), detected from the executed DC/IC target vs the slot's line, not
  a boolean. `icache_model.Machine` is instantiated and used.
- **B2 (rule diverged; impossible config) — FIXED.** `Machine.required()` keeps
  the `DSB`/`ISB` barriers even when IDC/DIC skip the cache op (matching Linux
  `cache.S`), so `omit-ISB` is STALE even under `IDC=1,DIC=1` and the
  `omit-DSB*` kernels are STALE. The impossible `{IDC=0,DIC=1}` config is gone;
  only the 3 valid combinations are swept.
- **B3 (cited, not quoted) — FIXED.** `ARM_REF` now **quotes verbatim** the Arm
  CTR_EL0 IDC/DIC text (incl. "if DIC=1 then IDC must also be 1") and the Linux
  `cache.S` barrier-kept fact; places the sequence at DDI 0487G.a §B2.2.5 (per
  Rutland/US11210222). The quote settles B2's DSB question.
- **B4 (semantic oracle on one kernel) — FIXED.** The oracle now compares the
  model's **coherent-mode** end state against qemu for **every** kernel (all NEW).
- **N1/N2** disclosed in README (herdtools7 covers only the full sequence; Linux
  mitigates the line-size class via the `ARM64_MISMATCHED_CACHE_TYPE` trap).

Re-verified: 11/11 VERDICTs PASS, encoder 22/22, semantic oracle all kernels ==
qemu; reproduced under `env -i`. RUN.md re-captured.

## Fix round 2 (REVIEW-04-build round 2, CHANGES REQUESTED @3e1ca1e)

Round 2 confirmed B1–B4 fixed and raised one blocker, B5, plus nits N3–N6.

- **B5 (freshness ignored where the store happens) — FIXED.** Two changes in
  `icache_model.py`, which together implement both of the reviewer's options:
  - **Anchored after the latest store.** Each STR to a word resets that word's
    progress through `required()`. The ops are then walked in program order,
    and an op counts only when it is the next required one (DC/IC also only
    when their address covers the word's line). Maintenance executed before
    the store therefore counts for nothing.
  - **The fetch reads model state.** `fetch_word` returns the instruction
    side's guaranteed view (`iview`). It starts as the loaded image and is
    advanced to the new bytes only when the anchored sequence completes.
    Otherwise it returns the last guaranteed bytes: "not guaranteed" is
    reported as STALE, never as a lucky fresh fetch.
  - `explain()` names the cause from the trace.

  New `ORDERING` kernels are VERDICTs (IDC=0,DIC=0):
  - `flush-then-write` → `OLD!dc` ("dc executed only BEFORE the latest store")
  - `re-patch` → fetch sees the maintained `NEW`, not `NEW2`; `!dc`
  - `dc-before-str` → `OLD!dc`
  - `control` → FRESH

  The reviewer's `round2_tests.py`, run unchanged against this tree, gives
  T1/T2/T3 STALE (missing `dc`), T4 `dsb`, and T0/T5 unchanged.
- **N3 (omit-DSB1 named `ic`) — FIXED.** An IC issued before the DSB that
  completes the clean is now named as the missing `dsb`, so omit-DSB1 is
  `OLD!dsb` under IDC=0 and IDC=1,DIC=0. New VERDICT.
- **N4 (line-size VERDICT was one wrong address) — FIXED.** `build_strided` is a
  real (unrolled) JIT flush: DC then IC every `stride` bytes over 4 lines,
  starting one line below the slot's line. Stride 64 → FRESH; stride 128 (a
  line size read from another core's CTR_EL0) hits lines 0x0/0x80, skips the
  slot's line 0x40 → `OLD!dc`. `flush_off` is removed.
- **N5 (sequence citation secondary) — LABELLED** "(SECONDARY: … as quoted by
  Rutland's LKML post and US11210222)" in `ARM_REF`, README and AGENTS.md.
  AGENTS.md's stale round-1 "DDI 0487K.a B2.7.4" line is also corrected.
- **N6 (`mkdtemp` litter) — FIXED** in `run_qemu`, and in `a64asm._as_encode`
  (22 dirs per run, the same class). A run now leaves 0 new temp dirs.

Also:
- **64-byte-aligned code base.** The ELF headers are padded to 128 bytes, so
  `CODEBASE` is line-aligned and the model's line partition is the real
  address-aligned one. The reviewer's T5 results are unchanged by this.
- The semantic oracle covers **all 13 kernels**: model(coherent) == qemu ==
  latest stored word, so `re-patch` exits NEW2 = 0x33.

Re-verified: 16/16 VERDICTs PASS, encoder 22/22, under `env -i`
(`make_exit=0`). RUN.md re-captured.

## Post-clearance nits (REVIEW-04 round 3: APPROVE @a980f38, N7/N8)

- **N7 — FIXED.** Under IDC=1 there is no clean, so `explain()` now says "IC
  IVAU issued before a DSB completed the **store**" (IDC=0 keeps "…the clean").
- **N8 — DISCLOSED.** `DSB ISHST` is accepted wherever a DSB is required (a
  comment in `decode`, and a README Limits bullet). Whether ISHST suffices after
  `DC CVAU` when IDC=0 is UNVERIFIED either way; the kernels use `DSB ISH`.

Re-verified: 16/16 VERDICTs PASS under `env -i`. The make output is identical
to the cleared round-2 capture. RUN.md re-captured.
