# SUMMARY — lowlevel-lab

Author lane, Step 3. Five low-level project frames were chosen for novelty
against live GitHub and the literature (Gate 1: [research/](research/), cleared
at REVIEW-01). Each was then built as a small runnable prototype and gated under
adversarial review.

Two Step-1 concepts were **cut on the reviewer's prior-art evidence**:
- P3 / C04, the hybrid P/E undefined-flags diff: **libLISA** (OOPSLA'24) already
  diffs P- against E-cores.
- P5 / C10, the in-process TF mirror: **gperftools `SingleStepper`** already
  does it.

They were replaced by **C12** and **C09**. The five built are **P1, P2, P4, C12
and C09**. Every x86 result ran **natively** on this machine's Intel Panther Lake
(family 6 model 0xCC), with core classes kept separate: Cougar Cove P = CPUs
0–3, Darkmont E = 4–11, Darkmont LP-E = 12–15. Every AArch64 result ran **under
qemu-aarch64 8.2.2, never on silicon**, and P4 is explicitly a **model**.

## The five, ranked by novelty confidence

The ranking is by how confident the evidence lets me be that the *observable*
is not already public. That is the mission's bar: "genuinely novel, not already
on GitHub". Difficulty and what each proves are separate axes, covered per
concept below.

| # | concept | arch | novelty | strongest prior-art threat | gate |
|---|---|---|---|---|---|
| 1 | **P1 smc-observatory** | x86 hybrid, native | **N3** | Botacin, Zanata & Grégio, *SMC-Aware Processor (SAP)* + `marcusbotacin/Self-Modifying-Code`: one core class, no distance sweep, no hybrid split, no XMC | CLEARED r2 |
| 2 | **C12 cross-ISA quine relay** | x86-64 + AArch64 (qemu) | **N3** | **Actually Portable Executables**: *one* self-rewriting multi-arch binary with a dispatcher, not a chain of single-ISA binaries. Also `ixty/xarch_shellcode`, Arm64X, and source-level `mame/quine-relay` | CLEARED r1 |
| 3 | **P4 ifetch-sanitizer** | AArch64 (modelled) | **N2** | **herdtools7 `aarch64-ifetch` + RMEM**: litmus-scale, IDC/DIC knobs, no whole-program step naming, no line-size class | CLEARED r3 |
| 4 | **P2 pt-truth** | x86, native | **N2** | **`wilvk/asm-test` `asmtest_codeimage`**, plus perf `intel_pt_text_poke`, libipt `sideband/`, DRAKVUF `emit_ptwrite64`: time-keyed version decoding exists | CLEARED r2, re-opened by me (see P2) |
| 5 | **C09 x86 superset lattice** | x86-64, native | **N2** | **Linn & Debray CCS'03 §3.1** *published* the resync claim qualitatively; Andriesse et al. 2016 restates it differently | CLEARED r2 |

Why this order:
- **The two N3s lead** because their gap is a missing artifact: no public tool
  does it at all.
- **The three N2s are reshaped deltas** against real, named prior art. P4's
  delta is the most substantial: whole-program step naming, store ordering, and
  the line-size class.
- **P2's delta is narrow but now mechanistic.**
- **C09 is last** because the phenomenon it measures is itself published. Its
  novelty is the measurement and the visualization, and it is defended as
  exactly that.

## Per concept — what the prototype proves, and its honest limits

### 1 · P1 smc-observatory — `parts/01-smc-observatory/` (N3, CLEARED)

**Proves** that the self-modifying-code detection window on this die is
**microarchitecture-specific**. It was measured deterministically (0.00
clears/iter spread across repeats) and matched the reviewer's independent
reference sweep:
- **Cougar Cove P-cores** clear only within the executing code's **64-byte
  line** (`P@63` = 2.00, `P@64` = 0.00).
- **Darkmont E / LP-E** clear on a **1 KiB subpage** (`E@1023` = 1.00, `E@1024`
  = 0.00). That matches **Intel 248966 §3.6.8.1**, which the data shows does
  **not** describe Cougar Cove.
- The window tracks the **code's subpage, not the page base**.
- In-window clears per iteration are exactly **P = 2.000, Darkmont = 1.000**.
- **Cross-core patching is booked differently by class.** A Darkmont executor
  books it as `MACHINE_CLEARS.XMC` (≈1.1×10⁵ per 10⁶ iterations, SMC ≈ 0). A
  Cougar Cove executor books it as `SMC` (≈1.5×10⁵ per 10⁶), and Cougar Cove has
  no XMC counter.
- **No torn instruction fetch was observed** across a line-straddling patch.

**Limits:**
- These are observations on one part under stated conditions, not
  architectural guarantees.
- Measurement is strictly own-process. The side-channel neighbour (SMaCk) is
  out of scope by design.
- The P=2 vs Darkmont=1 clears-per-iteration difference is measured exactly,
  but its cause is not established.

### 2 · C12 cross-ISA machine-code quine relay — `parts/03-quine-relay/` (N3, CLEARED)

**Proves** a true **byte-exact cross-ISA fixed point**:
1. A hand-emitted x86-64 ELF (`stage0`) writes an **AArch64** ELF (`stage1`).
2. Run under qemu-aarch64, `stage1` writes `stage2`.
3. `stage2` is **byte-identical to `stage0`** (`cmp` + sha256).

The checks:
- `readelf -h` confirms stage0/stage2 are x86-64 and stage1 is AArch64.
- Both ISAs' code decodes (GNU objdump) to the intended instruction sequences.
- A **fail-closed** audit shows each stage makes exactly 3 × `write(1,…)` +
  `exit` and nothing else.

It is a relay, not a polyglot: the other ISA's bytes are carried only as data.

**Limits:**
- The load address and alignment are conventions, not requirements. Review
  found the real silent failure was a missing `+x`, not alignment; that was
  corrected.
- The stages are syscall-only freestanding ELFs.
- The AArch64 stage runs **under qemu, never on silicon**.

### 3 · P4 ifetch-sanitizer — `parts/04-ifetch-sanitizer/` (N2, CLEARED)

**Proves (as a model)** a **whole-program** check for missing AArch64
instruction-cache maintenance. It reads the program, not a recipe. An A64
interpreter decodes the kernel's actual `STR / DC CVAU / DSB / IC IVAU / ISB`,
drives an I/D coherence model, and re-fetches the patched slot through it.
- The correct `DC→DSB→IC→DSB→ISB` sequence is fresh in every valid `CTR_EL0`
  config.
- **Each omission is named.** The barriers are kept even where `IDC`/`DIC`
  excuse the cache op, as in Linux `cache.S`, so a missing ISB is stale even
  under `IDC=1,DIC=1`. A missing DSB before the IC is named as the DSB.
- The impossible `{IDC=0,DIC=1}` config is excluded, quoting Arm CTR_EL0
  verbatim.
- **Order matters.** "Flush, then write", a second unmaintained patch, and a DC
  issued before the STR are each diagnosed **stale with a named cause**.
- **The big.LITTLE line-size bug is caught from the program's own addresses.**
  A stride-128 flush loop (a line size read from another core) skips the
  slot's 64-byte line and is diagnosed stale. Stride 64 is fresh.

**Oracles:**
- The encoder is 22/22 byte-identical to `aarch64-linux-gnu-as`, and 120/120 on
  the reviewer's own seeds.
- The coherent-mode end state equals qemu on **all 13 kernels**.
- The reviewer's 15 independent probes are all architecturally right.

**Limits:**
- **Model, not silicon.** qemu is coherent and *cannot* show stale fetches.
- The model reports "not guaranteed" as **stale** (conservative). Real silicon
  may happen to fetch new bytes in some of those cases.
- It covers a scoped A64 subset, straight-line kernels and one PE.
- `DSB ISHST` is accepted wherever a DSB is required; whether that suffices
  after `DC CVAU` when IDC=0 is UNVERIFIED either way.
- Linux's `ARM64_MISMATCHED_CACHE_TYPE` trap mitigates the line-size class in
  practice.

### 4 · P2 pt-truth — `parts/02-pt-truth/` (N2, CLEARED then re-opened)

**Proves**, on one Intel PT capture of self-modifying code scored against
independent trap-flag single-step ground truth:
- **An executed in-band `PTWRITE(version)` fence attributes every execution to
  its exact code version.** That holds on **every core class**, across the
  whole patch→execute range, with **no timing packets**.
- **The strong time-keyed decoder** (TMA-anchored, MTC-*payload* clock, the way
  perf/libipt reconstruct time) **behaves per core class**:
  - **Darkmont (E, LP-E): exact only over an interval band.**
    - It fails at the shortest intervals.
    - It fails at long gaps from the **predicted** 2^(mtc_period+8) CTC × 192/2
      = **196,608 TSC ticks**, the 8-bit MTC payload wrap.
    - With branch tracing off, Darkmont's trace carries only ~200–400 MTCs and
      a single TSC per capture, and 43–77% of consecutive MTC steps are a
      whole payload wrap (Δ0). So the clock cannot see the wraps that elapsed.
  - **Cougar Cove (P): exact at every interval ≥ 2 MTC periods**, out to
    ~10⁷ TSC, because its trace carries an MTC **every period**. Its lower
    edge sits at about one MTC period (768 TSC), the clock's resolution. A
    dedicated probe found failures only for median intervals below ~1.2
    periods. The price is a trace ~220–510× larger.
  - So the fence's **accuracy** advantage is on Darkmont (both regimes), and
    on P only near or below one MTC period. On every class it needs no timing
    packets and no particular emission density.

**Why it was re-opened.** This per-class split surfaced *after* P2 cleared,
when I applied the reviewer's nit to pin the captures. The cleared runs were
unpinned. Because it changes a cleared claim, I re-opened the gate rather than
fold it in. Review then caught me over-generalizing the short-interval failure
to every class (REVIEW-02 round 3, B3). The statement above is the corrected
one.

**Limits:**
- The delta is narrow and stated as such: "exact without timing packets, and
  exact where time-keyed fails".
- The core-class mechanism is **inferred from packet counts** in one
  configuration (BranchEn=0, `mtc_period` 3). Each class is represented by a
  single CPU.
- The framer is packet-level, not a full PT instruction decoder.
- CYC is enabled but not decoded. That can only understate time-keyed accuracy
  where fine mode is already exact.

### 5 · C09 x86 superset lattice — `parts/05-x86-lattice/` (N2, CLEARED)

**Proves**, by decoding x86-64 at **every byte offset** with an objdump
authority, that misaligned decode streams rejoin the compiler-intended stream
in a measured, not asserted, distribution. The authority (`-w -z`) is
self-checked for contiguity and cross-checked at all 39,249 true boundaries.
- **Ground truth:** 8 self-built `gcc -O2` objects; 61 function entries are
  confirmed by the symbol table; n = 8,400 misaligned starts.
  - The **median is 2 instructions**: 49% resync within 1, 71% within 2, 83%
    within 3, and the longest takes 14.
  - Excluding chains through a `(bad)` decode, the median is **1**.
- **Reference decode, `/usr/bin`:** 5 binaries, n = 115,884. The median is also
  2, with a heavier tail (P≤2 56%, max 101). That tail is entirely
  `(bad)`-driven: the `(bad)`-free subset matches ground truth (77% vs 76%).

That **settles the published disagreement**: Linn & Debray's "one or two" and
Andriesse et al.'s "two or three" describe **different populations**, and the
`(bad)` policy is the hinge. The reviewer re-derived every pooled figure with
an independent tool, and got the same picture on a different corpus.

`lattice.html` is a real superset lattice: true-stream arcs, misaligned arcs,
merge points, and example chains followed to their merge. A VERDICT re-derives
every arc's geometry, every merge and the histogram from the embedded data.
`lendec.py`, a from-scratch length decoder, has **0 wrong** sizes on the corpus.

**Limits:**
- The five claims were **formulated from this measurement**. They are
  regression pins, not pre-registered tests, and the README says so.
- The `(bad)`-free population is biased short by selection.
- The corpus is gcc-only and modest (~11 KB of ground-truth code).
- Stripped binaries have only a reference decode.

## Cross-cutting honesty

- **qemu is not silicon.** P4 and C12's AArch64 stage are never described as
  running "on ARM64". qemu is SMC/ifetch-coherent: it validates function, and
  structurally cannot exhibit the stale cases P4 models.
- **x86 results are native and part-specific.** Every per-core claim separates
  P / E / LP-E. P2's correction shows why that rule matters.
- **Every quantitative claim is a grep-able `VERDICT PASS` in its part's
  RUN.md**, reproduced under `env -i` from a clean tree. Independent oracles are
  the authority, not the tool under test: GNU `as`/`objdump`, qemu, trap-flag
  single-step, and the symbol table.
- **What adversarial review changed** (each fix is recorded in
  `builds/BUILD-NN.md`):

| part | rounds | what review caught |
|---|---|---|
| P1 | 2 | torn-fetch probe had zero power (vacuous VERDICT); a false run instruction |
| P2 | 2 + re-open (+1) | time-keyed baseline was a packet-counting strawman; non-reproducible `make` (OVF); later, my own pinning split the long-gap result by core class, and review then caught me over-generalizing the short-interval failure to every class |
| C12 | 1 + nits | a false "64 KiB alignment required" claim (the real cause was a missing `+x`); fail-open safety checks |
| P4 | 3 | verdict read a recipe, not the program; IDC=1 dropped a barrier and an impossible config; citation unquoted; then freshness ignored store order |
| C09 | 2 | objdump parsed without `-w`/`-z` (false boundaries, lengths capped at 7); a one-function anecdote; no lattice actually drawn |

## v2 — the three most promising directions

1. **A native ARM64 run (e.g. Apple Silicon): the biggest single upgrade.**
   - **P4:** silicon could turn the model's verdicts into **measurements**.
     - Observe actual stale fetches.
     - Measure how often each "not guaranteed" case really shows stale bytes,
       per `CTR_EL0` value the part reports.
     - Test the line-size class on cores that report different minimum line
       sizes.
     - Confirm the per-config skips, which herdtools7 (full sequence only)
       and qemu (coherent) cannot.
   - **C12:** the AArch64 stage would run on-core.
   - **Porting caveat:** macOS uses Mach-O, its own syscall ABI, and W^X JIT
     rules (`MAP_JIT`, `pthread_jit_write_protect_np`). So the ELF stages and
     the Linux-syscall kernels must either be ported, or run under Linux on the
     same hardware.
2. **A hybrid-core tracing study, growing out of P1 and P2.** P2 found that
   Cougar Cove and Darkmont emit PT timing packets at ~1000× different densities
   under BranchEn=0, and P1 found they detect SMC at different granularities and
   book cross-modification to different counters. Next:
   - Sweep MTC/TSC/CYC emission per class, with BranchEn=0 vs 1 and across
     `mtc_period` values.
   - Measure where time-keyed decoding breaks on each class.
   - Write it up as practical guidance for tracing JITs on hybrid parts.
3. **C09 at scale, plus the benched C22 viz.**
   - Widen the corpus: clang and gcc, `-O0` to `-O3`, whole distributions.
   - Attribute what derails resync: instruction classes, padding, VEX prefixes.
   - Add the C22 PT control-flow "barcode" renderer on top of P2's capture.

   This turns one measured distribution into a population study of x86
   self-repairing disassembly.
