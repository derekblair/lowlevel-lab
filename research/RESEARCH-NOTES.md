# RESEARCH-NOTES — mechanism grounding for the 5 builds

Author lane, written while awaiting REVIEW-01 (no builds started). These are
the mechanism facts each shortlisted build must get right, plus the reviewer
challenge I expect per concept and how the design answers it. Sourced from the
evidence already in `research/raw/` + verified machine probes; no new searches
(the reviewer is mid-Gate-1 and we share one gh token — I'm not competing for
the search bucket while REVIEW-01 is in flight).

## P1 — smc-observatory

**Mechanism facts to get right.**
- On x86, a store into bytes an in-flight instruction will fetch triggers an
  SMC machine clear (nuke): the pipeline is flushed and fetch restarts. Event:
  `MACHINE_CLEARS.SMC` (P-core 0xC3/0x04, E-core 0xC3/0x01, from Intel perfmon
  family-6-model-0xCC tables, extracted to `research/raw/` discussion).
- Cross-modifying code (one core writes code another core runs) needs the SDM
  §9.1.3 handshake (serializing instruction before executing patched bytes);
  the E-core exposes a dedicated `MACHINE_CLEARS.XMC` 0xC3/0x80.
- `perf_event_open` with `type` = the hybrid PMU (`cpu_core` vs `cpu_atom`,
  read from `/sys/bus/event_source/devices/*/type`), `config` = event|umask<<8,
  `exclude_kernel=1`, pinned with `sched_setaffinity`. paranoid=2 permits
  counting own task. RDPMC is not exposed (`.../rdpmc` empty), so read via the
  fd (or mmap self-monitoring), not a bare `rdpmc`.
**Expected reviewer challenge:** "this is just SMaCk / a known ~100-cycle
number." **Answer:** SMaCk is an L1i *attack* measured on older non-hybrid
parts (confirmed from its source + arXiv full text); the deliverable is a
benign *cost/behaviour map* over write-distance × core-type × cross-core with
the E-core XMC counter — a combination no read repo produces. Report ratios
with spread, not a single cycle count.
**Honesty line:** no cache-attack primitive; own-process patches only.

## P2 — pt-truth  (highest build risk)

**Mechanism facts.**
- Intel PT emits packets into a `perf_event_open` AUX ring: PSB (sync), PSBEND,
  TNT (taken/not-taken bits), TIP/TNT/FUP (IPs, compressed via "last IP"), MODE,
  CBR, PAD, OVF, and PTWRITE payloads (needs `ptw` config bit; `fup_on_ptw`
  adds a FUP with the IP). Verified caps: `ptwrite=1`, `ip_filtering=1`.
- A decoder needs the *instruction bytes that executed* to resolve TNT bits to
  edges — that's why SMC/JIT breaks it: it reads bytes-as-now. Proven on this
  box: `research/probes/pt-smc-misdecode/` (gdb+libipt silently wrong).
- The fix: at each self-patch the target executes `PTWRITE imm=<version>`; the
  decoder keeps a per-version snapshot of the code region and, on seeing the
  PTWRITE payload in the stream, switches the image it decodes against. So the
  version fence is *in-band and ordered* with the control-flow packets — unlike
  perf jitdump / `perf inject --jit`, which key on side-band timestamps.
**Expected reviewer challenge:** "libipt already supports an image callback /
you reinvented perf jitdump." **Answer:** libipt's `pt_image_set_callback`
(read as data) supplies *one* current image; it has no notion of
version-fenced images ordered against packets, and LLDB's wrapper "does not
handle self-modified code… only signals the anomaly as a trace error"
(web-confirmed). jitdump is side-band + timestamp-keyed, not in-band packet
order. The novel observable is a decode that is *correct* where libipt is
*silently wrong*, proven against single-step ground truth.
**De-risk:** capture to a file first and decode offline; the from-scratch
decoder only needs the packet subset the target emits; the gdb probe backs the
claim even if scope shrinks (README states the fallback — no hidden failure).

## P3 — hybrid-diff

**Mechanism facts.**
- Core type at runtime: `CPUID.1AH:EAX[31:24]` (0x40 = Core/P, 0x20 = Atom/E),
  read *inside* the pinned probe to prove affinity was honoured.
- Undefined-flag rule already characterised (probe): shifts/rotates count≥2 →
  OF differs P vs E (P first-step, E last-step); results + SAR agree.
- Length/legality via the sandsifter page-boundary trick: place the candidate
  so it straddles a guard page; SIGSEGV vs SIGILL distinguishes "decoded, ran
  off the page" (legal, length = bytes before the fault) from "#UD" (illegal).
  Probe children run under `seccomp` strict-ish with a SIGILL/SIGSEGV handler.
**Expected reviewer challenge (now pre-empted):** "Intel documents that P/E
differ on undefined OF, so this isn't novel." **Answer (disclosed in README +
NOVELTY-LOG):** correct — the bare fact is public (Intel 12th-Gen Game Dev
Guide, Wikipedia). The N2 contribution is the *tool* (no public scanner diffs
the two core types of one die), the *specific rule* each core follows (prose
gives none), and the migration-visible demo. yufengzjj/hybrid-x86-oracle diffs
model backends, not core types — usable as a tie-break oracle, not a duplicate.

## P4 — ifetch-sanitizer (ARM64, reshaped)

**Mechanism facts.**
- Correct A64 code-patch sequence: `DC CVAU` (clean D to Point of Unification)
  → `DSB ISH` → `IC IVAU` (invalidate I to PoU) → `DSB ISH` → `ISB`. `CTR_EL0`
  `IDC`=1 lets you skip the DC step, `DIC`=1 lets you skip the IC step. Line
  sizes (`CTR_EL0.DminLine`/`IminLine`) drive the loop stride — a mismatch is
  the classic big.LITTLE JIT breaker.
- Prior art (read as data): goliajp/aarch64-study models I-side only (DC CIVAC
  a no-op), one fixed demo, no CTR_EL0 variation; cyyself/jit-coherence-test is
  pass/fail on the host CPU with skip flags. Neither diagnoses *which* step is
  missing across a config matrix.
**Expected reviewer challenge:** "collapses into aarch64-study's demo" / "you
can't run ARM64 natively here." **Answer:** the centrepiece is the coherence
*matrix* + per-step omission *diagnosis* (neither prior art has it); the A64
*encoder* is differentially tested against aarch64-linux-gnu as/objdump (real
oracle), while cache behaviour is explicitly *model output* (REVIEW-00 §0.2/R10)
— labelled, never claimed as silicon; qemu-aarch64 (SMC-coherent, §0.2) is the
"silent here, broken there" contrast, not a fidelity claim.

## P5 — mirror

**Mechanism facts.**
- Set TF (EFLAGS bit 8) in the signal `ucontext->uc_mcontext.gregs[REG_EFL]`
  from the SIGTRAP handler so each instruction re-traps; the kernel clears TF
  on handler *entry* (so a self-SIGTRAP handler doesn't loop) — re-arm it on
  handler exit, and handle the first-instruction "stuck TF" quirk (web-noted).
- No ptrace, no child: the process traps itself. Record RIP + register deltas
  per step; render with curses/ANSI (tkinter absent). The SMC demo patches its
  own arithmetic immediate and the listing visibly changes under the cursor.
**Expected reviewer challenge:** "TF self-stepping = anti-debug trick / sgx-step."
**Answer:** the mechanism is shared, the *purpose* is a benign teaching
visualizer of a program's own execution incl. its own SMC — no analysis
evasion, no foreign process (REVIEW-00 §2.4). Oracle: trace must match gdb's
single-step of the same binary.

---

**Cross-cutting build discipline (so builds pass REVIEW-00 §2.2 first time):**
each `parts/NN-*/` gets AGENTS.md + README (with a Requirements line naming
every tool beyond gcc/binutils/make/python3-stdlib, R8), a Makefile/build.sh
using present tools only, RUN.md with verbatim commands+output+exit codes and a
declared-nondeterminism note (R3), the named novel observable pointing at the
RUN.md lines that show it (R4), a differential-oracle test for any encoder/
decoder/emulator (R6), and commits touching only my paths with the lane author
identity (R7/R12). No network, no sudo, no writes outside the tree (R: §2.2).
