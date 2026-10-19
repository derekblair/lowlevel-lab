# ifetch-sanitizer (ARM64)

On AArch64, data writes are **not** automatically visible to instruction fetch:
to execute code you just wrote you must `DC CVAU → DSB ISH → IC IVAU → DSB ISH →
ISB` (modulo `CTR_EL0.{IDC,DIC}`), by cache line. Skip a step — or stride the
maintenance loop by the wrong cache-line size — and the CPU runs **stale** code.
The bug is invisible on x86 (coherent I-fetch) and invisible under qemu-aarch64
(SMC-coherent), so it ships to phones and bites in the field.

This is a **whole-program sanitizer** for that mistake. Give it a self-modifying
kernel and a `CTR_EL0` / line-size config; it runs the kernel through a small
A64 interpreter whose instruction fetch obeys a modelled I/D cache hierarchy and
reports whether the patched code runs **fresh or stale** and, if stale, **exactly
which maintenance step is missing**.

```
kernel        IDC=0,DIC=0   IDC=1,DIC=0   IDC=1,DIC=1
correct             NEW           NEW           NEW
omit-DC          OLD!dc           NEW           NEW   <- IDC=1 excuses DC; step named
omit-DSB1       OLD!dsb       OLD!dsb           NEW   <- the IC is there; the DSB before it is not
omit-IC          OLD!ic        OLD!ic           NEW   <- DIC=1 (=>IDC=1) excuses IC
omit-DSB2       OLD!dsb       OLD!dsb           NEW
omit-ISB        OLD!isb       OLD!isb       OLD!isb   <- ISB is never excused (kept even if DIC=1)
none             OLD!dc       OLD!dsb       OLD!dsb
```
(Only the three architecturally-valid CTR_EL0 combinations are swept:
`{IDC=0,DIC=1}` is impossible — Arm CTR_EL0 says DIC=1 implies IDC=1. The
barriers (`DSB`, final `ISB`) are **kept even when IDC/DIC excuse the cache op**,
matching Linux `cache.S` — see B2 below.)

**Order matters.** The maintenance must come *after the store it publishes*. Three
real JIT bugs with every instruction present but in the wrong place are all
caught, each with its cause (REVIEW-04 round 2, B5):
```
kernel             IDC=0,DIC=0   IDC=1,DIC=0   IDC=1,DIC=1   cause (IDC=0,DIC=0)
control                    NEW           NEW           NEW   fresh
flush-then-write        OLD!dc       OLD!dsb       OLD!dsb   dc executed only BEFORE the latest store
re-patch                NEW!dc       NEW!dsb       NEW!dsb   re-patched after its maintenance completed
dc-before-str           OLD!dc           NEW           NEW   dc executed only BEFORE the latest store
```
(`re-patch` stores NEW, maintains it, then stores NEW2 and runs: the fetch sees
the maintained NEW, not NEW2. `dc-before-str` is fresh under IDC=1 because no
clean is required there — the DSB, IC, DSB, ISB do follow the store.)

## Why this is novel (see ../../research/NOVELTY-LOG.md C01; REVIEW-01 §2.4)

The ifetch-coherence hazard is well studied, but existing tools stop short of a
whole-program step-naming sanitizer that also models the line-size-mismatch
class:
- **goliajp/aarch64-study** v0.22 models a stale I-cache demo but makes
  `DC CIVAC` a **no-op** (no D-cache), varies no `CTR_EL0` bits, and is one fixed
  demo — it cannot show the DC step, the barriers, or IDC/DIC mattering.
- **cyyself/jit-coherence-test** runs the real-hardware skip-flag test but is
  pass/fail on whatever CPU runs it, with no per-step diagnosis and no model.
- **herdtools7** `catalogue/aarch64-ifetch` (herd7 `-variant ifetch`) and
  **RMEM** (cl.cam.ac.uk/~pes20/iflat/, which exposes the IDC/DIC knobs) model
  ifetch at **litmus-test scale** — tiny fixed programs, not a sanitizer over an
  arbitrary patch sequence, and without the line-size-mismatch class.
- **hatter6822/seLe4n** `CacheModel.lean` (found by REVIEW-FINAL's fresh
  searches; as read by the reviewer): a Lean proof model of one microkernel's
  own I-cache obligations. It has no CTR_EL0 IDC/DIC, no line-size class and no
  step naming.
- **Arm FVP** `cache_state_modelled` and **DynamoRIO**'s SW-cache-consistency
  (keyed on the app's `IC IVAU`) hide or react to the hazard; neither *diagnoses*
  the omitted step.

The surviving N2 delta: a **whole-program** model that, for any patch sequence
and any `CTR_EL0`/line-size config, **names the specific omitted step** and
covers the **I/D line-size-mismatch** (big.LITTLE JIT) class.

## The pieces

- `a64asm.py` — a tiny A64 assembler for the kernel subset. `selftest()`
  differential-tests all 22 encoders against `aarch64-linux-gnu-as` (R6 / P4-2
  encoder oracle): GNU binutils is the authority, not this file.
- `icache_model.py` — the modelled I/D coherence state + `Config(IDC,DIC,Dline,
  Iline)`. It is **driven by the instructions the interpreter executes**: the
  interpreter calls `store/dc/ic/dsb/isb` as it decodes `STR / DC CVAU / IC IVAU
  / DSB / ISB`. Each STR to a word **resets** that word's progress through the
  required sequence, so only maintenance executed *after the latest store*
  counts, in program order (B5). `fetch_word` reads the model's **instruction-
  side view**: the loaded image, advanced to the new bytes only when that
  anchored sequence completes; otherwise it returns the last guaranteed bytes.
  `explain` names the cause from the trace. All staleness is **model output**
  (R10 / P4-4).
- `sanitize.py` — the interpreter (executes each kernel **through** the model),
  a kernel builder from ordered action lists (warm / store / DC / IC / DSB / ISB
  / run), the matrix, ordering and strided-flush kernels, the qemu semantic
  oracle, and the grep-able VERDICTs. The verdict depends on the program's
  instructions and their order, not on any recipe (REVIEW-04 B1, B5).

## Oracles (P4-2) and architecture citation (P4-3)

- **Encoder oracle:** 22/22 a64asm encoders are byte-identical to
  `aarch64-linux-gnu-as` (RUN.md). The reviewer may add instructions to
  `a64asm._CASES` at the gate.
- **Semantic oracle (P4-2, B4):** **all 13** kernels' end state under the
  model's **coherent** mode equals their exit code under **qemu-aarch64 8.2.2**
  and the latest word each one stores (the 7 matrix kernels, the 4 ordering
  kernels — `re-patch` exits with NEW2=0x33 — and both strided flushes). qemu runs
  every kernel fresh (it is SMC-coherent), so qemu **cannot** show the stale
  cases — those are model output (R10). "Runs fine under qemu" means qemu's
  coherence, never silicon.
- **Architecture citation (P4-3, B3):** `ARM_REF` in `sanitize.py` **quotes
  verbatim** the Arm CTR_EL0 IDC/DIC definitions (incl. "if DIC=1 then IDC must
  also be 1") and the Linux `cache.S` fact that the **barriers are kept** when
  IDC/DIC skip a cache op — which is why `omit-ISB` is stale even under
  `IDC=1,DIC=1`, and `omit-DSB*` are stale. The canonical sequence's location,
  DDI 0487G.a §B2.2.5, is **secondary** (as quoted by Rutland's LKML post and
  US11210222; not checked against the manual here).
- **herdtools7 cross-check (data, not run):** the published litmus test
  `SM.udf+dc.cvau+dsb.ish-ic.vau-dsb.ish-isb.litmus`
  (`research/raw/repos/herd__herdtools7-ifetch/`, fetched from herd/herdtools7
  @12690a83da) patches `NOP` over a `UDF` and runs the **full** five-step
  sequence; its assertion is `exists(fault(P0:L0, UndefinedInstruction))`, i.e.
  with the full sequence the **new** instruction must run and the stale (UDF)
  outcome is forbidden. That is exactly this model's `correct ⇒ fresh in every
  config`. (herd7 itself cannot be installed here; the test + its assertion are
  the fetched evidence.)

## How to run

```
make            # encoder oracle + semantic oracle + diagnosis matrix + VERDICTs
python3 a64asm.py     # just the encoder differential test
python3 sanitize.py   # just the sanitizer
```

## Limits / honesty

- **Model, not silicon (R10).** There is no ARM hardware here; staleness is the
  model's output, corroborated only where qemu can (the coherent case). The
  model encodes the DDI 0487 rule; it is not a timing or microarchitectural
  simulator.
- **Scoped A64 subset (P4-5).** The assembler/interpreter cover exactly what the
  kernels need (movz/movk, add/sub, str/ldr, blr/ret/br, dc/ic/dsb/isb, svc).
  Not a general A64 implementation.
- **Single-thread (SM-style).** The kernels are store-modify-execute on one
  thread (matching the herdtools7 `SM.*` tests); cross-thread (`MP.*`) ifetch
  is out of scope and noted for v2.
- **The maintenance rule is the required sequence walked in program order,
  anchored after the latest store** to the word (DC, DSB, IC, DSB, ISB; the
  cache ops skippable per IDC/DIC but the DSB/ISB barriers kept). An op counts
  only when it is the next required one; DC/IC count only where their actual
  target address covers the word's line, so a wrong flush stride is caught from
  the program. An IC issued before the DSB that completes the clean is named as
  a missing DSB.
- **Conservative fetch: "not guaranteed" is reported as STALE.** Where the
  architecture does not guarantee the new bytes, the model fetches the last
  guaranteed ones (the worst case a stale I-cache, a dirty D-line or an
  un-synchronised prefetch can show), never a lucky fresh fetch. Real silicon
  may *happen* to fetch the new bytes in some of those cases; the sanitizer's
  claim is about what the architecture guarantees. This is the architectural
  requirement, not a cycle-level cache simulation.
- **`DSB ISHST` is accepted wherever a DSB is required** (REVIEW-04 N8). Linux
  issues `dsb ishst` only on the IDC path. Whether ISHST (stores only) suffices
  after `DC CVAU` when IDC=0 is not established here: **UNVERIFIED either way**.
  The kernels themselves use `DSB ISH`.
- **Lines are address-aligned:** the kernels load at a 64-byte-aligned code base
  (ELF headers padded to 128 bytes), so the model's line partition is the real
  one. The strided flush is **unrolled** (the interpreted subset has no
  branches): the loop body a JIT emits, written out.
- **herdtools7 cross-check covers only the full sequence** (N1): the `SM.udf`
  litmus test corroborates `correct ⇒ fresh`, not the per-config skips, which
  rest on the quoted Arm/Linux rule.
- **Linux mitigates the line-size class** (N2): the `ARM64_MISMATCHED_CACHE_TYPE`
  CTR_EL0 trap makes the kernel advertise the smallest line across cores, so the
  big.LITTLE stride bug this part models is mitigated in practice on Linux.
- **Safety:** benign — a cache-maintenance teaching/diagnostic tool; the qemu
  runs are tiny own-built kernels; no network, no writes outside the dir.
