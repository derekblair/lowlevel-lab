# Reviewer pre-gate prior-art dossier (working notes → feeds REVIEW-01)

These are written before Gate 1, against `research/CANDIDATES.md` (mtime 2026-10-18 22:23:39). The author's NOVELTY-LOG.md and SHORTLIST.md didn't exist yet when I wrote them.

Every claim below cites one of:
- a logged query: `review/evidence/search/presearch-*.log`;
- a file read via `gh api`, with repo, path and commit;
- a reproduced output: `review/evidence/presearch/*`.

Third-party content was read as data and never executed.

## Machine facts that bear on several candidates
- **Three core classes, not two** (`review/evidence/00-core-topology.txt`):
  - P: CPUs 0–3, Cougar Cove, private L2, L3 0–11, 4.7–4.8 GHz.
  - E: CPUs 4–11, Darkmont, two 4-core L2 clusters, L3 0–11, 3.7 GHz.
  - LP-E: CPUs 12–15, Darkmont, own L2, **no L3**, 3.3 GHz.

  CANDIDATES.md treats 4–15 as one class. For anything about coherence or latency (C02 XMC, C05), E and LP-E are different topologies, even though the microarchitecture is the same.
- **PMU event encodings are VERIFIED** from `intel/perfmon` @ 8da58930a226:
  - `PTL/events/pantherlake_cougarcove_core.json`: `MACHINE_CLEARS.SMC` 0xC3/0x04.
  - `PTL/events/pantherlake_darkmont_core.json`: `MACHINE_CLEARS.SMC` 0xC3/0x01 and `MACHINE_CLEARS.XMC` 0xC3/0x80.

  These match CANDIDATES.md lines 22–25.
- **qemu-aarch64 8.2.2 is SMC-coherent** (`review/evidence/qemu-fidelity/`). It can't exhibit stale fetch.
- **perf is absent** from this machine, so any "perf intel_pt" baseline would have to be raw `perf_event_open`.

## C03 pt-truth — the strongest pre-gate threat file

The claim (CANDIDATES.md:96–117): decoders misdecode SMC. The proposed fix is a versioned code image plus in-band `PTWRITE <version>` fences. The stated novelty is "PTWRITE packets as exact code-version fences".

**The problem is VERIFIED.** It's the author's probe `research/probes/pt-smc-misdecode/probe-output.txt`: gdb shows the first call as `mov $0x2` when it actually returned 1. It's also well documented: perf-intel-pt docs say the executed images are needed, "which makes use in JIT-compiled environments, or with self-modified code, a challenge".

**Prior art for version-correct decoding (time- or side-band-keyed), found by me:**
1. **wilvk/asm-test** (created 2026-06-23, 0★, pushed 2026-10-05).
   - `docs/internal/analysis/jit-runtime-tracing.md` and `docs/internal/plans/hardware-trace-plan.md` describe `asmtest_codeimage`: "a userspace `PERF_RECORD_TEXT_POKE` that builds the timestamped code-image timeline", using soft-dirty + PAGEMAP_SCAN + process_vm_readv.
   - They also describe `asmtest_pt_decode_window`, which decodes PT "with a recorder-backed `pt_image_set_callback` (`src/pt_backend.c`)", "the same-address-different-bytes case resolving to the version live at each `when`".
   - The docs say it was "validated whole-window and foreign-pid decode on real silicon" at commit c7b4ef7 (2026-07-21).
   - Found via `code "pt_image_set_callback" self-modifying` (2 hits, both this repo). **It's absent from all 106 of the author's raw gh results** (`grep -l wilvk research/raw/gh/*.json` → none). The author's `"pt_image_set_callback"` query returned 370 hits with no wilvk in its top 10, so this is query design, not selective logging.
2. **Linux perf `PERF_RECORD_TEXT_POKE`** (kernel SMC). In `torvalds/linux tools/perf/util/intel-pt.c`, `intel_pt_text_poke()` invalidates cached decode blocks overlapping the poke and is called on `PERF_RECORD_TEXT_POKE`. That's time-ordered side-band versioning for kernel code.
3. **perf jitdump + `perf inject --jit`**: the author knows this one (CANDIDATES.md:104).
4. **FlowJIT** (Suchakra Sharma, LPC 2017; `github.com/tuxology/flowjit`): a PoC kernel patch that saves JIT'd page copies for PT reconstruction. Source: web search, LPC 2017 session page. The repo hasn't been read yet.
5. A **2018 Univ. of Crete MSc thesis**, "JIT Tracing using Intel Processor Trace" (K. Kleftogiorgos). Same author as `kleftog/streamcfi`, a ptwrite-based repo that hit `ptwrite in:readme`.
6. **JPortal** (PLDI'21) and **libxdc** capture-on-execute (cited in wilvk's analysis; not yet independently read).

**Prior art for in-band PTW annotation (the claimed delta):**
- **DRAKVUF** `tklengyel/drakvuf` @ b2f64d8d73d4, `src/plugins/ipt/ipt.cpp:120–132`: `emit_ptwrite64()` writes a synthetic PTW packet (0x02 0x32 + 8-byte payload) into the trace stream via `ipt_vcpu::annotate()`. That's in-band PTW annotation of side events (CR3/TID per wilvk's description).
- wilvk's recommended pipeline step 4 also says "PTWRITE can inject region markers".

**Reviewer position before the gate: N2 at best → RESHAPE.**
- Version-correct PT decoding of rewritten code exists three times over (kernel TEXT_POKE, jitdump, wilvk userspace).
- In-band PTW annotation exists (DRAKVUF).
- The surviving delta is *using an executed PTWRITE as an exact code-version fence*. It only earns its keep if the prototype **demonstrates a case where time-keyed versioning gets it wrong and the fence gets it right**. Example: a patch followed by execution of the patched code within one timing-packet quantum (MTC/CYC granularity), or several versions inside one quantum.
- Without that observable it's N1: one more versioning mechanism.
- Also required: cite all of the above in NOVELTY-LOG and the README.

## C04 hybrid-diff — UPDATE ~02:33 PDT (from gh-log UTC stamps): published prior art found (libLISA), novelty collapses to N1

**libLISA**: Craaijo, Verbeek, Ravindran, *"libLISA: Instruction Discovery and Analysis on x86-64"*, OOPSLA 2024 (PACMPL 8:283, DOI 10.1145/3689723). I read the PDF itself (sha256 prefix b3bee6a9f2b1bf82); excerpts are in `review/evidence/presearch/C04-liblisa-excerpts.txt`.

What the paper establishes:
- **Lines 1002–1017.** It analyses the Intel i9-13900's **performance cores (𝐴2, Raptor Cove) and efficiency cores (𝐴3, Gracemont) as separate architectures**, alongside the AMD 3900X/7700X and a Xeon 4110. That's about 118k instruction groups per architecture.
- **§5.3.1 (lines 1240–1262).** Its group 1 ("bit shifts, rotates, multiplication, division and bit manipulation instructions") **distinguishes 𝐴3 from 𝐴2**. The paper explicitly discusses building **fingerprinting programs** from these differences.
- **Lines 60–72 and 96–101.** Its motivating example is `rcl` followed by `jno`: the undefined OF of a rotate, used to "behave benign on an AMD Ryzen R9 3900X but behave maliciously on an Intel Core i9-13900".
- **What it doesn't cover:** I grepped for migrat|schedul|thread|affinity and found nothing relevant. The *in-process migration hazard* (one thread's flags change when the scheduler moves it) is not discussed.

Neighbours (2026, all post-cutoff):
- `kmx00/ub86-pred` (2026-06-07). An obfuscation demo: its `devdocs/plans.md` uses undefined effects to predicate control flow so as to break "control flow recovery of analysis tools"; it has a `use-affinity` P/E split and cites libLISA and the Denuvo UB abuse.
- `dominicolucci/dift86` (2026-09-23). Silicon-vs-Unicorn/QEMU differential with "two clean undefined-flag laws", per-CPU JSON, on homogeneous Xeon only.
- `Yazan2314/x86-validation-tool` (2026-09-27). Unicorn vs native.
- Also sandpile flags tables and SingleStepTests/80386.

**libLISA appears in none of the author's 106 raw gh results.**

**Position:** N1. The phenomenon (P-core vs E-core undefined-flag divergence, shifts and rotates included) is published, so the new chip generation is a qualifier, not a frame.
- Only delta left: a demonstrator of the **migration hazard** (same process, same instruction, flags change across a scheduler migration). That's N2 at most.
- Safety: it sits next to two documented misuses, libLISA's own "fingerprinting"/"malicious" framing and ub86-pred's anti-analysis predicates. Any build would have to be framed as a hazard plus mitigation (don't consume undefined flags; emulators, JITs and record-replay must mask them). No detector, no predicate library, no "behaves differently per core" demo.
- Leaning: **CUT**, or RESHAPE only on those terms.

## C04 hybrid-diff — (original pre-update notes)

**The author's probe is VERIFIED by my independent re-run** (`review/evidence/presearch/C04-uflags-repro.txt`):
- I copied the sources (sha256 recorded) and ran them on CPUs 0, 2, 3, 4, 9, 11, 12 and 15.
- P {0,2,3} hashes are identical to each other. E {4,9,11} and LP-E {12,15} are identical to each other.
- P and E differ on shl, shr8, shld16, shrd16, rol and rcl8. `rule.c` output is byte-identical to the author's.
- Content: the OF of multi-bit shifts and rotates (architecturally undefined for count ≥ 2) follows a "first-step" rule on Cougar Cove and a "last-step" `MSB(res)^CF` rule (shl/rol), or OF=0 / ror-style (shr/ror), on Darkmont.

**Prior art:**
- Cross-generation undefined-flag differences are folklore. Example: the 2006 report of Core Duo vs Pentium 4 shift OF (factor-language blog mirror), dismissed as "undefined, not a bug".
- My web searches found **no documentation of a same-die P-vs-E divergence**.
- My GitHub queries for C04 are in batch 2.

**Safety framing to watch.** Undefined-flag discrepancies are a classic way to tell emulators from real silicon (anti-analysis "red pill" checks). C04 has to stay framed as a correctness and migration hazard: same binary, different flags after the scheduler moves a thread. It must not be framed or packaged as an environment detector. As a migration-hazard study it's benign.

## C01 stale-fetch
- **Prior art (author already aware):**
  - Simner et al., ESOP 2020 ("ARMv8-A System Semantics: Instruction Fetch in Relaxed Architectures"), with operational and axiomatic models.
  - **RMEM** runs self-modifying tests under "Instruction Fetch" with relaxed fetching and IDC/DIC off, giving "the weakest semantics" (web: cl.cam.ac.uk/~pes20/iflat/ and an rmem guide).
  - Arm FVP `cache_state_modelled` (author STATUS 22:23).
- **My GitHub record:**
  - `"instruction cache" aarch64 emulator in:readme` → 49 results: generic emulators, nothing adversarial.
  - `code "IC IVAU" stale emulator` → 83 results: real JIT flush code (erlang BEAM JIT, dynarmic users), no adversarial models.
  - `isla ifetch` → 0 (repo search).
- **Pre-gate position:** N2 → RESHAPE, which the author already plans ("sanitizer framing"). The delta: a lightweight whole-program user-mode emulator that runs a real JIT pattern and names the missing maintenance step. Litmus-scale tools and the full-system proprietary FVP don't cover that. My batch 2 checks for an existing "icache sanitizer".
- **Batch 2 (02:26–02:30 PDT; log stamps 09:26–09:30Z):**
  - `icache sanitizer` → 0 and `cache maintenance checker arm` → 0 (repo search). No sanitizer found.
  - **herdtools7 @ 12690a83da** has `catalogue/aarch64-ifetch/` (README: "`herd7 -variant ifetch`" simulates the tests, and "`litmus7 -variant self`" runs them on hardware at EL0, or EL1 via kvm-unit-tests). So the Arm/Inria tooling both simulates and *hardware-tests* ifetch, at litmus scale.
  - **DynamoRIO** `core/dispatch.c:958–968` (AArch64): "Software cache consistency: we are handling an IC IVAU instruction". In that mode DynamoRIO's code-cache invalidation is keyed on the app's IC IVAU, so a missing IC IVAU leaves stale translated code. That's a real tool that behaves "adversarially" by accident, though it diagnoses nothing.
  - `"cache_state_modelled"` → 2284 code hits, all FVP launch configs (zephyr, TF-A, OP-TEE).
- **Position unchanged:** N2 → RESHAPE to a sanitizer that **names the missing step** (DC CVAU / DSB / IC IVAU / DSB / ISB, plus the CTR_EL0 line-size and IDC/DIC handling). It must cite RMEM, herdtools7 aarch64-ifetch, Arm FVP `cache_state_modelled`, and DynamoRIO's software cache-consistency mode.
- **Oracle note:** qemu is coherent, so it's a valid "coherent mode" oracle, and its agreement with the emulator's coherent mode can be tested.

## C02 smc-observatory
- **Hits so far:**
  - `clamchowder/Microbenchmarks` matched `"self-modifying" benchmark in:readme`, but its README mentions SMC only as something it avoids ("to avoid crazy stuff like self modifying code"). None of its 360 tree paths is SMC-related. **Not prior art.**
  - `"cross-modifying" in:readme` (15) → libraries that *do* XMC safely (backtrace-labs/dynamic_flag, appnexus/acf), the 2017 Ryzen segfault test, and an educational dual-P54C computer. None maps cost.
  - `code "machine_clears.smc"` (16128) → event tables only.
- **The literature gives a figure, not a map:** ~100 cycles per SMC clear (arXiv 2308.14185, semi-static conditions).
- **A falsifiable hypothesis is available:** Intel's documented guidance to avoid writing within the same 1-KB subpage being executed, or fetching from the 2-KB subpage being written. My web search didn't fetch the exact manual wording yet, so this stays [recall] until fetched. A distance sweep per core class tests it directly.
- **The hypothesis is VERIFIED from the primary source.** Intel 248966-050US (pdf sha256 prefix 4da42303a8d82a0b):
  - §3.6.8 Rule 50: "make sure the code that performs the modifications and the code being modified are on separate 4-KByte pages or on separate aligned 1-KByte subpages".
  - §3.6.8.1: "Software should avoid writing to a code page in the same 1-KByte subpage that is being executed or fetching code in the same 2-KByte subpage of that is being written. In addition, sharing a page containing directly or speculatively executed code with another processor as a data page can trigger an SMC condition causing the entire pipeline of the machine and the trace cache to be cleared."

  The text dates from the Pentium 4 era (it mentions the trace cache). Whether 1 KB / 2 KB is still the detection granularity on Cougar Cove and Darkmont is a falsifiable, unanswered question, and a good novel observable.
- **Academic neighbour (batch 2):** Botacin, Zanata, Grégio, *"The Self Modifying Code (SMC)-Aware Processor (SAP): A security look on architectural impact and support"* (J. Computer Virology and Hacking Techniques). Repo `marcusbotacin/Self-Modifying-Code` @ ed09a3abd6 has a PIN-based flush-aware cache simulator, a PEBS-based SMC detector (Windows driver) and SMC examples. That's architectural-impact measurement with a security framing. It has no per-core-class map and no distance sweep. Must be cited.
- `code patching latency` → 15 results and `jit patching benchmark` → 0: noise and nothing. `"MACHINE_CLEARS.XMC"` → 236 code hits, all event tables.
- **Pre-gate position:** N3 looks plausible.
  - Measurement claims must follow REVIEW-00 §1.18.
  - E and LP-E must be distinguished.
  - The XMC counter is E-core-only, so asymmetric observability has to be stated.

## C06 reversible-jit
- My queries found no reversible-ISA JIT:
  - `pisa simulator reversible` → 0;
  - `reversible language compiler x86` → 0;
  - `reversible machine code` → 12, unrelated except `BenKnill/lattice-echo` (2026-09-26, a reversible lattice map with HOL Light-verified AArch64 code — a specific program, not an ISA or JIT).
- Academic prior art on *generating inverse code* exists and must be cited:
  - Akgul & Mooney, assembly-level reverse execution via reverse code generation;
  - reverse computation for optimistic PDES (Carothers, Perumalla, Fujimoto 1999);
  - Backstroke (2011, source-level).

  These are [recall], to verify by web search.
- **Pre-gate position:** N2–N3. The delta ("an exactly invertible ISA makes the inverse stream mechanical, at native speed") is real but has to be argued against reverse code generation.

## C12 quine-relay-isa
- Single-ISA ELF quines exist (`fishilico/synacktiv-winter-chall-2025-quinindrome`, `meithecatte/mips-quine`). Source-level relays exist (`mame/quine-relay`; `Zushah/quine`, 2026-04: Assembly→C→Rust…).
- My searches found **no cross-ISA machine-code relay**:
  - `polyglot elf multi architecture` → 0;
  - `assembly quine arm64` → 0;
  - `quine relay assembly` → 1 (source-level).
- Now runnable with qemu-aarch64. N3 likely. Learning value is medium.

## C22 tnt-barcode
- `branch trace image visualization`, `intel pt visualizer` and `control flow fingerprint image algorithm` → all 0 (repo search only — weak). Code/web search pending (batch 2).

## Batch-2 additions for the remaining candidates (2026-10-19 02:26–02:30 PDT per log stamps)

- **C03:** `tuxology/flowjit`, created 2016-11-18: "Kernel patch for hardware trace reconstruction of runtime compiled code". FlowJIT exists on GitHub. `jit tracing intel pt` → 0.
- **C05 silicon-corewar:**
  - `radareorg/r2wars` (64★): "Corewars but within r2", with real-ISA warriors run in radare2's ESIL emulator.
  - CodeGuru Xtreme lineage: `codeguru-il/corewars8086-survivors`, `shooshx/corewars8086_js`, `maorrado/corewars8086-lab` (2026-09).
  - `corewar x86-64` → 0.
  - The native-cores delta survives (N2–N3), but the claim that every Core War runs on an emulated VM must cite r2wars and corewars8086.
  - Outcome claims are inherently nondeterministic, so they fall under REVIEW-00 §1.18.
- **C06 reversible-jit:**
  - `reversible jit` → 0.
  - `brkmnd/Jnsc` compiles Janus to the reversible Bob ISA. `mbudde/jana` and `yokoyama-lab/PyJanus` (2026) are interpreters.
  - Inverse-code generation for *irreversible* ISAs is verified 20+ years old: Akgul & Mooney (GT TR GIT-CC-02-49, PASTE'02, ICSE'04, PhD 2004; PowerPC assembly-level reverse execution by generating a reverse program) and Koju et al. (VEE'05, "generating an inverse program").
  - Position: N2. The delta is that an exactly reversible ISA makes inversion mechanical and garbage-free, and the JIT runs both streams natively. The README must argue against RCG.
- **C07 isa-hop:**
  - `arm64ec` → 51 results. Real-world mixed ISA in one process: Windows ARM64EC / CHPEv2, analysed in `FFRI/ProjectChameleon`, and implemented in Wine + FEX ARM64EC.
  - Plus box64/FEX thunks, and Popcorn/Unifico (the author is aware of those).
  - Position: N1–N2, the educational in-process hop at block granularity being the only delta.
- **C12 quine-relay-isa:**
  - `quine aarch64` → 1 (`quine-build/quine-target-aarch64`, a compiler backend, unrelated). `binary quine x86-64 elf` → 0, `polyglot elf multi architecture` → 0, `assembly quine arm64` → 0.
  - Position: N3 likely. It's now executable via qemu-aarch64, with an exact-bytes fixed-point oracle (`cmp`).
- **C15 rep-probe:** `rep movsb microcode` → 0. The code hits are rr syscallbuf and cosmopolitan ape.S, which use rep movsb but aren't about progress granularity. Raymond Chen's 2025 post is the author's citation. N3 plausible, small.
- **C22 tnt-barcode:** `processor trace visualization` → 87, generic tracing UIs (Paraver etc.), nothing PT-TNT. Code search was noise (184452). N3 plausible. It depends on C03's capture working.

## C02 reviewer reference measurement (2026-10-19 02:39 PDT; oracle for the C02 build gate — NOT a substitute for the author's study)
Probe source: `review/evidence/presearch/c02-probe/smcprobe.c` (benign own-process store near a 6-byte `mov eax,0; ret` at page offset 0, 200k iterations, unprivileged perf_event_open raw events from intel/perfmon PTL @8da58930a226). Raw: `c02-probe/output.txt` (single runs), `c02-probe/sweep.txt` (3 runs each).
- **Feasibility VERIFIED:** perf_event_paranoid=2 permits user-only counting of MACHINE_CLEARS.SMC on both cpu_core (0x04c3) and cpu_atom (0x01c3).
- **Clear counts deterministic across 3 runs:** P (CPU0): 2.000 clears/iter only when the store is in the code's own 64-B line; 0 for store offsets 64..2048. E (CPU5) and LP-E (CPU13): 1.000 clear/iter for store offsets 6..512 (same aligned 1-KB subpage), 0 at ≥1024.
- **=> Intel 248966 §3.6.8.1's "1-KByte subpage" rule matches Darkmont exactly and does NOT match Cougar Cove (64-B line granularity).** Cost (TSC ticks/iter, 3 runs): P in-line 730–1303; E in-line 612–802, same-1KB-other-line ~181; LP-E in-line 1170–1435, adjacent-line 1249–1388, 128–512 B ~145. P=2 clears vs E=1 clear per iteration for the identical pattern is itself an asymmetry to explain.
- Consequences for REVIEW-01: C02 has a concrete, falsifiable, reproducible novel observable available; its build must (a) distinguish E (4–11) from LP-E (12–15), (b) report granularity per class against §3.6.8.1, (c) treat timing per REVIEW-00 §1.18. Reviewer will hold the C02 build's counts to these reference values (clear counts must match exactly for the same pattern; timings within an order of magnitude).

## C10 mirror — prior art found 2026-10-19 02:42 PDT (author's pre-gate NOVELTY-LOG claims N3, citing only attack uses)
- **gperftools** @635500ed68 `src/base/single_stepper.{h,cc}` (2024): `SingleStepper::Start` "intercepts SIGTRAP and enables single-stepping (in currently running thread). On ~each instruction given callback will be invoked with signal's ucontext" (h:43-45); sets `gregs[REG_EFL] |= kTF` (cc:79), `kTF = 0x100` (cc:61); used by `src/tests/tcmalloc_unittest.cc`. Benign, production-grade in-process TF stepper with per-instruction callback.
- Also via `code "gregs[REG_EFL]" "0x100" SIGTRAP` (356): v8 `src/sandbox/trap-fuzzer.cc`; ERESI `libe2dbg` (in-process embedded debugger; `code "REG_EFL" "|= 0x100"`, 93); Linux selftest `tools/testing/selftests/x86/single_step_syscall.c`; jwhitham.org 2016 "x86 single step mode - how slow is it?" (web).
- **Technical issue (observer effect):** each TF trap is an exception delivery, which serialises execution; a self-single-stepped program therefore always executes freshly written bytes — TF tracing *masks* the model-specific "how far ahead of the execution pointer" SMC window (Intel SDM Vol 3A "Handling Self- and Cross-Modifying Code"). C10 can show *architectural* SMC (the listing changes) but cannot show microarchitectural SMC behaviour; any claim otherwise is FALSE by construction.
- **Position:** N1–N2 (mechanism mainstream; delta = the self-rendering visualisation). Weakest of the author's five.

## Addendum pre-search — likely replacements (2026-10-19 02:58 PDT; web only, leaving the gh budget to the author)
- **C12 quine-relay-isa:** web "cross-architecture quine relay machine code …" → no relay found. Nearest: `ixty/xarch_shellcode` (2016) = multi-arch **polyglot shellcode** (x86/x86_64/arm/arm64 via "polyglot dispatching shellcode") — exploit-adjacent technique; Microsoft ARM64X fat binaries (loader mechanism, oldnewthing 2026-08-14). **Safety marker for any C12 addendum:** a *relay* of separate per-ISA ELFs printing the next stage to stdout is benign; a single-file multi-ISA *polyglot* drifts toward shellcode technique → not acceptable.
- **C22 tnt-barcode:** **HeNet** (arXiv 1801.02318, 2018): Intel PT control-flow traces converted to "a time-series of images generated from control flow trace of an execution" via "a lightweight image conversion and segmentation of the control flow trace", for DL exploit detection (abstract, fetched). → "PT trace as image" exists; C22's delta (human-readable per-algorithm TNT textures, educational) is **N2**, not N3. Also PTrix (arXiv 1905.10499, PT fuzzing bitmaps) — coverage bitmaps, not images.
- **C09 x86-lattice:** web → no visual/statistical resync explainer found; self-repairing disassembly is documented (US patent 11263065 text; Linn & Debray 2003; NDISASM sync points). N2 (technique known; viz+stats explainer is the delta).

## P2 surviving-delta check — is executed PTWRITE-as-code-version-fence already proposed? (2026-10-19 07:23 PDT)
- web (extended) "PTWRITE JIT compiler code generation marker processor trace decode generated code versions" → nothing PTWRITE-specific.
- **intel/libipt#57** (2019, .NET JIT decode): maintainer Markus Metzger's answer is the *time-keyed sideband* route — "If memory is reused, you would need timestamps in your map files and extend the sideband decoder to add the mappings at the appropriate time during decode." No in-band fence suggested.
- **intel/libipt#21** (2017): a self-modifying-code user's workaround = "remove and re-add a section periodically" / request to read instructions from memory (→ today's `pt_image_set_callback`); `ptwrite` appears only in the maintainer's IP-filter example.
- GitHub issue search: `ptwrite "self-modifying"` → 1 (#21 above); `ptwrite jit` → 47, none relevant (WAMR/IREE/numba noise).
- **Conclusion:** consistent with REVIEW-01 §2.2 — the executed-PTWRITE fence is unproposed in the places it would most likely appear; N2 delta stands, conditional on the P2-3 head-to-head.

## P2 capture feasibility — VERIFIED (2026-10-19 07:23 PDT)
Probe `review/evidence/presearch/p2-ptw-probe/ptwprobe.c` (own-process, user-only): perf_event_open(type=intel_pt, config = pt|branch|ptw[|fup_on_ptw]), data+AUX mmap, 4× `ptwrite` with magic payloads. Output (`p2-ptw-probe/output.txt`, 4 runs): **4/4 PTW packets with the magic payloads, in order**, hdr `02 32` (no FUP) / `02 b2` + 3-byte FUP (fup_on_ptw). → unprivileged PTWEn works at perf_event_paranoid=2; P2's capture path is feasible. **Oracle for BUILD-02:** the author's capture must show its version payloads as PTW packets in program order.

## Round-4 pre-search for the announced replacements (2026-10-19 07:27 PDT; `search/presearch-queries-4.tsv`, logs presearch-C09/C12.log)
- **C12:** `"quine" in:readme aarch64 x86-64` → 27, none a cross-ISA relay (languages/engines/noise); `ouroboros binary architectures` → 0; code `quine "EM_AARCH64" "EM_X86_64"` → 0. Still N3-plausible; safety marker from round 3 stands (relay of separate ELFs to stdout, never a polyglot).
- **C09 neighbours (offensive side of the same mechanism):** `UlfKargen/desync-cc` @14b80a1a63 — "Automatic Disassembly Desynchronization Obfuscator", gcc drop-in with "opaque predicates … fake jump into the middle of an instruction" (README:1–5); `expend20/shifting-codes-python-port` (2026-02) — "Injects crafted x86 inline assembly that desynchronizes linear-sweep disassemblers" (README:40). **Academic/defensive:** `junxzm1990/x86-sok` @23679a5e4f (USENIX Security '22 artifact; reports overlapping-instruction counts), Linn & Debray 2003, superset disassembly (NDSS'18), probabilistic disassembly (ICSE'19).
- **Safety line for a C09 addendum:** analysis/visualisation of *natural* x86 self-synchronisation over existing binaries = benign; any component that *generates* desynchronising code, opaque predicates, or "anti-disassembly" transforms = [BLOCKING] (REVIEW-00 §2.4: hindering analysis).

## P4 context — Linux already mitigates the CTR_EL0 line-size-mismatch class (2026-10-19 07:29 PDT)
`torvalds/linux arch/arm64/kernel/cpu_errata.c`: capability "Mismatched cache type (CTR_EL0)" (`ARM64_MISMATCHED_CACHE_TYPE`), `.matches = has_mismatched_cache_type` ("make sure that all the CPUs in the system expose a consistent CTR_EL0 to make sure that applications behaves correctly with migration"), `.cpu_enable = cpu_enable_trap_ctr_access` → EL0 CTR_EL0 reads are trapped and answered with the system-safe value. Excerpt in `C01-priorart-excerpts.txt`. **Implication for BUILD-04 (README honesty, R-level nit unless overclaimed):** the big.LITTLE flush-stride bug class is historically real (Mono 2016 era) and still modelable, but on current Linux/arm64 it is OS-mitigated; the README must say so rather than present it as a live Linux hazard.
