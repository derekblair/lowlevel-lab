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
