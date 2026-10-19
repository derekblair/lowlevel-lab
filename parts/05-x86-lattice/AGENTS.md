# part 05 — x86-lattice (AGENTS.md)

Part of **lowlevel-lab** (see ../../AGENTS.md). Author-lane build of the P5-slot
replacement C09 (APPROVED WITH CONDITIONS, N2, REVIEW-01 §6.2). The
visualization-theme concept: x86-64 superset-decode lattice + resync statistics
over a corpus.

- **What:** `lendec.py` (from-scratch x86-64 length decoder, scope listed in its
  docstring), `superset.py` (objdump `-w -z` authority with parser + windowed
  self-checks, ground-truth and reference corpora, resync statistics with and
  without `(bad)` chains, SVG lattice, VERDICTs), `Makefile`. README explains
  it; RUN.md is the verbatim evidence; `lattice.html` is the emitted
  visualization (generated, clean-able).
- **Build/run:** `make` = compile the ground-truth corpus (this part's inline
  functions + every C source in the repo, `gcc -O2` with symbols; never
  executed), superset-decode every offset of every code section and of five
  `/usr/bin` `.text` regions, measure resync, emit lattice.html, print VERDICTs.
  Present tools only: python3 stdlib, gcc, objdump, readelf (+ firefox to
  render the viz). No installs. No temp-dir litter.
- **Novel observable (R4):** the measured resync distribution, which settles
  Linn & Debray's "one or two" vs Andriesse et al.'s "two or three":
  ground-truth median 2 (P<=2 71%, P<=3 83%, n=8,400), and median 1 over
  `(bad)`-free chains. Plus the lattice. Five claims, each a VERDICT in RUN.md.
- **Oracle (C09-3/R6):** objdump is the authority, guarded by a contiguity
  self-check and a windowed-vs-linear cross-check at every true boundary
  (39,249/39,249). lendec is differential-tested in the REVIEW-05 categories:
  0 WRONG at true boundaries and at every offset.
- **Ground truth (C09-4):** a section counts only if its sweep is clean and
  every symbol-table function entry is one of its boundaries (61/61). The
  reference arm is labelled reference-decode. Resync is defined to the first
  boundary of the true stream, in bytes and instructions.
- **Safety (C09-2):** ANALYSIS ONLY — reads binaries read-only; compiles fixed
  benign C only to disassemble it; never generates desync, junk, opaque-
  predicate or overlapping-instruction code.
- **Viz (C09-5):** lattice.html is self-contained (no CDN) and embeds the
  per-offset data + corpus stats in <script id=data>. A VERDICT re-derives the
  arcs, merge points and histogram from that data and requires them to match
  the drawing.
