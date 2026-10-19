# RUN.md — quine-relay, verbatim build+verify on nibbles

Captured 2026-10-19 09:04:40 PDT on nibbles, user derekblair. Deterministic; verbatim from clean.

## Environment
```
$ python3 --version
Python 3.12.3
$ qemu-aarch64 --version|head -1
qemu-aarch64 version 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.18)
```

## make  (build stage0, run one relay cycle, verify the fixed point)
```
$ make
./verify.sh
built stage0: x86-64 stage_X, 632 bytes (HDR=120 code_X=80 code_A=112 payload=432); stage_A would be 664 bytes; entry=V+0x78
stage0 (x86-64, native) exit=0 -> stage1 664 bytes
stage1 (AArch64, under qemu-aarch64) exit=0 -> stage2 632 bytes
ce9a974b5ca80b3ca7ac380f61959dbad8fb1c5f66fdc512a87302724a56d7cf  stage0
d08b30297fd93b7be4ce2ec592085b2cf47fc1e88e5424ea336f3df5d68cfe24  stage1
ce9a974b5ca80b3ca7ac380f61959dbad8fb1c5f66fdc512a87302724a56d7cf  stage2
VERDICT PASS: fixed point: stage2 is byte-identical to stage0 (cmp + sha256 above)
stage0: Advanced Micro Devices X86-64 | ELF 64-bit LSB executable, x86-64
stage1: AArch64 | ELF 64-bit LSB executable, ARM aarch64
stage2: Advanced Micro Devices X86-64 | ELF 64-bit LSB executable, x86-64
VERDICT PASS: stage0/stage2 are x86-64 ELFs, stage1 is an AArch64 ELF (readelf -h)
--- aarch64-linux-gnu-objdump of stage1's code (entry region):
  78:	d2800808 	mov	x8, #0x40                  	// #64
  7c:	f2a00008 	movk	x8, #0x0, lsl #16
  80:	d2800020 	mov	x0, #0x1                   	// #1
  84:	f2a00000 	movk	x0, #0x0, lsl #16
  88:	d2801d01 	mov	x1, #0xe8                  	// #232
  8c:	f2a00801 	movk	x1, #0x40, lsl #16
  90:	d2800f02 	mov	x2, #0x78                  	// #120
  94:	f2a00002 	movk	x2, #0x0, lsl #16
  98:	d4000001 	svc	#0x0
  9c:	d2800020 	mov	x0, #0x1                   	// #1
  a0:	f2a00000 	movk	x0, #0x0, lsl #16
  a4:	d2802c01 	mov	x1, #0x160                 	// #352
  a8:	f2a00801 	movk	x1, #0x40, lsl #16
  ac:	d2800a02 	mov	x2, #0x50                  	// #80
  b0:	f2a00002 	movk	x2, #0x0, lsl #16
  b4:	d4000001 	svc	#0x0
  b8:	d2800020 	mov	x0, #0x1                   	// #1
  bc:	f2a00000 	movk	x0, #0x0, lsl #16
  c0:	d2801d01 	mov	x1, #0xe8                  	// #232
  c4:	f2a00801 	movk	x1, #0x40, lsl #16
  c8:	d2803602 	mov	x2, #0x1b0                 	// #432
  cc:	f2a00002 	movk	x2, #0x0, lsl #16
  d0:	d4000001 	svc	#0x0
  d4:	d2800ba8 	mov	x8, #0x5d                  	// #93
  d8:	f2a00008 	movk	x8, #0x0, lsl #16
  dc:	d2800000 	mov	x0, #0x0                   	// #0
  e0:	f2a00000 	movk	x0, #0x0, lsl #16
  e4:	d4000001 	svc	#0x0
stage0: writes=3 exits=1 other=0 rc=0 out=664B
VERDICT PASS: C12-2 x86 stage0: exactly 3x write(1,..) + exit, no other syscalls (fail-closed)
stage1: writes=3 exits=1 other=0 rc=0 out=632B
VERDICT PASS: C12-2 AArch64 stage1 (qemu -strace): exactly 3x write(1,..) + exit (fail-closed)
x86 decode : mov mov movabs mov syscall mov movabs mov syscall mov movabs mov syscall mov xor syscall 
a64 decode : movz movk movz movk movz movk movz movk svc movz movk movz movk movz movk svc movz movk movz movk movz movk svc movz movk movz movk svc 
VERDICT PASS: R6 x86 code decodes (GNU objdump) to the intended mov/movabs/syscall sequence
VERDICT PASS: R6 AArch64 code decodes (GNU aarch64 objdump) to the intended movz/movk/svc sequence
ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0
```
