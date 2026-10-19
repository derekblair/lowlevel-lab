# SHORTLIST — lowlevel-lab, the final 5

Author lane. Chosen from [CANDIDATES.md](CANDIDATES.md) on the evidence in
[NOVELTY-LOG.md](NOVELTY-LOG.md). Each concept below gives: the gap it fills,
the evidence that the gap is real, the prototype plan (language, arch, files,
what running it shows, independent oracle), an effort estimate, and the
honest risks. Build order and parallelism are at the end.

**Theme balance (mission names ARM64 first, then x64, SMC, visualization):**
ARM64 — P4. x86/hybrid silicon — P1,P2,P3. Self-modifying code — P1,P2,P4,P5.
Visualization of how machines work — P5 (and the maps P1/P3 emit). Every
prototype builds and runs on nibbles with present tools only.

**Machine facts that make these reachable** (verified, REVIEW-00 §0 concurs):
Intel Panther Lake, family 6 model 0xCC — 4 Cougar Cove P-cores (CPUs 0–3,
`cpu_core`), 12 Darkmont E-cores (CPUs 4–15, `cpu_atom`); unprivileged Intel
PT (gdb `record btrace pt`, `set record btrace cpu none`); `perf_event_open`
user-task counting (paranoid=2); `MACHINE_CLEARS.SMC` on both core types +
`MACHINE_CLEARS.XMC` on the E-core; CET/IBT/LAM present; qemu-aarch64 8.2.2 +
aarch64-linux-gnu binutils/gcc 13.3 present (ARM64 **assembles/links/runs
under qemu — never "on ARM64"**, REVIEW-00 §0.2–0.3). No clang/nasm on PATH.
Python is stdlib-only (curses yes, tkinter/numpy/capstone no) → visualizations
are ANSI/curses or emitted SVG/PPM/HTML.

---

## P1 — smc-observatory (was C02) · x86 hybrid · **N3**

**Gap.** No public tool maps the *cost and behaviour* of self- and
cross-modifying code on a hybrid P/E die: SMC machine-clear cost as a function
of write↔execute distance, P-core vs E-core, cross-core patch-visibility
latency and XMC clears, and torn-fetch at boundaries. Existing repos are
either SMC *attacks* (SMaCk, L1i Prime+Probe), *tamper-proofing* (SelfModTamper),
or a single-µarch *bug repro* (ryzen_segv_test) — none a benign hybrid map,
none sweeping distance, none using the E-core's dedicated `MACHINE_CLEARS.XMC`.
(Evidence: NOVELTY-LOG C02, three repos read as data; arXiv full-texts confirm
single-CPU, dual-page, no hybrid, no XMC.)

**Prototype plan.**
- **Lang/arch:** C + GNU `as` inline, raw `perf_event_open` (no PAPI — not
  installed). x86-64 native.
- **Files:** `parts/01-smc-observatory/{AGENTS.md,README.md,RUN.md,Makefile,
  smcprobe.c,counters.c,counters.h,plot.py}`.
- **What running it shows:** (1) a text/ANSI heatmap of SMC machine-clears and
  cycles vs write-distance {same 64B line, same 4K page ≠ line, adjacent page,
  far} — pinned to a P-core and to an E-core via `sched_setaffinity`, median
  ± spread over ≥5 runs (REVIEW-00 §1.18); (2) a cross-core experiment: core A
  patches a NOP→RET another core executes, with and without a serializing
  `cpuid`/`SERIALIZE`, reporting visibility latency and XMC-clear counts;
  (3) a torn-fetch probe: patch an instruction straddling a line/page boundary
  from another core and count mismatches (expect ~0 on Intel — that *is* the
  finding, "Intel's SMC detection holds here").
- **Oracle:** `MACHINE_CLEARS.SMC`/`.XMC` event codes from Intel perfmon tables
  (family 6 model 0xCC, already extracted); cross-checked against `INST_RETIRED`
  sanity and the known ~order-of-magnitude penalty. Counts are inequalities/
  ratios with tolerance, not byte-exact (REVIEW-00 §1.18).
- **Effort:** Medium (≈1 focused build). Counter plumbing is the work.
- **Risks:** (a) perf_event_open PMU selection on hybrid (must open on the
  right `type` = cpu_core/cpu_atom); (b) frequency/thermal noise → report
  ratios + spread, pin with taskset; (c) must stay benign — measurement of
  own-process patches only, no cache-attack primitive (REVIEW-00 §2.4).

## P2 — pt-truth (was C03) · x86 · **N3**

**Gap.** Intel-PT decoders reconstruct the instruction stream from the code
bytes *currently* in memory, so self-modifying/JIT code is silently
misdecoded. No tool uses in-band `PTWRITE <version>` packets as exact
code-version fences to fix this; simple-pt says plainly "Tracing JITed code
is not supported", libipt reads a single live/static image, JPortal uses
side-band jitdump maps. (Evidence: NOVELTY-LOG C03; simple-pt + libipt read
as data; the misdecode is already demonstrated in
`research/probes/pt-smc-misdecode/`.)

**Prototype plan.**
- **Lang/arch:** C for capture (`perf_event_open` with an `aux` ring for
  `intel_pt`), Python stdlib for packet decode + reconciliation. x86-64.
- **Files:** `parts/02-pt-truth/{AGENTS.md,README.md,RUN.md,Makefile,
  ptcap.c,ptdecode.py,target_smc.c,verify_singlestep.py}`.
- **What running it shows:** a target rewrites its own code in a loop and emits
  `PTWRITE(version)` at each patch; the naïve decode (bytes-as-now, like
  gdb/libipt) gets the stream **wrong**, our version-fenced decode gets it
  **right**, proven instruction-for-instruction against a single-step
  (TF/ptrace) ground-truth log. Also reproduces the gdb misdecode as the
  baseline (`research/probes/pt-smc-misdecode/`).
- **Oracle:** single-step ground truth (independent of the PT path); plus
  `objdump -d` on each per-version code snapshot for instruction lengths.
- **Effort:** High (hardest build). PT AUX capture + enough packet decode
  (PSB/PAD/TNT/TIP/FUP/MODE/PTW) to walk the target.
- **Risks:** (a) libipt has no header here (gdb links it privately) → I decode
  packets myself in Python; scope the target to the packet subset it actually
  produces; (b) if from-scratch capture stalls, the gdb probe still proves the
  *claim*, and the deliverable degrades gracefully to "demonstrate misdecode +
  decode a captured-to-file trace" — stated in README, not hidden.
  (c) PTWRITE must be enabled (`fup_on_ptw`); verified cap `ptwrite=1`.

## P3 — hybrid-diff (was C04) · x86 hybrid · **N3**

**Gap.** Instruction fuzzers (sandsifter, vmsifter, baresifter) scan one core;
the one differential x86 framework found (yufengzjj/hybrid-x86-oracle) diffs
*reference backends* (Sail/Bochs/KVM) against each other, **not the two core
types of one hybrid die**. Nobody pins identical instructions to a P-core and
an E-core and diffs legality/length/result/**undefined flags**/CPUID. (Evidence:
NOVELTY-LOG C04; oracle repo read as data to confirm "hybrid" = backends.)

**A divergence is already in hand.** `research/probes/hybrid-undefined-flags/`:
for shift/rotate count ≥ 2 the **architecturally-undefined OF** differs by
core type (P = first-step rule, E = last-step rule); results and `SAR` agree.
So the build systematizes a *confirmed* phenomenon.

**Prototype plan.**
- **Lang/arch:** C + `sched_setaffinity`, candidate instructions assembled via
  GNU `as`; children under `seccomp` strict-ish (probe can't syscall) with a
  SIGILL/SIGSEGV handler for legality/length (sandsifter page-boundary trick).
  x86-64 native.
- **Files:** `parts/03-hybrid-diff/{AGENTS.md,README.md,RUN.md,Makefile,
  diff.c,probe.c,ops.inc,report.py}`.
- **What running it shows:** a diff report over a chosen instruction set
  (shifts/rotates/mul/div/bsf/bsr/bt/popcnt… with both initial-flag states):
  per instruction, P vs E on {legal?, length, result, each undefined flag,
  CPUID leaf 0x1A core-type}. Headline: the OF first-step/last-step split,
  reproduced, with the exact encodings and counts. Where the two disagree, it
  reports which (if either) matches the SDM / a formal model.
- **Oracle:** the instructions' *defined* bits must match on both cores (a
  divergence there would be a real bug → flag it); for *undefined* bits, report
  the rule each core follows. Optional third opinion: the yufengzjj oracle's
  Sail/Bochs backends (cited, not a dependency).
- **Effort:** Medium (probe harness already prototyped).
- **Risks:** (a) scope the instruction set so a clean run is quick and
  reproducible; (b) affinity must be honoured (verify via CPUID 0x1A in-probe);
  (c) benign — own-process probing, syscalls blocked.

## P4 — ifetch-sanitizer (reshaped C01) · ARM64 · **N2**

**Gap.** Prior art models the *I-side* stale-fetch demo (goliajp/aarch64-study
v0.22, passing tests) and runs the real-hardware skip-flag test
(cyyself/jit-coherence-test), but **neither models the full
`DC CVAU → DSB ISH → IC IVAU → DSB ISH → ISB` sequence as a configurable
coherence matrix with per-step omission diagnosis**: aarch64-study makes
`DC CIVAC` a no-op (no D-cache), varies no `CTR_EL0` bits, and is one fixed
demo; jit-coherence-test is pass/fail on whatever CPU runs it. (Evidence:
NOVELTY-LOG C01; both repos + source read as data, with quotes.)

**Prototype plan.**
- **Lang/arch:** Python (stdlib) A64 subset interpreter + a tiny A64
  assembler for the test kernels; ARM64 is the *modelled* ISA. A thin C
  companion runs the **same** patch sequence natively on x86 (coherent) and
  under qemu-aarch64 (REVIEW-00 §0.2: SMC-coherent) to show it passing where
  the model says it would fail on real silicon.
- **Files:** `parts/04-ifetch-sanitizer/{AGENTS.md,README.md,RUN.md,
  Makefile,a64asm.py,icache_model.py,sanitize.py,kernels/*.s,
  oracle_qemu.sh}`.
- **What running it shows:** feed it a code-patching sequence; it reports
  **exactly which maintenance step is missing** and under which
  `CTR_EL0.{IDC,DIC}` and I/D line-size config it would execute stale — e.g.
  "omitted `IC IVAU`: stale on all configs"; "omitted `DC CVAU`: stale when
  `IDC=0`"; "omitted `ISB`: stale until next context-synchronising event".
  A correct sequence is reported clean on every config. Side-by-side: the
  identical bytes run *fine* natively/under qemu (the "silent here, broken
  there" cross-check).
- **Oracle:** the A64 **encoder** is differentially tested against
  `aarch64-linux-gnu-as`/`objdump` 2.40/2.42 on ≥20 instructions (REVIEW-00
  §2.3); cache/coherence behaviour is **model output, labelled as such** — no
  hardware oracle exists on this box (REVIEW-00 §0.2), and the README says so.
  Rules cross-checked against the Arm ARM B2.7.4 sequence and cyyself's
  recorded M1/Phytium results.
- **Effort:** Medium-High (assembler + interpreter + matrix).
- **Risks:** (a) **must not collapse** into aarch64-study's single-line demo —
  the matrix + step diagnosis is the novelty; (b) honest labelling: this is a
  *model*, not silicon (REVIEW-00 §0.2, R10); (c) scope the A64 subset to what
  the kernels need, differentially tested.

## P5 — mirror (was C10) · x86 · **N3**

**Gap.** Trap-flag single-stepping appears on GitHub only as an *attack*
mechanism (sgx-step, rosenbridge) or via ptrace; no benign program that
single-steps *itself* in-process and renders its own execution — including
watching its own self-modification rewrite the listing. (Evidence: NOVELTY-LOG
C10; 0 relevant repo hits; code hits are attack tools.)

**Prototype plan.**
- **Lang/arch:** C + inline asm, `sigaction(SIGTRAP)`, set TF via the signal
  `ucontext` (`REG_EFL |= 0x100`). x86-64 native, no ptrace, no child.
- **Files:** `parts/05-mirror/{AGENTS.md,README.md,RUN.md,Makefile,mirror.c,
  render.c,selfmod_demo.c}`.
- **What running it shows:** a curses/ANSI live view of the program's own
  instruction pointer walking its own disassembly, register deltas per step,
  and — the payoff — a small self-modifying routine patching its own
  arithmetic while you watch the listing change under the cursor.
- **Oracle:** the captured instruction trace is diffed against gdb's
  single-step trace of the same binary (independent) — must match.
- **Effort:** Low-Medium (self-contained).
- **Risks:** (a) TF-in-signal-handler edge cases (the "stuck TF on first
  handler instruction" kernel quirk — handle the first step carefully);
  (b) disassembly: use a tiny built-in length/mnemonic decoder for the demo's
  own fixed instruction set + `objdump` for the static listing, not a full
  x86 decoder; (c) benign — own process, educational (REVIEW-00 §2.4).

---

## Build order, parallelism, and the bench

**Order (by de-risking + shared infra):**
1. **P3 hybrid-diff** — phenomenon already captured; fastest to a verified,
   oracle-backed result; establishes the perf/affinity harness P1 reuses.
2. **P1 smc-observatory** — reuses P3's counter/affinity plumbing.
3. **P5 mirror** — independent, low-risk, pure win; good while PT work incubates.
4. **P2 pt-truth** — highest risk; the gdb probe already backs the claim, so
   schedule it with slack. **C22 (TNT-bit barcode) is a visualization bonus on
   P2's capture if time allows — not a 6th concept.**
5. **P4 ifetch-sanitizer** — ARM64; most "build-the-tooling-yourself"; benefits
   from being last so the assembler/oracle discipline is warm.

I will **not** start a build until REVIEW-01 clears, and will build one gate at
a time unless the reviewer grants proceed-in-parallel. P3→P1 and P2→C22 share
code, so those pairings are the natural parallel candidates if offered.

**Alternates (reviewed, benched, ready to swap in if the reviewer CUTs one):**
C09 x86-lattice (N2, superset-decode viz+stats), C12 cross-ISA quine relay
(N2), C17 cpuid-mirror (N2), C05 silicon-corewar (N2 but §2.4 sandbox burden).
Any swap-in gets its own NOVELTY-LOG addendum before its build starts
(REVIEW-00 §1.7).

**Cut-consistency statement (REVIEW-00 §1.6):** nothing was cut "for
buildability" that is harder than a kept concept. P4 (ARM64, N2) is kept over
C06 (reversible JIT, N2) because C06's core — reverse native codegen — is
already implemented by kostyk348/phase-vm (via C-AOT), while P4 is ARM64
(mission-central) and about behaviour the project itself models. The full
reasoning is in NOVELTY-LOG "Cuts — consistency check".
