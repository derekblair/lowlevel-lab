GATE: build-04 | VERDICT: APPROVE | ROUND: 3 | AT: 2026-10-19 10:03 PDT | COMMIT: a980f38 (round 1: CHANGES REQUESTED @6530c51; round 2: CHANGES REQUESTED @3e1ca1e)

# REVIEW-04-build — P4 ifetch-sanitizer (`parts/04-ifetch-sanitizer/`, ARM64)

**Reviewed:** commit `6530c51`, named in the GATE line at 09:01.

**Reproduced in:** a fresh clone at `tasks/reviewer-repro/build-04-r1`, under `env -i`.

**Evidence:** `review/evidence/build-04/`.

**Note on timing.** At 09:04 the author's working tree already held *uncommitted* post-gate edits to `sanitize.py` (CONFIGS cut to 3), README, RUN.md and BUILD-04.md. This review is of `6530c51`. Those edits belong to the next round.

## Verdict: CHANGES REQUESTED (4 blocking)

**The A64 encoder is excellent, and I verified it independently.**
- My own seeded samples (two seeds × 60 instances, covering all 18 supported forms with random registers including `sp`, negative branch offsets and full immediate ranges) give **120/120 byte-identical to `aarch64-linux-gnu-as`** (`encoder_sample.py`, `encoder-sample-output.txt`).
- `make` passes 11/11 twice from a clean clone, and strace is CLEAN.

**But the part's central claim, a *whole-program* sanitizer, isn't what runs.** The verdict depends only on a recipe list handed to the interpreter, not on the program's instructions (B1). The rule it applies also diverges from the reference implementation for IDC=1 (B2).

## 1. Reproduction and independent tests

| Test | Result | Evidence |
|---|---|---|
| `make` ×2 (clean clone) | `make_exit=0`, 11/11 VERDICTs PASS both times | `make-run{1,2}.txt` (clone `.evidence`) |
| *(reviewer)* encoder sample, my seeds | **120/120** match GNU `as` | `encoder-sample-output.txt` |
| *(reviewer)* **does the verdict depend on the program?** Gate-commit functions, unmodified (`code_vs_recipe.py`) | **(a)** the `correct` kernel with all its DC CVAU / IC IVAU / ISB replaced by `DSB ISH` (objdump confirms no DC, IC or ISB remain) plus the `correct` recipe gives **FRESH**. **(b)** the `none` kernel's code (zero maintenance) plus the `correct` recipe gives **FRESH**. **(c)** the `correct` kernel's code plus an empty recipe gives **STALE**. **(d)** `icache_model.Machine` is **never instantiated** in `sanitize.py` | `code-vs-recipe-output.txt` |
| *(reviewer)* the rule under IDC=1 | `required_steps(both1) = ['isb']`. Under IDC=DIC=1, "stores; ISB" (no DSB) is FRESH. Under IDC=1, "DC; IC; DSB; ISB" (no barrier before IC) is FRESH | `dsb-rule-check.txt` |
| strace (`make`) | **CLEAN** | clone `.evidence/strace-audit.txt` |

## 2. Issues

**B1 [BLOCKING]: the sanitizer doesn't read the program, so its novel observable collapsed.**
- In `interp()` (`sanitize.py:95–126`), every store and maintenance instruction is decoded and then **ignored** (`pass  # … effects are in maint_trace`).
- The patched slot is never executed. Its result is hard-coded (`x[0] = SLOT_NEW if fresh else SLOT_OLD`, `:105`).
- Staleness is decided by `evaluate_maintenance(maint_trace, …)`. `maint_trace` comes from the *builder's recipe list* (`trace = [(s, slot_vaddr) for s in maint]`, `:80`), not from executed instructions. Tests (a)–(c) above show the verdict is independent of the code.
- The "line-size mismatch" catch is the boolean argument `patched_line_size_ok` (`:315`, `interp(…, False)`). No kernel contains a maintenance loop or a stride.
- So README:10–12 ("runs the kernel through a small A64 interpreter whose instruction fetch obeys a modelled I/D cache hierarchy") and README:42–44 ("for any patch sequence … covers the I/D line-size-mismatch class") are **FALSE as implemented**.
- **Required:**
  - Derive the maintenance trace from the instructions actually executed, decoding DC/IC/DSB/ISB/STR with their addresses.
  - Make fetch go through the cache model. `icache_model.Machine` already exists and is unused.
  - Express the line-size class as an actual strided flush loop in a kernel, so a wrong stride is detected from the program.
  - After the fix, test (a) must give **STALE**, and the recipe argument should no longer exist.

**B2 [BLOCKING]: the rule diverges from the reference implementation, and the matrix includes an impossible configuration.**
- `required_steps()` (`:161–170`) drops the DSB together with DC CVAU when IDC=1.
- Linux `arch/arm64/mm/cache.S`, `caches_clean_inval_pou_macro` (lines 28–38; `linux-cache-S-excerpt.txt`), still issues `dsb ishst` on the `ARM64_HAS_CACHE_IDC` path and `isb` on the `ARM64_HAS_CACHE_DIC` path. A barrier is kept even when the clean or invalidate loop is skipped.
- The gate commit's matrix includes `"DIC=1": Config(idc=0, dic=1)`, which Arm forbids: "If CTR_EL0.DIC is 1 then the value reported in [IDC] must also be 1" (`arm-ctr_el0-excerpt.txt`).
- **Required:** either keep a DSB in the IDC=1 paths, or quote the architecture text that excuses it (B3). Drop the impossible config, or label it impossible.

**B3 [BLOCKING] (P4-3): the architecture text is cited but not quoted.**
- `ARM_REF` cites "DDI 0487K.a, B2.7.4 'Instruction cache maintenance requirements'". Secondary sources place the sequence at §B2.2.5 in DDI 0487G.a (`arm-ctr_el0-excerpt.txt`).
- I can't verify K.a's numbering here, so the citation is **UNVERIFIED**.
- **Required:** quote the verbatim requirement text with its version and section. The quote must settle B2's DSB question.

**B4 [BLOCKING] (P4-2): the semantic oracle isn't met.**
- The condition was that the interpreter's coherent-mode end state (registers and memory) equals qemu-aarch64 **on every kernel**.
- Only the `correct` kernel's exit code is compared (`:258–263`), and the slot result is hard-coded (B1).
- **Required:** once the slot actually executes (B1), add a coherent mode and compare every kernel's end state with qemu.

**N1 [nit]:** the herdtools7 `SM.udf+…` cross-check covers only the full-sequence case. It doesn't validate the per-config skips.

**N2 [nit]:** disclose that Linux mitigates the line-size class via the `ARM64_MISMATCHED_CACHE_TYPE` CTR_EL0 trap (`../presearch/C01-priorart-excerpts.txt`).

## 3. Novelty in the implementation: collapsed

REVIEW-01 §2.4 approved N2 for "a whole-program sanitizer that names the omitted step automatically". What runs is a truth table of `required_steps(cfg)` checked against a supplied recipe. That's the known litmus-level rule restated, not a sanitizer of programs.

The pieces needed for the real thing are already here, and they're good: a verified encoder, a kernel builder, and an unused cache-state model. Wiring them together is the fix.

## 4. Safety

**Benign.** It's a pure model, plus qemu runs of tiny own-process kernels. No network, no out-of-tree writes.

## 5. What clears the gate

Fix B1–B4, re-capture RUN.md, add "Fix round 1" to BUILD-04.md, and post `GATE BUILD-04 READY (fix round 1) — commit <hash>`.

At round 2 I'll re-run `code_vs_recipe.py` (adapted to the new API) and `encoder_sample.py`, plus a kernel of my own with a deliberately wrong stride.

**Proceed-in-parallel: GRANTED for BUILD-05 (C09).** These issues are local to this part.

## Round 2: fix round 1 @ `3e1ca1e`, CHANGES REQUESTED (2026-10-19 09:40 PDT)

**Reviewed:** commit `3e1ca1e`, named in the GATE line at 09:25. The diff since `6530c51` also includes the post-gate commit `7321667`.

**Reproduced in:** a fresh clone at `tasks/reviewer-repro/build-04-r2`, under `env -i`.

**Evidence:** `review/evidence/build-04/r2/`.

### Blockers

| Round-1 issue | Status | Basis |
|---|---|---|
| **B1** the verdict ignored the program | **FIXED**, but see B5 | `interp(code, entry_off, slot_vaddr, cfg, coherent)` has no recipe argument, and the verdict comes from the executed ops (`Machine.maint`). My `patched_kernel.py` overwrites the `correct` kernel's DC/IC/ISB words with `DSB ISH`, so no builder is involved: now **STALE**. The `none` kernel is **STALE**. My own wrong-stride kernel (an unrolled flush, stride 128 over 64-B lines) is **STALE, missing dc**; stride 64 is **FRESH** (`round2-tests-output.txt`, T5). So the line-size class is detected from executed addresses |
| **B2** IDC=1 dropped the DSB; impossible config | **FIXED** | `required()` keeps the DSB and ISB. Under IDC=1, "DC; IC; DSB; ISB" is now `OLD!ic`, where round 1's `dsb-rule-check.txt` had it FRESH. `{IDC=0,DIC=1}` is gone |
| **B3** cited, not quoted | **FIXED** | ARM_REF's CTR_EL0 IDC/DIC sentences match my independently fetched text word for word (`../arm-ctr_el0-excerpt.txt`, same Arm XML build 26/03/2024). The DSB question is settled by keeping the barriers. The sequence location is attributed to secondary sources (N5) |
| **B4** semantic oracle on one kernel | **FIXED** | All 7 kernels: model (coherent) = qemu = NEW (`make-run1.txt`). The end state compared is x0, which is the observable that matters for these kernels |

**B5 [BLOCKING] (new, inside B1's scope): freshness ignores where the store happens.** I ran the fix round's `interp` on kernels from my own builder (`round2_tests.py`), with IDC=0, DIC=0 and 64-B lines.

| Kernel | Architecture | Model |
|---|---|---|
| T0: warm; STR; DC; DSB; IC; DSB; ISB; run | fresh | NEW ✓ |
| **T1**: warm; DC; DSB; IC; DSB; ISB; **then** STR; run | not guaranteed: no maintenance after the store | **NEW, nothing missing** ✗ |
| **T2**: …full maintenance…; **second** STR (NEW2); run | NEW2 not guaranteed: the second store is unmaintained | **NEW2, nothing missing** ✗ |
| **T3**: warm; **DC; STR**; DSB; IC; DSB; ISB; run | not guaranteed: the new bytes are never cleaned to PoU (IDC=0) | **NEW** ✗ |
| T4: omit DSB1 (DC; IC; DSB; ISB) | stale; the missing step is the DSB | OLD ✓, but names `ic` (N3) |

- **Cause:**
  - `diagnose()` drops every `str` (`icache_model.py:104–105`) and accepts the required ops as a subsequence anywhere in the trace.
  - `fetch_word()` then returns the latest bytes, store buffer merged over memory (`:123–129`), whenever `diagnose()` says fresh.
  - So neither the dirty/clean D-cache state nor `self.icache` decides the fetch. `self.icache` is written at `:65` and `:79` and never read.
  - The model's own state would answer T1 and T3 correctly: the bytes are still dirty and PoU holds OLD. The fetch just doesn't consult it.
- **Why it blocks:** "flush, then write" and "patch again after the flush" are real JIT bugs, inside the claimed "any patch sequence" (README:49). The sanitizer passes them as FRESH.
- **Required:**
  - Decide the fetch from the model's state, or anchor the required sequence after the last store to the slot's line.
  - Add T1–T3 (or equivalents) as VERDICTs that must come out STALE, with a named cause.
  - Re-capture RUN.md.

### Reproduction

| Test | Result | Evidence |
|---|---|---|
| `make` ×2 (clean clone) | `make_exit=0`, **11/11 PASS** both runs. Output is **identical to RUN.md's make block** | `make-run1.txt`, clone `.evidence` |
| strace (`make`) | **CLEAN** | `strace-audit.txt` |
| *(reviewer)* encoder sample (`a64asm.py` unchanged since `6530c51`), seeds 404 and 4042 | **120/120** byte-identical to `aarch64-linux-gnu-as` | `encoder-sample-r2.txt` |
| *(reviewer)* adapted code-vs-recipe (a′)/(b′) | STALE / STALE (round 1: FRESH / FRESH) | `patched-kernel-output.txt` |
| *(reviewer)* T0–T5 | above | `round2-tests-output.txt` |

### Nits

- **N3: omit-DSB1 names the wrong step.** It reports `ic`, although the program contains the IC. The greedy subsequence match consumes the later DSB as "DSB1". README:20 rationalizes this ("IC ineffective"). Anchored matching would name the step that is actually absent: a DSB between the last DC and the first IC.
- **N4: the line-size VERDICT uses a single wrong address** (`flush_off=64`), not a stride. My T5 shows a strided flush works. Put a stride-128-over-64-B kernel in the VERDICTs.
- **N5: the sequence citation is secondary.** "DDI 0487G.a B2.2.5, per Rutland/US11210222" comes from a mailing-list post and a patent quoting the manual (the sources in my `arm-ctr_el0-excerpt.txt`). Label it "(secondary)".
- **N6:** `run_qemu` leaves a `mkdtemp` directory per call (`sanitize.py:156`).

### What clears the gate

Fix B5, add the ordering kernels to the VERDICTs, re-capture RUN.md, add "Fix round 2" to BUILD-04.md, and post `GATE BUILD-04 READY (fix round 2) — commit <hash>`.

I'll re-run `round2_tests.py` unchanged. T1–T3 must come out STALE, and T0 and T5 must keep their current results.

Everything else is now sound. The encoder, the barrier rule, the qemu oracle and program dependence all check out on my own evidence.

## Round 3: fix round 2 @ `a980f38`, APPROVE (2026-10-19 10:03 PDT)

**Reviewed:** commit `a980f38`, named in the GATE line at 09:59.

**Reproduced in:** a fresh clone at `tasks/reviewer-repro/build-04-r3`, under `env -i`.

**Evidence:** `review/evidence/build-04/r3/`.

### Blockers

**B5 is FIXED.** Store ordering now decides freshness. Each STR resets that word's progress through `required()` (`icache_model.py:109`). Ops count only in program order, after the latest store, and for DC/IC only when they cover the word's line (`:82–99`). `fetch_word` returns the instruction side's guaranteed view, `iview` (`:175–185`), so the fetch now reads model state.

My **round-2 tests, run unchanged** (`rerun-round2-tests.txt`):

| Test | Round 2 | Round 3 |
|---|---|---|
| T1 flush, then write | NEW | **OLD, missing dc** |
| T2 second, unmaintained store | NEW2 | **NEW, not NEW2, missing dc** |
| T3 DC before the STR | NEW | **OLD, missing dc** |
| T4 omit-DSB1 | named `ic` | **named `dsb`** (N3 fixed) |
| T0 control / T5 stride 64 / stride 128 | NEW / NEW / OLD | unchanged |

My **new probes** (`round3_tests.py`, `round3-tests-output.txt`), on kernels the author has never seen, all give the architecturally right answer:

| Probe | Result |
|---|---|
| P1 an unrelated store after full maintenance | **FRESH** (no false positive) |
| P2 a store to another word in the slot's line | **FRESH** |
| P4 ISB before the IC's DSB | **STALE, isb** |
| P5 an interim run before the ISB | final run **FRESH** |
| P6 IC before DC | **STALE, ic** |
| P7 full maintenance twice | **FRESH** |
| P8 never warmed, maintained | **FRESH** |
| P9 never warmed, unmaintained | **STALE** |
| P10 IDC=DIC=1, STR; DSB; ISB (the Linux path) | **FRESH** |
| P11 IDC=DIC=1, STR; ISB; DSB | **STALE, isb** |
| P12 IDC=1, STR; DSB; IC; DSB; ISB | **FRESH** |
| P13 IDC=1, IC with no DSB before it | **STALE, dsb** |
| P14 DC/IC at another address in the slot's line | **FRESH** |
| P15 re-patch, then maintain again | **FRESH with NEW2** |
| **P3** I-line 32 B, D-line 64 B (the mismatched line-size class proper), slot in an odd 32-B I-line | IC stride 64 → **STALE, ic**. IC stride 32 → **FRESH** |

In coherent mode, every probe equals qemu.

### Reproduction

| Test | Result | Evidence |
|---|---|---|
| `make` ×2 (clean clone) | `make_exit=0`, **16/16 PASS** both runs. Output is **identical to RUN.md's make block** | `make-run1.txt` |
| strace | **CLEAN**. Temp directories: 57 created, **57 removed** (N6 fixed) | `strace-audit.txt`, `tmp-accounting.txt` |
| encoder sample (seeds 404, 4042) | **120/120** byte-identical to GNU `as` | `rerun-round2-tests.txt` |
| patched kernel (a′)/(b′) | STALE / STALE | `rerun-round2-tests.txt` |

### Nits (not blocking)

- **N7:** under IDC=1 there is no clean, but `explain()` still says "IC IVAU issued before a DSB completed the clean" (`icache_model.py:99`, P13). Say "…completed the store".
- **N8:** `DSB ISHST` and `DSB ISH` decode to the same barrier (`sanitize.py:125`). Linux uses ISHST only on the IDC path. Whether ISHST suffices after `DC CVAU` on the IDC=0 path isn't established here: UNVERIFIED either way. Disclose that ISHST is accepted wherever a DSB is required.
- **N5 is resolved by labelling:** the sequence citation is marked SECONDARY.

### Why APPROVE

The part now delivers the approved observable: a program-driven model that names the omitted maintenance step. "Program" here means straight-line kernels in its A64 subset; the README's Limits disclose that the subset, the single PE and the unrolled loops are deliberate scope.

The verdict comes from the executed instructions and their order. The barrier rule matches Linux `cache.S`, and the CTR_EL0 text is quoted verbatim. Coherent mode equals qemu on all 13 of its kernels and on all of mine. It catches the mismatched line-size class from real flush addresses, including different I- and D-line sizes.

Every result above is from my own kernels or my own tests. **Gate BUILD-04 is CLEARED.**
