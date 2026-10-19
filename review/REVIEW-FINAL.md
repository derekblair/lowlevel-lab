GATE: final | VERDICT: APPROVE | AT: 2026-10-19 12:39 PDT | COMMIT: b4f37b3

# REVIEW-FINAL — lowlevel-lab

**Reviewed:** commit `b4f37b3`, named in the `FINAL READY` line at 12:33.

**Method:**
- `review/tools/final_rerun.sh` cloned that commit fresh and ran each part's README `make` **twice** under `env -i` (§1).
- Every novelty claim was re-checked against **fresh** searches: 14 GitHub queries, 5 web searches, and two kill-rule source reads (§2).
- The five parts are ranked by the rubric **pre-registered in REVIEW-00 §2.6**, which was frozen before any build existed: **N × W × I**, ties broken by W (§3).

**Evidence:** `review/evidence/final/`.

## Verdict: APPROVE (no blocking issues; 3 nits)

All five builds reproduce from a clean clone of the final commit, twice: **54/54 VERDICTs PASS in each run**. Every strace audit is CLEAN. No novelty claim was killed or narrowed by the fresh searches.

## 1. Clean re-run of all five builds

| Part | Run 1 | Run 2 | vs RUN.md | strace (`make`, traced) |
|---|---|---|---|---|
| P1 smc-observatory | 10/10, 17 s | 10/10, 13 s | All 10 VERDICT names match. Every granularity value is identical across runs: P@63 = 2.00, P@64 = 0.00, E@1023 = 1.00, E@1024 = 0.00. The cross-core rates vary (N1) | CLEAN |
| P2 pt-truth | 12/12, 2 s | 12/12, 1 s | Per-class structure as verified in REVIEW-02 round 4 and its N9 addendum | CLEAN |
| C12 quine relay | 6/6 | 6/6 | **run 1 = run 2 = RUN.md** | CLEAN. Under my outer strace, its x86 C12-2 check **fails closed** by design (nested ptrace) |
| P4 ifetch-sanitizer | 16/16 | 16/16 | **run 1 = run 2 = RUN.md** | CLEAN |
| C09 x86 lattice | 10/10, 4 s | 10/10, 4 s | **run 1 = run 2 = RUN.md** | CLEAN |

Evidence: `rerun/final-summary.txt`, `rerun/*-run{1,2}.txt`, `rerun/comparison.txt`, `rerun/final-strace-summary.txt`, `rerun/*-strace-audit.txt`.

**C12 stage audit at the final commit** (`c12-stage-audit.txt`):
- `stage0` (x86-64) and `stage1` (AArch64, under qemu) each make **exactly 3× `write` + `exit`**.
- `stage0` = `stage2`, byte for byte (sha256 `ce9a974b…`, the same as at the BUILD-03 gate).
- `stage1`'s output is byte-identical to `stage2`.

**My own tooling fault, disclosed.** At this final step my `review/tools/stage_syscalls.sh` printed "ONLY-WRITE1-EXIT: yes" for the non-executable output file `stage2`. That was an empty trace after `exec: Permission denied`: a **fail-open**, the same class as the C12 nit I raised in REVIEW-03 (N2). I've made the tool fail closed and re-run it.

My earlier REVIEW-03 uses of the tool were on executable stages, with real traces of 3 `write` + 1 `exit` (`../evidence/build-03/indep-checks.txt`), so those conclusions stand. Together with REVIEW-05 round 2's missing-`-z` correction, that makes two reviewer-tool defects found and fixed during this review. Both are recorded. Earlier fixes to my tools are logged in STATUS-REVIEWER: the `objdump_lengths` stop address, and `strace_audit` false positives.

## 2. Novelty re-check against fresh searches

**Queries.** `../evidence/search/final-queries.tsv` holds 14 GitHub queries, all exit 0: 11 repo and 3 code, with recency slices `created:>2026-09-15` and `pushed:>2026-10-01`. There were also 5 web searches (`../evidence/search/final-web.txt`). Two of them first hit a WebSearch session limit and were re-run after it reset. Kill-rule reads are in `priorart-excerpts.txt`.

| Part (approved level) | Fresh evidence | New neighbours (read as data) | Verdict |
|---|---|---|---|
| **P1** (N3) | F01–F03; web W1 | None. No per-core-class SMC-granularity measurement exists. The hits are background: arXiv 2604.12407 and 2509.18909, and Intel patents on 1 KB / FINE HIT granularity | **N3 stands** |
| **P2** (N2) | F04 (0 since 2026-09-15), F05, F06; web W2 found nothing on PTWRITE fences or version attribution | **`avisi-group/icewind`**: its brig DBT emits `PTWRITE(block_start_pc)` per translated block for guest-PC tracing. That's in-band PTW annotation, the class REVIEW-01 §2.2 already recorded (DRAKVUF). It does no SMC version attribution and no time-keyed comparison | **N2 stands** |
| **C12** (N3) | F07–F09: 0 / 0 / 0; web W3: nothing | None | **N3 stands** |
| **P4** (N2) | F10, F11: 0 / 0; F12; web W4: no tool diagnoses an omitted step | **`hatter6822/seLe4n`** `CacheModel.lean`: a Lean proof model of a microkernel's own I-cache obligations. No CTR_EL0 IDC/DIC, no line-size class, no step naming | **N2 stands** |
| **C09** (N2) | F13, F14: 0 / 0; web W5: no measured resync distribution | None since BUILD-05. Andriesse 2016 and Kruegel 2004 were read at source then | **N2 stands** |

Recommended additions to the record (not blocking): cite icewind next to DRAKVUF in P2's prior art, and seLe4n next to herdtools7/RMEM in P4's.

## 3. Ranking: N × W × I (REVIEW-00 §2.6)

How each axis is scored:
- **N** = approved level + 1, unchanged by §2.
- **W:**
  - 5 = clean reproduction twice, oracle tests, edge cases handled;
  - 4 = also has an independent-oracle test;
  - 3 = works as claimed, with caveats;
  - 2 = builds, but the demo misstates;
  - 1 = doesn't build.
- **I** = does *running* it teach something about how machines work that §3's prior art can't?

| Rank | Part | N | W | I | **N×W×I** | Basis |
|---|---|---|---|---|---|---|
| 1 | **P1 smc-observatory** | 4 | 5 | 5 | **100** | It measures, on silicon, that the two core classes of one die detect SMC at **different granularities**: a 64-B line on Cougar Cove, a 1 KiB subpage on Darkmont. Intel 248966 §3.6.8.1 describes only Darkmont. The classes also book cross-modification to **different counters**. W: my independent sweep (REVIEW-01-build), a powered torn-fetch probe, and identical boundaries in both final runs. No public per-class measurement was found |
| 2 | **C12 quine relay** | 4 | 5 | 4 | **80** | A byte-exact x86-64 → AArch64 → x86-64 ELF fixed point, verified over two full rounds outside the harness, with each stage audited to `write` + `exit` only. It teaches ELF headers, entry points, two ISAs' immediate encodings and syscall ABIs side by side ("medium–high", REVIEW-03 §4). I stops at 4 because the result is a *construction*, with nothing new *observed* about machine behaviour, and the AArch64 half runs under qemu |
| 3 | **P2 pt-truth** | 3 | 5 | 5 | **75** | It shows how Intel PT reconstructs time (TMA plus MTC payloads) and exactly where that fails. It also found that hybrid core classes emit MTC at ~10²–10³× different densities under BranchEn=0: Darkmont about once per payload wrap (Δ0 steps), Cougar Cove every period. That decides whether time-keyed SMC attribution survives long gaps. I verified it at the packet level with my own framer. The exact in-band fence is the N2 delta. N is limited to 3 by the reshape at Gate 1 |
| 4 | **C09 x86 lattice** | 3 | 5 | 4 | **60** | A measured resync distribution where the literature had only qualitative claims. Ground truth: median 2, 71% within 2, 83% within 3. Excluding `(bad)` chains, the median is 1. That reconciles Linn & Debray's "one or two" with Andriesse's "two or three". My independent survey reproduced every pooled figure, and the lattice self-check catches 6/6 of my mutations. The phenomenon itself is published, which caps N |
| 5 | **P4 ifetch-sanitizer** | 3 | 5 | 3 | **45** | A program-driven model that names the omitted AArch64 maintenance step. It is correct on every kernel from my round-2 and round-3 suites (T0–T5 and P1–P15), including store ordering and I-line < D-line. But everything it reports is **model output**. qemu is coherent, so no stale fetch is ever *observed*, and the rules it teaches are already public (Arm ARM, Linux `cache.S`, herdtools7 litmus tests) |

W is 5 for every part, so the tie-break never decides a place. The order is set by N and I.

## 4. The weakest: P4 ifetch-sanitizer (45), and what would fix it

**Why it is weakest.** P4 works exactly as now claimed. It took three rounds to get there:
- round 1: the verdict read a recipe, not the program;
- round 2: it ignored store ordering;
- round 3: correct on all my probes.

But it is the only part whose headline is **not a measurement of any machine**. Its staleness verdicts are model output, and the one AArch64 environment available (qemu-aarch64 8.2.2) is ifetch-coherent, so it cannot show a single stale fetch. A learner who runs it learns the *rules* (IDC/DIC, barriers, order, line size), which are already public. They don't learn how any real core *behaves*.

**What would fix it, in order of value:**
1. **Run the kernels on ARM64 silicon.** For example, Linux on Apple Silicon (Asahi), which keeps the ELF stages and Linux syscalls and avoids the Mach-O/W^X port the SUMMARY notes. An Ampere, Graviton or Raspberry Pi 5 board would also do.
   - Execute each omission kernel 10⁵–10⁶ times per `CTR_EL0` configuration actually reported, under cache pressure.
   - Report the **observed stale-execution rate per omitted step**, next to the model's "not guaranteed".
   - On an SoC whose cores report different `IminLine`, reproduce the line-size class **empirically**.

   This turns I from 3 to 5. Since my searches found no public per-step stale-rate measurement, it likely raises the N2 claim too.
2. **Give the interpreter branches and a second PE.** It could then sanitize *real* JIT flush routines, such as LLVM's `__clear_cache` or V8's `FlushICache` compiled for AArch64, instead of unrolled kernels. A second PE would make "ISB on the executing PE" testable for cross-modifying code.
3. **Cross-check every per-configuration verdict against herdtools7 `aarch64-ifetch` / RMEM.** Today only the full sequence is cross-checked (REVIEW-04 N1). Disagreements would either find model bugs or become findings.

## 5. SUMMARY.md, checked against the reviews

It's accurate on every point I could check against the gates and the final re-run:
- the levels;
- the strongest prior-art threats;
- the "qemu is not silicon" framing;
- the per-class P2 statement, as corrected in `e90ea37`;
- P4's model caveats;
- C09's corpus figures;
- the review-impact table.

**N1 [nit]:** SUMMARY.md:62–63 quotes P1's cross-core rates as point values: "≈1.1×10⁵" XMC on Darkmont and "≈1.5×10⁵" SMC on Cougar Cove, per 10⁶ iterations. They are scheduling-dependent. In the final runs, Darkmont XMC was 7.2×10⁵ and 1.2×10⁵ per 10⁶, and Cougar Cove SMC was 1.46×10⁵ and 1.32×10⁵ (`rerun/comparison.txt`). P1's RUN.md already declares them nondeterministic; say so in SUMMARY. The *class split* (XMC vs SMC booking) is stable.

**N2 [nit]:** SUMMARY.md:186 says C09's `/usr/bin` tail is "*entirely* `(bad)`-driven". The evidence is that the `(bad)`-free subset matches ground truth within a point (77% vs 76% within 2). "The excess is `(bad)`-driven" is the supported wording.

**N3 [nit]:** add icewind to P2's prior art and seLe4n to P4's (§2).

## 6. Overall

Five low-level prototypes went through 12 build-gate rounds, 6 of which were CHANGES REQUESTED and then fixed. Each now reproduces cleanly, twice, from the final commit, and its novelty claims hold against fresh searches. Every result was checked against independent evidence:
- my own probes, encoders, framers and surveys;
- GNU binutils;
- qemu;
- trap-flag ground truth.

The author's handling of review was exemplary:
- re-opening BUILD-02 after their own pinning experiment changed a cleared claim;
- disclosing post-hoc thresholds;
- adopting reviewer evidence only with attribution.

**APPROVE.** The ranking is P1 > C12 > P2 > C09 > P4. The weakest is P4, and the fix is native ARM64 measurement (§4).

---

**Post-final commit `bb85d9d`, weighed 2026-10-19 12:40 PDT.** It is **docs only**: SUMMARY.md, `research/NOVELTY-LOG.md`, and the prior-art paragraphs of the P2 and P4 READMEs. No code under `parts/` changed, so §1's clean re-run at `b4f37b3` stands for all five builds. All three nits are resolved accurately:
- **N1:** the cross-core rates are now stated as scheduling-dependent ranges, Darkmont XMC 1.1–7.2×10⁵ and Cougar Cove SMC 1.3–1.5×10⁵ per 10⁶, matching `rerun/comparison.txt` and the gate runs.
- **N2:** "the excess is `(bad)`-driven".
- **N3:** icewind and seLe4n are added, attributed as reviewer-read.

SUMMARY reproduces §3's ranking table exactly, next to the author's novelty-confidence ranking, and names P4 as the weakest with this review's fix. **Nothing remains open.**
