# CANDIDATES — lowlevel-lab, Step 1.1

Author lane, 2026-10-18. 23 candidate frames across the theme space (ARM64,
x86-64, self-modifying code, visualization of how computers work, JIT,
code-as-data, esoteric VMs, execution tracing, defensive study of
self-transforming code, hand-rolled assemblers/emulators).

Each entry gives: one-line pitch · why it might be novel · closest existing
thing known *before* searching · what a minimal prototype would prove ·
learning value · feasibility on nibbles · safety. The "closest existing
thing" here is my prior knowledge; the live evidence (exact queries, hits,
verdicts) is in [NOVELTY-LOG.md](NOVELTY-LOG.md), and the post-search status
of every candidate is in the table at the end of this file.

## What this machine makes possible (measured, 2026-10-18)

These facts shaped the candidate space; the frames that exploit them are the
ones least likely to have been done, because few people have this exact rig:

- **Hybrid Intel Panther Lake** (Core Ultra X7 358H, family 6 model 0xCC):
  4 Cougar Cove P-cores (CPUs 0-3, PMU `cpu_core`) + 12 Darkmont E-cores
  (CPUs 4-15, PMU `cpu_atom`). Intel's own perfmon tables (intel/perfmon
  `PTL/events/*.json`) give `MACHINE_CLEARS.SMC` = 0xC3/0x04 on the P-core,
  and on the E-core both `MACHINE_CLEARS.SMC` = 0xC3/0x01 **and a dedicated
  cross-modifying-code counter `MACHINE_CLEARS.XMC` = 0xC3/0x80**.
- **Intel PT works unprivileged** (perf_event_paranoid=2, user-only):
  verified with `gdb record btrace pt` (needs `set record btrace cpu none`
  because libipt 2.0.6 does not know this CPU). PT caps: `ptwrite=1`,
  `ip_filtering=1` (2 ranges), `mtc`, `psb_cyc`. libipt.so.2.0.6 is on disk
  (gdb dependency, no header).
- **Probe result** ([probes/pt-smc-misdecode](probes/pt-smc-misdecode/)):
  gdb+libipt **silently misdecode self-modifying code** — the program prints
  `v1 returned 1` while the hardware-trace history shows that same execution
  as `mov $0x2,%eax; nop×4; ret`, with no gap or warning.
- [CORRECTED 2026-10-19, G-3] AArch64 now **assembles/links/runs under
  qemu-aarch64 8.2.2** on this box (Derek-approved install of qemu-user +
  aarch64-linux-gnu, 2026-10-18 22:13; see TOOLCHAIN.md). This line originally
  read "No AArch64 execution anywhere (no qemu, no ARM CPU)" — that was true at
  21:57 but stale by the time research finished; SHORTLIST.md is correct.
  qemu is user-mode and **SMC-coherent** (REVIEW-00 §0.2), so it runs ARM64
  *functionally* but shows no cache/timing/memory-order behaviour. No ARM CPU,
  no native execution. A separate
  AArch64 GNU as/objdump 2.40 + clang 20.1.8 *also* exists inside the Unreal
  Engine 5.8.2 install (not on PATH) — ruled (REVIEW-01 §1.9): optional
  differential-test oracle only (see STATUS-AUTHOR.md disclosure).
- Also present: CET user shadow stacks, IBT, PKU, LAM, LASS, FRED,
  `cpuid_fault`; KVM usable (in `kvm` group); ffmpeg; headless firefox.

---

## C01 — stale-fetch: an AArch64 emulator with an adversarial I-cache

- **Pitch:** An AArch64 user-mode emulator whose instruction fetch obeys the
  *weakest* behaviour the architecture permits: data stores do not reach
  instruction fetch until the program performs the required
  `DC CVAU → DSB ISH → IC IVAU → DSB ISH → ISB` sequence (honouring
  `CTR_EL0.IDC/DIC`), so a JIT that forgets a step visibly executes stale
  code — and the emulator names the missing step.
- **Why it might be novel:** Practical emulators (QEMU, Unicorn) make
  instruction fetch coherent with stores and so *hide* missing cache
  maintenance; the bug only appears on real silicon (classic: big.LITTLE
  phones with mismatched cache-line sizes breaking JIT flush loops).
- **Closest known:** Arm Fast Models/FVP (models cache state; proprietary,
  full-system); the Cambridge ifetch formal model (Simner et al., ESOP 2020)
  and isla/herd litmus tooling (litmus-test scale, not whole programs);
  QEMU's 2023 `IC IVAU` handling.
- **Minimal prototype proves:** Two versions of the same tiny ARM64 JIT —
  one with correct maintenance, one missing `IC IVAU` (or the `ISB`, or using
  the wrong line size) — produce *different* results under the emulator,
  with a diagnosis naming the missing step; identical results under a
  coherent mode.
- **Learning value:** Very high — Harvard-vs-unified caches, points of
  unification, why ARM requires software maintenance and x86 doesn't, how
  JITs (V8, ART, wasmtime) actually flush, plus a hand-rolled A64 encoder.
- **Feasibility:** Python stdlib emulator + assembler for an A64 subset;
  optional encoding cross-check against the on-disk aarch64 objdump.
- **Safety:** Benign (emulated, educational).

## C02 — smc-observatory: self- and cross-modifying-code cartography on hybrid x86

- **Pitch:** Measure, on real silicon, what self-modifying and
  cross-modifying code *costs* and *does*: a distance sweep (same line, same
  page, next page, far) of SMC machine clears; P-core vs E-core; one core
  patching code another core is executing (visibility latency, XMC clears),
  and a hunt for torn instruction fetch when a patch straddles a boundary.
- **Why it might be novel:** SMC penalties are folklore ("~100 cycles,
  avoid it"), but a reproducible *map* on a hybrid part, with the E-core's
  dedicated XMC counter, is not something I know exists. Cross-modifying
  code is usually discussed only as "follow SDM §9.1.3 or else".
- **Closest known:** Agner Fog's microarchitecture notes; Intel SDM;
  uops.info / nanoBench (instruction latency, not SMC); Linux `text_poke_bp`
  design notes; scattered blog measurements.
- **Minimal prototype proves:** A heatmap of clears/cycles vs write
  distance for P and E cores; a CMC latency histogram per core pair; a
  torn-fetch counter (zero or not) per boundary class.
- **Learning value:** Very high — pipeline nukes, snoop-based SMC detection,
  why JITs separate code and data pages, why the kernel's live patching
  uses an `int3` protocol and Windows hot-patching uses 2-byte `mov edi,edi`.
- **Feasibility:** C + GNU as + raw `perf_event_open` (user-only); verified
  event codes from Intel's perfmon tables.
- **Safety:** Benign (own-process code patching, measurement only).

## C03 — pt-truth: version-correct hardware tracing of self-modifying code

- **Pitch:** Intel PT decoders reconstruct the instruction stream from the
  code bytes *currently* in memory, so self-modifying code is silently
  misdecoded (probe-verified). Fix it: keep a versioned code image and mark
  every code write *in-band* with `PTWRITE <version>`, so the decoder knows
  exactly where in the packet stream the code changed.
- **Why it might be novel:** Known workarounds are side-band and
  time-based (perf jitdump + `perf inject --jit` keyed on timestamps);
  using PTWRITE packets as exact code-version fences is not something I
  have seen.
- **Closest known:** libipt / ptxed, perf intel-pt + jitdump, JPortal
  (PLDI'21, JVM JIT code + PT), gdb `record btrace pt`.
- **Minimal prototype proves:** On a program that rewrites its own code
  inside a loop, gdb's PT history is wrong, ours is exact — verified
  instruction-for-instruction against single-step ground truth.
- **Learning value:** High — PT packet formats (PSB/TNT/TIP/FUP/PTW), how
  hardware tracing compresses control flow, why decoders need the image.
- **Feasibility:** C for capture (perf_event_open + AUX buffer), Python
  for packet decode; objdump on per-version snapshots for instruction
  lengths; unprivileged PT verified working.
- **Safety:** Benign; makes analysis of self-modifying code *more* correct.

## C04 — hybrid-diff: P-core vs E-core differential instruction scanner

- **Pitch:** Execute the same instruction candidates pinned to a P-core and
  to an E-core and diff every observable: legality (SIGILL), length
  (sandsifter's page-boundary trick), results, architecturally *undefined*
  flags, CPUID leaves.
- **Why it might be novel:** sandsifter scanned one core; hybrid parts put
  two microarchitectures behind one ISA. Divergence in "undefined" outputs
  would be visible to software that migrates between cores.
- **Closest known:** sandsifter (Domas, 2017); emulator-vs-CPU differential
  testers (PokeEMU, EmuFuzzer); known CPUID topology inconsistencies.
- **Minimal prototype proves:** A diff report over N million probes; at
  minimum a definitive "no divergence found in classes X, Y" or concrete
  divergent encodings.
- **Learning value:** High — x86 encoding, undefined behaviour, hybrid
  scheduling.
- **Feasibility:** C + sched_setaffinity + seccomp-strict probe children.
- **Safety:** Benign (own-process instruction probing, syscalls blocked).

## C05 — silicon-corewar: Core War with native warriors on real cores

- **Pitch:** Core War where warriors are real x86-64 machine code executing
  natively, each pinned to its own physical core, in one shared RWX arena —
  so the battle physics is the CPU's actual cross-modifying-code and cache
  coherence behaviour.
- **Why it might be novel:** Every Core War I know (pMARS, CodeGuru Xtreme)
  runs on an emulated VM with a time-sharing scheduler.
- **Closest known:** Redcode/pMARS, CodeGuru Xtreme (8086, emulated), ICWS.
- **Minimal prototype proves:** A referee runs battles, attributes every
  arena byte to its writer, and renders the arena over time; results show
  outcome distributions that depend on core placement (P vs E).
- **Learning value:** Medium-high — CMC, coherence, signals, seccomp.
- **Feasibility:** C + GNU as; seccomp-filtered warrior threads.
- **Safety:** Benign game in own process; warriors cannot make syscalls.

## C06 — reversible-jit: a reversible ISA with a bidirectional x86-64 JIT

- **Pitch:** A tiny reversible instruction set (PISA/BobISA-style: every
  instruction has an exact inverse, branches are paired) whose JIT emits
  *two* native x86-64 code streams — forward and inverse — so programs run
  backwards at native speed and restore their initial state exactly.
- **Why it might be novel:** Reversible ISAs exist with interpreters and
  simulators; reverse debuggers record state. A JIT that generates inverse
  machine code is not something I know exists.
- **Closest known:** Pendulum/PISA (MIT), BobISA, Janus→PISA compilers,
  REL-16-style VMs; rr/gdb reverse execution (log-based).
- **Minimal prototype proves:** Fibonacci/sorting programs run forward and
  backward natively; garbage-free uncompute returns memory to its initial
  state bit-for-bit; JIT output matches the reference interpreter.
- **Learning value:** High — information conservation, Landauer, why
  ordinary ISAs are irreversible, JIT emission.
- **Feasibility:** C or Python→machine code; mmap RX.
- **Safety:** Benign.

## C07 — isa-hop: one process that hops between native x86-64 and emulated AArch64

- **Pitch:** The same program compiled (by our tiny compiler) to x86-64 and
  AArch64 with a unified stack/frame layout; at basic-block boundaries the
  process hops between native x86-64 execution and an in-process AArch64
  emulator sharing the same memory, by swapping register files.
- **Why it might be novel:** Heterogeneous-ISA migration is research-grade
  (Popcorn Linux; Unifico) and between machines; an educational in-process
  hop is not something I know exists.
- **Closest known:** Popcorn Linux, Unifico (CC'24), DBT exit-to-interpreter.
- **Minimal prototype proves:** Results are identical regardless of hop
  schedule (every block / random / never).
- **Learning value:** High — ABI, register mapping, flags semantics.
- **Feasibility:** Needs a compiler to two ISAs + A64 emulator in C.
- **Safety:** Benign.

## C08 — a64-atlas: whole-encoding-space atlas of AArch64

- **Pitch:** Map all 2^32 A64 encodings on a Hilbert curve coloured by
  instruction class; diff against binutils' decoder.
- **Why it might be novel:** Visually striking ISA-design lesson.
- **Closest known:** binvis (files, not ISAs); x86 opcode tables.
- **Minimal prototype proves:** A full-space image + disagreement list.
- **Learning value:** Medium.
- **Feasibility:** Easy. **Safety:** Benign.

## C09 — x86-lattice: the superset-decoding lattice of x86 code

- **Pitch:** Decode at *every* byte offset, draw the resulting
  instruction lattice, and measure how fast misaligned decode paths
  resynchronise with the true stream across real binaries.
- **Why it might be novel:** Superset disassembly exists as a technique;
  a visual + statistical explainer of x86's self-synchronisation is rare.
- **Closest known:** Multiverse (superset disassembly, NDSS'18),
  probabilistic disassembly (ICSE'19), Linn & Debray.
- **Minimal prototype proves:** Resync-length distributions for /usr/bin
  binaries + an interactive lattice view.
- **Learning value:** High (x86 encoding).
- **Feasibility:** Own length decoder in C, objdump as oracle.
- **Safety:** Benign (analysis).

## C10 — mirror: a program that watches itself execute

- **Pitch:** An x86-64 program that sets the trap flag on itself (no
  ptrace), records every instruction it executes from a SIGTRAP handler,
  and renders its own execution — including its own self-modification —
  as a live terminal animation.
- **Why it might be novel:** Self-tracing via TF is an anti-debug trick,
  rarely a teaching instrument.
- **Closest known:** ptrace-based tracers; Qira/Tenet trace explorers.
- **Minimal prototype proves:** Exact instruction trace from in-process TF
  matches gdb's; SMC visible as the listing changes.
- **Learning value:** Medium-high.
- **Feasibility:** Easy (C + inline asm). **Safety:** Benign.

## C11 — mini-rosetta: AArch64 → x86-64 binary translator

- **Pitch:** Translate a small AArch64 ELF (made by our own assembler) into
  a native x86-64 ELF, with an exhaustively verified NZCV↔EFLAGS mapping
  (ARM's C flag after SUB is the inverse of x86's CF).
- **Why it might be novel:** Educational A64→x64 translators are rare.
- **Closest known:** dynarmic, Ryujinx ARMeilleure, QEMU TCG, lunatic (ARMv4/5).
- **Minimal prototype proves:** ARM64 programs run natively on nibbles.
- **Learning value:** High. **Feasibility:** Medium. **Safety:** Benign.

## C12 — quine-relay-isa: a cross-ISA machine-code quine relay

- **Pitch:** An x86-64 ELF that prints an AArch64 ELF that prints the
  original x86-64 ELF, byte for byte.
- **Why it might be novel:** Quine relays are source-level; binary quines
  are single-ISA.
- **Closest known:** mame/quine-relay; ELF quines; Susam Pal's
  self-printing machine code.
- **Minimal prototype proves:** Fixed point verified via our A64 emulator.
- **Learning value:** Medium (ELF, encodings). **Feasibility:** Medium.
- **Safety:** Benign.

## C13 — bitflip-map: single-bit fault sensitivity of machine code

- **Pitch:** Flip every bit of a small program's code, run each mutant
  (sandboxed native x86-64 / emulated A64), classify outcomes, render a
  sensitivity map over the bytes.
- **Closest known:** FiSim (Riscure), ARMORY, LLFI, GOOFI.
- **Learning value:** Medium. **Feasibility:** Easy. **Safety:** Benign
  (defensive fault-tolerance study).

## C14 — skid-map: sampling-skid atlas per core type

- **Pitch:** Map where perf samples land relative to the instruction that
  caused the event, with and without `precise_ip`, on P vs E cores.
- **Closest known:** PEBS documentation; PERF_SAMPLE_SKID_IP patches.
- **Learning value:** Medium. **Feasibility:** Medium (paranoid=2 allows
  user-only sampling). **Safety:** Benign.

## C15 — rep-probe: fast-string progress granularity via guard pages

- **Pitch:** Use a guard page to stop `rep movsb/stosb` mid-flight and read
  RCX/RSI/RDI to infer the internal chunking of fast-string microcode, per
  core type.
- **Closest known:** SDM fast-string notes; Raymond Chen's 2025 post on
  partial progress.
- **Learning value:** Medium. **Feasibility:** Easy. **Safety:** Benign.

## C16 — befunge-smc-jit: Befunge JIT that honours self-modification

- **Pitch:** JIT Befunge-93 to x86-64 and invalidate/recompile on `p`.
- **Closest known:** Befunge JITs (Betty, Befunjit, Bejit).
- **Learning value:** Medium. **Feasibility:** Easy. **Safety:** Benign.

## C17 — cpuid-mirror: see (and steer) every CPUID a program executes

- **Pitch:** Use CPUID faulting (`arch_prctl(ARCH_SET_CPUID)`) to trap every
  CPUID, log what code probes, and optionally spoof answers to exercise
  fallback paths.
- **Closest known:** rr (uses CPUID faulting); Intel SDE (feature spoofing);
  glibc tunables (hwcap masking).
- **Learning value:** Medium. **Feasibility:** Medium (faulting resets on
  exec → needs ptrace injection). **Safety:** Benign.

## C18 — loader-film: watch the dynamic loader rewrite a process

- **Pitch:** Animate ld.so applying relocations and lazy binding patching
  the GOT — runtime code-as-data.
- **Closest known:** LD_DEBUG; countless PLT/GOT blog posts.
- **Learning value:** Medium. **Feasibility:** Easy. **Safety:** Benign.

## C19 — native-tierra: artificial life in real machine code

- **Pitch:** Tierra-style self-replicators as native x86-64 code under
  seccomp.
- **Closest known:** Tierra, Avida, evolved machine code GP (Discipulus).
- **Safety:** Borderline optics (self-replicating native code).
  **Learning value:** Medium.

## C20 — cfi-duel: CET shadow stack (native) vs PAC (emulated)

- **Pitch:** Show the same return-address corruption caught by x86 CET
  natively and by A64 PAC in an emulator.
- **Closest known:** kernel selftests `test_shadow_stack.c`; QEMU PAC.
- **Safety:** Requires demonstrating a control-flow hijack — exploit-
  adjacent. **Expected: CUT.**

## C21 — meta-equiv: equivalence checking of metamorphic variants

- **Pitch:** Show that semantically-equivalent rewrites of a code block
  normalise to the same canonical form (defensive).
- **Closest known:** BinHunt, BinDiff, Esh, Asm2Vec, semantics-based
  malware detection literature.
- **Safety:** Producing the variants is metamorphic-engine work — the brief
  forbids tooling that only makes sense for malware. **Expected: CUT.**

## C22 — tnt-barcode: control-flow barcodes from hardware trace bits

- **Pitch:** Render PT's taken/not-taken bit stream as an image —
  algorithms get visual "textures" (quicksort vs mergesort vs bubble sort).
- **Closest known:** magic-trace (function-level PT → Perfetto),
  perf branch samples.
- **Learning value:** Medium. **Feasibility:** Easy once PT capture exists
  (shares C03 capture). **Safety:** Benign.

## C23 — kvm-pagewalk: a KVM mini-guest that visualises page walks

- **Pitch:** Build page tables by hand, run a tiny KVM guest, and visualise
  the 4/5-level walk for chosen addresses.
- **Closest known:** many "KVM hello world" repos; page-table visualisers.
- **Learning value:** Medium. **Feasibility:** Easy. **Safety:** Benign.

---

## Post-search status (filled in from NOVELTY-LOG.md)

See the end of [NOVELTY-LOG.md](NOVELTY-LOG.md) for the verdict table.
