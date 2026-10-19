# part 05 — x86-lattice (AGENTS.md)

Part of **lowlevel-lab** (see ../../AGENTS.md). Author-lane build of the P5-slot
replacement C09 (APPROVED WITH CONDITIONS, N2, REVIEW-01 §6.2). The
visualization-theme concept: x86-64 superset-decode lattice + resync statistics.

- **What:** `lendec.py` (from-scratch x86-64 length decoder), `superset.py`
  (objdump-authoritative per-offset decode, lattice, resync stats, HTML viz,
  VERDICTs), `Makefile`. README explains it; RUN.md is the verbatim evidence;
  `lattice.html` is the emitted visualization (generated, clean-able).
- **Build/run:** `make` = build a self-built -O2 target, superset-decode at every
  offset, measure resync, emit lattice.html, print VERDICTs. Present tools only:
  python3 stdlib, gcc, objdump (+ firefox to render the viz). No installs.
- **Novel observable (R4):** a measured resync-length distribution (median ~1
  instruction, ~80% ≤2) quantifying Linn & Debray CCS'03 §3.1, plus the lattice.
  Proven by the `VERDICT PASS` lines in RUN.md.
- **Oracle (C09-3/R6):** objdump is the authoritative per-offset decoder (lattice
  correct by construction); lendec is differential-tested at every offset vs
  objdump, agreement reported (100% on true boundaries of the self-built target).
- **Ground truth (C09-4):** primary = self-built -O2 binary with symbols;
  secondary = /usr/bin/true with the "reference decode, stripped" caveat. Resync
  length defined in bytes AND instructions to the first shared boundary.
- **Safety (C09-2):** ANALYSIS ONLY — reads binaries read-only, never generates
  desync/junk/opaque-predicate/overlapping-instruction code. Benign.
- **Viz (C09-5):** lattice.html self-contained (no CDN), embeds data in
  <script id=data>, renders headless in firefox.
