# NOVELTY-LOG — lowlevel-lab, Step 1.2

Author lane. Live GitHub + web evidence for every plausible candidate in
[CANDIDATES.md](CANDIDATES.md). Reviewer: do not trust my dispositions —
the raw records are machine-readable and re-runnable (see Method), so you
can diff your counts against mine.

## Method (so this is auditable, per REVIEW-00 §2.1 / §1.3)

- **Tooling.** `research/tools/ghsearch.py` runs every query through
  `gh api -X GET search/{repositories,code} -f q=… -f per_page=10` — the
  same REST endpoint `gh search` uses — and writes one JSON record per
  query to `research/raw/gh/<cand>-<kind>-<hash>.json` with: exact query,
  UTC-ish timestamp, exit status (absence of an `"error"` key), GitHub's
  `total_count`, `incomplete_results`, and up to 10 trimmed hits
  (full_name, stars, created/pushed, description). The `render` subcommand
  regenerates the human log; the full rendered dump is
  [NOVELTY-LOG-APPENDIX.md](NOVELTY-LOG-APPENDIX.md) (916 lines, all 179
  queries). Re-run: `python3 -I research/tools/ghsearch.py run research/queries.tsv`.
- **Counts.** A "0 hits / total_count=N" claim here is backed by a record
  that shows exit-ok and that `total_count`. Where `total_count` is large
  but all top hits are irrelevant, I say "large but off-target" and name
  why (GitHub repo search matches description/README fuzzily; many hits are
  unrelated projects sharing a word).
- **Kill reads.** Where a hit could kill a concept, I read its README **and
  at least one source file** via `research/tools/ghread.py` (which saves
  verbatim copies under `research/raw/repos/OWNER__REPO/` with a meta.json
  recording the repo's HEAD SHA and fetch time). Nothing fetched was run.
  26 repos were read this way; quotes below are from those saved copies.
- **Web.** ~30 web searches + targeted arXiv fetches (recorded inline in
  the per-candidate sections). Non-GitHub prior art caps novelty at N2 and
  is disclosed even though the mission's literal bar is "on GitHub".
- **Novelty levels** are REVIEW-00 §2.1: N0 exists · N1 known, qualifier
  delta · N2 adjacent, substantive delta · N3 no implementation found ·
  N4 new way of seeing. **Recall-only claims are marked UNVERIFIED.**
- **Limits I disclose up front.** (a) `gh search code` is the legacy index
  (default branch, <384 KB files, forks mostly unindexed, punctuation
  ignored) — I treat code-search silence as supporting, never primary.
  (b) My recall cutoff is Jan 2026; GitHub has ~9 months since, so every
  theme got a `created:>2026-04-01` slice. (c) The reviewer shares my model
  and token, so two logged queries per shortlisted concept should be
  independently re-run.

---

## Verdict table (full candidate list — guards against cherry-picking)

| # | Frame | Best novelty | Decision | Killer / strongest threat (read as data) |
|---|---|---|---|---|
| C01 | stale-fetch A64 I-cache emulator | **N2** | **RESHAPE → ifetch-sanitizer** | goliajp/aarch64-study v0.22 *models stale I-cache w/o IC IVAU, passing tests*; cyyself/jit-coherence-test runs it on HW |
| C02 | SMC/XMC cartography on hybrid x86 | **N3** | **SHORTLIST #1** | SMaCk (L1i *attack*, not benign cost-map, not hybrid/XMC/distance); SelfModTamper (tamper-proofing) |
| C03 | version-correct PT decode of SMC | **N2** (was N3) | **SHORTLIST #2 — RESHAPE** (REVIEW-01 §2.2) | wilvk/asm-test `asmtest_codeimage` (TEXT_POKE code-image timeline, was in my own 1-hit query); perf `intel_pt_text_poke`; libipt `sideband/` image-over-time; FlowJIT; DRAKVUF PTW inject. In-band *executed* PTWRITE fence survives as the N2 delta |
| C04 | P-core vs E-core differential scanner | **N1** (was N3) | **CUT** (REVIEW-01 §2.3) | **libLISA (OOPSLA'24) already diffs i9-13900 P-cores (Raptor Cove) vs E-cores (Gracemont) on undefined shifts/rotates/mul/div and proposes fingerprinting** — reviewer verified the PDF (sha256 b3bee6a9). Newer-gen-of-published ⇒ N1. Probe kept as SUMMARY research evidence; migration-hazard reshape is [BLOCKING safety] |
| C05 | native Core War on real cores | N2 | alternate (safety) | r2wars (ESIL VM, multi-arch, *emulated*); pMARS/corewar.io (VM). Native-on-cores unseen but sandbox burden high |
| C06 | reversible ISA, bidirectional native JIT | **N2** | cut (for C01) | kostyk348/phase-vm *emits phase_fwd/phase_rev C, cc -O2 -shared + dlopen* = reverse native codegen already |
| C07 | in-process x86↔A64 hop | N2 | cut | systems-nuts/unifico, ssrg-vt/popcorn-* (research, cross-machine); core idea exists |
| C08 | AArch64 encoding-space atlas | **N0** | cut | zyedidia/armvis = A64 Hilbert-curve atlas by instr class, exactly this |
| C09 | x86 superset-decode lattice + resync stats | N2 | alternate | utds3lab/multiverse, KennethAdamMiller/superset_disassembler (technique exists; viz/stats explainer doesn't) |
| C10 | program single-steps & renders itself (TF) | **N1** (was N3) | **CUT** (REVIEW-01 §2.5) | **gperftools `SingleStepper` (2024): benign in-process SIGTRAP+TF per-instruction stepper** (`gregs[REG_EFL] |= 0x100`), used in tcmalloc_unittest; ERESI e2dbg; v8 trap-fuzzer. My "attacks only" claim was FALSE; record below §2.1 minimums |
| C11 | A64→x64 educational translator | N1 | cut | dynarmic/box64/AArchX/Rosette/microlift; many toy translators |
| C12 | cross-ISA machine-code quine relay | N2 | alternate | meithecatte/mips-quine (single-ISA ELF quine); no cross-ISA binary relay found |
| C13 | single-bit fault sensitivity map | N1 | cut | Keysight/FiSim (deterministic fault-injection sim); ARMORY/LLFI |
| C14 | sampling-skid atlas per core type | N2 | cut (thin) | kernel PERF_SAMPLE_SKID_IP patches; no per-core-type skid atlas, but thin interest |
| C15 | rep movsb fault granularity | N2 | cut (thin) | SDM 7.3.9.3; Raymond Chen 2025; no repo, but narrow |
| C16 | Befunge SMC JIT | **N0** | cut | adrianton3/befunjit-86 = Befunge-93 JIT to x86-64 with p-triggered recompile |
| C17 | CPUID-faulting tracer/spoofer | N2 | alternate | rr uses it; cpuid-fault-emulation modules spoof (for games), not trace |
| C18 | loader relocation/lazy-binding film | N1 | cut | LD_DEBUG + many PLT/GOT explainers; akshvy/aarch64-reloc-visualizer |
| C19 | native artificial-life soup | N1 | cut | redpill (arXiv 1105.1534), yurbar/primordia, damianfye/vestige |
| C20 | CET shadow stack vs PAC duel | — | cut (safety) | requires demonstrating control-flow hijack |
| C21 | metamorphic variant equivalence | — | cut (safety) | engine-building is forbidden + a0rtega/metame etc. exist |
| C22 | PT TNT-bit control-flow barcode | **N3** | bonus within C03 | magic-trace = function timeline (Perfetto), not a TNT-bit texture; no viz found |
| C23 | KVM page-walk visualiser | N1 | cut | dpw/kvm-hello-world + many page-walk visualisers |

**Post-REVIEW-01 shortlist state (2026-10-19).** REVIEW-01 verdict
APPROVE WITH CHANGES (commit 19c7ecb). Surviving builds: **P1 C02** (KEEP N3),
**P2 C03** (RESHAPE N2), **P4 C01-reshaped** (KEEP N2, ARM64). **CUT: P3 C04**
(libLISA, N1) and **P5 C10** (gperftools SingleStepper, N1). Two replacement
slots are open; each gets a §2.1-complete + ≥2 paper/web addendum reviewed
before its build (REVIEW-01 §5.5). Reviewer's non-binding steer: C12 (cross-ISA
machine-code relay) + a visualization concept (C22-on-P2 or C09). Rationale and
the cut-consistency check are in [SHORTLIST.md](SHORTLIST.md). The addendum
dispositions for the replacements are appended at the end of this file.

---

## C01 — stale-fetch A64 I-cache → **RESHAPE to "ifetch-sanitizer"** (N2)

**What I set out to prove novel:** an A64 emulator that executes *stale*
instructions when a JIT omits cache maintenance, naming the missing step.

**Threats found (both within my recall gap, both read as data):**

1. **goliajp/aarch64-study** (★1, created 2026-04-29, HEAD 8f5e1f95b528) —
   a browser AArch64 SoC teaching simulator (Rust→wasm). Its roadmap v0.22
   is "I-cache + `IC IVAU` / `DC CIVAC` + self-modifying code demo", and the
   simulator core `crates/aarch64-sim/src/lib.rs` (3446 lines, read as data)
   **implements a per-core PIPT I-cache and two passing tests** that encode
   exactly my core observable. Verbatim:
   > `fn icache_returns_stale_without_ic_ivau()` … "without IC IVAU the
   > cache should hand back the stale instruction" (asserts `x[1]==1`, the
   > stale value, after rewriting PA 0x4004 post-fetch)
   and `fn ic_ivau_lets_self_modifying_code_take_effect()`. The SYS decoder
   handles `IC IVAU` (invalidate line) and treats `DC CIVAC` as a modelled
   no-op. **This is N0 for the bare "emulator shows stale fetch" idea.**
2. **cyyself/jit-coherence-test** (★6, 2026-03-21, HEAD efa78c583433) —
   `test.cpp` (223 lines, read as data) runs the *real-hardware* experiment:
   a writer thread JITs an instruction with a random immediate, a second
   thread executes it, and it checks whether skipping D-cache clean
   (`-fidc`), I-cache invalidate (`-fdic`), or `fence.i` (riscv) corrupts
   coherence. It reads `CTR_EL0.{IDC,DIC}`, supports `-alias` via
   `memfd_create` dual-mapping, and records per-CPU findings (Apple M1:
   `-fdic` fails; Phytium D2000: `-fidc` fails sometimes). This is the real
   silicon oracle my emulator would imitate — it exists.

**Why a reshaped frame still reaches N2 (substantive, nameable gap):**
Neither prior art models the **full** maintenance sequence as a
*configurable coherence matrix with per-step omission diagnosis*:
- aarch64-study models only the **I-side** (IC IVAU invalidates a line);
  **D-cache is an explicit no-op** ("we do not model the D-cache"). It
  therefore cannot show the `DC CVAU`-to-Point-of-Unification step, the two
  `DSB ISH` barriers, or the `ISB` mattering *independently*, and it does
  not vary `CTR_EL0.{IDC,DIC}` or the I/D line-size mismatch (the real
  big.LITTLE JIT-breaker). It is one fixed demo, not a checker.
- jit-coherence-test is pass/fail on **whatever CPU you run it on** (here:
  an x86 host, where it would report coherent), with skip flags — not an
  emulator, no step-level diagnosis, no line-size-mismatch model.

**Reshaped C01 ("ifetch-sanitizer"):** a small A64 execution model whose
I-cache/D-cache coherence is parameterised by `CTR_EL0.{IDC,DIC}` and by an
I/D line-size mismatch, that takes a code-patching sequence and reports
**exactly which of `DC CVAU → DSB ISH → IC IVAU → DSB ISH → ISB` was
omitted and under which config it would execute stale on real hardware** —
while the same bytes run fine natively on this x86 box and under
qemu-aarch64 (which REVIEW-00 §0.2 verified is SMC-coherent). Novel
observable: the *diagnosis*, and the cross-check "silent here, broken
there". Centrepiece is the model, so per §2.1 N2 is KEEP-as-RESHAPE.
**Prior art disclosed in README.** Risk: must not collapse into
aarch64-study's single-line demo — the matrix + diagnosis is the point.

**More prior art to position against (added per REVIEW-01 §2.4, reviewer-found;
I agree — adjacent, each at litmus/fixed-demo scale, none a whole-program
step-diagnosing sanitizer with the line-size-mismatch class):**
- **herdtools7** @12690a83da `catalogue/aarch64-ifetch/` — an ifetch litmus
  catalogue, simulated by `herd7 -variant ifetch`, run on hardware by
  `litmus7 -variant self`. (herd7 can't be installed here; its tests are
  fetched as data for cross-checking expected outcomes — P4-3.)
- **RMEM** (Cambridge, cl.cam.ac.uk/~pes20/iflat/) — exposes the **IDC/DIC**
  knobs ("turn off IDC and DIC to get the weakest semantics"), so the IDC/DIC
  matrix exists **at litmus scale** — but not whole-program with step naming.
- **DynamoRIO** `core/dispatch.c:958` (AArch64): handles the app's `IC IVAU`
  for SW cache consistency; a missing `IC IVAU` leaves stale code there too,
  but it **diagnoses nothing**.
The surviving delta (REVIEW-01 §2.4): a *whole-program* sanitizer that names
the omitted step automatically and covers the **I/D line-size-mismatch** class
(CTR_EL0 differing across cores breaking flush-loop strides — the classic
big.LITTLE JIT bug), which litmus enumeration and fixed demos don't. BUILD-04
conditions P4-1…P4-5 (semantic oracle = qemu end-state; encoder oracle =
aarch64-linux-gnu as/objdump on ≥20 reviewer-chosen insns; every per-config
verdict cites DDI 0487 § x.y; model-output labelling) apply.

Queries: `research/raw/gh/C01-*.json` (round 1–3). Web: QEMU IC-IVAU
commit 9719f125 (2023); Arm FVP `cache_state_modelled` (hides maintenance
defects when off); Simner et al. ESOP'20 ifetch model + isla/herd
(litmus-scale, not whole-program). All recorded in STATUS and below.

## C02 — SMC/XMC cartography on hybrid x86 → **SHORTLIST #1** (N3)

**Pitch:** a reproducible *map* of what self- and cross-modifying code
cost and do on this Panther Lake hybrid part — SMC machine-clear cost vs
write↔exec distance (same line / same page / next page / far), P-core vs
E-core, cross-core patch visibility latency and XMC clears, and a torn-fetch
probe at instruction boundaries.

**Closest threats (read as data):**
- **hunie-son/SMaCk** (ASPLOS'25, read README + `SMaCk_cachetime/main.c`):
  an **instruction-cache *attack*** (Prime+Probe/Spectre on L1i via SMC
  conflicts) to leak crypto keys, measured on 10 older Intel/AMD µarches
  (Cascade/Comet/Ice/Tiger Lake, Ryzen) with PAPI counters incl.
  `MACHINE_CLEARS.SMC`. Verbatim purpose: "efficient instruction cache
  attacks via self-modifying code (SMC) conflicts". It is **not** a benign
  cost-map, has **no hybrid P/E comparison** (confirmed via arXiv full-text:
  single i7-9750H for the SMC timing), **no write-distance sweep** (dual-page
  only, "using three or four pages did not materially improve results"), and
  **no XMC**. Disposition: adjacent, does not kill. N3 stands.
- **GregoryMorse/SelfModTamper** (★1, companion to arXiv 2604.12407,
  read README): SMC for **tamper-proofing** — timing predicates that *avoid*
  machine clears for integrity checking. Also single CPU (i7-9750H), dual-page,
  cross-modifying listed as *future work*. Adjacent purpose, does not kill.
- **hayamdk/ryzen_segv_test** (★48, 2017, read README): a **bug repro** of
  Ryzen cross-modifying-code SEGV — 3 threads, writer+executor, CPUID
  serialization. It *demonstrates* CMC hazard but measures nothing, maps
  nothing, is single-µarch, not hybrid. Adjacent, does not kill.
- Repo searches `self-modifying code benchmark`/`machine clears
  self-modifying`/`cross-modifying code`/`smc machine clear`/
  `hybrid p-core e-core microbenchmark` → total_count 0–1 relevant
  (records C02-*.json). `topic:self-modifying-code` (70 repos) is almost
  entirely obfuscators/packers/virtualizers (xObf, covirt, mkpoly,
  elf-packer) — the population REVIEW-00 §1.15 warned about, none a cost-map.

**Evidence the phenomenon is real & reachable here:** Intel perfmon tables
for family 6 model 0xCC give P-core `MACHINE_CLEARS.SMC` 0xC3/0x04 and
E-core `MACHINE_CLEARS.SMC` 0xC3/0x01 **plus a dedicated
`MACHINE_CLEARS.XMC` 0xC3/0x80 on the E-core** — so the hybrid + XMC angle
is specifically supported by this silicon. Unprivileged `perf_event_open`
counting of own task is allowed (paranoid=2). **N3, KEEP strong.** Non-GitHub
prior art (Agner Fog, SDM §9.1.3, blog ~100-cycle folklore) disclosed; caps
nothing because none is a hybrid distance/XMC map.

**Prior art to cite (added per REVIEW-01 §2.1, reviewer-found, I agree it's
adjacent not fatal):** Botacin, Zanata & Grégio, *"The Self Modifying Code
(SMC)-Aware Processor (SAP): A security look on architectural impact and
support"* (J. Computer Virology and Hacking Techniques); repo
`marcusbotacin/Self-Modifying-Code` @ed09a3abd6 has a PIN flush-aware cache
simulator + PEBS-based SMC detector — architectural-impact measurement, single
core class, **no distance sweep, no hybrid, no XMC**. `clamchowder/Microbenchmarks`
matched "self-modifying" but only *avoids* SMC (not prior art). The README/
BUILD-01 novelty section must cite Botacin SAP. **Reviewer's own reference
sweep** (`review/evidence/presearch/c02-probe/`) already shows the striking
observable and is the oracle BUILD-01 will be held to (see SHORTLIST P1 and the
BUILD-01 conditions P1-1…P1-6): P-core clears only within its own 64-B line,
E/LP-E on a 1-KB granularity — matching Intel 248966 §3.6.8.1's Pentium-4-era
rule for Darkmont but not Cougar Cove. **Three core classes P(0–3)/E(4–11)/
LP-E(12–15)** must be reported separately (R14); "E = 4–15" is wrong.

## C03 — version-correct PT decode of self-modifying code → **SHORTLIST #2 · RESHAPE to N2** (REVIEW-01 §2.2)

**Pitch:** Intel-PT decoders reconstruct the instruction stream from the
code bytes *currently* in memory, so self-modifying code is silently
misdecoded. Keep a versioned code image and emit an in-band `PTWRITE
<version>` at each code write, so the decoder re-bases on the exact version.

**Phenomenon proven on this box** (research/probes/pt-smc-misdecode/):
a program prints `v1 returned 1`, but gdb's own PT instruction-history for
that same execution shows `mov $0x2,%eax; nop×4; ret` — the *post-patch*
bytes. [Correction per REVIEW-01 §2.2 nit: the misdecoded *instructions*
carry no gap/warning, but the gdb session does report "1 gaps" from a buffer
wrap before the SMC region — "no gap or warning" was too broad.]

**Why the N3 claim FAILS — the reshape (REVIEW-01 §2.2, verified by the
reviewer, re-confirmed by me against review/evidence/presearch/C03-priorart-excerpts.txt):**
version-correct PT/stepper decoding of rewritten code already exists. The
surviving delta is narrow and must be *shown* to matter.
1. **wilvk/asm-test** (created 2026-06-23) ships `asmtest_codeimage` — a
   userspace `PERF_RECORD_TEXT_POKE` that builds a **timestamped code-image
   timeline** (soft-dirty + `PAGEMAP_SCAN`, bytes via `process_vm_readv`),
   consumed by a *versioned* ptrace stepper `asmtest_ptrace_trace_attached_versioned`.
   **This was in my own results** — query `"pt_image_add_cached" jit`
   (`research/raw/gh/C03-code-81ba038c99.json`, total_count=1) returned exactly
   `wilvk/asm-test/docs/internal/plans/hardware-trace-plan.md`, rendered at
   APPENDIX:334, and I failed to disposition it. **That is the §2.1
   selective-logging failure the reviewer flagged (P2-1).** Mea culpa:
   a 1-hit count is the *most* important to read, not the least. (Note: wilvk's
   own docs say the **hardware half — feeding the timeline into Intel PT/libipt
   — is still forward-looking**, so the *PT-decode* of SMC is not shipped there;
   the time-keyed *machinery* and the versioned *stepper* are.)
2. **Linux perf** `tools/perf/util/intel-pt.c`: `intel_pt_text_poke()` +
   `intel_pt_cache_invalidate()` version kernel SMC by time-ordered
   `PERF_RECORD_TEXT_POKE`.
3. **intel/libipt `sideband/`** (`pt_sb_pevent.c`): applies
   `PERF_RECORD_MMAP/MMAP2/AUX/ITRACE_START` at TSC-converted times
   (`time_shift/time_mult/time_zero`) — an **image-over-time facility at
   mapping granularity**. ⇒ **my earlier claim "there is no
   versioned-image-over-time facility" was FALSE** (it is true only that there
   is no *TEXT_POKE-granularity* fence in libipt-sb). Corrected here.
4. **FlowJIT** (tuxology/flowjit, LPC'17) + the 2018 Univ. Crete MSc thesis
   "JIT Tracing using Intel Processor Trace" — PT reconstruction of JITed code.
5. **DRAKVUF** (`src/plugins/ipt/ipt.cpp`): `emit_ptwrite64()` already
   **injects synthetic PTW packets** (0x02 0x32 + payload) into the trace.
   So "PTW as an annotation" is not itself novel.

**What survives — N2 delta:** using an *executed* `PTWRITE <version>` as an
**exact, in-band, control-flow-ordered fence for same-address byte rewrites**,
versus the three **time-keyed** mechanisms above (which switch versions at
TSC/MTC/CYC timestamps). This only counts if demonstrated **head-to-head**:
find the patch→execute interval below which a time-keyed decode mis-attributes
(at stated MTC/CYC settings), where the PTWRITE fence stays exact. If time-keyed
decoding turns out exact even at cycle-accurate settings, the honest claim
shrinks to "exact without timing packets" — still N2. "Naive bytes-as-now is
wrong" is the **known baseline**, not the observable. (See SHORTLIST P2 for the
rewritten observable; P2-1/2/3 are committed before any build.)
**C22 (TNT-bit barcode) rides this capture as a visualization bonus, not a
scoring criterion (REVIEW-01 §2.2 P2-5).**

## C04 — P-core vs E-core differential scanner → **CUT at N1** (REVIEW-01 §2.3)

**Verdict: CUT.** The phenomenon is real and reproduced (the reviewer re-ran
my probe byte-identically across P/E/LP-E cores), but the *frame is published*:
**libLISA** (Craaijo, Verbeek & Ravindran, *"libLISA: Instruction Discovery and
Analysis on x86-64"*, OOPSLA 2024, PACMPL 8:283, DOI 10.1145/3689723) analyses
the **Intel i9-13900's P-cores (Raptor Cove) and E-cores (Gracemont) as
separate architectures** (~118k instruction groups each) and reports that the
microarchitectural-difference groups "consist primarily of … **bit shifts,
rotates, multiplication, division and bit manipulation** … that can exhibit
undefined behavior", proposing **"fingerprinting programs"** from them. Its
motivating example (Fig. 1) is exactly a rotate's undefined OF (`rcl` then
`jno`) that "behave[s] benign on an AMD Ryzen … but … maliciously on an Intel
Core i9-13900." (Reviewer verified the PDF, sha256 b3bee6a9; excerpts in
`review/evidence/presearch/C04-liblisa-excerpts.txt`.) Panther Lake
(Cougar Cove/Darkmont) is a newer generation of a *published* comparison —
REVIEW-00 §2.1 ⇒ **N1 → CUT**. Also post-cutoff: `kmx00/ub86-pred` (undefined
effects as opaque predicates, P/E split), `dominicolucci/dift86` (silicon-vs-
model differential testing). libLISA appears in none of my 179 raw results —
a **paper-search gap** (G-2), not selective logging; it is reachable only by
academic-venue search, which my repo-name queries structurally missed.

**Why not reshape to the migration hazard.** The one unpublished delta (a
thread's flags changing after a scheduler move) requires building a
**core-type-dependent predicate** — exactly the misuse libLISA
("fingerprinting", "maliciously") and ub86-pred ("break analysis tools")
document. REVIEW-01 §2.3 marks that reshape **[BLOCKING, safety]**. I accept
that; no reshape.

**Disposition of the probe.** `research/probes/hybrid-undefined-flags/` stays
as honest **research evidence** and will be cited in SUMMARY.md as "the libLISA
P/E finding re-confirmed on Panther Lake (Cougar Cove first-step vs Darkmont
last-step OF rule)" — a true, useful sentence, not a part. The earlier
Intel-GameDev-Guide / Wikipedia disclosure (below) stands; libLISA is the
stronger, deciding prior art.

**Superseded analysis (kept for the record — my pre-CUT reasoning):**
run identical instruction candidates pinned to a P-core and an
E-core and diff every observable — legality, length, result, *architecturally
undefined* flags, CPUID — on one die with two microarchitectures behind one
ISA.

**A real divergence is in hand** (research/probes/hybrid-undefined-flags/,
probe-output.txt): for shift/rotate counts ≥ 2, the **architecturally
undefined OF flag differs between core types** — P-cores (Cougar Cove)
compute OF by a "first-step" rule, E-cores (Darkmont) by a "last-step" rule;
`SAR` agrees, results agree. So the concept's payoff ("do the two core types
disagree on undefined behaviour?") is **demonstrated**, not hoped-for.

**Non-GitHub prior art I must disclose (caps the bare claim to N2).** The
*fact* that P and E cores differ on the undefined OF flag is already public:
- **Intel's "Game Dev Guide for 12th Gen Intel Core Processor"** (web search,
  extended) states the x86 ISA defines OF only for multiplies and 1-bit
  shifts, and that the undefined shift OF "can vary between Performance-cores
  and Efficient-cores." (Original `alder-lake-developer-guide.html` now
  301→404s; live copy titled "12th-gen-intel-core-processor-gamedev-guide".)
- **Wikipedia, "Alder Lake"**: "minor differences between the behavior of the
  two cores with regard to an undefined overflow flag in certain bitwise
  operations" (cites a source I could not open from search).

So "P and E differ on undefined OF" is **documented, not discovered** → the
bare claim is N2, and the README will say so. **What is still unpublished**
and what P3 builds: (a) a *systematic scanner* (no public tool does this —
sandsifter/vmsifter scan one core; yufengzjj diffs model backends), (b) the
*specific rule* each core follows (first-step vs last-step, per instruction
and count — my probe characterises it; the Intel/Wikipedia prose does not),
and (c) a migration-visible demonstration. That trio is a genuine N2
contribution; it is not N3. Honest level, disclosed up front.

**Closest threats (read as data):**
- **yufengzjj/hybrid-x86-oracle** (★0, 2026-09-29, read README +
  `docs/backend-differences.md`, 78 KB): a differential x86 oracle framework.
  Crucially it diffs **reference *backends*** (Sail model / Bochs / KVM-host)
  against each other; its "architecturally undefined flags" table is
  **Bochs-vs-Sail** (e.g. "Bochs sets OF; Sail leaves it clear" for SHLD/SHRD).
  It does **not** pin to and diff the **two core types of one hybrid die** —
  "hybrid" in its name refers to pluggable reference backends. Adjacent and
  genuinely useful as an *oracle* (I may cite it), does **not** kill the
  "P-core vs E-core silicon divergence" frame. Its name made me read it
  closely precisely because it looked like a killer; it isn't.
- **Battelle/sandsifter** (★532), **intel/vmsifter** (★16),
  **blitz/baresifter**: single-core instruction fuzzers (length/legality via
  the page-boundary trick). None diffs core types. Disposition: method
  ancestors, not the hybrid frame.
- `topic:cpu-fuzzing` → 0; `p-core e-core created:>2026-04-01` → benchmarking
  /power-toggle repos, none differential-ISA (records C04-*.json).

**N2, KEEP.** Novel observable already captured; the build turns the probe
into a systematic scanner with the yufengzjj oracle as a tie-breaker for
"which core (if either) matches the SDM/formal model". The bare "they differ"
fact is documented (Intel/Wikipedia, above) — the scanner, the specific rule
characterisation and the migration demo are the contribution.

## C10 — program single-steps & renders itself → **CUT at N1** (REVIEW-01 §2.5)

**Verdict: CUT.** My claim ("TF single-stepping appears only as an attack
mechanism or via ptrace") was **FALSE**. Benign in-process TF single-stepping
is mainstream (reviewer evidence, `review/evidence/presearch/C10-priorart-excerpts.txt`,
re-confirmed by me):
- **gperftools** `src/base/single_stepper.{h,cc}` (@635500ed68, 2024): *"Start
  intercepts SIGTRAP and enables single-stepping (in currently running thread).
  On ~each instruction given callback will be invoked with signal's ucontext."*
  Sets `gregs[REG_EFL] |= 0x100` (TF). In-process, benign, used by
  `src/tests/tcmalloc_unittest.cc`. This is my exact mechanism and purpose.
- **ERESI** `libe2dbg` (embedded in-process ELF debugger); **v8**
  `src/sandbox/trap-fuzzer.cc`; the Linux selftest
  `tools/testing/selftests/x86/single_step_syscall.c`. Code search
  `"gregs[REG_EFL]" "0x100" SIGTRAP` → 356 hits.
- Execution visualization is already well covered (Blinkenlights, gdb TUI).
- **Technical limit the reviewer noted:** each TF step is an exception +
  user-mode return (through FRED on this kernel), so a self-traced program
  can observe only the *architectural* fact that its listing changed, never SMC
  *cost* — the "payoff" was the trivial part.

My C10 search record was also **below the §2.1 minimums** (REVIEW-01 §1.3: 6
repo / 0 topic / 0 in:readme / 0 recency / 1 code). Two failures at once. **CUT
accepted; no reshape.** Dispositions recorded here per P5-1.

---

## Cuts — consistency check (REVIEW-00 §1.6)

I cut nothing "for buildability" that is harder than what I kept; the cuts
are N0/N1 (idea already implemented) or safety:

- **C08 (N0):** zyedidia/armvis is the A64 Hilbert atlas (README + arm-vis
  source read; plots every encoding over a Hilbert curve by instr class).
- **C16 (N0):** adrianton3/befunjit-86 is a Befunge-93→x86-64 JIT whose `p`
  triggers recompile (README read) — my exact pitch.
- **C06 (N2, cut for C01):** kostyk348/phase-vm (read `src/aot.rs`) already
  generates `phase_fwd`/`phase_rev` C from a reversible kernel and compiles
  it (`cc -O2 -shared` + dlopen) with bit-exact `F⁻¹(F(S))==S` fuzz — i.e.
  reverse *native* codegen exists (via C). My only delta would be direct
  machine-code emission vs via-C — a qualifier, not a centrepiece. dabernado/
  iris plans a Cranelift reversible JIT. C01 wins the slot because it is
  ARM64 (mission-central) and about behaviour the project itself models.
- **C11 (N1):** dynarmic, box64, AArchX, Rosette, microlift + many toy
  A64/x64 translators.
- **C05 (N2) / C09 (N2) / C12 (N2) / C17 (N2):** kept as **alternates**, not
  cut on novelty — see SHORTLIST.md "bench". C05 is held back for the §2.4
  sandbox burden (native warriors in a shared RWX arena), not weak novelty.
- **C20 / C21:** cut on safety (control-flow hijack demo; metamorphic engine
  building). C13/C18/C19/C23: N1 (FiSim; LD_DEBUG; redpill/primordia/vestige;
  dpw/kvm-hello-world). C14/C15: real N2 gaps but thin interest for the
  effort; noted for v2.

Full per-query records: [NOVELTY-LOG-APPENDIX.md](NOVELTY-LOG-APPENDIX.md)
and `research/raw/`.

---

# Replacement addenda (post-REVIEW-01, for the P3 and P5 slots)

Each addendum meets REVIEW-01 G-1 (§2.1 minimums: ≥3 repo incl. ≥1 topic, ≥1
in:readme, ≥1 created:>; ≥2 code) and G-2 (≥2 paper/web). Query records are in
`research/raw/gh/C12-*.json` / `C09-*.json` and rendered in
NOVELTY-LOG-APPENDIX.md; dispositions below. No build starts before the reviewer
appends a verdict to REVIEW-01 §6.

## ADDENDUM — C12 cross-ISA machine-code quine relay (P3-slot replacement) — N2–N3

**Concept.** A 2-cycle machine-code quine *relay*: a native **x86-64 ELF** that,
run, writes a complete **AArch64 ELF** to stdout; that AArch64 ELF (run under
qemu-aarch64), writes the original x86-64 ELF back, **byte-for-byte**. Each stage
is a distinct single-ISA executable; together they form a fixed point across two
ISAs. Mission-central (ARM64 *and* x86-64 machine code), now runnable here
(x86-64 native + AArch64 under qemu-aarch64 8.2.2).

**Search record (§2.1 met: repo 11, topic 1, in:readme 1, created 1, code 2).**
- `topic:quine` (201) and `quine relay in:readme` (208): top hits are
  **mame/quine-relay** (★14610) and **mame/quine-clique**, **rvantonder/pentaquine**
  — all **source-level** relays/multiquines across high-level languages, read as
  data earlier; none emits *machine code*, let alone across ISAs. Disposition:
  the "relay" idea is famous at source level; the machine-code-across-ISA version
  is not these.
- `cross-architecture quine` (0), `multi-architecture quine` (0),
  `elf quine created:>2026-04-01` (0): no hits.
- `polyglot elf executable` (1): `latedeployment/oci2bin` — an OCI-image→ELF+tar
  packer, not a quine.
- code `quine aarch64 x86-64 elf` (68, top hits are blogs / a Raku toolchain /
  kernel notes — none a relay) and `"EM_AARCH64" "EM_X86_64" quine` (0).
  [Disclosure per REVIEW-01 §6.1 nit: a third code query `"e_machine" quine elf`
  hit GitHub's HTTP-503 "too many shards failed" repeatedly (a server-side error
  for that query shape, not throttling); it was replaced by the working
  `quine aarch64 x86-64 elf` above, so two clean code queries stand. The erroring
  record remains in research/raw/gh/ for audit.]
- Single-ISA binary quines read as data (do **not** kill — none is cross-ISA or a
  relay): **panzi/binary-quine** (x86-64 ELF writes itself to stdout without
  reading its code), **meithecatte/mips-quine** (MIPS ELF that disassembles
  itself), 42-DrQuine (elf64 asm quine).

**Paper/web (G-2).** No binary quine *relay* across x86-64↔ARM64 found. The
closest multi-arch artifacts are **Actually Portable Executables** (Tunney —
one self-rewriting binary with per-arch code blocks + a dispatcher, runs on
x86-64 and Arm64) and **ixty/xarch_shellcode** (a polyglot dispatcher with one
block per arch), and Microsoft **Arm64X** (loader-level dual-arch PE). **The
distinction that makes C12 novel:** those are *one* polyglot/self-rewriting
binary choosing an arch at run time; a relay is a *chain of distinct single-ISA
binaries*, each generating the *next* ISA's binary, cycling back to the original
— no dispatcher, no polyglot header, each stage a clean ELF for exactly one ISA.

**Novel observable.** `x86 ELF → (run native) → AArch64 ELF → (run qemu) →
x86 ELF'`, and `sha256(x86 ELF) == sha256(x86 ELF')`, i.e. a verified cross-ISA
fixed point. Shown with `cmp`/`sha256sum` and `aarch64-linux-gnu-objdump` on the
emitted ELF. Level **N2–N3** (reviewer independently leveled N2–N3).

**Prototype plan.** Hand-written x86-64 and AArch64 freestanding ELF emitters
(GNU `as`/`ld`; no libc), each carrying the *other* stage's bytes as data and
reconstructing itself from a template + its own data table (the classic quine
split), extended across the ISA boundary. Files:
`parts/NN-quine-relay/{AGENTS.md,README.md,RUN.md,Makefile,stage_x64.s,
stage_a64.s,build_fixpoint.py,verify.sh}`. Oracle: byte-exact `cmp` round trip +
independent `objdump` decode of each stage; `verify.sh` is the machine-checkable
pass/fail. Effort: Medium–High (quine construction across two ISAs is fiddly).
**Safety (REVIEW-01 §5):** each stage writes the next stage to **stdout only**;
`verify.sh` redirects it and runs it under qemu; **nothing writes itself to disk
or execs itself**. Risk: getting a true byte-exact fixed point (not just
"runs") is the hard part; if a full 2-cycle fixed point proves infeasible in the
time, the honest fallback (stated in README) is a verified one-way
x86→AArch64 self-describing emitter + a separate AArch64→x86 emitter with the
round-trip `cmp` shown, short of a single self-contained fixed point.

## ADDENDUM — C09 x86 superset-decode lattice + resync statistics (P5-slot replacement, visualization) — N2

**Concept.** Decode x86-64 at **every byte offset** of a code region, render the
resulting overlapping-instruction **lattice**, and **measure how quickly**
misaligned decode paths **resynchronise** with the compiler-intended stream
across real `/usr/bin` binaries — a visual + statistical explainer of *why x86
is self-synchronising and disassembly is hard*. Restores the visualization theme
(REVIEW-01 §2.5/§3). Independent of P2.

**Search record (§2.1 met: repo 11, topic 1, in:readme 1, created 1, code 2).**
- `superset disassembly` (0 as exact repo name), `superset disassembly in:readme`
  (269): top hits **GrammaTech/ddisasm** (Datalog reassembleable disassembler),
  and the superset/probabilistic tools below. `topic:disassembler` (931): ghidra,
  capstone, etc. — general disassemblers.
- `superset disassembler created:>2026-04-01` (0); `disassembly drift` (1, an
  unrelated Apple II repo); `overlapping instructions disassembly` (1,
  `vikrant-vikram/disasm`, a teaching x86 disassembler, not superset/resync).
- code `"superset" disassembler every offset` (1984; top hit is
  **KennethAdamMiller/superset_disassembler**) and
  `resynchronization disassembly x86 offset` (131; top hits are network-protocol
  dissectors, unrelated).
- Read as data (do **not** kill — all are *rewriting techniques/tools*, none a
  resync-statistics visualization): **utds3lab/multiverse** (superset-disasm
  static rewriter, NDSS'18; needs capstone/pwntools/pyelftools — external deps I
  don't have), **KennethAdamMiller/superset_disassembler** (OCaml probabilistic
  superset disassembler, "no false negatives").

**Paper/web (G-2) — corrected per REVIEW-01 §6.2 (record corrections a/b/c, all
reviewer-verified from the PDFs).** Superset disassembly = "disassemble every
byte offset, no false negatives, many false positives"; a single decode error
"cascades" (the term *disassembly drift* appears in
**Zhao, Yang, Zheng & Quinn, "Exploiting Control-flow Enforcement Technology for
Sound and Precise Static Binary Disassembly" (2025, arXiv 2506.09426)** — its
abstract reports instrumentation speed, not resync statistics; (a) corrected: I
had mislabeled this paper "disassembly drift"). Foundational: **Multiverse**
(Bauman, Lin & Hamlen, NDSS 2018), **Andriesse et al.** (USENIX Security 2016
SoK + ground truth).
**(b) The resync claim is PUBLISHED, not folklore.** **Linn & Debray, CCS 2003,
§3.1 "Self-Repairing Disassembly"** states it, with a worked example (off by
1/2/3 bytes, back in sync within 1–3 instructions) and, verbatim (reviewer-
verified, sha256 f59b0db8…): *"In practice, however, we have found that
disassembly errors usually resynchronize quite quickly — often within just one
or two instructions beyond the point at which the disassembly error occurred."*
It is **qualitative — no distribution, no dataset**. So C09's N2 delta is to
**quantify that 2003 qualitative claim on modern x86-64 binaries, plus the
lattice visualization** — stated as such, not as "first to notice resync".
**(c) Neighbours to distinguish** (reviewer round-4): `UlfKargen/desync-cc`
(Kargén et al., SANER'22 / SCP'23, an *automatic disassembly desynchronization
obfuscator* — offensive; C09 is analysis-only, never generates desync code),
`expend20/shifting-codes-python-port` (desyncs linear-sweep disassemblers —
offensive), and `junxzm1990/x86-sok` (the USENIX Sec'22 disassembly ground-truth
artifact — relevant to C09-4's ground-truth caveat). None is a resync-statistics
lattice visualization. **The N2 delta stands, re-stated honestly.**

**Novel observable.** For a real binary: (1) a rendered lattice (ANSI or emitted
SVG/HTML) showing, per byte offset, the instruction decoded there and where each
misaligned stream **merges** into the true one; (2) a **quantified** distribution
of **resync length** (bytes AND instructions, from the misaligned start to the
first boundary shared with the reference stream) over many functions — the
measured, dataset-backed version of Linn & Debray's 2003 qualitative "1–2
instructions". Machine-checkable: the length decoder is differential-tested at
**every offset** against `objdump -d` per offset (C09-3), ground-truth method
and the stripped-binary caveat stated (C09-4), the viz emitted as parseable
data (C09-5).

**Prototype plan.** A small x86-64 **length decoder** in C (enough of the
encoding to advance correctly — prefixes, ModRM, SIB, disp/imm; it need not
name instructions, only size them), used to decode from every offset; Python
stdlib for the lattice render + resync histogram. `objdump -d` is the
independent oracle for the aligned stream. Files:
`parts/NN-x86-lattice/{AGENTS.md,README.md,RUN.md,Makefile,lendec.c,lattice.py,
resync_stats.py,oracle_objdump.sh}`. Effort: Medium. Risk: the length decoder
must be correct enough that the aligned decode matches objdump on the sampled
functions (differential-tested, R6); scope it to the instruction forms the
sampled binaries actually use, and report coverage honestly.

## Alternate for the P5 slot (benched): C22 — PT TNT-bit control-flow barcode

Kept as the fallback visualization if C09 is rejected: render Intel-PT
taken/not-taken bits as a per-algorithm texture. It **rides P2's capture**
(couples to P2's build risk), which is why C09 (independent) is proposed first.
Reviewer leveled C22 N3 with a short record; a full §2.1+G-2 addendum would
precede any C22 build.
