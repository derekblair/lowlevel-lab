# quine-relay — a cross-ISA machine-code quine relay

A 2-cycle quine relay across two instruction sets, in raw machine code:

```
stage0  (x86-64 ELF)  --run natively-->       stage1 (AArch64 ELF)
stage1  (AArch64 ELF) --run under qemu-aarch64--> stage2 (x86-64 ELF)
sha256(stage0) == sha256(stage2)              # a byte-exact fixed point
```

Each stage, run, writes the *next* stage to stdout and exits. Run the x86-64
stage and it prints the AArch64 stage; run that (under qemu-aarch64) and it
prints the original x86-64 stage back, **byte-for-byte**. (`stage1` is executed
**under qemu-aarch64** — this box has no ARM hardware; R10.)

## Why this is novel (see ../../research/NOVELTY-LOG.md C12)

Quine *relays* are famous at **source level** (mame/quine-relay, 100+ languages).
Binary quines exist but are **single-ISA** (panzi/binary-quine x86-64,
meithecatte/mips-quine). One-file multi-arch artifacts exist — Actually Portable
Executables, ixty/xarch_shellcode, Windows Arm64X — but those are **one polyglot
binary** that selects an architecture at run time. This is different: a **chain
of distinct single-ISA ELF executables**, each emitting the next ISA's complete
binary, closing to a byte-exact fixed point. No public cross-ISA *machine-code*
relay was found (N3; reviewer-confirmed, REVIEW-01 §6.1).

## How the fixed point works (the payload design — C12-5)

Naively, "stage A prints stage B and vice-versa" regresses infinitely (each
would have to contain the other, which contains the other…). The standard quine
trick, lifted across the ISA boundary, avoids that with **one shared payload**
carried verbatim by both stages:

```
P        = header_X ‖ code_X ‖ header_A ‖ code_A      (no copy of P inside P)
stage_X  = header_X ‖ code_X ‖ P                      (the x86-64 stage, = stage0)
stage_A  = header_A ‖ code_A ‖ P                      (the AArch64 stage, = stage1)
```

`code_X`, when run, emits `header_A ‖ code_A ‖ P` — i.e. it reads the OTHER
stage's header and code **out of P** (as data) and appends P. That output is
exactly `stage_A`. Symmetrically `code_A` emits `header_X ‖ code_X ‖ P =
stage_X`. P is identical in both stages and is written out verbatim by both, so
the relay closes: `stage_X → stage_A → stage_X`.

**It is a relay, not a polyglot (C12-3):** the other ISA's header and code sit
in a stage **only as data inside P**; no stage ever *executes* the other ISA's
bytes — `code_X` is x86-64 that runs on x86-64, `code_A` is AArch64 that runs on
AArch64. That is the line separating this from the xarch_shellcode "one binary,
many code blocks + dispatcher" technique.

Each stage is a freestanding ELF with a single `PT_LOAD` (R+X, W^X) at vaddr
`0x400000`, 64 KiB-aligned (the conventional arm64 alignment — **not** required;
see "Limits"). Each `code_*` is three `write(1, …)` syscalls (emit the other
header, the other code, then P) and `exit(0)` — nothing else (C12-2).

## How to run

```
make            # build stage0, run one relay cycle, verify the fixed point
./verify.sh     # same; prints grep-able VERDICT lines, exit 0 iff all pass
```

`build_fixpoint.py` (Python stdlib only) hand-emits both code blocks with
fixed-width instructions, lays out the ELF headers and P, and writes `stage0`.
No assembler is needed to *build*; `verify.sh` uses the GNU assemblers' decoders
only to *check* (see Requirements).

## Verification (RUN.md, grep `VERDICT`)

- **fixed point**: `cmp stage0 stage2` byte-identical + matching sha256 (C12-1).
- **single-ISA ELFs**: `readelf -h` shows stage0/stage2 = X86-64, stage1 =
  AArch64; the AArch64 stage is disassembled with `aarch64-linux-gnu-objdump`
  (C12-1).
- **safety**: `strace` (x86 stage) and `qemu-aarch64 -strace` (AArch64 stage)
  show **only** `write(1,…)` + `exit` — no `open`/`execve`/`fork`, no network,
  no file-backed mmap (C12-2). No stage writes or execs itself; the *harness*
  (verify.sh) saves each stage's stdout, marks it `+x`, and runs it.
- **independent encoder oracle (R6)**: GNU `objdump` / `aarch64-linux-gnu-objdump`
  decode the hand-emitted bytes to exactly the intended `mov/movabs/syscall`
  (x86) and `movz/movk/svc` (AArch64) sequences.

## Requirements (R8)

- `python3` (stdlib only) to build; `make`.
- `qemu-aarch64` to run the AArch64 stage (user-mode emulation — **not** ARM
  hardware). `aarch64-linux-gnu-objdump` + `objdump` for the disassembly/oracle
  checks. `strace` for the safety check. `readelf`, `file`, `cmp`, `sha256sum`.

## Limits / honesty

- **2 stages, 2 ISAs.** A longer relay (add RISC-V via qemu-riscv64, etc.) is a
  straightforward extension of the same payload scheme and is noted for v2.
- **The AArch64 stage runs under qemu-aarch64**, which is functional user-mode
  emulation; there is no ARM hardware on this box (R10). The fixed point is a
  property of the bytes, independent of where stage1 runs.
- **Hand-rolled fixed layout**, specific to these two freestanding ELF shapes
  (one `PT_LOAD`, syscall-only). It is a demonstration of the construction, not
  a general quine-relay compiler.
- **qemu-aarch64 runner quirk (corrected, REVIEW-03-build N1):** the real quirk
  is that qemu-user exits 1 **silently** (no output, no message) when the stage
  file lacks the executable bit — which is why `verify.sh` `chmod +x`'s each
  emitted stage. The `p_align = 0x10000` is the conventional arm64 alignment but
  is **not** required; qemu-aarch64 8.2.2 also runs the relay at `p_align =
  0x1000` (verified by the reviewer). My earlier "64 KiB required / 4 KiB
  rejected" claim was wrong and conflated the alignment with the missing-`+x`
  symptom.
