# BUILD-05 — x86-lattice (C09, P5-slot replacement)

Author lane. Build of the P5-slot replacement C09 (APPROVED WITH CONDITIONS,
N2, REVIEW-01 §6.2). The visualization-theme concept. Part dir:
`parts/05-x86-lattice/`.

## What was built

An x86-64 superset-decode lattice + resynchronisation-statistics tool.
`superset.py` decodes a code region at **every** byte offset (authoritative
per-offset decode = objdump), draws the overlapping-instruction lattice
(`lattice.html`), and measures how fast misaligned decode streams resync with
the compiler-intended stream. `lendec.py` is a from-scratch x86-64 length
decoder, differential-tested at every offset against objdump.

## The result

On a self-built `-O2` function (known ground truth): misaligned decodes resync
with a **median of 1 instruction**, **~80% within ≤2 instructions** — a measured
quantification of Linn & Debray's 2003 qualitative claim. All 5 VERDICTs PASS.

## How verified

- **C09-1 novelty text:** README carries the corrected prior-art (arXiv 2506.09426
  real title; Linn & Debray CCS'03 §3.1 quoted verbatim as the published resync
  claim; desync-cc/shifting-codes/x86-sok neighbours distinguished).
- **C09-2 safety:** analysis only — reads binaries read-only, never generates
  desync/junk/opaque-predicate/overlapping code. Stated and true.
- **C09-3 oracle:** objdump is the authoritative per-offset decoder (lattice +
  stats correct by construction); lendec is differential-tested at **every**
  offset and its agreement reported — **100% on the self-built target's true
  (compiler-intended) boundaries** (38/38), lower on arbitrary misaligned bytes
  (opcodes outside its scoped table), which defer to objdump. Undecodable
  offsets are counted and handled (deferred).
- **C09-4 ground truth:** primary target is a self-built -O2 binary with symbols
  (real ground-truth boundaries); the /usr/bin/true sample is labelled a
  reference decode with the stripped-binary caveat. Resync length defined in
  bytes AND instructions, to the first boundary shared with the reference
  stream.
- **C09-5 viz:** `lattice.html` is self-contained (inline CSS, no CDN) and embeds
  the stats + resync histogram in `<script id=data>`; it renders headless in
  firefox (verified: 64 KB PNG produced).
- **Clean-env:** built + run under `env -i` (5 VERDICT PASS, exit 0).

## Known weak spots (stated plainly)

- **objdump is the authority; lendec is scoped.** lendec covers the common
  gcc/clang 64-bit forms (true-boundary agreement 100% on the self-built
  target), not the whole ISA; misaligned bytes it can't size defer to objdump,
  so lendec's incompleteness lowers a *reported rate*, never the lattice/stats.
- **gcc-version-dependent bytes:** the self-built target's exact encoding varies
  with the toolchain, so resync numbers are a median/fraction, not a fixed
  vector; the ~1–2-instruction result is the stable claim.
- **Stripped /usr/bin binaries lack true ground truth** (reference decode +
  caveat); the self-built target is the one with real boundaries.
- **Single region per target**, not a whole-corpus survey (v2).

## Files

`parts/05-x86-lattice/`: AGENTS.md, README.md, RUN.md, Makefile, lendec.py,
superset.py (+ generated lattice.html — clean-able).

## Fix round 1 (REVIEW-05-build, CHANGES REQUESTED @9f1a7ae)

All three blockers are fixed, and every nit is addressed. The reviewer's own
tools, run against this tree, confirm the B1 fix.

- **B1 (the "authoritative" decode was misparsed) — FIXED.**
  - **`-w -z` on every objdump call**, and objdump's `.byte` (a truncated tail)
    is treated like `(bad)`.
  - **Parser self-check:** every linear decode is contiguous and sums to its
    region, or the run aborts.
  - **Windowed per-offset decode:** one objdump call per region (the reviewer's
    perf hint), cross-checked against the linear decode at every true
    boundary: **39,249 / 39,249** over 23 regions.
  - The 7 initial mismatches were all where the 48 KiB cap cut the last
    instruction of `sort`/`ls`. A capped region is now cut at an instruction
    boundary, and a decode that ends past the region is not treated as an
    instruction of it.
  - **`(bad)` policy stated** (stepped by objdump's byte count, flagged), and
    every statistic is reported with and without chains through a `(bad)`.
  - The reviewer's `indep_true.py`, run unchanged against this tree, finds no
    false boundaries (was 3) and lendec 45/45 (was "45/48"). The one
    remaining per-offset difference is the zero run that `-z` decodes as
    `00 00 add`, which the review required.
- **B2 (single-function anecdote) — FIXED: a corpus with two arms.**
  - **Ground truth:** 8 self-built `gcc -O2` objects (the 8 inline functions
    plus every C source in the repo), every code section. A section counts
    only if its sweep is clean **and** every symbol-table function entry is
    one of its boundaries: 18 sections, **61/61** entries confirmed, 0
    excluded. n = **8,400**.
  - **Reference decode:** `/usr/bin/{true,cat,wc,sort,ls}`, labelled. n =
    **115,884**.
  - Per-object/per-binary and pooled n, median, Q1/Q3, P(≤1/2/3), max and
    never are reported, with and without `(bad)` chains.
  - **Restated headline:** ground-truth median **2** (P≤1 49%, P≤2 71%, P≤3
    83%, max 14); `(bad)`-free median **1** (P≤2 76%). Reference: median 2,
    P≤2 56%, max 101; `(bad)`-free P≤2 77%. This agrees with the reviewer's
    independent survey.
  - **The VERDICTs test the corpus claims (5 claims).** The README says
    plainly that they were formulated from this measurement and that the
    VERDICTs pin them; it also names the selection effect in the `(bad)`-free
    population.
- **B3 (no lattice drawn; false legend) — FIXED.**
  - `lattice.html` is now a real SVG lattice of `work()`: every in-region
    decode is an arc `k → k+len(k)`, with the true stream green above the
    axis, misaligned decodes grey below, `(bad)` red dashed, merge points as
    orange dots, three example chains in purple followed to their merge, and
    the histogram plotted.
  - The legend matches the code.
  - `<script id=data>` embeds the per-offset bytes, objdump and lendec
    lengths, `(bad)` and boundary flags, the drawn histogram and the corpus
    stats.
  - A VERDICT **re-derives** the arcs (127), merges (52) and histogram from
    that data alone and requires them to equal the drawing (N5).
  - Rendered headless (RUN.md).
- **N1 — FIXED.** `syscall` (0f 05) and `ud2` (0f 0b) are no-ModRM, 2 bytes
  (also `cpuid`, `rdtsc`). On the reviewer's four system sample regions WRONG
  goes 3 → 0. lendec's scope is listed (no VEX/EVEX, string ops, `int3`, x87;
  it sizes some `(bad)`s). Over the ground-truth corpus: 0 WRONG at true
  boundaries (2,715 AGREE, 38 NONE) and 0 WRONG at every offset.
- **N2 — FIXED:** "no VEX/EVEX support at all".
- **N3 — FIXED:** the slug is `expend20/shifting-codes-python-port`. Andriesse
  et al. 2016 §3 ("two or three [21]", worst-case mean 0.09%), Kruegel et al.
  2004 §4.2.1 and probdisasm (2026; superset + probabilistic, no resync stats)
  are cited, with the quoted wording attributed to the reviewer's excerpts.
- **N4 — FIXED:** no `mkdtemp` (all `TemporaryDirectory`; 0 dirs left by a
  run); the docstring comes first; the unused `out` is gone; the O(N²)
  per-offset calls are replaced by one windowed call per region (~9 s for the
  whole corpus).
- **N5 — FIXED:** the loose "median ≤ 3" thresholds are replaced by the claim
  VERDICTs and the re-derivation check.
- `objdump_len_at` and `region_from_symbol_elf` are kept as thin helpers over
  the fixed code, so the reviewer's round-1 scripts still run.

Re-verified: 10/10 VERDICTs PASS under `env -i` (`make_exit=0`); RUN.md
re-captured.
