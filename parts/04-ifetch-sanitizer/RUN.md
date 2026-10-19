# RUN.md — ifetch-sanitizer, verbatim build+run on nibbles (fix round 2)

Captured 2026-10-19 09:59:04 PDT on nibbles, user derekblair, under `env -i` (HOME, PATH=/usr/local/bin:/usr/bin:/bin, LANG=C.UTF-8). Deterministic; verbatim.

## Environment
```
$ python3 --version
Python 3.12.3
$ aarch64-linux-gnu-as --version|head -1
GNU assembler (GNU Binutils for Ubuntu) 2.42
$ qemu-aarch64 --version|head -1
qemu-aarch64 version 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.18)
```

## make (encoder oracle + qemu semantic oracle + program-dependence + matrix + store ordering + strided flush)
```
$ make
python3 a64asm.py          # encoder differential test vs aarch64-linux-gnu-as
a64asm differential test vs aarch64-linux-gnu-as: 22/22 encoders match
python3 sanitize.py        # semantic oracle + the diagnosis matrix + VERDICTs
==============================================================================
ifetch-sanitizer (program-driven): which cache-maintenance step is missing
Staleness is MODEL output (R10); every kernel runs FRESH under qemu-aarch64.
Arm CTR_EL0 (DDI 0487, AArch64-ctr_el0; Arm XML build 26/03/2024), verbatim:
  IDC=1: "Data cache clean to the Point of Unification is not required for
          instruction to data coherence."
  DIC=1: "Instruction cache invalidation to the Point of Unification is not
          required for data to instruction coherence."
  "If CTR_EL0.DIC is 1 then the value reported in [IDC] must also be 1."
Canonical modify-execute sequence (SECONDARY: DDI 0487G.a B2.2.5 as quoted by
  Rutland's LKML post and patent US11210222; not checked against the manual here):
  modifying PE: DC CVAU,Xn ; DSB ISH ; IC IVAU,Xn ; DSB ISH ; and each executing
  PE: ISB.
Linux arch/arm64/mm/cache.S caches_clean_inval_pou_macro: on ARM64_HAS_CACHE_IDC
  the DC loop is skipped but a 'dsb ishst' is STILL issued; on ARM64_HAS_CACHE_DIC
  the IC loop is skipped but an 'isb' is STILL issued. => the barriers are kept
  even when IDC/DIC excuse the cache op; that is the rule this model applies.
==============================================================================
VERDICT PASS: encoder oracle: a64asm matches aarch64-linux-gnu-as (22/22)  [[]]

-- semantic oracle: model(coherent) end-state vs qemu exit, every kernel --
  correct          qemu= 34  model(coherent)= 34  latest-stored= 34  ok
  omit-DC          qemu= 34  model(coherent)= 34  latest-stored= 34  ok
  omit-DSB1        qemu= 34  model(coherent)= 34  latest-stored= 34  ok
  omit-IC          qemu= 34  model(coherent)= 34  latest-stored= 34  ok
  omit-DSB2        qemu= 34  model(coherent)= 34  latest-stored= 34  ok
  omit-ISB         qemu= 34  model(coherent)= 34  latest-stored= 34  ok
  none             qemu= 34  model(coherent)= 34  latest-stored= 34  ok
  control          qemu= 34  model(coherent)= 34  latest-stored= 34  ok
  flush-then-write qemu= 34  model(coherent)= 34  latest-stored= 34  ok
  re-patch         qemu= 51  model(coherent)= 51  latest-stored= 51  ok
  dc-before-str    qemu= 34  model(coherent)= 34  latest-stored= 34  ok
  stride-64        qemu= 34  model(coherent)= 34  latest-stored= 34  ok
  stride-128       qemu= 34  model(coherent)= 34  latest-stored= 34  ok
VERDICT PASS: B4 semantic oracle: model coherent-mode == qemu == latest stored word, all 13 kernels
VERDICT PASS: B1(a): a kernel whose maintenance is only DSBs is diagnosed STALE (reads the program)  [x0=17]
VERDICT PASS: B1(c): the correct kernel is FRESH  [x0=34]

-- diagnosis matrix: x0 after re-running the patched slot --
kernel         IDC=0,DIC=0     IDC=1,DIC=0     IDC=1,DIC=1
correct                NEW             NEW             NEW
omit-DC             OLD!dc             NEW             NEW
omit-DSB1          OLD!dsb         OLD!dsb             NEW
omit-IC             OLD!ic          OLD!ic             NEW
omit-DSB2          OLD!dsb         OLD!dsb             NEW
omit-ISB           OLD!isb         OLD!isb         OLD!isb
none                OLD!dc         OLD!dsb         OLD!dsb
VERDICT PASS: correct sequence is FRESH in every valid config
VERDICT PASS: omit-DC: STALE under IDC=0,DIC=0 and the sanitizer names 'DC CVAU (clean D-cache to PoU)'  [missing=dc x0=17]
VERDICT PASS: omit-IC: STALE under IDC=0,DIC=0 and the sanitizer names 'IC IVAU (invalidate I-cache to PoU)'  [missing=ic x0=17]
VERDICT PASS: omit-ISB: STALE under IDC=0,DIC=0 and the sanitizer names 'ISB (synchronize fetch)'  [missing=isb x0=17]
VERDICT PASS: omit-DC becomes FRESH under IDC=1 (DC excused) but omit-ISB stays STALE  [IDC=1 excuses DC (barrier kept); ISB never excused]
VERDICT PASS: omit-IC becomes FRESH only under DIC=1 (=>IDC=1), else STALE
VERDICT PASS: omit-DSB1 names the step that is ABSENT: the DSB between DC and IC (N3)  [IDC=0,DIC=0 -> dsb; IDC=1,DIC=0 -> dsb (the IC is present)]

-- store ordering (B5): x0 / missing step, and the cause under IDC=0,DIC=0 --
kernel                 IDC=0,DIC=0     IDC=1,DIC=0     IDC=1,DIC=1   cause (IDC=0,DIC=0)
control                        NEW             NEW             NEW   fresh
flush-then-write            OLD!dc         OLD!dsb         OLD!dsb   dc executed only BEFORE the latest store (flush, then write)
re-patch                    NEW!dc         NEW!dsb         NEW!dsb   re-patched after its maintenance completed: the later store is unmaintained (no dc after it)
dc-before-str               OLD!dc             NEW             NEW   dc executed only BEFORE the latest store (flush, then write)
VERDICT PASS: B5 control: STR then the full sequence then run is FRESH  [x0=34]
VERDICT PASS: B5 flush-then-write: maintenance BEFORE the store is STALE, cause named  [missing=dc: dc executed only BEFORE the latest store (flush, then write)]
VERDICT PASS: B5 re-patch: a second, unmaintained store is STALE (fetch sees the maintained NEW, not NEW2)  [x0=0x22 missing=dc: re-patched after its maintenance completed: the later store is unmaintained (no dc after it)]
VERDICT PASS: B5 dc-before-str: a DC issued before the STR never cleans the new bytes -> STALE  [missing=dc: dc executed only BEFORE the latest store (flush, then write)]

-- line-size mismatch: unrolled JIT flush loop, Iline=Dline=64, IDC=0,DIC=0 --
  stride  64: slot line +0x80; DC hit lines ['0x40', '0x80', '0xc0', '0x100'] -> x0=34 (NEW); missing: None
  stride 128: slot line +0x40; DC hit lines ['0x0', '0x80'] -> x0=17 (OLD); missing: dc
VERDICT PASS: line-size: a stride-128 flush (another core's line size) skips the slot's 64-B line -> STALE; stride 64 FRESH  [decided from the executed flush addresses, not a flag]

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0
```
