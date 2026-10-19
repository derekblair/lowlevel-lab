# x86-lattice — superset-decode lattice + resync statistics

x86-64 has no instruction alignment: a decode can start at *any* byte, and a
disassembler that starts at the wrong offset produces wrong instructions — until
it **resynchronises** with the compiler-intended stream. This part decodes a
code region at **every** byte offset (the "superset" decode), draws the
overlapping-instruction **lattice**, and **measures how fast** misaligned decode
streams rejoin the true stream.

The headline, on a self-built `-O2` function: misaligned decodes resync with a
**median of 1 instruction** and **~80% within ≤2 instructions**.

## Why this is novel (see ../../research/NOVELTY-LOG.md C09; REVIEW-01 §6.2)

Superset disassembly is a known *technique* — **Multiverse** (Bauman, Lin &
Hamlen, NDSS 2018), **ddisasm**, **KennethAdamMiller/superset_disassembler** —
all static *rewriters*. The resync behaviour is a published *qualitative* claim:

> **Linn & Debray, CCS 2003, §3.1 "Self-Repairing Disassembly":** "In practice,
> however, we have found that disassembly errors usually resynchronize quite
> quickly — often within just one or two instructions beyond the point at which
> the disassembly error occurred."

That 2003 statement has **no distribution and no dataset**. The N2 delta here is
to **quantify it on modern x86-64** (a measured resync-length distribution) and
to **render the superset lattice** as a machine-checkable artifact. Neither the
rewriters above nor the SoK/ground-truth work (Andriesse et al., USENIX Sec
2016; `junxzm1990/x86-sok`) does that. (Record corrections a/b/c applied: the
arXiv 2506.09426 paper's real title is *"Exploiting Control-flow Enforcement
Technology for Sound and Precise Static Binary Disassembly"*, which reports
instrumentation speed, not resync stats; the resync claim is Linn & Debray's,
quoted above, not folklore.)

## Analysis only — no offensive capability (C09-2)

This is strictly **analysis**. It reads binaries read-only and **never**
generates desynchronising code, inserts junk bytes, builds opaque predicates, or
emits overlapping-instruction transforms. It is the opposite of
`UlfKargen/desync-cc` / `expend20/shifting-codes` (which *produce* desync to
*defeat* disassemblers); this *measures* how robust decoding is.

## How it works

- `lendec.py` — a from-scratch x86-64 instruction **length** decoder (common
  64-bit encodings). It is **not trusted**: `superset.py` differential-tests it
  at **every** byte offset against `objdump` and reports the agreement rate
  (C09-3). It sizes **every compiler-intended instruction** on the self-built
  target correctly (true-boundary agreement 100% in RUN.md); on arbitrary
  *misaligned* bytes it covers a lower fraction (those hit opcodes outside its
  scoped table, e.g. AVX), and **those offsets defer to objdump**.
- `superset.py` — the authoritative per-offset decode is **objdump** (so the
  lattice and the statistics are correct **by construction**, C09-3), run at
  every offset. It builds the lattice, computes the resync statistics, emits
  the HTML visualization, and prints the VERDICTs.

## Ground truth and the resync definition (C09-4)

- **Primary target = a binary the project builds itself** (`gcc -O2`, with
  symbols), so the function's extent and the compiler-intended instruction
  boundaries are **known ground truth** — not an inference over a stripped blob.
- **Secondary = `/usr/bin/true`'s `.text` head**, where the "true" boundaries
  are objdump's **linear-sweep reference decode**, which is **not** real ground
  truth for a stripped binary (data, padding and jump tables can derail a linear
  sweep — exactly x86-sok's point). This is labelled a *reference decode* and
  reported with that caveat.
- **Resync length is defined precisely:** from a misaligned start offset `k`
  (not itself a true boundary), follow the authoritative (objdump) decode chain
  `k → k+len → …`; the resync point is the **first offset that is a boundary in
  the true/reference stream**. Resync length is reported in **both** bytes and
  instructions (start → that shared boundary).

## The visualization (C09-5)

`make` writes `lattice.html`: each cell is a byte offset, green = a true
instruction boundary, grey = a byte that starts a misaligned decode, red =
undecodable-by-lendec. It is **self-contained** (inline CSS, no CDN) and embeds
the stats + resync histogram as JSON in `<script id=data>`, so it is
machine-checkable. Render headless:
`firefox --headless --screenshot=lattice.png file://$PWD/lattice.html`.

## How to run

```
make            # build target, decode at every offset, resync stats, viz, VERDICTs
python3 superset.py   # same
```

## Limits / honesty

- **objdump is the authority** for the lattice and the statistics; `lendec` is a
  scoped length decoder whose agreement rate is reported, not assumed. It covers
  the common gcc/clang 64-bit forms, not the whole ISA (no full AVX/EVEX, etc.);
  misaligned offsets it can't size defer to objdump.
- **The self-built target's exact bytes depend on the gcc version**, so the
  resync numbers are reported as a median/fraction, not a fixed vector; the
  qualitative result (resync within ~1–2 instructions) is the stable claim and
  matches Linn & Debray.
- **Stripped `/usr/bin` binaries have no true ground truth**; that sample uses
  the objdump reference decode with the caveat stated. The self-built target is
  the one with real ground truth.
- Single region per target (one function / `.text` head), not a whole-corpus
  survey; a broader survey is a v2.
