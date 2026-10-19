# part 04 — ifetch-sanitizer (AGENTS.md)

Part of **lowlevel-lab** (see ../../AGENTS.md). Author-lane build P4 (reshaped
C01), KEEP as reshaped at N2 (REVIEW-01 §2.4). The mission's ARM64 build: a
whole-program sanitizer for missing AArch64 instruction-cache maintenance.

- **What:** `a64asm.py` (A64 encoder for the kernel subset; selftest vs
  aarch64-linux-gnu-as), `icache_model.py` (modelled I/D cache + CTR_EL0 config),
  `sanitize.py` (interpreter + kernels + diagnosis matrix + qemu oracle +
  VERDICTs), `Makefile`. README explains it; RUN.md is the verbatim evidence.
- **Build/run:** `make` = encoder oracle + semantic oracle + diagnosis matrix.
  Present tools only: python3 stdlib, aarch64-linux-gnu binutils, qemu-aarch64.
  No root, no installs.
- **Novel observable (R4):** for any patch sequence and CTR_EL0/line-size config,
  the sanitizer names the exact missing maintenance step (DC CVAU / DSB / IC
  IVAU / DSB / ISB), including maintenance in the wrong place relative to the
  store (flush-then-write, re-patch, DC before STR), and catches the I/D
  line-size-mismatch (big.LITTLE) bug from a strided flush. Proven by the
  `VERDICT PASS` lines in RUN.md.
- **Oracles (P4-2/R6):** encoder = aarch64-linux-gnu-as (22/22 byte-identical);
  semantic = qemu-aarch64 (coherent-mode model end-state == qemu exit == latest
  stored word, all 13 kernels). herdtools7 SM.udf litmus test cross-checked as
  data (P4-3).
- **Labelling (R10/P4-4):** all staleness is MODEL output, and conservative
  ("not guaranteed" => stale); qemu is SMC-coherent and can't show the stale
  cases — stated throughout.
- **Arch citation (P4-3):** CTR_EL0.{IDC,DIC} quoted verbatim (Arm XML build
  26/03/2024) + Linux `cache.S` barrier facts (`ARM_REF`); the sequence's
  location (DDI 0487G.a B2.2.5) is secondary, labelled as such.
- **Safety:** benign cache-maintenance diagnostic; tiny own-built qemu kernels;
  no network / no out-of-tree writes.
- **Artifacts:** none committed beyond sources + the fetched herdtools7 test
  evidence (../../research/raw/repos/herd__herdtools7-ifetch/). `make clean`
  removes __pycache__.
