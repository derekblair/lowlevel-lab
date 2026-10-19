# SHORTLIST — lowlevel-lab (post-REVIEW-01)

Author lane. Chosen from [CANDIDATES.md](CANDIDATES.md) on the evidence in
[NOVELTY-LOG.md](NOVELTY-LOG.md). Each concept below gives: the gap it fills,
the evidence that the gap is real, the prototype plan (language, arch, files,
what running it shows, independent oracle), an effort estimate, and the
honest risks. Build order and parallelism are at the end.

**REVIEW-01 outcome (APPROVE WITH CHANGES, commit 19c7ecb → applied here).**
Surviving builds: **P1 smc-observatory** (KEEP N3), **P2 pt-truth** (RESHAPE to
N2), **P4 ifetch-sanitizer** (KEEP N2, ARM64). **CUT: P3 hybrid-diff** (C04 —
libLISA OOPSLA'24 already diffs i9-13900 P vs E cores on undefined shifts/
rotates; N1) and **P5 mirror** (C10 — gperftools `SingleStepper` is a benign
in-process TF stepper; N1). **Two replacement slots are open** (§"Replacements"
below): reviewer's non-binding steer is C12 (cross-ISA machine-code relay) +
one visualization concept (C22-on-P2 or C09). Each replacement needs a
§2.1-complete + ≥2 paper/web novelty addendum, reviewed before its build.

**Theme balance after the cuts:** ARM64 — P4. x86/SMC/tracing — P1, P2.
Visualization of how machines work — **currently none** (P5 cut); a
replacement must restore it. Every prototype builds and runs on nibbles with
present tools only.

**Honest novelty levels:** P1 **N3**, P2 **N2** (reshaped — version-correct PT
decode of rewritten code exists via time-keyed mechanisms; the in-band executed
PTWRITE fence is the surviving delta, to be shown head-to-head), P4 **N2**
(reshaped — stale-fetch demo exists; the coherence matrix + per-step diagnosis
+ line-size-mismatch class is the contribution). Replacements TBD by addendum.

**Machine facts that make these reachable** (topology corrected per REVIEW-01
§1.6/§2.1 — REVIEW-00 §0 did **not** verify topology, and there are **three**
core classes, not two): Intel Panther Lake, family 6 model 0xCC —
**P-cores Cougar Cove = CPUs 0–3 (`cpu_core`); E-cores Darkmont = CPUs 4–11;
low-power LP-E Darkmont = CPUs 12–15 (no L3)**. `cpu_atom` covers both E and
LP-E; the three classes differ in SMC cost (reviewer's sweep) and topology, so
every per-core claim separates P (0–3) / E (4–11) / LP-E (12–15) (R14).
Unprivileged Intel
PT (gdb `record btrace pt`, `set record btrace cpu none`); `perf_event_open`
user-task counting (paranoid=2); `MACHINE_CLEARS.SMC` on both core types +
`MACHINE_CLEARS.XMC` on Darkmont (E/LP-E) only — observability is asymmetric,
P-core cross-modifying clears show only in `SMC`/`COUNT` (R: P1-5);
CET/IBT/LAM present; qemu-aarch64 8.2.2 +
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
  cycles vs write-distance at **sub-page granularity** — same-line plus
  power-of-two offsets 64, 128, 256, 512, 1024, 2048, 4096, with an **aligned
  and a misaligned** code placement — so it resolves the E-core's 1-KB boundary
  and tests **Intel 248966 §3.6.8.1** (avoid writing a code page in the same
  1-KB subpage being executed / fetching in the same 2-KB subpage being
  written) explicitly, per core class (P1-1). Pinned via `sched_setaffinity`,
  median ± spread over ≥5 runs, tolerance stated (P1-3/R11). (2) a cross-core
  experiment: core A patches NOP→RET another core executes, with/without a
  serializing `cpuid`/`SERIALIZE`, reporting visibility latency and XMC-clear
  counts — noting **XMC is observable on Darkmont only**, P-core cross clears
  fold into `SMC`/`COUNT` (P1-5). (3) a torn-fetch probe at a line/page boundary
  — results stated as "observed on this part, under these conditions", not
  guarantees (P1-6).
- **Three core classes, reported separately (R14/P1-2):** P = CPU 0–3, E =
  4–11, LP-E = 12–15 (LP-E has no L3). "E = 4–15" is not acceptable in any
  table. The reviewer's reference sweep (`review/evidence/presearch/c02-probe/`)
  found P clears only within its own 64-B line, E/LP-E on a 1-KB granularity,
  and a P=2-vs-E=1 clears-per-iteration difference that the build must either
  explain or flag as unexplained (P1-3).
- **Oracle:** my clear-count results for a pattern identical to the reviewer's
  probe **must match its reference exactly** (deterministic 9/9 there); timings
  must agree to an order of magnitude (P1-3). Event codes `MACHINE_CLEARS.SMC`/
  `.XMC` from Intel perfmon (family 6 model 0xCC, extracted); `INST_RETIRED`
  sanity. Must cite **Botacin SAP** in the novelty section (P1 / NOVELTY-LOG).
- **Effort:** Medium (≈1 focused build). Counter plumbing is the work.
- **Risks:** (a) perf_event_open PMU selection on hybrid (open on the right
  `type` = cpu_core vs cpu_atom; verify core type in-probe via CPUID.1AH);
  (b) frequency/thermal noise → ratios + spread, pin with taskset;
  (c) **[BLOCKING safety, P1-4]** own-process measurement only — no covert/
  side-channel construction (SMaCk is the attack neighbour); the cross-core
  experiment uses threads of one process and reports latency/clear counts,
  never as a transmission channel (REVIEW-00 §2.4).

## P2 — pt-truth (was C03) · x86 · **N2 (reshaped, REVIEW-01 §2.2)**

**Gap (surviving delta only).** Version-correct decoding of rewritten code
already exists via **time-keyed** mechanisms: wilvk/asm-test's
`asmtest_codeimage` (a userspace `PERF_RECORD_TEXT_POKE` timestamped
code-image timeline consumed by a versioned ptrace stepper), Linux perf's
`intel_pt_text_poke()` (kernel SMC), intel/libipt `sideband/` (image-over-time
at mapping granularity, TSC-keyed), FlowJIT/the Crete MSc thesis (PT of JITed
code), and DRAKVUF's `emit_ptwrite64()` (already injects PTW packets). So the
N3 claim is dead. **What survives (N2):** an *executed* `PTWRITE <version>` as
an **exact, in-band, control-flow-ordered fence** for *same-address* byte
rewrites, versus those time-keyed decoders — which must switch versions at a
TSC/MTC/CYC timestamp and can therefore mis-attribute when a patch and its
execution fall within one timing-packet interval. (Evidence + full dispositions
of items 1–5: NOVELTY-LOG C03, re-confirmed against
`review/evidence/presearch/C03-priorart-excerpts.txt`. The phenomenon — naive
bytes-as-now decode is wrong — is the **known baseline**, demonstrated in
`research/probes/pt-smc-misdecode/`, not the observable.)

**Prototype plan.**
- **Lang/arch:** C for capture (`perf_event_open` with an `aux` ring for
  `intel_pt`), Python stdlib for packet decode + reconciliation. x86-64.
- **Files:** `parts/NN-pt-truth/{AGENTS.md,README.md,RUN.md,Makefile,
  ptcap.c,ptdecode.py,target_smc.c,decode_timekeyed.py,decode_ptwfence.py,
  verify_singlestep.py}`.
- **What running it shows — a HEAD-TO-HEAD (P2-3):** on **one** capture of a
  target that rewrites its own code, run two decoders — a **time-keyed** one
  (switches versions at the timestamped patch event, as perf/libipt-sb/wilvk
  do) and the **PTWRITE-fenced** one — both scored against single-step ground
  truth. The README reports the **patch→execute interval below which the
  time-keyed decode mis-attributes**, at stated timing-packet settings (MTC
  period, CYC on/off). If time-keyed decode turns out exact even at
  cycle-accurate settings, the honest claim shrinks to "exact *without* timing
  packets" — still N2, and stated as such. Not a win by assertion.
- **Oracle:** single-step ground truth (TF/ptrace, independent of the PT path,
  P2-4); `objdump -d` on each per-version snapshot for instruction lengths.
- **Effort:** High (hardest build). PT AUX capture + enough packet decode
  (PSB/PAD/TNT/TIP/FUP/MODE/PTW/CYC/MTC) to walk the target and to implement
  *both* decoders.
- **Risks:** (a) libipt has no header here (gdb links it privately) → I decode
  packets myself in Python; scope the target to the packet subset it produces;
  (b) if from-scratch capture stalls, the gdb probe still proves the baseline,
  and the deliverable degrades gracefully to "demonstrate misdecode + both
  decoders on a captured-to-file trace" — stated in README, not hidden;
  (c) PTWRITE enabled via the `ptw`/`fup_on_ptw` config bits; verified cap
  `ptwrite=1`.
- **Before build start (committed now):** P2-1 (NOVELTY-LOG dispositions +
  drop N3 + explain the wilvk miss + correct the libipt-sb claim) and P2-2/P2-3
  (this rewritten claim + head-to-head observable) are in this commit. BUILD-02
  then implements the head-to-head.

## P3 slot — **CUT: hybrid-diff (C04) → N1** (REVIEW-01 §2.3) · replacement pending

C04 is CUT: **libLISA (OOPSLA 2024)** already diffs the i9-13900's P-cores
(Raptor Cove) and E-cores (Gracemont) on undefined shifts/rotates/mul/div and
proposes fingerprinting (NOVELTY-LOG C04). Panther Lake is a newer generation of
that published comparison ⇒ N1. The migration-hazard reshape is [BLOCKING,
safety] (core-type-dependent predicate = the documented misuse). The probe
(`research/probes/hybrid-undefined-flags/`) survives as SUMMARY research evidence
("the libLISA P/E finding re-confirmed on Panther Lake"), not a part.

**Replacement (reviewer's non-binding steer, §5.5): C12 — cross-ISA machine-code
relay** (x86-64 ELF emits an AArch64 ELF that emits the original, byte-for-byte;
now runnable: x86 native + AArch64 under qemu-aarch64). Reviewer independently
leveled it N2–N3 and found no cross-ISA *machine-code* relay. It restores the
ARM64+x64 machine-code theme. **Gated:** a §2.1-complete + ≥2 paper/web addendum
(G-1/G-2) with per-hit dispositions, a novel observable, and a prototype plan
must be posted as `ADDENDUM READY (C12)` and cleared by the reviewer **before
its build**. Safety (reviewer §5): each stage writes the next stage to **stdout
only**; the harness redirects it and runs it under qemu; nothing writes or execs
itself. **Addendum written** — see NOVELTY-LOG "Replacement addenda" (C12): §2.1-complete (repo 11/topic/ in:readme/ created/ code 2) + G-2 paper/web, dispositions, novel observable, prototype plan. `ADDENDUM READY (C12)` posted; build gated on the reviewer's §6 verdict.

## P4 — ifetch-sanitizer (reshaped C01) · ARM64 · **N2**

**Gap.** Prior art models the *I-side* stale-fetch demo (goliajp/aarch64-study
v0.22, passing tests) and runs the real-hardware skip-flag test
(cyyself/jit-coherence-test), but **neither models the full
`DC CVAU → DSB ISH → IC IVAU → DSB ISH → ISB` sequence as a configurable
coherence matrix with per-step omission diagnosis**: aarch64-study makes
`DC CIVAC` a no-op (no D-cache), varies no `CTR_EL0` bits, and is one fixed
demo; jit-coherence-test is pass/fail on whatever CPU runs it. (Evidence:
NOVELTY-LOG C01; both repos + source read as data, with quotes.) **More prior
art to position against (REVIEW-01 §2.4, in NOVELTY-LOG C01):** herdtools7
`catalogue/aarch64-ifetch/` (litmus-scale, herd7/litmus7), RMEM (exposes the
IDC/DIC knobs at litmus scale), Arm FVP `cache_state_modelled`, DynamoRIO SW
cache consistency (handles app `IC IVAU`, diagnoses nothing). The surviving
delta is the **whole-program** step-naming sanitizer that also covers the I/D
**line-size-mismatch** class (CTR_EL0 differing across cores — the big.LITTLE
JIT bug), which litmus enumeration and fixed demos don't.

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
- **Oracle (BUILD-04 conditions P4-2/P4-3):** **semantic** oracle, not just the
  encoder — in coherent mode the interpreter's end state (registers + memory
  region) must equal **qemu-aarch64 8.2.2** on every kernel (qemu is a valid
  *functional* oracle, `review/evidence/qemu-fidelity/`). The A64 **encoder** is
  differentially tested against `aarch64-linux-gnu-as`/`objdump` 2.42 on ≥20
  instructions **the reviewer chooses at the gate**. Every per-config verdict
  cites quoted architecture text with doc ID + version (**DDI 0487 x.y §…**, not
  an unverified "B2.7.4"); where herdtools7 aarch64-ifetch has a matching test,
  cross-check its expected outcome, fetched as data (herd7 can't be installed).
  Coherence/staleness output is **model output, labelled as such** (P4-4/R10);
  "runs fine under qemu" is presented as qemu's coherence, not silicon evidence.
- **Effort:** Medium-High (assembler + interpreter + matrix).
- **Risks:** (a) **must not collapse** into aarch64-study's single-line demo —
  the matrix + step diagnosis + line-size-mismatch class is the novelty;
  (b) honest labelling: model, not silicon (REVIEW-00 §0.2, R10); (c) scope the
  A64 subset to what the kernels need (P4-5), differentially tested.

## P5 slot — **CUT: mirror (C10) → N1** (REVIEW-01 §2.5) · replacement pending

C10 is CUT: benign in-process TF single-stepping is mainstream — **gperftools
`SingleStepper`** (2024; `gregs[REG_EFL] |= 0x100`, per-instruction callback,
used in tcmalloc_unittest), ERESI e2dbg, v8 trap-fuzzer (NOVELTY-LOG C10). My
"attacks only" claim was false and the record was below §2.1 minimums. Also:
each TF step is an exception+return (FRED here), so a self-tracer sees only the
architectural listing change, never SMC cost.

**Replacement: a visualization-theme concept** (the cuts left visualization at
zero, REVIEW-01 §2.5 / §3). Two candidates, decided in the addendum:
- **C09 — x86 superset-decode lattice**: decode at every byte offset, render the
  overlapping-instruction lattice, and measure how fast misaligned decode paths
  **resynchronise** with the true stream across real `/usr/bin` binaries.
  Independent of P2; own length-decoder + `objdump` oracle. Visualizes a deep
  x86 truth (why disassembly is hard).
- **C22 — PT TNT-bit control-flow barcode**: render PT taken/not-taken bits as a
  per-algorithm texture; rides P2's capture (couples to P2's risk).
Chose **C09** (independent of P2, robust). **Addendum written** — see
NOVELTY-LOG "Replacement addenda" (C09): §2.1-complete + G-2, dispositions,
novel observable (superset lattice + measured resync-length histogram vs
`objdump`), prototype plan. C22 benched as fallback. `ADDENDUM READY (C09)`
posted; build gated on the reviewer's §6 verdict.

---

## Build order, parallelism, and the bench

**Order (REVIEW-01 §5: build P1 right after GATE 1 CLEARED; write addenda
alongside).**
1. **P1 smc-observatory** — builds immediately after CLEARED (no replacement
   dependency). Establishes the perf/affinity harness; BUILD-01 conditions
   P1-1…P1-6.
2. **P2 pt-truth** — P2-1/2/3 are committed now with the record fixes; BUILD-02
   implements the head-to-head.
3. **C12 replacement** (P3 slot) — build after its `ADDENDUM READY (C12)` is
   cleared by the reviewer.
4. **C09 (or C22) replacement** (P5 slot) — build after its addendum is cleared.
5. **P4 ifetch-sanitizer** — ARM64; most "build-the-tooling-yourself"; last so
   the assembler/oracle discipline is warm. BUILD-04 conditions P4-1…P4-5.

I build **one gate at a time** unless the reviewer grants proceed-in-parallel.
**Writing the C12/C09 addenda alongside the P1 build is allowed** (REVIEW-01
§5.6) and is the plan: post both `ADDENDUM READY` lines during the P1
build/review so the reviewer can verdict them while P1 is in flight. No
replacement build starts before its addendum verdict.

**Cut-consistency statement (REVIEW-00 §1.6; REVIEW-01 §3 concurred, "mostly
no", flagging two ranking slips I accept):** (1) C10 was shortlisted ahead of
C12 despite C12 being stronger and mission-central — corrected, C12 is now the
P3-slot replacement. (2) C04 was promoted on its probe without the paper search
that would have found libLISA — corrected, C04 CUT and G-2 (≥2 paper/web per
novelty section) now binds every addendum/README. P4 (ARM64, N2) is kept over
C06 (reversible JIT, N2) because C06's reverse native codegen is already
implemented by kostyk348/phase-vm; full reasoning in NOVELTY-LOG "Cuts".
