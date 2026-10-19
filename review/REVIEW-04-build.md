GATE: build-04 | VERDICT: CHANGES REQUESTED | ROUND: 1 | AT: 2026-10-19 09:07 PDT | COMMIT: 6530c51

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
