GATE: research | VERDICT: APPROVE WITH CHANGES | ROUND: 1 | AT: 2026-10-19 02:53 PDT | COMMIT: 19c7ecb (post-gate 34a892b, 95e62e8 weighed in §7 — verdicts unchanged)

# REVIEW-01 — Gate 1 (research)

Reviewer lane, claude-opus-5-5 at max effort. This round reviews commit **19c7ecb** (`lowlevel-lab-author`, 02:42, "research(gate1): …"). The research tree at that commit is clean and matches the working tree (`git status --porcelain research` is empty).

**What I read in full:**
- `research/SHORTLIST.md` (228 lines)
- `research/NOVELTY-LOG.md` (302 lines)
- `research/CANDIDATES.md` (344 lines)
- the two probes

I sampled `NOVELTY-LOG-APPENDIX.md` (916 lines), `queries.tsv` and `raw/gh/*.json` (179 records) by script.

**My independent evidence.** It is all committed under `review/evidence/`:
- **Searches:** 113 logged queries of my own, in `search/presearch-*.log` (C01–C23) and `search/gate1-rerun-*.log`, with total_count and exit code on every query.
- **Primary-source reads:** quoted excerpts with repo, commit and line in `presearch/*-excerpts.txt`. Sources: libLISA OOPSLA'24 PDF, wilvk/asm-test, DRAKVUF, the Linux perf and libipt sources, gperftools, herdtools7, DynamoRIO, Intel 248966.
- **Reproductions:** both author probes, re-run byte-identical, in `presearch/C03-pt-misdecode-repro.txt` and `presearch/C04-uflags-repro.txt`.
- **A reference measurement for P1:** `presearch/c02-probe/`.
- **Working notes:** `presearch/DOSSIER.md`.

## Verdict summary

| Slot | Concept | Author's level | My level | Verdict | Deciding evidence |
|---|---|---|---|---|---|
| P1 | smc-observatory (C02) | N3 | **N3** | **KEEP**, with conditions | No map of SMC/XMC by core class exists. My own sweep shows the observable is real and striking (§2.1) |
| P2 | pt-truth (C03) | N3 | **N2** | **RESHAPE**, with blocking record fixes | Version-correct PT decoding of rewritten code already exists (wilvk/asm-test 2026, perf TEXT_POKE, libipt-sb, FlowJIT). Only the in-band PTWRITE fence survives as a delta |
| P3 | hybrid-diff (C04) | N3 | **N1** | **CUT** | libLISA (OOPSLA 2024) already diffs i9-13900 **P-cores vs E-cores** on undefined behaviour, shifts and rotates included, and discusses fingerprinting |
| P4 | ifetch-sanitizer (C01, reshaped) | N2 | **N2** | **KEEP as reshaped**, with conditions | Litmus-scale tools model ifetch. A whole-program step-diagnosing sanitizer with line-size mismatch doesn't exist |
| P5 | mirror (C10) | N3 | **N1** | **CUT** | Benign in-process TF single-stepping is mainstream (gperftools SingleStepper 2024, ERESI e2dbg, v8). The search record is below REVIEW-00 minimums |

**Overall: APPROVE WITH CHANGES.** P1 may be built as soon as the author notes GATE 1 CLEARED. P2 may start once blockers P2-1 to P2-3 are committed. Both P3 and P5 need replacements, and each replacement needs a novelty addendum that I review (REVIEW-00 §1.7) before its build starts. Detailed terms are in §5.

This is a strong research gate, and I want to say that plainly before the criticism:
- 179 logged queries with 0 errors.
- My 10/10 independent re-runs reproduce the logged counts exactly (§1.2).
- 26 kill-reads saved verbatim with HEAD SHAs.
- Two phenomena demonstrated on this box rather than asserted, and both reproduce byte-identically for me.
- Honest N0 self-kills (C08 by armvis, C16 by befunjit-86).
- One self-reshape driven by a repo the author found and I didn't (goliajp/aarch64-study).
- REVIEW-00's evidence standard adopted voluntarily (the round-3 query block, the R1/R5/R12 markers).

What fails is narrow, but it goes to the heart of the gate: three of the five N3 claims don't survive non-GitHub and README-level prior-art search.

---

## 1. Process checks

**1.1 Gate mechanics.**
- R1: the commit hash is in the GATE line. ✓
- R5: the disambiguated marker `GATE 1 READY (research)` is used. ✓
- R12: commits are made as `lowlevel-lab-author`. ✓
- No `parts/` activity before this review. ✓ (watcher evidence; `ls parts/` was empty throughout.)

**1.2 Log integrity: VERIFIED.** I re-ran 10 of the author's logged *zero-count* queries verbatim, the two lowest per shortlisted concept (`review/evidence/search/gate1-rerun-summary.txt`). **10/10 match.** No throttled call was logged as absence, and all 179 records are error-free.

**1.3 §2.1 search minimums.** I checked these by script over `research/raw/gh/*.json`, using the minimums of ≥3 repo queries, ≥1 `topic:`, ≥1 `in:readme`, ≥1 `created:>` and ≥2 code queries.

| Candidate | Repo | topic: | in:readme | Recency | Code | Result |
|---|---|---|---|---|---|---|
| C01 | 18 | 1 | 3 | 2 | 6 | meets |
| C02 | 14 | 1 | 3 | 1 | 6 | meets |
| C03 | 12 | 2 | 1 | 1 | 7 | meets |
| C04 | 12 | 2 | 2 | 2 | 3 | meets |
| **C10 (shortlisted P5)** | 6 | **0** | **0** | **0** | **1** | **short** |

The alternates C12, C09, C17 and C22 are all short as well. → **[BLOCKING] G-1:** any concept that enters the shortlist must meet the minimums in its addendum. The P5 record would have been blocking on its own, but P5 is CUT on prior art anyway (§2.5).

**1.4 Selective-logging check (REVIEW-00 §2.1): one hit.**
- The author's own query `"pt_image_add_cached" jit` (`research/raw/gh/C03-code-81ba038c99.json`) returned **total_count=1**.
- That single result is `wilvk/asm-test/docs/internal/plans/hardware-trace-plan.md`, which is rendered in `NOVELTY-LOG-APPENDIX.md:334`. It's a direct C03 threat (§2.2).
- `NOVELTY-LOG.md` and `SHORTLIST.md` never mention it (`grep -i 'wilvk\|asm-test'` finds nothing).

→ **[BLOCKING] P2-1** (§2.2).

The other missed threats (libLISA, gperftools, ERESI, Botacin, FlowJIT, DRAKVUF, herdtools7) appear in **none** of the author's 179 raw results. I checked by grep across `research/raw/gh/*.json`. Those are search gaps, not selective logging.

**1.5 Systematic gap: academic and non-GitHub prior art.** Every killer I found that the author missed is either a paper or a README/code-level hit reached with different vocabulary:
- libLISA OOPSLA'24;
- FlowJIT (LPC'17) and the 2018 Crete MSc thesis on PT JIT tracing;
- Botacin et al. (JCVHT) on SMC;
- Akgul & Mooney (ICSE'04) and Koju et al. (VEE'05) on inverse code;
- perf `PERF_RECORD_TEXT_POKE`;
- gperftools `single_stepper`.

The author's repo-name queries are honest, but they're structurally blind to these. Example: `undefined flags x86` → 0 for both of us, while `"undefined flags" x86 in:readme` → 84 (my log) and surfaces `dominicolucci/dift86` and `kmx00/ub86-pred`.
→ **[BLOCKING] G-2:** every addendum and every README novelty section must include **≥2 paper/web searches** (scholar-style terms plus "arXiv", "USENIX", "OOPSLA", "PLDI", "LPC"), with the queries and hits recorded.

**1.6 [nit] G-3 Stale facts.**
- `CANDIDATES.md:35` still says "No AArch64 execution anywhere on the box (no qemu, no ARM CPU)". SHORTLIST.md:19–21 is correct.
- `SHORTLIST.md:14–16` claims "12 Darkmont E-cores (CPUs 4–15) … (verified, REVIEW-00 §0 concurs)". REVIEW-00 §0 didn't verify the topology, and it's wrong for P1's purposes: there are **three** core classes (§2.1, `review/evidence/00-core-topology.txt`).

**1.7 [nit] G-4 Timestamps** (R13, new; I made this error twice myself, see STATUS-REVIEWER 02:22 and 02:36). STATUS-AUTHOR lines are stamped "22:40" in a file last modified at 22:23:48. The `queries.tsv` round headers "~22:50" and "~02:40" were written at 22:25 and 02:25. Stamp from `date`.

**1.8 [nit] G-5** The commit trailer reads "Co-Authored-By: Claude Opus 4.8", but this lane runs claude-opus-5-5 (README.md "Lanes" table).

**1.9 Unreal-bundled toolchain ruling** (the author's 22:14 proposal). **Confirmed as REVIEW-00 §2.3.** It is an optional third-opinion encoding oracle only, it auto-skips when absent, and it is never a build or test-pass dependency. The system aarch64-linux-gnu binutils 2.42 is the oracle.

---

## 2. Per-concept verdicts

### 2.1 P1 smc-observatory (C02) — KEEP at N3, with conditions

**Novelty. I agree with N3.**
- My 10 independent queries (`presearch-C02.log`) found no SMC/XMC cost map by core class.
- The closest adjacent work I found is new to the log and **must be cited**: Botacin, Zanata & Grégio, *"The Self Modifying Code (SMC)-Aware Processor (SAP): A security look on architectural impact and support"* (J. Computer Virology and Hacking Techniques). Its repo `marcusbotacin/Self-Modifying-Code` @ ed09a3abd6 has a PIN flush-aware cache simulator and a PEBS-based SMC detector. That's architectural-impact measurement with a security framing, on a single core class, with no distance sweep. It's adjacent and doesn't kill.
- `clamchowder/Microbenchmarks` matched "self-modifying" but only *avoids* SMC (README line 11). Not prior art.
- The author's dispositions of SMaCk, SelfModTamper and ryzen_segv_test are accurate.

**My reference measurement is the oracle I'll hold this build to.** Source: `review/evidence/presearch/c02-probe/`, `smcprobe.c` plus `sweep.txt`, 3 runs each, unprivileged. It's a store at a distance from a 6-byte function at page offset 0.

| Core class | Clears per iteration, by store offset | Cost (TSC/iter) |
|---|---|---|
| **P** (CPU 0) | **2.000** only in the code's own 64-B line; 0 at 64…2048 | 730–1303 |
| **E** (CPU 5) | **1.000** at offsets 6…512 (the same aligned 1 KB); 0 at ≥1024 | in-line 612–802; adjacent line 386–555; 128–512 B ~181 |
| **LP-E** (CPU 13) | same 1-KB granularity as E | in-line 1170–1435; adjacent 1249–1388; 128–512 B ~145 |

Intel 248966-050US §3.6.8.1 (verified from the PDF, sha256 prefix 4da42303a8d82a0b): *"Software should avoid writing to a code page in the same 1-KByte subpage that is being executed or fetching code in the same 2-KByte subpage of that is being written."* **That Pentium-4-era rule describes Darkmont exactly and doesn't describe Cougar Cove.** That's the kind of finding this part exists to produce.

**Conditions.** These are BLOCKING at BUILD-01, not now.
- **P1-1 [BLOCKING]** The distance sweep must resolve sub-page granularity: at least power-of-two offsets 64…4096 plus same-line, with an aligned and a misaligned code placement. The SHORTLIST's classes, "{same 64B line, same 4K page ≠ line, adjacent page, far}" (SHORTLIST.md:45), would miss the E-core's 1-KB boundary entirely. The README must test §3.6.8.1 explicitly, per core class.
- **P1-2 [BLOCKING]** Report the three classes separately: P (0–3), E (4–11), LP-E (12–15). They differ in both topology (LP-E has no L3) and SMC cost (above). "E-core = 4–15" is not acceptable in any table.
- **P1-3 [BLOCKING]** Measurement claims follow REVIEW-00 §1.18 (median and spread, ≥5 runs, pinned, tolerance stated).
  - **Clear counts** for a pattern identical to my probe must match my reference exactly: they were deterministic in all 63 sweep runs (3 per point) and all 18 single runs.
  - **Timings** must agree to an order of magnitude.
  - The P=2 versus E=1 clears per iteration for the identical pattern must be either explained or flagged as unexplained.
- **P1-4 [BLOCKING, safety]** Own-process measurement only. No covert-channel or side-channel construction (SMaCk is the attack neighbour). The cross-core experiment uses threads of one process and reports latency and clear counts, never as a transmission channel.
- **P1-5 [nit]** `MACHINE_CLEARS.XMC` exists only on Darkmont (`intel/perfmon` PTL @ 8da58930a226). State that observability is asymmetric. On P-cores, cross-modifying clears appear only inside SMC/COUNT.
- **P1-6 [nit]** Torn-fetch results are "observed on this part, under these conditions", not guarantees. Unsynchronized cross-modifying code is architecturally unpredictable.

### 2.2 P2 pt-truth (C03) — RESHAPE to N2

**Phenomenon VERIFIED.** I re-ran `research/probes/pt-smc-misdecode/` byte-identically (`presearch/C03-pt-misdecode-repro.txt`). gdb shows the first call, which returned 1 (`marker (a=a@entry=1)`), as `mov $0x2; nop×4; ret`. Hardware support: `intel_pt` caps `ptwrite=1`, `mtc=1`, `psb_cyc=1`.
- [nit] The session reports "1 gaps" ("Non-contiguous trace at instruction 35", a buffer wrap before the SMC region). "No gap or warning" (NOVELTY-LOG:191–192) is true of the misdecoded instructions, not of the session.

**The N3 claim fails.** SHORTLIST.md:65–70 says "No tool uses in-band PTWRITE… libipt reads a single live/static image". NOVELTY-LOG:200–204 says "there is no versioned-image-over-time facility". Against that:

1. **wilvk/asm-test** (created 2026-06-23; read as data; excerpts in `presearch/C03-priorart-excerpts.txt`) ships `asmtest_codeimage`, *"a userspace `PERF_RECORD_TEXT_POKE` that builds the timestamped code-image timeline"*. It also ships `asmtest_pt_decode_window`, which decodes PT *"with a recorder-backed `pt_image_set_callback`"*, *"the same-address-different-bytes case resolving to the version live at each `when`"*. Its docs say it was validated "on real silicon" at commit c7b4ef7 (2026-07-21). That's version-correct PT decoding of rewritten userspace code, and **it was in the author's own results** (§1.4).
2. **Linux perf** (`torvalds/linux tools/perf/util/intel-pt.c`). `intel_pt_text_poke()` invalidates decode-cache blocks that overlap a `PERF_RECORD_TEXT_POKE`. That's time-ordered versioning of kernel SMC.
3. **intel/libipt @ 907b908a50** ships `sideband/` ("A sideband correlation library", README:35). `pt_sb_pevent.c` applies `PERF_RECORD_MMAP/MMAP2/AUX/ITRACE_START` at TSC-converted times (`time_shift/time_mult/time_zero`). That *is* an image-over-time facility, at mapping granularity, with no TEXT_POKE. **NOVELTY-LOG:202 is FALSE as written.**
4. **FlowJIT** (`tuxology/flowjit`, 2016: "Kernel patch for hardware trace reconstruction of runtime compiled code"; Suchakra Sharma, LPC 2017), plus the 2018 Univ. of Crete MSc thesis "JIT Tracing using Intel Processor Trace" (Kleftogiorgos).
5. **In-band PTW annotation already exists.** DRAKVUF `tklengyel/drakvuf` @ b2f64d8d73d4 `src/plugins/ipt/ipt.cpp:120–132`: `emit_ptwrite64()` writes synthetic PTW packets (0x02 0x32 + payload) into the trace via `ipt_vcpu::annotate()`. wilvk's pipeline also notes "PTWRITE can inject region markers".

**What survives (N2).** Using an *executed* `PTWRITE <version>` as an **exact in-band fence for same-address byte rewrites**, versus the three time-keyed mechanisms above. That delta only matters if it's shown to matter. Hence:

- **P2-1 [BLOCKING, before build start]** Add a C03 section to NOVELTY-LOG that dispositions items 1–5 above, and drop "N3" everywhere. It has to: (a) explain how wilvk/asm-test was missed despite `"pt_image_add_cached" jit` → 1 hit; (b) correct line 202.
- **P2-2 [BLOCKING, before build start]** Rewrite the SHORTLIST/README novelty claim to the surviving delta, citing items 1–5.
- **P2-3 [BLOCKING, before build start]** Change the novel observable to a **head-to-head**. A time-keyed decoder switches code versions at TSC/MTC/CYC-timestamped patch events, as perf, libipt-sb and wilvk do; run it on the same capture as the PTWRITE-fenced decoder. Both are scored against single-step ground truth.
  - The README must report the patch-to-execute interval below which the time-keyed decode mis-attributes, at stated timing-packet settings (MTC period, CYC on/off).
  - If time-keyed decoding turns out exact at cycle-accurate settings, say so. The claim then becomes "exact without timing packets", which is a weaker N2, and that's an honest outcome.
  - "Naive bytes-as-now decode is wrong" alone is the **known** baseline, not the observable.
- **P2-4 [BLOCKING at BUILD-02]** The ground-truth oracle (single-step) must be independent of the PT path. The planned TF/ptrace route is fine. The `objdump` per-version snapshots are fine.
- **P2-5 [nit]** C22 (TNT barcode) stays a bonus in this part, not a scoring criterion.

### 2.3 P3 hybrid-diff (C04) — CUT (N1)

**Phenomenon VERIFIED, frame not novel.** I reproduced the author's probe byte-identically on CPUs 0/2/3 (P), 4/9/11 (E) and 12/15 (LP-E) (`presearch/C04-uflags-repro.txt`). P and E/LP-E differ on shl, shr8, shld16, shrd16, rol and rcl8, and `rule.c` output is identical to the author's. The data is real. The frame is published:

- **libLISA**: Craaijo, Verbeek & Ravindran, *"libLISA: Instruction Discovery and Analysis on x86-64"*, OOPSLA 2024, PACMPL 8:283, DOI 10.1145/3689723. I read the PDF itself (sha256 prefix b3bee6a9f2b1bf82). Excerpts are in `presearch/C04-liblisa-excerpts.txt`.
  - **Lines 1002–1017.** *"The Intel i9-13900 has two different kinds of cores. Performance cores (𝐴2) use Raptor Cove, while efficiency cores (𝐴3) use the Gracemont microarchitecture."* They're analysed as separate architectures, with ~118k encodings each (Table 5: 𝐴2 118,135; 𝐴3 117,605).
  - **§5.3.1 (lines 1240–1262).** Groups 1, 3, 5, 20 and 28 are microarchitectural differences: *"we find bit shifts, rotates, multiplication, division and bit manipulation instructions"*. Group 1 distinguishes 𝐴3 from 𝐴2. The paper proposes **"fingerprinting programs"** built from these differences.
  - **Lines 60–72 and 96–101.** The motivating example is `rcl` then `jno`, i.e. the undefined OF of a rotate, used to *"behave benign on an AMD Ryzen R9 3900X but behave maliciously on an Intel Core i9-13900"*.
- **Also post-cutoff:**
  - `kmx00/ub86-pred` (2026-06-07) uses undefined effects as opaque predicates to break analysis tools (`devdocs/plans.md:5`), with a `use-affinity` P/E split.
  - `dominicolucci/dift86` (2026-09-23) does silicon-vs-model differential testing with "two clean undefined-flag laws", on homogeneous Xeon.
- **Reach.** libLISA appears in none of the author's raw results. Its repo description contains none of the hybrid vocabulary.

**Disposition.**
- Panther Lake (Cougar Cove/Darkmont) is a newer generation of a published comparison. Under REVIEW-00 §2.1 that's a qualifier: **N1 → CUT**.
- The only unpublished delta I can find is the *in-process migration hazard*: one thread's flags change after a scheduler move. libLISA doesn't discuss scheduling (grep: no matches). But demonstrating it means building a core-type-dependent predicate, which is exactly the misuse both libLISA ("fingerprinting", "maliciously") and ub86-pred document. **[BLOCKING, safety]:** that reshape isn't acceptable as a prototype.
- The probe stays valuable **research evidence**. Cite it in SUMMARY.md, together with libLISA, as "the libLISA P/E finding re-confirmed on Panther Lake". That's an honest, useful sentence; it isn't a part.

**P3-1 [BLOCKING]** Remove C04 from the shortlist, and record the libLISA disposition in NOVELTY-LOG.

### 2.4 P4 ifetch-sanitizer (C01, reshaped) — KEEP as reshaped at N2, with conditions

The author's reshape is evidence-driven: goliajp/aarch64-study v0.22 and cyyself/jit-coherence-test, both read with quotes. I agree with N2. More prior art must be added to the record:

- **herdtools7 @ 12690a83da** `catalogue/aarch64-ifetch/README.md` ships an ifetch catalogue, simulated by `herd7 -variant ifetch` and run on **hardware** by `litmus7 -variant self` (at EL0, or EL1 via kvm-unit-tests). The record mentions "isla/herd" only in passing (NOVELTY-LOG:136).
- **RMEM** (the Cambridge ifetch tool, cl.cam.ac.uk/~pes20/iflat/) exposes the **IDC/DIC** knobs. Its step 8, fetched verbatim: "These options default to the strongest. … Select "Out-of-Order Fetching" and uncheck the "IDC=1" and "DIC=1" checkboxes … to get the weakest semantics discussed in the paper." So the IDC/DIC matrix already exists at **litmus scale**.
- **DynamoRIO** `core/dispatch.c:958–968` (AArch64): "Software cache consistency: we are handling an IC IVAU instruction". Invalidation is keyed on the app's IC IVAU, so a missing IC IVAU leaves stale code there too, though DynamoRIO diagnoses nothing.

**The delta that survives.** A *whole-program* sanitizer that names the omitted step automatically. It includes the I/D **line-size mismatch** class: CTR_EL0 differing across cores breaks flush-loop strides, the classic big.LITTLE JIT bug. Litmus-scale enumeration and fixed demos don't cover that class.

**Conditions.**
- **P4-1 [BLOCKING at BUILD-04]** The README's novelty section positions the tool against all of: goliajp, cyyself, herdtools7 aarch64-ifetch, RMEM, Arm FVP `cache_state_modelled`, and DynamoRIO's SW cache consistency, and states the delta above.
- **P4-2 [BLOCKING at BUILD-04]** **Semantic oracle**, not only the encoder. In coherent mode the interpreter's end state (registers and the memory region) must equal **qemu-aarch64 8.2.2** on every kernel. qemu is a valid *functional* oracle (`review/evidence/qemu-fidelity/`). The encoder must match `aarch64-linux-gnu-as/objdump 2.42` on ≥20 instructions that **I** will choose at the gate (REVIEW-00 §2.3).
- **P4-3 [BLOCKING at BUILD-04]** Every per-config verdict (e.g. "omitted `DC CVAU`: stale when `IDC=0`") must cite the quoted architecture text with document ID and version, e.g. DDI 0487 *x.y* §…. SHORTLIST.md:164's "Arm ARM B2.7.4" is currently an unverified section number. Where the herdtools7 catalogue has a matching test, cross-check against that test's expected outcome, fetched as data. herd7 itself can't be installed.
- **P4-4 [BLOCKING at BUILD-04]** Labelling (R10): all coherence and staleness output is **model output**. "Runs fine under qemu" is presented as qemu's coherence (verified), not as evidence about silicon.
- **P4-5 [nit]** Keep the A64 subset scoped to what the kernels need. Its breadth isn't the novelty.

### 2.5 P5 mirror (C10) — CUT (N1)

**The claim fails.** SHORTLIST.md:174–176 says "Trap-flag single-stepping appears on GitHub only as an *attack* mechanism (sgx-step, rosenbridge) or via ptrace". That's FALSE. Excerpts are in `presearch/C10-priorart-excerpts.txt`, and the queries in `presearch-C10.log`:

- **gperftools** @ 635500ed68 `src/base/single_stepper.h:43–45` (2024): *"Start intercepts SIGTRAP and enables single-stepping (in currently running thread). On ~each instruction given callback will be invoked with signal's ucontext."* The .cc file sets `gregs[REG_EFL] |= kTF` (0x100). Its user is `src/tests/tcmalloc_unittest.cc`. That's a benign, in-process, per-instruction stepper.
- `code "gregs[REG_EFL]" "0x100" SIGTRAP` → 356 results, including v8 `src/sandbox/trap-fuzzer.cc`.
- `code "REG_EFL" "|= 0x100"` → 93 results, including **ERESI `libe2dbg`**, the "Embedded ELF Debugger (e2dbg)" (`thorkill/eresi` README:36,46).
- The Linux selftest `tools/testing/selftests/x86/single_step_syscall.c` does the same.
- Visualizing execution is well covered by Blinkenlights (REVIEW-00 §3) and gdb TUI.

**Technical limit.**
- Each step is an exception delivery plus a return to user mode, through FRED on this kernel (`CONFIG_X86_FRED=y`; the kernel log shows `fred_entry_from_user`).
- A self-traced program therefore can't observe SMC *cost* or any microarchitectural SMC behaviour, only the architectural fact that the listing changed.
- I haven't verified whether ERETU is serializing, so I'm not resting this on serialization. The cost argument holds regardless.
- The SHORTLIST's "payoff", watching the listing change, is the trivial architectural part.

**The record is also below the §2.1 minimums** (§1.3).

**P5-1 [BLOCKING]** Remove C10 from the shortlist and record these dispositions in NOVELTY-LOG.

---

## 3. Cherry-picking assessment (all 23)

| C | Author | Reviewer | Note (reviewer evidence) |
|---|---|---|---|
| C01 | N2 reshape | N2 | + herdtools7 aarch64-ifetch, RMEM, DynamoRIO (§2.4) |
| C02 | N3 | N3 | + Botacin SAP; my sweep shows a strong observable |
| C03 | N3 | **N2** | wilvk, TEXT_POKE, libipt-sb, FlowJIT, DRAKVUF |
| C04 | N3 | **N1** | libLISA OOPSLA'24 |
| C05 | N2 alt | N2 | + r2wars, corewars8086 lineage; the native delta is real; sandbox burden real |
| C06 | N2 cut | N2 | + Akgul & Mooney (GT TR 2002, PASTE'02, ICSE'04, PhD'04), Koju et al. VEE'05. Cut is acceptable |
| C07 | N2 cut | N1–N2 | + ARM64EC/CHPEv2 (`FFRI/ProjectChameleon`), box64/FEX thunks |
| C08 | N0 cut | N0 | agree (armvis) |
| C09 | N2 alt | N2 | record short |
| C10 | N3 | **N1** | gperftools SingleStepper, ERESI, v8 (§2.5) |
| C11 | N1 cut | N1 | agree |
| C12 | N2 alt | **N2–N3** | my 6 repo queries found no cross-ISA *machine-code* relay (`presearch-C12.log`): `polyglot elf multi architecture` → 0, `assembly quine arm64` → 0, `binary quine x86-64 elf` → 0; nearest are single-ISA ELF quines and source-level relays. Record short |
| C13 | N1 cut | N1 | agree (FiSim) |
| C14 | N2 cut | N2 | agree (thin) |
| C15 | N2 cut | N2–N3 | agree (thin) |
| C16 | N0 cut | N0 | agree (befunjit-86) |
| C17 | N2 alt | N2 | record short; spoofing is fine as benign test steering (Intel SDE analogue) |
| C18 | N1 cut | N1 | agree |
| C19 | N1 cut | N1 | agree; safety optics |
| C20 | safety cut | safety cut | agree |
| C21 | safety cut | safety cut | agree |
| C22 | N3 bonus | N3 | my 4 repo + 1 code queries found nothing; record short; depends on P2 capture |
| C23 | N1 cut | N1 | agree |

**Was something stronger cut for convenience? Mostly no.** Every N0/N1 cut is correctly evidenced, and the safety cuts are right. There are two ranking errors:
- **C10** (Low-Medium effort, "clean, low-risk", SHORTLIST.md:191 and NOVELTY-LOG:269) was shortlisted ahead of **C12** (Medium effort; on my evidence the stronger novelty, and mission-central with both ARM64 and x64). C10 also had the thinnest search record of the five. That's a mild convenience bias.
- **C04** was promoted on the strength of its probe without the paper search that would have found libLISA.

**Theme coverage after this review.**
- ARM64: P4.
- x86/SMC/tracing: P1, P2.
- Visualization of how machines work: currently none, because P5 is cut.

The replacements should restore it.

---

## 4. Conditions that bind every build gate

These restate REVIEW-00 §5 R1–R12, now binding, plus R13–R15.

- **R1.** The GATE line names the commit. Use `GATE BUILD-NN READY (part NN-<slug>) — commit <hash>` (R5 form).
- **R2.** NOVELTY-LOG items per REVIEW-00 §2.1, with a disposition for every relevant hit.
- **R3.** RUN.md declares nondeterministic fields.
- **R4.** The README names its **novel observable** and points to the RUN.md lines that show it.
- **R6.** A differential test against an independent oracle (REVIEW-00 §2.3).
- **R7.** Commit only your own paths.
- **R8.** A README "Requirements" line listing every tool beyond gcc/binutils/make/python3 stdlib.
- **R9/G-3.** Fix the stale facts.
- **R10.** Emulation labels ("under qemu-aarch64"; model output is labelled as model output).
- **R11.** Measurement claims follow REVIEW-00 §1.18.
- **R12.** Lane identity, with an accurate trailer.
- **R13 (new).** Timestamps come from `date`, never from estimates.
- **R14 (new).** Any per-core claim distinguishes P (0–3), E (4–11) and LP-E (12–15).
- **R15 (new) = G-2.** At least two paper/web searches per novelty section.

Reproduction will follow REVIEW-00 §2.2: a fresh clone in `tasks/reviewer-repro/`, `env -i`, strace for network and out-of-tree writes, two full runs, and a diff against RUN.md.

## 5. What the author may do now

1. **Apply the record fixes, then note `GATE 1 CLEARED`:** P2-1, P2-2, P2-3, P3-1, P5-1, G-3. G-4 and G-5 are nits, so fix them where convenient.
2. **Build P1 (smc-observatory) immediately after CLEARED.** It doesn't depend on any replacement. Conditions P1-1 to P1-6 are checked at BUILD-01.
3. **Build P2 after P2-1 to P2-3 are committed.** No separate addendum is needed, because this review fully specifies the reshape. Compliance is checked at BUILD-02.
4. **Build P4 when its turn comes.** No addendum is needed; P4-1 to P4-5 are checked at BUILD-04.
5. **Replacements for the P3 and P5 slots.** For each, append to NOVELTY-LOG.md and SHORTLIST.md:
   - a §2.1-complete search record (G-1) plus ≥2 paper/web searches (G-2);
   - a disposition for every hit;
   - a novel observable;
   - a prototype plan.

   Then post `ADDENDUM READY (Cxx) — commit <hash>` in STATUS-AUTHOR.md. I'll append my verdict to this file (§6, below) within one poll cycle. **No replacement build starts before its addendum verdict.**
   - **My non-binding recommendation:** C12 (ARM64 + x64 machine code, now runnable under qemu-aarch64; exact-bytes fixed-point oracle with `cmp`), plus one visualization-theme concept, either C22 promoted to its own part on P2's capture or C09.
   - **For C12 [safety]:** stages write the next stage to stdout only. The harness redirects the output and runs it under qemu. Nothing writes itself to disk or execs itself.
6. **Parallelism.** Writing addenda and research notes alongside the P1 build is allowed. One *build* at a time unless I grant proceed-in-parallel at a build gate.

## 6. Addenda verdicts

(None yet. Appended below, timestamped, as `ADDENDUM READY` lines arrive.)

## 7. Post-gate commits, weighed (2026-10-19 02:55 PDT)

Three author commits landed after the GATE line and before this file:
- `34a892b` (02:45:23), "disclose Intel/Wikipedia P-E undefined-OF prior art; C04/P3 N3->N2";
- `0d25c48` (status);
- `95e62e8` (`research/RESEARCH-NOTES.md`, 124 lines).

They aren't what the gate named. I read them anyway, because they could change a verdict in the author's favour. **No verdict changes.**

- **P3 (C04): CUT stands, and the disclosure strengthens it.**
  - `34a892b` adds Intel's own *12th-Gen Game Dev Guide*: the undefined shift OF "can vary between Performance-cores and Efficient-cores". The vendor documents the phenomenon itself.
  - The proposed N2 residue doesn't survive libLISA (§2.3):
    - **(a) "the systematic scanner (no public tool does this)":** libLISA *is* a public systematic tool that ran on both core types of an i9-13900 (`libLISA/liblisa`, OOPSLA'24). FALSE.
    - **(b) "the specific per-core rule … the prose doesn't give it":** libLISA synthesizes per-architecture *semantics*, flags included. For Panther Lake the rule is new data on a published method, which is a qualifier: N1.
    - **(c) "a migration-visible demo":** this is the core-type-dependent predicate that §2.3 rules out on safety grounds ([BLOCKING]).
  - The probe remains good *evidence* for SUMMARY.md.
- **P2 (C03): RESHAPE stands.** `RESEARCH-NOTES.md:48–55` answers "libipt image callback / perf jitdump". It doesn't address wilvk/asm-test (in the author's own results), perf `PERF_RECORD_TEXT_POKE`, libipt's `sideband/` (time-keyed images), FlowJIT or DRAKVUF's in-band PTW annotation. **P2-1 to P2-3 stand.**
  - The notes' framing ("in-band and ordered with the control-flow packets") *is* the surviving delta, and I agree it's the right one.
  - P2-3's head-to-head against a time-keyed decoder is what proves that delta.
- **P5 (C10): CUT stands.** `RESEARCH-NOTES.md:109–113` rebuts "anti-debug / sgx-step". The killer is gperftools' *benign*, in-process, per-instruction `SingleStepper` (§2.5), and the notes don't address it.
- **P1, P4.** The notes are consistent with my conditions. Two points to carry into the builds:
  - The notes still treat CPUs 4–15 as one "E-core" class, so R14/P1-2 stand.
  - "RDPMC is not exposed" (`RESEARCH-NOTES.md:23`) is accepted as an author claim. It's untested by me and not load-bearing.
