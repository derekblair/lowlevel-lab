# Toolchain update — ARM64 cross tools on nibbles

Date: 2026-10-18 (America/Los_Angeles)
Installed at Derek's explicit approval (2026-10-18 ~22:11 PDT):
`sudo apt-get install -y qemu-user gcc-aarch64-linux-gnu`
Full apt log: `install.log` in this directory (INSTALL_DONE, install rc=0).

## Packages (dpkg -l, verified after install)

```
ii  qemu-user                  1:8.2.2+ds-0ubuntu1.18        amd64  QEMU user mode emulation binaries
ii  gcc-aarch64-linux-gnu      4:13.2.0-7ubuntu1             amd64  GNU C compiler for the arm64 architecture
ii  gcc-13-aarch64-linux-gnu   13.3.0-6ubuntu2~24.04.1cross1 amd64  GNU C compiler for the aarch64-linux-gnu architecture
ii  binutils-aarch64-linux-gnu 2.42-4ubuntu2.10              amd64  GNU binary utilities, for aarch64-linux-gnu target
ii  libc6-arm64-cross          2.39-0ubuntu8cross1           all    GNU C Library: Shared libraries (for cross-compiling)
```

Versions:
- `qemu-aarch64 version 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.18)`
- `aarch64-linux-gnu-gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`

## Verification (run on nibbles, 2026-10-18)

ARM64 assembly hello (/tmp/hello-a64.s, Linux syscalls: write=64, exit=93):

```
$ aarch64-linux-gnu-as -o /tmp/hello-a64-asm.o /tmp/hello-a64.s
$ aarch64-linux-gnu-ld -o /tmp/hello-a64-asm /tmp/hello-a64-asm.o
$ file /tmp/hello-a64-asm
/tmp/hello-a64-asm: ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked, not stripped
$ qemu-aarch64 /tmp/hello-a64-asm
Hello, ARM64!
asm exit code: 42
```

C hello cross-compiled static (/tmp/hello-a64.c, returns 7):

```
$ aarch64-linux-gnu-gcc -static -o /tmp/hello-a64-c /tmp/hello-a64.c
$ file /tmp/hello-a64-c
/tmp/hello-a64-c: ELF 64-bit LSB executable, ARM aarch64, version 1 (GNU/Linux), statically linked, for GNU/Linux 3.7.0, not stripped
$ qemu-aarch64 /tmp/hello-a64-c
Hello from C on ARM64!
c exit code: 7
```

## What this unlocks for lowlevel-lab

- ARM64 assembly prototypes can now be assembled/linked with GNU as/ld and
  RUN on nibbles under qemu-aarch64 (user-mode emulation — not native
  hardware: no bare-metal, no privileged/SIMD-performance fidelity).
- x64 work remains native. The earlier no-cross-toolchain workaround in
  BRIEF-AUTHOR.md (self-built assembler/emulator for ARM64) is now
  optional, not required — author's choice per concept.
