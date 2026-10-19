# RUN.md — ifetch-sanitizer, verbatim build+run on nibbles

Captured 2026-10-19 09:03:25 PDT on nibbles, user derekblair. Verbatim, from clean.
Fully deterministic (no timing/sampling).

## Environment
```
$ python3 --version
Python 3.12.3
$ aarch64-linux-gnu-as --version | head -1
GNU assembler (GNU Binutils for Ubuntu) 2.42
$ qemu-aarch64 --version | head -1
qemu-aarch64 version 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.18)
```

## make (encoder oracle + semantic oracle + diagnosis matrix + VERDICTs)
```
$ make
python3 a64asm.py          # encoder differential test vs aarch64-linux-gnu-as
a64asm differential test vs aarch64-linux-gnu-as: 22/22 encoders match
python3 sanitize.py        # semantic oracle + the diagnosis matrix + VERDICTs
==============================================================================
ifetch-sanitizer: which cache-maintenance step is missing, per CTR_EL0 config
(ALL staleness output is MODEL output; the same kernels run FRESH under
 qemu-aarch64, which is SMC-coherent -- that is qemu's coherence, R10)
Arch ref: Arm ARM DDI 0487K.a, B2.7.4 'Instruction cache maintenance requirements' and D23.2.35 CTR_EL0.{IDC,DIC}; the sequence DC CVAU; DSB ISH; IC IVAU; DSB ISH; ISB
==============================================================================
VERDICT PASS: encoder oracle: a64asm matches aarch64-linux-gnu-as (22/22)  [all encoders byte-identical]

-- semantic oracle (coherent config IDC=0,DIC=0; correct kernel vs qemu) --
correct kernel: qemu exit=34  model(coherent) x0=34  (both must be NEW=34)
VERDICT PASS: semantic oracle: model coherent-mode result == qemu == NEW  [qemu=34 model=34 new=34]
VERDICT PASS: qemu runs EVERY kernel fresh (NEW) -- so qemu cannot show the stale cases  [qemu exits: {'correct': 34, 'omit-DC': 34, 'omit-DSB1': 34, 'omit-IC': 34, 'omit-DSB2': 34, 'omit-ISB': 34, 'none': 34}]

-- diagnosis matrix: x0 after calling the patched slot (NEW=fresh, OLD=stale) --
kernel                 IDC=0,DIC=0           IDC=1,DIC=0           IDC=1,DIC=1
correct                        NEW                   NEW                   NEW
omit-DC                     OLD!DC                   NEW                   NEW
omit-DSB1                  OLD!DSB                   NEW                   NEW
omit-IC                     OLD!IC                OLD!IC                   NEW
omit-DSB2                  OLD!DSB               OLD!DSB                   NEW
omit-ISB                   OLD!ISB               OLD!ISB               OLD!ISB
none                        OLD!DC                OLD!IC               OLD!ISB

VERDICT PASS: the correct full sequence executes FRESH in every config
VERDICT PASS: omit-DC: stale under IDC=0/DIC=0, sanitizer names 'DC CVAU (clean D-cache to PoU)'  [missing=dc x0=17]
VERDICT PASS: omit-IC: stale under IDC=0/DIC=0, sanitizer names 'IC IVAU (invalidate I-cache to PoU)'  [missing=ic x0=17]
VERDICT PASS: omit-ISB: stale under IDC=0/DIC=0, sanitizer names 'ISB (context-synchronize the fetch)'  [missing=isb x0=17]
VERDICT PASS: omit-DC becomes FRESH when IDC=1 (D-cache clean to PoU not required)  [config-sensitive, as the architecture specifies]
VERDICT PASS: omit-IC becomes FRESH when DIC=1 (requires IDC=1; config IDC=1,DIC=1)  [DIC=1 implies IDC=1 per DDI 0487 D23.2.35; {IDC=0,DIC=1} is impossible and omitted]
VERDICT PASS: omit-ISB is stale in EVERY config (ISB is never excused by IDC/DIC)

-- I/D line-size mismatch: correct sequence, but the maintenance loop
   strides by the wrong line size so it misses the patched line --
   correct-stride x0=34 (NEW)   wrong-stride x0=17 (OLD, stale)
VERDICT PASS: line-size mismatch: a correct-looking sequence with the wrong stride goes STALE  [the classic big.LITTLE mismatched-cache-line JIT bug, caught by the model]

ALL VERDICTS PASS
$ echo make_exit=$?
make_exit=0
```
