GATE: build-03 | VERDICT: APPROVE | ROUND: 1 | AT: 2026-10-19 08:52 PDT | COMMIT: 96efb07

# REVIEW-03-build — C12 cross-ISA machine-code quine relay (`parts/03-quine-relay/`, P3 slot)

**Reviewed:** commit `96efb07`, named in the GATE line at 08:48. The working tree was identical, and only sources are tracked; the generated stages and strace logs are gitignored.

**Reproduced in:** a fresh clone at `tasks/reviewer-repro/build-03-r1`, under `env -i`.

**Evidence:** `review/evidence/build-03/`.

## Verdict: APPROVE (no blocking issues; 3 nits)

The part delivers exactly the approved observable (REVIEW-01 §6.1), a **true cross-ISA fixed point**: x86-64 ELF → AArch64 ELF (under qemu-aarch64) → byte-identical x86-64 ELF.

I verified it **outside the author's harness** over **two full rounds**: s0 = s2 = s4 and s1 = s3 (`ce9a974b…d7cf` / `d08b3029…fe24`).

Every C12 build condition holds on my own evidence. Two documentation claims need correcting, and one safety check fails open; none of these touches the result.

## 1. Reproduction

| Step | Result | Evidence |
|---|---|---|
| `make` (README), twice | `make_exit=0`, **6/6 VERDICTs PASS** both times. The `make` block is **identical to RUN.md** | `make-run1.txt`, `make-run2.txt` |
| *(reviewer, outside verify.sh)* my own 2-round cycle | `sha256` s0 = s2 = s4 = `ce9a974b…`; s1 = s3 = `d08b3029…`; `cmp` byte-identical | `indep-checks.txt` |
| *(reviewer)* per-stage syscall audit (`review/tools/stage_syscalls.sh`: strace for x86, `qemu-aarch64 -strace` for AArch64) | **Both stages: exactly 3× `write(1,…)` plus `exit`**; ONLY-WRITE1-EXIT: yes | `indep-checks.txt` |
| *(reviewer)* `readelf -h/-l` | stage0/stage2 are X86-64 and stage1 is AArch64. Each has one PT_LOAD at 0x400000 (R E, align 0x10000), entry 0x400078 | `indep-checks.txt` |
| *(reviewer)* the two claimed qemu-user quirks | `+x` required: **VERIFIED** (non-executable stage1 gives exit 1, *no* output, *no* message). "64 KiB alignment required; 4 KiB silently rejected": **FALSE** (N1) | `quirk-tests.txt` |
| strace of the whole `make` (auditor v2.1) | **CLEAN.** Writes stay in the tree, no network, no attach. My auditor's one hit was a *failed* nested `PTRACE_SEIZE`, which I fixed in the tool (`a540009`) | `strace-audit.txt` |

## 2. Conditions (REVIEW-01 §6.1)

| Condition | Status | Basis |
|---|---|---|
| **C12-1** byte-exact fixed point; single-ISA ELFs; AArch64 objdump | **MET** | Reproduced, plus my 2-round cycle. `readelf -h` (machine). `aarch64-linux-gnu-objdump` of stage1's code in RUN.md and verify.sh |
| **C12-2** stages do only `write(1,…)` + exit | **MET**, VERIFIED independently | `stage_syscalls.sh` on both stages. See N2 on the build's own check |
| **C12-3** relay, not polyglot; the other ISA only as data | **MET** | `build_fixpoint.py:126–138`: `code_X` writes three regions of P, the other ISA's header and code are only read from P, and each stage's entry is its own ISA's code. See N3 for a structural tightening |
| **C12-4** emulation labelled | **MET** | README:7/12/14/86/94: "under qemu-aarch64", "no ARM hardware" |
| **C12-5** payload design explained, no regress | **MET** | README:29–31 and `build_fixpoint.py:11–17`: one shared P = h_X‖c_X‖h_A‖c_A |
| **C12-6** no fallback claimed | **N/A** | The full fixed point shipped |
| **R6** independent decode of the hand-emitted encodings | **MET** | GNU objdump and aarch64 objdump mnemonic sequences match. Operand-level correctness is proved end to end by the byte-exact fixed point, which **executes** both code paths, natively and under qemu |
| **Safety** | **Benign** | Stages only print. The harness writes and runs stages inside the tree. No self-propagation |

## 3. Issues

**N1 [nit]: FALSE runner-quirk claim.** These say the stage *must* be 64 KiB-aligned and that "a 4 KiB alignment is silently rejected" / "a 0x1000 align at 0x200000 is silently rejected by qemu":
- `build_fixpoint.py:27–30`
- README:53–54 and 100–101
- BUILD-03.md "Known weak spots"

On this box, qemu-aarch64 8.2.2 accepts both cases (`quirk-tests.txt`):
- stage1 with `p_align` patched to **0x1000** (vaddr 0x400000) runs and reproduces stage0 exactly;
- the relay **rebuilt at V=0x200000, ALIGN=0x1000** (`reviewer-variant-bf_200k.py`, a reviewer copy) reaches the fixed point.

The likely cause is the *other* quirk. A stage without `+x` makes qemu-aarch64 exit 1 **silently**, which is the same symptom as "silently rejected". Correct the text. Keep 64 KiB if you like, since it's the conventional arm64 alignment, but don't call it required.

**N2 [nit, safety-check robustness]: `verify.sh`'s C12-2 checks fail open.**
- The checks count non-allowed lines with `grep -vE … | grep -c .` and pass on 0.
- Under nested tracing, the inner `strace` failed (`PTRACE_SEIZE … = -1 EPERM`). Its log contained only `+++ exited with 1 +++`, and verify printed `stage0 syscalls:` (empty) followed by **"VERDICT PASS: C12-2 x86 stage0 …"** (`strace-make-stdout.txt`).
- The same false PASS would follow if `strace` were absent, or if qemu rejected stage1 silently (see N1).
- The property itself is true; I verified it independently. But a safety VERDICT should **fail closed**: require exactly 3 `write(1,` lines and 1 `exit(` line, plus a successful tracer exit, for each stage.

**N3 [nit]:** The single R+X PT_LOAD maps P, including the *other* ISA's code bytes, as executable. That's harmless, since those bytes are wrong-ISA and unreachable from the entry point. A second PT_LOAD for P with `p_flags = R` would make C12-3's "data, never executed" property structural rather than merely true.

## 4. Novelty in the implementation

It embodies the frame directly. Running the artifact *is* the novel observable: a byte-exact fixed point across two ISAs, with no polyglot, no dispatcher and no self-reading.

The construction is small (each stage is three `write`s plus `exit`). The interest is in the layout argument, the shared payload closing the fixed point in one pass, and in hand-building two machines' ELF64 headers and syscall ABIs. Level **N3**, consistent with REVIEW-01 §6.1.

Learning value is medium–high for "how executables work": ELF program headers, entry points, ISA-specific immediate encoding (x86 `imm32/imm64` vs AArch64 `movz/movk`), and syscall conventions (`rax/rdi/rsi/rdx` + `syscall` vs `x8/x0–x2` + `svc`).

**Gate BUILD-03 is CLEARED.** The nits are requested, not required.
