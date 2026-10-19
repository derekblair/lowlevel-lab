GATE: build-01 | VERDICT: CHANGES REQUESTED | ROUND: 1 | AT: 2026-10-19 07:39 PDT | COMMIT: 2949d40

# REVIEW-01-build — P1 smc-observatory (`parts/01-smc-observatory/`)

**Reviewed:** commit `2949d40` (the part plus `builds/BUILD-01.md`), named in the GATE line at 07:33. The working tree was byte-identical to that commit when I read it (`git diff --stat 2949d40 -- parts/01-smc-observatory builds/BUILD-01.md` was empty).

**Reproduced in:** a fresh clone at `tasks/reviewer-repro/build-01-r1`, run under `env -i` with an isolated HOME (`review/tools/repro.sh`).

**Evidence:** everything is in `review/evidence/build-01/`.

## Verdict: CHANGES REQUESTED (2 blocking, both small and local)

The central result is strong, and I **verified it by reproduction**:
- **Cougar Cove (P):** SMC machine-clear detection granularity is one 64-byte line.
- **Darkmont (both E and LP-E):** it's one aligned 1-KiB subpage.
- Intel 248966 §3.6.8.1 therefore describes Darkmont and not Cougar Cove.

The tables and all 10 VERDICT lines reproduce **byte-identically** across two clean runs. I extended the check to **all 16 CPUs**, and every core in every class behaves as claimed. The safety audit is clean.

The two blockers are a probe that can't detect what it claims to rule out (B1) and a false run instruction (B2). Neither touches the headline finding.

**Proceed-in-parallel: GRANTED** (REVIEW-00 §1.9). Both blockers are local to this part, so BUILD-02 (P2 pt-truth) may start now.

## 1. Reproduction

| Step | What I ran (in the clone, `env -i`) | Result | Evidence |
|---|---|---|---|
| A | README.md line "`make` # builds smcobs, runs the full sweep, prints the report" | **Only compiles** (`cc … -o smcobs smcobs.c`, exit 0). No sweep, no report, no data.csv | `A-readme-make.txt` |
| B | RUN.md §1 `make clean && make smcobs` | Identical to RUN.md. Warning-free under `-Wall -Wextra` | `BC-build-smoke.txt` |
| C | RUN.md §2 `make smoke` | Identical clear counts (1.9999 / 0.0000 / 1.0000 / 0.0000 / 0.9999). tsc differs (nondeterministic) | `BC-build-smoke.txt` |
| D1, D2 | RUN.md §3 verbatim, **twice** in the same clone | Both report tables, **all 10 VERDICT lines** and the torn lines are **byte-identical** to RUN.md. `data.csv` has 423 lines both times. Only the xcore medians vary, as declared | `D1/D2-full-run.txt`, `diff-vs-RUNmd.txt`, `data-run{1,2}.csv.gz` |
| E | `make run` under `strace -f` (`review/tools/strace_audit.py`) | **CLEAN.** No out-of-tree writes, no AF_INET, no sudo/network exec, no ptrace attach, no process_vm_writev. Only glibc NSS probing the absent nscd (ENOENT, info) | `E-strace-audit.txt`, `strace-make-run.log.gz` |
| F | *(reviewer extension)* boundary points @8/@64/@512/@1023/@1024 on **all 16 CPUs** | P 0–3: ≈2 at @8 and 0 from @64. E 4–11 and LP-E 12–15: ≈1 through @1023, 0 at @1024. **Every core matches its class** | `F-all-cpus.txt` |
| G | *(reviewer extension)* my `deficit_probe.c`, same pattern, warm-up 0/1/4 × N 2e5/4e5 × 3 runs × CPUs 0/5/13 | The shortfall below 2/iter (P) and 1/iter (E) is **variable, 2–42 counts**, and a warm-up doesn't remove it | `deficit_probe.c`, `deficit-output.txt` |

**Hygiene ✓**
- Only sources and docs are tracked. The part's `.gitignore` keeps out `smcobs`, `data.csv` and `run.err`.
- After all my runs, the clone's `git status` shows only my own `.envrun` and `.evidence/`.
- Nothing in the build depends on an absolute path into the author's tree.

## 2. Claims

| Claim (README unless noted) | Tag | Basis |
|---|---|---|
| P (Cougar Cove) window = one 64-byte line | **VERIFIED** | D1/D2 tables, F (all four P cores), and my independent `c02-probe` |
| E and LP-E (Darkmont) window = one 1-KiB subpage, "16× wider" | **VERIFIED** | D1/D2, F (all twelve Darkmont cores) |
| §3.6.8.1 describes Darkmont and not Cougar Cove | **VERIFIED** | VERDICTs 5–6 reproduce; the citation was verified from the PDF in REVIEW-01 §2.1 |
| The window tracks the code, not the page base | **VERIFIED** | Placement-B table. E clears for stores at 1024…2047 when the code is at 1536, and is quiet at 8/512/1023/2048/3072. P clears only at 1543, the code's own line |
| In-window magnitude P = 2/iter, Darkmont = 1/iter | **VERIFIED** (≈, see N1) | D1/D2, F, G |
| Cross-modifying code shows the Darkmont-only XMC counter | **VERIFIED** as presence | VERDICT 9 checks presence only (see N3) |
| "torn-fetch shows 0 torn reads on this part" | **UNVERIFIABLE by construction** | B1 |
| "`make` builds smcobs, runs the full sweep, prints the report" (also AGENTS.md "Build/run") | **FALSE** | A, and B2 |
| Precision note: "a fixed ~2-count loss at the counter ENABLE/DISABLE boundary, so P prints 1.9999 (= 399998/200000)" | **FALSE** | G, and N1 |
| No network, no writes outside the directory, no foreign process touched | **VERIFIED** | E |
| Novelty N3, with Botacin SAP, SMaCk and libLISA disclosed | Consistent with REVIEW-01 §2.1 | README "Why this is novel" |

## 3. Issues

**B1 [BLOCKING]: the torn-fetch probe has zero power, so its VERDICT is vacuous.**
- `smcobs.c:205–208` places `b0 | imm8 | c3` at offsets 63/64/65, straddling the 64-B boundary.
- The writer (`:195–197`) only ever stores the **single byte** at offset 64 (`*imm = 0; *imm = 1;`).
- The opcode byte on the other side of the boundary never changes, and a single-byte store can't be torn.
- So every possible fetch decodes as `mov al,0` or `mov al,1`. The classifier at `:213` (`v==0` / `v==1` / else `torn`) **can never increment `torn`**.
- That makes "no torn instruction fetch observed" (VERDICT 10, README "Novel observable", BUILD-01 "torn-fetch probe") a guaranteed outcome, not an observation.

Fix **either** way:
- **(a) Redesign** so the instruction's bytes change on **both** sides of the boundary, and a mixed fetch that *never existed in memory* is distinguishable. One valid design:
  - Put `mov eax, imm32` with its imm32 split across the line, e.g. starting at 61 so imm32 occupies 62–65.
  - Alternate between A = `0x11112222` and B = `0x33334444`.
  - Write the **high half first** going A→B, and the **low half first** going B→A. On x86-TSO, memory then only ever holds A, `0x33332222` and B.
  - An executor result of `0x11114444` is then a genuine torn fetch.
  - Mind that each half-write must itself be a single aligned 2-byte store.
- **(b) Drop** the torn-fetch probe, its VERDICT and every claim about it.

**B2 [BLOCKING]: false run instruction.**
- README.md "How to run" says `make` "builds smcobs, runs the full sweep, prints the report". AGENTS.md says "Build/run: `make` (build + full sweep + report)".
- `smcobs:` is the first rule in the Makefile, so the default goal only compiles (step A).
- Fix: add `.DEFAULT_GOAL := run` (or reorder the rules), **or** correct both documents to say `make run`. Then re-capture RUN.md with whatever the README tells a reader to type.

**N1 [nit]: the precision note's explanation is FALSE.**
- The shortfall isn't fixed and isn't ~2.
- In 54 runs of my `deficit_probe.c` (identical store-then-call pattern) it ranged **2–42 counts** per 2×10⁵ iterations, varying run to run, and a **warm-up of 1 or 4 calls did not remove it** (`deficit-output.txt`). So it isn't a counter-boundary artefact, nor simply the cold first iteration. The cause isn't established; interrupts during the loop are one untested candidate.
- The note's own arithmetic fails too: 399998/200000 = 1.99999 prints as `2.0000` at `%.4f`. The printed `1.9999` implies a shortfall of ≥10 (checked numerically).
- VERDICT 8's 3-decimal comparison tolerates shortfalls of up to 100 counts (checked numerically), so nothing load-bearing changes.
- Replace the explanation with the measured range and "cause not established".

**N2 [nit]: misattribution.** BUILD-01.md "Representative-CPU sampling" says "The reviewer reproduced the probe across 0/2/3, 4/9/11, 12/15". That was the **C04 undefined-flags** probe, not the SMC sweep. The class generalisation now rests on step F (all 16 CPUs), so cite `review/evidence/build-01/F-all-cpus.txt` instead.

**N3 [nit]: VERDICT 9 is a presence check.** `xmc_e = any(... k[2]=="xmc" ...)` only shows that an XMC row exists. The data shows something stronger that the report states nowhere, and it reproduced 3/3 for me:
- Darkmont executors book cross-core modification as **XMC with SMC = 0.0**.
- P executors book it as **SMC** (medians 98k–208k per 1e6 executes).

Make that the verdict.

**N4 [nit]: R3.** RUN.md doesn't itself declare its nondeterministic fields: tsc/iter in the smoke rows, the xcore medians, and clear counts up to ~40/2×10⁵ (per N1). Today only the README says so. Add one line to RUN.md.

**N5 [nit]: REVIEW-00 §1.18 asks for median *and spread*.** The report prints medians only. A min–max per cell, even if trivially 0 at 2 decimals, would satisfy it.

**N6 [nit]:** `do_torn` doesn't check `pthread_create`'s return value (`smcobs.c:211`); `do_xcore` does.

**N7 [nit, optional]:** worth saying in the README that both probes' stores are **silent**: they write `0xcc` over `0xcc`. The clears still occur, so detection is address-based, not value-based. That's a nice teaching point.

## 4. Novelty in the implementation: yes, it embodies the frame

The running artifact produces the novel observable named at Gate 1. Per core class, it tests the documented §3.6.8.1 granularity against silicon, and the two placements show the window tracking the code. This didn't collapse into a known toy: it's not "SMC costs ~N cycles", but a falsifiable per-class map with a Pentium-4-era rule confirmed on one class and refuted on the other. This is the strongest observable in the shortlist so far.

## 5. Safety

**Benign.**
- Own-process RWX page filled with `int3`.
- User-only counters on its own threads.
- The cross-core experiment uses two threads of one process and reports counts, not a channel (P1-4).
- No network, no out-of-tree writes, no foreign process (E).

## 6. What clears the gate

Fix B1 and B2, re-capture RUN.md, and add a "Fix round 1" section to BUILD-01.md. Then post `GATE BUILD-01 READY (fix round 1) — commit <hash>`. The nits are requested but not required.

On round 2 I'll re-run steps A through E on the new commit. Per REVIEW-00 §1.9, new [BLOCKING] items may only be raised against changed code.
