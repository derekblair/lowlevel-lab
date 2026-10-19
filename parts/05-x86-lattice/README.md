# x86-lattice — superset-decode lattice + resync statistics

x86-64 has no instruction alignment: a decode can start at *any* byte, and a
disassembler that starts at the wrong offset produces wrong instructions — until
it **resynchronises** with the compiler-intended stream. This part decodes code
at **every** byte offset (the "superset" decode), draws the overlapping-
instruction **lattice**, and **measures, over a corpus, how fast** misaligned
decode streams rejoin the true stream.

**Headline (ground truth: 8,400 misaligned starts in 61 functions across 8
self-built `gcc -O2` objects):** a misaligned decode rejoins the true stream in a
**median of 2 instructions**. 49% rejoin within 1 instruction, **71% within 2**,
83% within 3, and the longest takes 14. Leaving out chains that pass through a
`(bad)` decode, the median is **1** (76% within 2). On five `/usr/bin` binaries
(115,884 starts, reference decode) the median is also 2, but the tail is heavier
(56% within 2, max 101). That excess is `(bad)`-driven: the `(bad)`-free subset
matches ground truth (77% within 2).

## Why this is novel (see ../../research/NOVELTY-LOG.md C09; REVIEW-01 §6.2)

Superset disassembly is a known *technique* — **Multiverse** (Bauman, Lin &
Hamlen, NDSS 2018), **ddisasm**, **KennethAdamMiller/superset_disassembler**, and
**Program-Understanding/probdisasm** (2026; superset plus probabilistic hints).
All of these are disassemblers or rewriters, and none reports resync statistics.
The resync behaviour is published only as *qualitative* statements:

> **Linn & Debray, CCS 2003, §3.1 "Self-Repairing Disassembly":** "In practice,
> however, we have found that disassembly errors usually resynchronize quite
> quickly — often within just one or two instructions beyond the point at which
> the disassembly error occurred."

> **Andriesse et al., USENIX Security 2016, §3** (restating [21] = Linn &
> Debray): "This is because x86/x64 disassembly automatically resynchronizes
> within two or three instructions [21]." Their only quantitative figure is
> downstream: missed instructions "due to desynchronization … at a worst-case
> mean of 0.09%".

> **Kruegel et al., USENIX Security 2004, §4.2.1:** sequences shifted by a few
> bytes "synchronize quickly, often after a few instructions."

(The Andriesse and Kruegel wording is as recorded in the reviewer's source
excerpts, `review/evidence/build-05/priorart-excerpts.txt`.)

None of these gives a distribution or a dataset, and the two restatements
disagree ("one or two" vs "two or three"). The N2 delta here is to **measure the
distribution** on modern x86-64, which settles that disagreement (claims 1–3
below). It also shows **what the disagreement hinges on**, the `(bad)` policy
(claims 4–5), and **renders the superset lattice** as a machine-checkable
artifact. (Record corrections: arXiv 2506.09426's real title is *"Exploiting
Control-flow Enforcement Technology for Sound and Precise Static Binary
Disassembly"*, and it reports instrumentation speed, not resync statistics.)

## Analysis only — no offensive capability (C09-2)

This is strictly **analysis**. It reads binaries read-only and compiles fixed
benign C sources (its own and this repo's) only in order to disassemble them;
nothing is ever executed. It **never** generates desynchronising code, inserts
junk bytes, builds opaque predicates, or emits overlapping-instruction
transforms. It is the opposite of `UlfKargen/desync-cc` and
`expend20/shifting-codes-python-port`, which *produce* desync to *defeat*
disassemblers; this *measures* how robust decoding is.

## How it works

- **The authority is objdump, run with `-w -z`** (REVIEW-05 B1). Without `-w`,
  objdump wraps instruction bytes at 7 per line, and a line parser would mistake
  the continuation line for a new instruction (false boundaries; lengths capped
  at 7). Without `-z` it elides zero runs. Two guards make the authority
  trustworthy:
  - **Parser self-check:** every linear decode's instruction lengths are
    contiguous and sum to the region size, or the run aborts.
  - **Windowed per-offset decode, cross-checked:** every offset's first-
    instruction length comes from **one** objdump call per region. The region
    is expanded into 15-byte windows (the maximum x86 instruction length), each
    followed by 16 × `0x90`, so the sweep re-aligns on the NOPs. At every true
    boundary that length must equal the linear decode's: **39,249 / 39,249**.
  - A decode that would end past the region consumed padding, not program
    bytes. It is not an instruction of the region: a chain reaching it runs off
    the end (never resyncs), and the lattice does not draw it.
- **`(bad)` policy, stated:** an offset objdump prints as `(bad)`, or as `.byte`
  (a truncated tail), is stepped by the byte count objdump assigns it and
  **flagged**. Every chain records whether it passed through one, and **all
  statistics are reported twice**: over all chains, and over `(bad)`-free
  chains only.
- **`lendec.py`** is a from-scratch x86-64 **length** decoder, differential-
  tested against objdump at every offset in the REVIEW-05 categories (C09-3).
  Over the ground-truth corpus (offsets whose decode ends inside the region):

  | where | AGREE | WRONG | LENDEC-NONE | BAD-ACCEPTED | BAD-REJECTED |
  |---|---|---|---|---|---|
  | compiler-intended boundaries | 2,715 | **0** | 38 | 0 | 0 |
  | every offset | 9,816 | **0** | 856 | 191 | 302 |

  It **never mis-sizes** an instruction here. Where it can't size one, it
  returns None and objdump decides. Its scope is listed in `lendec.py`: no
  VEX/EVEX at all (`c4`/`c5`/`62` are absent); no `rep stos`/string ops, `int3`
  or x87. `syscall`/`ud2`, which were mis-sized before this fix round, are now
  2 bytes. It is a length decoder, not a validator, so it sizes some bytes
  objdump rejects (BAD-ACCEPTED). None of this touches the lattice or the
  statistics, which come from objdump.

## Ground truth and the resync definition (C09-4)

- **Ground-truth arm:** 8 objects the project compiles itself with `gcc -O2`
  and symbols. They are this part's 8 inline functions plus every C source in
  this repo (`smcobs.c`, `ptcap.c`, `verify_singlestep.c`, and the research
  probes `rule.c`, `uflags.c`, `refine.c`, `smc.c`). Every **code section** is
  analysed whole (.text, .text.startup, …), so a misaligned chain can run across
  function boundaries as it would in a real binary. A section counts as ground
  truth only if its linear sweep is **clean** (0 `(bad)`/`.byte`) **and every
  function entry in the symbol table is a boundary of that sweep**. That is an
  independent confirmation of the boundaries: all **61** entries in **18**
  sections are confirmed, and none is excluded.
- **Reference-decode arm:** the `.text` of `/usr/bin/{true,cat,wc,sort,ls}`
  (the first ≤48 KiB, **cut at an instruction boundary**, so the cap never
  truncates an instruction). The "true" boundaries are objdump's linear sweep,
  which is **not** ground truth for a stripped binary (data, padding and jump
  tables can derail it; that is x86-sok's point). It is labelled as such
  throughout.
- **Resync length:** from a misaligned start `k` (not a boundary of the
  true/reference stream), follow the objdump decode chain `k → k+len(k) → …`.
  The resync point is the **first offset that is a boundary of the true
  stream**. Length is counted in instructions and in bytes. A chain that runs
  off the region is *never*.

## Results

| arm | n | median | Q1 | Q3 | P(≤1) | P(≤2) | P(≤3) | max | never |
|---|---|---|---|---|---|---|---|---|---|
| ground truth, all chains | 8,400 | **2** | 1 | 3 | 49% | 71% | 83% | 14 | 24 |
| ground truth, `(bad)`-free | 7,425 | **1** | | | 54% | 76% | 87% | 13 | |
| reference, all chains | 115,884 | **2** | 1 | 4 | 37% | 56% | 68% | 101 | 31 |
| reference, `(bad)`-free | 73,379 | **1** | | | 54% | 77% | 88% | 19 | |

Per-object and per-binary rows are in RUN.md and in `lattice.html`. Every
ground-truth object has a median of 1 or 2.

**Claims (each one is a VERDICT).** I formulated these *from* this measurement,
so they are not pre-registered hypotheses. The VERDICTs pin them, so a change
of toolchain, corpus or method that alters a finding is caught.

1. Linn & Debray's "one or two" describes the **typical** chain: the
   ground-truth median is 2.
2. …but it is **not a bound**: 29% of ground-truth chains need 3 or more
   instructions, up to 14.
3. Andriesse et al.'s "two or three" covers **83%** of ground-truth chains.
4. **The `(bad)` policy is the hinge.** Excluding chains through a `(bad)`
   moves the median from 2 to 1 in both arms. The two populations answer
   different questions. All chains: how far a misaligned decode runs if
   undecodable bytes are stepped over. `(bad)`-free chains: how far a misdecode
   runs **silently**, with no visible error, before it heals. Part of the drop
   is a **selection effect**: a longer chain has more chances to touch a
   `(bad)`, so the `(bad)`-free population is biased short.
5. **`/usr/bin`'s heavier tail is `(bad)`-driven.** Over all chains it is
   worse (56% vs 71% within 2). Over `(bad)`-free chains it matches ground truth
   (77% vs 76%). 37% of the reference chains touch a `(bad)`, against 12% in
   ground truth.

## The visualization (C09-5)

`make` writes `lattice.html`. Its region is `work()` (128 B), drawn as a real
lattice. Each **tick** is a compiler-intended boundary. Each **arc** is one
decoded instruction `k → k+len(k)`:
- **green** arcs above the axis are the true stream;
- **grey** arcs below are misaligned decodes;
- **red dashed** arcs are objdump `(bad)`;
- **orange dots** mark where a misaligned arc lands on a true boundary (a merge
  point);
- **purple** arcs are three example misaligned chains (the longest, a 2- and a
  3-instruction one), followed arc by arc from their start dot to the merge.

The resync histogram is plotted beneath, and the corpus table follows. `work()`
is the *illustration*: at a median of 1 it is one of the more favourable regions,
so the headline comes from the corpus, not from it.

The page is self-contained (inline CSS/SVG, no CDN). `<script id=data>` embeds
the per-offset data (bytes, objdump length, lendec length, `(bad)` flag,
boundary flag), the drawn histogram and the corpus statistics. The last VERDICT
**re-derives** the arcs, merge points and histogram from that data alone and
requires them to equal what was drawn. Render headless:
`firefox --headless --screenshot=lattice.png file://$PWD/lattice.html`.

## How to run

```
make            # compile the ground-truth corpus, decode every offset, stats, viz, VERDICTs
python3 superset.py   # same
```

## Limits / honesty

- **objdump is the authority** for the lattice and the statistics. lendec is a
  scoped length decoder whose agreement is reported, not assumed.
- **The claims were formulated from this measurement** (see Results). The
  thresholds in claims 2, 3 and 5 are mine, stated as such.
- **The corpus is modest and gcc-only:** 8 objects (61 functions, ~11 KB of
  code) for ground truth, and 5 binaries for the reference arm. There is no
  clang and no other optimisation level. Exact bytes depend on the gcc version,
  so the numbers are a toolchain-specific measurement, though the reviewer's
  independent survey (14 objects, n=10,898) found the same median of 2 and P(≤2)
  of 0.70.
- **Stripped `/usr/bin` binaries have no true ground truth.** That arm uses the
  objdump reference decode, labelled, with its caveat.
- **"Resync" means rejoining the linear true stream**, as Linn & Debray define
  it. It says nothing about whether a disassembler would *accept* the
  misaligned instructions before the merge.
