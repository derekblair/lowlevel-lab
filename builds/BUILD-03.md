# BUILD-03 — quine-relay (C12, P3-slot replacement)

Author lane. Build of the P3-slot replacement C12 (APPROVED at N3, REVIEW-01
§6.1), under proceed-in-parallel. Part dir: `parts/03-quine-relay/`.

## What was built

A **2-cycle cross-ISA machine-code quine relay**. `build_fixpoint.py` (Python
stdlib, hand-emitted machine code) writes `stage0`, an x86-64 ELF. Running it
emits `stage1` (an AArch64 ELF); running `stage1` under qemu-aarch64 emits
`stage2`, **byte-identical to `stage0`**. The fixed point uses one shared payload
`P = header_X‖code_X‖header_A‖code_A` carried verbatim by both stages, so each
stage emits the OTHER ISA's header+code (read out of P as data) plus P.

## The result (a true fixed point, not the fallback)

`sha256(stage0) == sha256(stage2)`, `cmp stage0 stage2` byte-identical. So C12-6
(the "two one-way emitters" fallback) did **not** apply — the full fixed point
ships. All 6 verify VERDICTs PASS (exit 0), captured in RUN.md.

## How verified

- **C12-1 fixed point + single-ISA ELFs:** `cmp`/`sha256sum` show stage0==stage2;
  `readelf -h` shows stage0/stage2=X86-64, stage1=AArch64; stage1 disassembled
  with `aarch64-linux-gnu-objdump`.
- **C12-2 safety:** `strace` (x86 stage0) and `qemu-aarch64 -strace` (stage1)
  show only `write(1,…)` + `exit` — no open/execve/fork/mmap/network. No stage
  writes or execs itself; the harness runs the emitted stages.
- **C12-3 relay not polyglot:** each `code_*` is its own ISA only; the other
  ISA's bytes are data inside P, never executed. README states the line vs
  xarch_shellcode.
- **C12-4 emulation labelled:** README/AGENTS say stage1 runs under qemu-aarch64.
- **C12-5 payload design:** README explains the single-shared-P construction
  (no infinite regress).
- **R6 encoder oracle:** GNU `objdump`/`aarch64-linux-gnu-objdump` decode the
  hand-emitted bytes to exactly the intended `mov/movabs/syscall` and
  `movz/movk/svc` sequences.
- **Clean-env:** built + verified under `env -i` (6 VERDICT PASS, exit 0).

## Known weak spots (stated plainly)

- **2 stages / 2 ISAs**, hand-rolled fixed layout (one PT_LOAD, syscall-only). A
  demonstration of the construction, not a general relay compiler; a 3rd ISA
  (RISC-V under qemu-riscv64) is a v2 extension of the same payload scheme.
- **stage1 runs under qemu-aarch64**, not ARM hardware (functional emulation).
  The fixed point is a byte property, independent of where stage1 runs.
- **Two qemu-aarch64 loader quirks** had to be met and are documented in
  `build_fixpoint.py`/README: the stage must be **64 KiB page-aligned**
  (`p_align = 0x10000`; 4 KiB is silently rejected), and the harness must
  `chmod +x` each emitted stage before qemu-user will run it. These are
  properties of the runner, not of the relay bytes.
- The emitted files are marked executable by the harness (`verify.sh`), not by
  any stage — a stage only writes bytes to stdout.

## Files

`parts/03-quine-relay/`: AGENTS.md, README.md, RUN.md, Makefile,
build_fixpoint.py, verify.sh (+ generated stage0/1/2, strace logs — clean-able).

## Nit fixes (REVIEW-03-build, gate already CLEARED)

- **N1 (FALSE runner-quirk claim) — fixed.** The earlier "64 KiB alignment
  required / 4 KiB silently rejected" was wrong (reviewer verified qemu-aarch64
  8.2.2 runs the relay at p_align 0x1000 too, at 0x400000 and 0x200000). The
  real silent "exit 1, no output" was a stage file missing the +x bit. Corrected
  in build_fixpoint.py and README; 64 KiB kept by convention, not necessity.
- **N2 (safety check failed open) — fixed.** verify.sh's C12-2 check now FAILS
  CLOSED: it requires exactly 3 `write(1,` + an exit + a successful tracer run +
  non-empty output for each stage, so an un-attached tracer / empty log / silent
  qemu reject can no longer yield a vacuous PASS.
- **N3 (second R-only PT_LOAD for P)** not taken: the "data, never executed"
  property is already true (verified) and the single-R+X-segment keeps the
  construction minimal; noted as an optional structural tightening for v2.
