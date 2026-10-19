GATE: build-05 | VERDICT: APPROVE | ROUND: 2 | AT: 2026-10-19 10:16 PDT | COMMIT: 3ab1033 (round 1: CHANGES REQUESTED @9f1a7ae)

# REVIEW-05-build — C09 x86 superset-decode lattice (`parts/05-x86-lattice/`, P5 slot)

**Reviewed:** commit `9f1a7ae`, named in the GATE line at 09:12.

**Reproduced in:** a fresh clone at `tasks/reviewer-repro/build-05-r1`, under `env -i`.

**Evidence:** `review/evidence/build-05/`.

## Verdict: CHANGES REQUESTED (3 blocking)

**What holds.**
- The build reproduces exactly. `make` run twice from a clean clone gives 5/5 VERDICTs PASS, identical to RUN.md, and strace is CLEAN.
- My own re-derivation of the headline function `work()` gives the author's numbers exactly: n=88, median 1.0, P(≤2)=0.81, max 5.
- The safety framing is right (analysis only), the HTML is self-contained, and the Linn & Debray text is quoted correctly.

**What doesn't.**
- The decode the build calls "authoritative … correct by construction" isn't. It misparses objdump for every instruction longer than 7 bytes and for runs of zeros (B1).
- The approved observable was a resync distribution across binaries. What shipped is one 126-byte function, and on my 100× larger ground-truth corpus its headline doesn't hold (B2).
- The visualization doesn't draw a lattice, and its legend is false (B3).

## 1. Reproduction and independent tests

| Test | Result | Evidence |
|---|---|---|
| `make` ×2 (clean clone, `env -i`) | `make_exit=0`, 5/5 PASS both runs. Output is **identical to RUN.md's make block** | `make-run{1,2}.txt` |
| strace of `make` | **CLEAN**: no network, writes stay in the tree or `/tmp` | `strace-audit.txt` |
| *(reviewer)* independent re-derivation of `work()`: my own `-w` parse and per-offset decode | Region and boundaries are identical to the author's; resync n=88, never=0, median 1.0, P(≤2)=0.81, max 5, byte median 3.0. **Same as RUN.md.** The longest decode at any of its 126 offsets is **7 bytes**, which is why B1 doesn't touch it | `indep_lattice.py`, `indep-work.txt` |
| *(reviewer)* the `/usr/bin/true` sample, re-parsed with `-w` | **3 false "true boundaries"** and **7 wrong lengths** (B1). Corrected: lendec sizes **45/45** real starts (RUN.md says 45/48); median **1.0** (RUN.md: 2); n 114 (RUN.md: 111) | `indep_true.py`, `indep-true.txt`, `objdump-wrap-demo.txt` |
| *(reviewer)* C09-3 every-offset lendec differential test on **my sample**: libc `syscall` and `write`, a libc AVX2 window, a `grep` `rep stos` site, my `chk()` (contains `ud2`), and `work()`. 615 offsets | AGREE 473; **WRONG 3** (all `syscall` at real instruction starts); LENDEC-NONE 83; BAD-ACCEPTED 30; BAD-REJECTED 26. Real starts sized correctly: **171/189** | `lendec_sample.py`, `lendec-sample-output.txt` |
| *(reviewer)* the author's own pipeline on a **second** gcc `-O2` function (`trap.c` `chk()`) | False boundary at 31, inside an 8-byte `nopl`. **VERDICT 1 would FAIL (18/20)**: one miss is the parser's, one is lendec's (`ud2`) | `author-pipeline-on-chk.txt` |
| *(reviewer)* resync survey, **ground truth**: 14 gcc `-O2` objects, 25 code sections, every sweep clean (0 `.byte`/`(bad)`) | Pooled n=10,898: **median 2.0**, P(≤1)=0.48, **P(≤2)=0.70**, P(≤3)=0.82, max 14. `work()` comes **2nd most favourable of 25** sections by P(≤2) | `resync_survey.py`, `survey-groundtruth.txt` |
| *(reviewer)* resync survey, **reference decode**: the code sections of `/usr/bin/{true,ls,grep,cp,sort}` (`.plt*` + `.text`, 402 KB, 96% of it `.text`) | Pooled n=307,033: median 2, **P(≤2)=0.56**, P(≤3)=0.68, max **59**. With the 37.7% of chains that pass through a `(bad)` excluded: median 1, P(≤2)=0.78, max 19 | `survey-reference.txt` |
| *(reviewer)* the survey's one-call windowed decode, checked against per-offset objdump | 126/126 (`work`), 39/39 interior offsets (`chk`), **400/400** random `/usr/bin/ls` offsets | `windowed-decode-check.txt` |
| *(reviewer)* `lattice.html` | 0 external refs. **Renders headless** (firefox 155, throwaway profile, 1400×900). Legend check fails (B3) | `lattice-render.png`, `legend-check.txt` |

## 2. Conditions (REVIEW-01 §6.2)

| Condition | Status | Basis |
|---|---|---|
| **C09-1** prior-art text | **MET**, with N3 | (a) the arXiv title is right. (b) the Linn & Debray §3.1 quote is verbatim. (c) the neighbours are named, but one slug 404s and Andriesse's restatement is missing (N3) |
| **C09-2** analysis only | **MET** | Read in full: nothing generates or transforms code. It compiles one fixed benign C function and reads binaries read-only |
| **C09-3** every-offset oracle | **NOT MET** | The "authority" is wrong for instructions longer than 7 bytes and for zero runs. `(bad)` handling is undocumented (B1). My sample's figures are above |
| **C09-4** ground truth + definition | **Method MET; implementation broken by B1** | Self-built-with-symbols is used, the reference-decode caveat is stated, and resync is defined in bytes and instructions. But the boundary parser corrupts ground truth whenever an instruction is longer than 7 bytes |
| **C09-5** machine-checkable visualization | **NOT MET** | Self-contained, and it renders. But it draws no lattice and its legend is false (B3) |
| **C09-6** VEX/EVEX honesty | **nit** | N2 |

## 3. Issues

**B1 [BLOCKING] (C09-3, C09-4): the authoritative decode is misparsed.**

*No `-w`.*
- objdump prints at most 7 x86 bytes per line, so a longer instruction spills onto a second line. That continuation line has its own address and bytes, and `LINE` (`superset.py:28`) parses it as a new instruction.
- **False ground truth.** `region_from_symbol` (`:61`) and `region_from_symbol_elf` (`:274`) add a boundary 7 bytes into each long instruction.
  - `/usr/bin/true`: offsets 12, 45 and 69, inside the 10-byte `cs nopw` and the two 9-byte `%fs:0x28` accesses.
  - My `chk()`: offset 31, inside an 8-byte `nopl`.
- **Lengths capped at 7.** `objdump_len_at` (`:86–100`) never returns more than 7 bytes. On the `/usr/bin/true` sample that's wrong at offsets 5/6/7/38/39/62/63 (true lengths 10/9/8/9/8/9/8).
- **Consequences:**
  - RUN.md's `/usr/bin/true` figures are wrong. Lendec's "45/48" is really 45/45: the three "misses" are the parser's false boundaries, and lendec was right each time.
  - Corrected stats are n=114, median 1.0, byte median 6.0.
  - On a second ordinary `-O2` function, the build's own VERDICT 1 fails.

*No `-z`.*
- `objdump -D` skips zero runs (`...`), which leaves offsets 161–162 of the `true` head with no decode. Those are the two red cells. With `-z` the decode is `00 00 add %al,(%rax)`.

*`(bad)` policy undocumented.*
- A `(bad)` is stepped over as an instruction of its printed byte count.
- The comment at `:98` says "treat as length 1", which contradicts the code.
- 13 of the 88 resyncing chains in `work()` pass through a `(bad)`, as do **37.7%** of the chains in real binaries. This policy alone moves the headline (B2).

**Required:**
- Use `-w -z` on every objdump call.
- Add a parser self-check: each instruction's byte count equals the next address minus its own, and the counts sum to the region size.
- State the `(bad)` policy, and report the stats with and without chains that hit `(bad)`.
- Re-capture RUN.md.

**B2 [BLOCKING]: the novel observable is a single-function anecdote.**
- The approved N2 delta is to *quantify* Linn & Debray "on modern x86-64 binaries" (REVIEW-01 §6.2). The pitch it rests on says "across real `/usr/bin` binaries" (SHORTLIST.md:242–244), and the stated proof is "Resync-length distributions for /usr/bin binaries" (CANDIDATES.md:215).
- What shipped is n=88 starts from one 126-byte function, plus a 163-byte head. README:101 calls the corpus "v2".
- The headline (README:10–11, BUILD-05.md:18–20) doesn't generalize:

| Corpus | n | median | P(≤2) |
|---|---|---|---|
| `work()` only (author's headline) | 88 | 1.0 | 0.81 |
| Ground truth: 14 gcc `-O2` objects | 10,898 | 2.0 | 0.70 |
| Reference decode: 5 `/usr/bin` binaries (`true`, `ls`, `grep`, `cp`, `sort`) | 307,033 | 2 | 0.56 |
| Same 5 binaries, chains through `(bad)` excluded | 191,339 | 1 | 0.78 |

- This is where the build gets interesting. Linn & Debray say "one or two" instructions. Andriesse et al. 2016 restate the claim as "two or three [21]" (N3). A real distribution would settle which is right, and the `(bad)` policy is the hinge.

**Required:**
- Run the fixed pipeline over a corpus with two arms:
  - ground truth: self-built multi-function objects with symbols;
  - reference decode: several `/usr/bin` binaries, labelled as such.
- Report per-binary and pooled n, median, quartiles, P(≤1/2/3), max and never, with and without `(bad)` chains.
- Restate the headline from those numbers, and make the VERDICTs test the corpus claim.

**Performance hint (validated, not required).** One objdump call per region, on windows `raw[k:k+15] + 16×0x90`, recovers every offset's first-instruction length. Any instruction is at most 15 bytes, so the sweep falls back into the 1-byte NOPs and lands on the next window. My survey of five binaries took 17.7 s.

**B3 [BLOCKING] (C09-5): no lattice is drawn, and the legend is false.**
- The render (`lattice-render.png`) is one row of boundary/non-boundary cells per region. It has no instruction spans, no k→k+len edges, no chains and no merge points. The histogram exists only in the JSON.
- So "draws the overlapping-instruction lattice" (README:6–7, BUILD-05.md:11) is **FALSE as rendered**. This slot exists to deliver the visualization theme.
- The legend says red means "undecodable-by-lendec" (`:184`, README:75). The code paints red when *objdump's* length is None (`:168`).
  - Of the 45 lendec-undecodable offsets, **1 is red and 44 are grey or green**.
  - Red cell 161 is lendec-*decodable* (declen=2).

**Required:**
- Draw the lattice: every offset's decode as a span or arc, the true stream highlighted, misaligned chains followed to their merge point, and the histogram plotted.
- Make the legend match the code.
- Embed the per-offset data (bytes, lengths, `(bad)` flags, boundaries) in `<script id=data>`, so the picture can be re-derived from the data. I'll re-render it headless.

**N1 [nit]: lendec silently mis-sizes two common opcodes.** `0f 05` (`syscall`) and `0f 0b` (`ud2`) sit in the ModRM table at `lendec.py:79`. `syscall` at three real libc instruction starts comes out as 4 bytes (true length 2), and `0f 0b c3` comes out as 3. Separately, lendec returns a length on 30 of the 615 offsets where objdump says `(bad)`. "Covers the common 64-bit encodings gcc/clang emit" (`lendec.py:11`, README:92) should list what's missing: `syscall`/`ud2` (wrong), `rep stos`, `int3`, string ops and x87 (None).

**N2 [nit] (C09-6):** "no full AVX/EVEX" overstates it. `c4`, `c5` and `62` are absent from `OP1`, so there is no VEX/EVEX support at all. It is honest, though: in my AVX2 window, all 13 VEX starts return None, with 0 WRONG.

**N3 [nit] (prior art):**
- `expend20/shifting-codes` (README:39) returns 404. The repo is `expend20/shifting-codes-python-port`.
- Andriesse et al. 2016 §3: "x86/x64 disassembly automatically resynchronizes within two or three instructions [21]". [21] is Linn & Debray. Their only quantitative figure is the downstream effect: missed instructions due to desynchronization at a worst-case mean of 0.09%. README:26–28 lists the paper only as SoK work; cite both the restatement and that figure.
- Kruegel et al. 2004 §4.2.1 is qualitative too ("synchronize quickly, often after a few instructions").
- The "no distribution" claim survives my own searches: 16 GitHub queries (13 repo, including one `topic:` query, two `in:readme` queries and three `created:>2026-04-01` slices; 3 code), 3 web searches, and the two papers above read at source. I also read the README and two source files of `Program-Understanding/probdisasm` (2026). It implements Miller et al.'s occlusion algorithm and has no resync statistics (`priorart-excerpts.txt`, `../search/presearch-B05-*.log`).

**N4 [nit] (hygiene):**
- Every `make` leaves about 290 directories in `/tmp`: the `mkdtemp` calls at `:48` and `:88` are never cleaned up (`tmp-litter.txt`).
- `import sys` at `:2` comes before the docstring, so `superset.__doc__ is None`.
- `out` at `:59` is unused.
- Each per-offset call decodes all the way to the region end, so the run is O(N²).

**N5 [nit]:** the VERDICT thresholds are loose (median ≤3; `/usr/bin/true` median ≤5). VERDICT 4 only checks that the string `<script id=data` is present.

## 4. Novelty in the implementation

As shipped, the build measures a known qualitative claim on 88 starts from a single function, so N1 in practice.

The N2 delta is now cheap to reach, and it would be a real result: a pooled median of 2, not 1, with the `(bad)` policy deciding between "one or two" and "two or three". The lendec work and the clean safety framing carry over unchanged.

## 5. Safety

**Benign.** The build reads binaries read-only, compiles one fixed C function, and writes `lattice.html` plus temp files. It makes no network calls and generates no code.

## 6. What clears the gate

Fix B1–B3, re-capture RUN.md, add a "Fix round 1" section to BUILD-05.md, and post `GATE BUILD-05 READY (fix round 1) — commit <hash>`.

At round 2 I'll re-run `indep_true.py`, `lendec_sample.py` and `resync_survey.py` against your corpus numbers, and re-render the lattice headless.

BUILD-04 fix round 1 (`3e1ca1e`, posted 09:25) is next in my queue.

## Round 2: fix round 1 @ `3ab1033`, APPROVE (2026-10-19 10:16 PDT)

**Reviewed:** commit `3ab1033`, named in the GATE line at 10:10.

**Reproduced in:** a fresh clone at `tasks/reviewer-repro/build-05-r2`, under `env -i`.

**Evidence:** `review/evidence/build-05/r2/`.

### Blockers

| Round-1 issue | Status | Basis |
|---|---|---|
| **B1** authority misparsed (no `-w`/`-z`); `(bad)` policy undocumented | **FIXED** | `-w -z` on every call. Linear decodes are self-checked for contiguity. Per-offset lengths come from one windowed call per region and are cross-checked at every true boundary (39,249/39,249). The `(bad)`/`.byte` policy is stated, and every statistic is given with and without `(bad)` chains. My `indep_true.py`, run against this tree, finds **0 false boundaries** (was 3) and lendec **45/45** (`rerun-indep-tools.txt`) |
| **B2** single-function anecdote | **FIXED** | Two arms: ground truth (8 gcc `-O2` objects, 18 sections, 61/61 function entries confirmed by the symbol table, n=8,400) and a labelled reference decode (5 `/usr/bin` binaries, n=115,884). **I re-derived both pooled results with my own `resync_survey.py` on the same corpus definition, and every figure matches RUN.md exactly** (`survey-author-corpus.txt`). Ground truth: median 2, P(≤1)=0.49, P(≤2)=0.71, P(≤3)=0.83, max 14, never 24; `(bad)`-free n=7,425, median 1, P(≤2)=0.76. Reference: median 2, P(≤2)=0.56, max 101; `(bad)`-free 0.77. My own *different* corpus from round 1 (14 objects; 5 binaries, uncapped) gives the same picture: ground truth 2.0/0.70, reference 2/0.56, reference `(bad)`-free 1/0.78. **So the finding is robust to the corpus choice** |
| **B3** no lattice drawn; false legend | **FIXED** | My headless render (`lattice-render-r2.png`, firefox, 1600×1200) shows a real superset lattice: true-stream arcs above the axis, misaligned decodes below, `(bad)` edges dashed, merge points, example chains followed to their merge, a histogram and the corpus table. The legend matches the classes the code assigns, and there are 0 external refs. **The self-check VERDICT is not vacuous** (`lattice-mutation-output.txt`): deleting an arc, a merge marker or a histogram bar, or falsifying the embedded histogram or one embedded length, each makes `_check_lattice` **FAIL**. (Geometry is not checked: N6) |

### Reproduction

| Test | Result | Evidence |
|---|---|---|
| `make` ×2 (clean clone) | `make_exit=0`, **10/10 PASS** both runs, about 9 s each. Output is **identical to RUN.md's make block** | `make-run1.txt` |
| strace | **CLEAN**. Temp directories: 51 created, **51 removed** (round-1 N4 fixed) | `strace-audit.txt`, `tmp-and-refs.txt` |
| my C09-3 sample (unchanged) | **WRONG 0** (was 3: `syscall`). Real starts sized correctly: **175/189**. The misses are VEX (13, honest None), `rep stos` (1) and region edges. BAD-ACCEPTED 30 is now disclosed in lendec's docstring | `rerun-indep-tools.txt` |
| lendec on the corpus (author's run, reproduced) | True boundaries: AGREE 2,715, **WRONG 0**, NONE 38 | `make-run1.txt` |

### Correction to my round-1 evidence

My `indep_lattice.wide_decode` lacked `-z`, the very flaw B1 named, so it too elided the `/usr/bin/true` head's trailing zero run (offsets 161–162). With `-z` (`indep-tools-with-z.txt`), round 1's "corrected" figures for that sample become:

| Figure | Round 1 (my tool without `-z`) | Corrected (with `-z`) |
|---|---|---|
| n | 114 | 118 |
| never | 2 | 0 |
| median | 1.0 | 1.0 |
| byte median | 6.0 | 5.0 |

Every round-1 conclusion stands: the 3 false boundaries, the 7 capped lengths, lendec 45/45 rather than 45/48, and the median falling from 2 to 1. The `work()` re-derivation is unaffected because it has no zero runs.

### Nits (not blocking)

- **N6:** `_check_lattice` counts arcs, merges and bars, but doesn't verify arc **geometry**. Moving one arc's endpoint by a byte still PASSES (mutation f). Comparing each `M x0 … x1` against `k` and `k+objlen` would close this.
- **N7:** the HTML heads the drawn region "headline region — gt.c:work()" (`superset.py:497`). The README correctly calls it the *illustration*, at median 1 against the corpus's 2. Rename the heading to match.
- **Observation, not a defect:** the five claim VERDICTs were formulated from the data, and their thresholds are the author's. The README says both. They are regression pins, not pre-registered tests. That's the honest framing, and it is the one used.

### Novelty in the implementation: N2 delivered

The running artifact now quantifies Linn & Debray's qualitative claim on a corpus:
- Ground truth: a median of 2 instructions, 71% within 2 and 83% within 3.
- `(bad)`-free chains: a median of 1.
- `/usr/bin`: a heavier tail, explained by 37% `(bad)`-touching chains.

That settles the "one or two" vs "two or three" discrepancy: they describe two different populations. The README discloses the `(bad)`-free selection effect and the gcc-only corpus. The lattice is now an actual superset-decode picture that a learner can read. **Gate BUILD-05 is CLEARED.**
