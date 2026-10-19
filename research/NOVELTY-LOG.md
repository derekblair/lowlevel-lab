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
| C03 | version-correct PT decode of SMC | **N3** | **SHORTLIST #2** | simple-pt ("Tracing JITed code is not supported"); libipt live-image only; JPortal (JVM side-band) |
| C04 | P-core vs E-core differential scanner | **N3** | **SHORTLIST #3** | yufengzjj/hybrid-x86-oracle (diffs *model backends*, NOT the two core types of one die); sandsifter/vmsifter (one core) |
| C05 | native Core War on real cores | N2 | alternate (safety) | r2wars (ESIL VM, multi-arch, *emulated*); pMARS/corewar.io (VM). Native-on-cores unseen but sandbox burden high |
| C06 | reversible ISA, bidirectional native JIT | **N2** | cut (for C01) | kostyk348/phase-vm *emits phase_fwd/phase_rev C, cc -O2 -shared + dlopen* = reverse native codegen already |
| C07 | in-process x86↔A64 hop | N2 | cut | systems-nuts/unifico, ssrg-vt/popcorn-* (research, cross-machine); core idea exists |
| C08 | AArch64 encoding-space atlas | **N0** | cut | zyedidia/armvis = A64 Hilbert-curve atlas by instr class, exactly this |
| C09 | x86 superset-decode lattice + resync stats | N2 | alternate | utds3lab/multiverse, KennethAdamMiller/superset_disassembler (technique exists; viz/stats explainer doesn't) |
| C10 | program single-steps & renders itself (TF) | **N3** | **SHORTLIST #5** | sgx-step/rosenbridge use TF for *attacks*; no benign self-tracing SMC visualizer found |
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

**Shortlist #4 is C01-reshaped (ifetch-sanitizer), ARM64.** Rationale for
the final five and the cut consistency check is in
[SHORTLIST.md](SHORTLIST.md).

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

## C03 — version-correct PT decode of self-modifying code → **SHORTLIST #2** (N3)

**Pitch:** Intel-PT decoders reconstruct the instruction stream from the
code bytes *currently* in memory, so self-modifying code is silently
misdecoded. Keep a versioned code image and emit an in-band `PTWRITE
<version>` at each code write, so the decoder re-bases on the exact version.

**Phenomenon already proven on this box** (research/probes/pt-smc-misdecode/):
a program prints `v1 returned 1`, but gdb's own PT instruction-history for
that same execution shows `mov $0x2,%eax; nop×4; ret` — the *post-patch*
bytes — with no gap or warning. So "PT misdecodes SMC" is demonstrated, not
asserted.

**Closest threats (read as data):**
- **andikleen/simple-pt** (★359, read README + `sptdecode.c`): a full PT
  tracer/decoder. README verbatim: **"Tracing JITed code is not supported."**
  It decodes `ptev_ptwrite` payloads but uses them as opaque logged values,
  **not** as code-version fences. Confirms the gap, does not kill.
- **intel/libipt** (read `pt_image_set_callback.3.md`): the decoder reads
  instruction bytes through an image callback — i.e. from live memory or a
  static image; there is no versioned-image-over-time facility. LLDB's
  wrapper (per web search) "does not handle self-modified code… only signals
  the anomaly as a trace error". Confirms gap.
- **JPortal** (PLDI'21, web): recovers JVM JIT control flow from PT but via
  **side-band** jitdump-style maps, not in-band PTWRITE version fences.
  hase-project/hase, OctopusTakopi/trace-mcp, ptgraph2 (read/greased):
  function-call timelines / record-replay, none version-aware for SMC.
- `gh search repos intel pt self-modifying` → 0; `topic:intel-pt` → 5, none
  SMC-aware (records C03-*.json). PTWRITE code hits are GCC/NASM tests and
  PS4SDK intrinsics, not version fences.

**N3, KEEP.** Novel observable: our decode is correct where gdb/libipt are
wrong, verified instruction-for-instruction vs single-step ground truth.
**Build risk (disclosed):** PT AUX capture + packet decode is the hardest
build of the five; the gdb probe de-risks the *claim* even if the from-scratch
decoder is reduced in scope. **C22 (TNT-bit barcode) rides this capture as a
visualization bonus.**

## C04 — P-core vs E-core differential scanner → **SHORTLIST #3** (N3)

**Pitch:** run identical instruction candidates pinned to a P-core and an
E-core and diff every observable — legality, length, result, *architecturally
undefined* flags, CPUID — on one die with two microarchitectures behind one
ISA.

**A real divergence is already in hand** (research/probes/hybrid-undefined-flags/,
probe-output.txt): for shift/rotate counts ≥ 2, the **architecturally
undefined OF flag differs between core types** — P-cores (Cougar Cove)
compute OF by a "first-step" rule, E-cores (Darkmont) by a "last-step" rule;
`SAR` agrees, results agree. So the concept's payoff ("do the two core types
disagree on undefined behaviour?") is **demonstrated**, not hoped-for.

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

**N3, KEEP strong.** Novel observable already captured; the build turns the
probe into a systematic scanner with the yufengzjj oracle as a tie-breaker
for "which core (if either) matches the SDM/formal model".

## C10 — program single-steps & renders itself → **SHORTLIST #5** (N3)

**Pitch:** an x86-64 program that sets its own trap flag (no ptrace, no child),
records every instruction from its SIGTRAP handler, and renders its own
execution — including its own self-modification — as a terminal animation.

**Threats:** repo searches `trap flag single step tracer`, `self-tracing
program`, `sigtrap single step in-process`, `eflags tf single step` →
total_count 0 (records C10-*.json). Code search for the TF bit + SIGTRAP
(`"REG_EFL" 0x100 SIGTRAP`) surfaces **sgx-step** and **rosenbridge** — TF
single-stepping used for **enclave attacks / backdoor fuzzing**, a different
purpose, and ptrace/driver-based besides. No benign *self*-tracing
visualizer, and none that shows the listing mutating under SMC. **N3, KEEP.**
Clean, low-risk, pure stdlib + inline asm; verifiable against gdb's trace as
an independent oracle. ARM-neutral (x86), but balances the ARM64-heavy C01.
Benign per REVIEW-00 §2.4 (own-process, educational).

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
