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
