GATE: plan | VERDICT: n/a — plan review (sets the evidence standard; binds the reviewer now, the author from REVIEW-01) | ROUND: 1 | AT: 2026-10-18 22:35 PDT | COMMIT: 625ad5d

# REVIEW-00 — the brief pair, the gate design, and the evidence standard

Reviewer lane `lowlevel-lab-reviewer` · claude-opus-5-5 / max · nibbles.

**What I reviewed** (all at 625ad5d):
- `BRIEF-AUTHOR.md`, `BRIEF-REVIEWER.md`, `README.md`, `AGENTS.md`, `capabilities.yaml`
- `COORDINATION-2026-10-18.md`, `TOOLCHAIN.md`, `install.log`
- `STATUS-AUTHOR.md` up to its 22:14 lines

I also re-probed the machine live. Raw evidence:
- `review/evidence/00-machine-facts.txt`
- `review/evidence/qemu-fidelity/` (source and verbatim output)
- `review/evidence/search/smoke-test.log`

**Who this binds, and when.** The author brief makes only REVIEW-01 and later binding, so this file doesn't bind the author yet. Every request in §5 will be restated as a condition in REVIEW-01, where it does bind. I am bound by §2 and §4 from the moment this file is committed.

---

## 0. Machine facts — what the briefs say vs. what I measured

1. **The ARM64 toolchain is now present and Derek-approved, so both briefs are stale.**
   - My first probe at 22:05:30 found qemu-* and aarch64-* absent.
   - From 22:13:12 to 22:13:19 the box ran `apt-get install -y qemu-user gcc-aarch64-linux-gnu`. Sources: `/var/log/apt/history.log` (Requested-By derekblair), `run-install.sh`, commit 625ad5d. TOOLCHAIN.md records Derek's approval at ~22:11.
   - Now present: aarch64-linux-gnu-gcc 13.3.0, aarch64-linux-gnu-as/ld/objdump 2.42, qemu-aarch64 8.2.2, qemu-x86_64 8.2.2.
   - `qemu-user-binfmt` came in as a dependency and registered **29** `qemu-*` binfmt handlers.
   - BRIEF-AUTHOR.md "Hard constraints" and BRIEF-REVIEWER.md "Machine constraints" still say qemu-aarch64 and cross-gcc are absent, and still say "NO installs".
   - **My ruling for review purposes:** AGENTS.md "Off-limits" (approved list 2026-10-18: qemu-user + gcc-aarch64-linux-gnu) and TOOLCHAIN.md govern. They are the later, explicit record of Derek's approval, and COORDINATION-2026-10-18.md item 4 says the brief text stands only "until [TOOLCHAIN.md] lands", which it now has.
   - Every other install remains [BLOCKING].
   - For Bossman: those two brief lines should be updated. I don't edit coordinator files.

2. **qemu-user is a functional oracle, not a microarchitectural one.** I verified this (`review/evidence/qemu-fidelity/`).
   - The test is a benign own-process patch: `mov w0,#1` becomes `mov w0,#2` in an RWX page, *after* the first version has already executed and been translated.
   - Without `__builtin___clear_cache`, the patched page returns the **new** value 3/3 times. That's identical to the flushed variant, and the same happens through binfmt.
   - So qemu-aarch64 8.2.2 is SMC-coherent. It can never exhibit the stale-instruction hazard that ARM64's `DC CVAU / DSB ISH / IC IVAU / DSB ISH / ISB` sequence exists to prevent.
   - Not yet verified, and expected from how TCG works [recall]: no cache or pipeline timing model, and guest weak-memory reorderings largely masked by the x86-TSO host.
   - **Consequence:** an ARM64 claim about caches, timing or memory ordering can't be demonstrated by running under qemu here. It has to come from an explicit model in the project's own code, be labelled as model output, or move to SUMMARY's "native ARM64 v2" section.

3. **binfmt makes emulation invisible.** `./prog` on an aarch64 ELF now silently runs under qemu (verified). Wherever that's what happens, a README must say "under qemu-aarch64". "Runs on ARM64" is a FALSE claim on this box.

4. **x86 facts:**
   - Host binutils targets x86 only.
   - `gcc -m32` exits 1 with four "cannot find" errors (Scrt1.o, crti.o, -lgcc twice). **No 32-bit x86 builds.**
   - `gcc -static` works.
   - CPU: Intel Core Ultra X7 358H. It has avx2, bmi2, sha_ni, rdtscp and intel_pt, and **no avx512f**, so AVX-512 emission will SIGILL.
   - The author reports a hybrid PMU (cpu_core on CPUs 0–3, cpu_atom on 4–15). I'll verify that if a build depends on it.
   - Kernel knobs: `ptrace_scope=1` (descendants only), `perf_event_paranoid=2` (user-space counting of own tasks only), `randomize_va_space=2` (addresses vary per run unless `setarch -R`), `mmap_min_addr=65536`.
   - `/tmp` sits on `/` (ext4, no noexec), so RWX mmaps and exec from /tmp work.

5. **Python is stdlib-only.** Absent: capstone, unicorn, keystone, elftools, lief, iced_x86, z3, numpy, PIL, matplotlib, pygame and **tkinter**. curses is present. gdb 15.1 embeds Python 3.12.3.
   - So visualizations have to be terminal output (curses/ANSI) or emitted files (text, SVG, HTML, PPM).

6. **Present, but in neither brief:** node v24.21.0, cmake 3.28.3, perl 5.38, strace 6.8, setarch and taskset (util-linux 2.39.3), firefox 155.0.1, ffmpeg 6.1.1, OpenJDK 21.
   **Absent, and in neither brief:** valgrind, rr, perf, ltrace, bpftrace, docker, podman, wine, ruby, go, rustc, tcc, zig, and a riscv64 cross-gcc (qemu-riscv64 exists, but there's nothing to compile for it).

7. **RAM:** 30 GB total, but only **4 GB available** at 22:17 because other workloads run on this laptop. Prototypes must not assume more than ~2 GB.

8. **gh:** a single token (derekblair) is shared by both lanes, with limits of 30 search/min and 10 code_search/min. See §1.3.

9. **The author's 22:14 status line is stale.** It says "ABSENT on PATH: … qemu-*, aarch64 cross tools", which predates or misses the 22:13 install. The author's "PROPOSED POLICY" for the Unreal-bundled aarch64 toolchain is answered in §2.3, and I'll rule on it formally in REVIEW-01.

---

## 1. Attacks on the brief pair and the gate design

Each item gives the hole, how it gets exploited (deliberately or not), and the rule I'll apply.

**1.1 The reviewer is correlated with the author.** We share the model, effort, pool, machine and GitHub token; README.md's "Lanes" table records this as a deliberate exception. The risk isn't collusion. It's shared blind spots: the prior art I'd recall is the prior art the author would recall.
→ My novelty verdicts rest on searches, never on recall; recall only generates queries. Every KEEP I give names the strongest threat that search found and says why it doesn't kill the concept. I also pre-register each theme's heavyweight prior art in §3, before seeing CANDIDATES.md, so neither lane can quietly leave it out.

**1.2 "Novel" is undefined, so stacking qualifiers wins.** "Not done yet on GitHub" is trivially true of any conjunction. "ARM64 + self-modifying + curses + Python + visualizer" returns zero hits even though every component, and most pairs, already exist.
→ I apply the strip test (§2.1). I remove incidental qualifiers (implementation language, UI medium, file format, "for learners") and search for the stripped core. If the core already exists, the novelty lives in a qualifier. The candidate then has to explain how that qualifier changes what the thing *shows*. ARM64's non-coherent I-cache genuinely changes SMC semantics compared with x86. "Written in Python" changes nothing.

**1.3 The shared rate-limit bucket can make errors look like absence.** Both lanes draw on one 30 + 10 per-minute budget. A throttled call (HTTP 403/429), or a response with `incomplete_results: true`, could be logged as "0 hits" and then read as evidence of novelty.
→ A "0 hits" claim counts only if the log shows exit 0 and a `total_count` from that same call. I'll re-run at least two of the author's logged queries per shortlisted concept. If my count is materially higher (the author logged 0, I get 40), that concept's novelty record is [BLOCKING] until it's redone. I pace my own lane (≤6 code and ≤20 repo searches/min) and back off on 403. My wrapper `review/tools/ghsearch.sh` records exit, `total_count` and `incomplete_results` for every query.

**1.4 `gh search code` is a weak oracle for absence.** It uses the legacy REST code index: default branch only, files under 384 KB, no regex, punctuation ignored, forks mostly unindexed, capped results.
→ Silence from code search is supporting evidence, never primary. Primary absence evidence means repo searches (name, description and topics, plus `in:readme`) across several vocabularies, plus a web search.

**1.5 The "closest existing thing" can be a strawman.** CANDIDATES.md asks for "the closest existing thing you know of". "Know of" invites naming a weak neighbour.
→ See §3. A candidate in a theme has to be distinguished from that theme's giants, whether or not the author mentions them.

**1.6 Padding and cherry-picking.** "≥15 candidates" can be met with ten weak fillers so that the final five look selected. The quieter failure is the reverse: a stronger but harder candidate gets cut "for buildability" while a weaker, easier one survives.
→ In REVIEW-01 I score all ≥15 candidates on the same axes and check that cut reasons are applied consistently. If X was cut as "hard to build" and shortlisted Y is just as hard, that's [BLOCKING].
→ The ARM64 excuse is gone. ARM64 now assembles, links and runs (under qemu), so "no toolchain" no longer justifies a shortlist with no ARM64 content. The mission names ARM64 first. The opposite trap is new: since qemu can't show microarchitecture (§0.2), an ARM64 frame has to be about something qemu does model (ISA semantics, encodings, control and data flow) or something the project models itself.

**1.7 Replacements can skip review entirely.** BRIEF-AUTHOR Step 1.4 says cut or reshaped concepts are "replaced or reworked, then note GATE 1 CLEARED". Nothing requires those replacements to be reviewed, so a concept I CUT could be swapped for one nobody has novelty-checked, and then built.
→ REVIEW-01 clears only the concepts it names. A replacement, or a materially reshaped concept, needs a written addendum in `REVIEW-01-research.md` before its build starts; I'll turn that around within one poll cycle. Building an unreviewed concept is [BLOCKING] at its build gate.

**1.8 The gate markers collide.** The research gate marker is "GATE 1 READY — awaiting REVIEW-01". Build 01's marker, from Step 2, is "GATE 01 READY — awaiting REVIEW-01". They differ by one character and share an identical suffix. A glob like `review/REVIEW-01*` matches the research review and could be mistaken for build-01 approval.
→ Every review file starts with one grep-able header line: `GATE: <plan|research|build-NN|final> | VERDICT: … | ROUND: n | AT: … | COMMIT: …`. That line always holds the **current** verdict, with history underneath. A verdict for build NN lives only in `review/REVIEW-NN-build.md`.

**1.9 There's no re-review trigger, no round cap and no dispute path.** After CHANGES REQUESTED, the author "fixes, re-captures RUN.md, notes the fix round in BUILD-NN.md". Nothing says when I look again, how many rounds are allowed, or what happens if the author disagrees.
→ **Trigger.** I re-review when a new STATUS-AUTHOR.md line names the gate, or when BUILD-NN.md gains a "Fix round" section.
→ **No goalpost-moving.** A later round may add a new [BLOCKING] only for code changed since my previous round, or for evidence I couldn't reasonably have found then, and I'll say which. Anything else gets filed as a [nit].
→ **Disputes.** The author rebuts in BUILD-NN.md with evidence. Factual matters (a failed reproduction, a false README claim, safety) stay blocking until the evidence changes. Judgment calls I may downgrade to [nit], with the dissent recorded.
→ **Cap.** After three rounds on one gate I write `ESCALATE` in STATUS-REVIEWER.md for Derek, stating exactly what's unresolved.
→ **Parallelism.** I may write "proceed-in-parallel" when the remaining blockers are local to the build under review.

**1.10 "Verbatim RUN.md" can't be falsified unless the tree and the commands are pinned.** RUN.md could have been captured from an earlier tree, an uncommitted edit, or a warm build directory.
→ I reproduce the commit named in the GATE line (or HEAD when I start, which I record) from a fresh `git clone` into `tasks/reviewer-repro/`. That gets the committed state only, so uncommitted work isn't what I review. I run the README's commands exactly as written and diff the output against RUN.md (§2.2).

**1.11 Self-consistency is not correctness.** An author-written assembler, disassembler and emulator can agree with each other perfectly while sharing one misreading of the encoding tables. The same tautology appears whenever golden files are generated by the code under test.
→ Each build needs at least one test against an independent oracle (§2.3). On this box that's now possible for both x86-64 and ARM64.

**1.12 "Build them out" has no defined depth, and the novel part can quietly disappear.** I accept the "small, sharp prototypes" style. The risk is a build that drops the novel part: the frame is "X that shows Y", and the running thing is a generic X.
→ Each README must name its **novel observable**: the specific thing a run shows that §3's prior art doesn't. It must point to the RUN.md lines where that observable appears. If it doesn't appear in my reproduced output, that's [BLOCKING]. I'll also diff the concept text from NOVELTY-LOG to SHORTLIST to README, because the thing built has to be the thing that was searched.

**1.13 Three writers share one branch, and `tasks/` is a trap.** Bossman (two commits at 22:14), the author and I all commit to `master` in one working tree.
- A `git add -A` or `git commit -a` from anyone sweeps up the others' files, including Bossman's untracked `run-*.sh` and `install.log`.
- `tasks/` isn't gitignored. My `tasks/reviewer-repro/` clone is a nested git repo, so a `git add -A` would commit it as an **embedded gitlink**.
- Concurrent commits race on `.git/index.lock`.

→ I commit with `git commit -- <my paths>`, which commits only those paths and leaves anyone else's staged work alone. If the lock is held I retry; I never delete a lock. I never run `git add -A`, `stash`, `checkout`, `reset` or `clean` in the shared tree.
→ For Bossman [nit]: add `tasks/` to `.gitignore`. That file is his, not mine.

**1.14 Tooling goes undeclared in both directions.** The brief's tool list is incomplete either way (§0.6). Prototypes can quietly depend on node, gdb-python, strace or firefox, on binfmt, or on kernel knobs.
→ Any command my clean reproduction can't resolve is [BLOCKING] as silently assumed tooling. Using a present-but-undeclared tool is fine once the README declares it.

**1.15 The safety line is vaguest exactly where this theme is riskiest.** I logged `topic:self-modifying-code` (70 repos, in `review/evidence/search/smoke-test.log`). Its best-match top ten are mostly an instruction-level obfuscator, a VM-based code virtualizer, polymorphic engines, an ELF encrypting packer and an anti-analysis crackme. The existing GitHub population for this theme is what the brief forbids, so a "novel SMC" frame can drift into it just by imitating its neighbours.
→ §2.4, stated now so it surprises nobody at a build gate.

**1.16 My recall has a recency gap.** My knowledge cutoff is June 2026 and today is 2026-10-18, so my recall misses about four months of GitHub, a period full of machine-generated toy repos.
→ Every theme search includes a recency-sliced query (`created:>2026-04-01`). A low-star repo counts as prior art if it implements the core idea (§2.1).

**1.17 The environment changed mid-gate.** The install landed at 22:13 and the layout change (`projects/` → `parts/`, reproductions in `tasks/`) at 22:14, eight minutes into the author's research.
→ Each gate is judged against the environment as it stood at its GATE READY time, recorded in the review header. Changes that happen during a review get noted, not retroactively enforced.

**1.18 Measurement frames on a hybrid laptop CPU.** The author's 22:14 line points toward per-core-type measurements. Timing and PMU numbers vary with core type, frequency, thermal state and power source, so a byte-exact RUN.md is impossible.
→ A measurement claim has to be an inequality or ratio with a declared tolerance, pinned with `taskset` to a named core type, and reported as a median and spread over at least five runs. I reproduce at least three runs and check the direction and order of magnitude. Anything else is UNVERIFIED.

**1.19 Review latency is unbounded.**
→ My commitments:
- I start a gate review within one poll cycle (≤5 min) of its marker, and post a "reviewing" line.
- Target turnaround: REVIEW-01 ≤ 90 min, build reviews ≤ 60 min, fix rounds ≤ 30 min.
- If I miss a target, I say so in STATUS-REVIEWER.md.

---

## 2. The evidence standard (binding on me as well)

### 2.1 Novelty

**Levels**, used in every verdict:

| Level | Meaning | Outcome |
|---|---|---|
| N0 — exists | A public implementation does the same core thing for the same purpose | CUT |
| N1 — known idea, minor delta | The delta is a qualifier (language, UI, architecture) that doesn't change what the thing shows | CUT or RESHAPE |
| N2 — adjacent prior art, substantive delta | The parts exist, and a specific, nameable gap changes the observable | KEEP only if that gap is the prototype's centrepiece, otherwise RESHAPE |
| N3 — no implementation found | A documented, diverse search found nothing, though the components are known | KEEP |
| N4 — N3, and the frame itself is a new way to see something | — | KEEP, strong |

**Minimum search record per shortlisted concept.** I meet this too.
1. At least three repo searches using different vocabularies, including at least one `topic:` and one `in:readme` query.
2. At least one recency-sliced repo search (`created:>2026-04-01`).
3. At least two code searches on a distinctive implementation signature (mnemonics, syscall combinations, magic constants), not on the pitch's own words.
4. At least one web search for non-GitHub prior art (papers, blogs, GitLab/Codeberg, Hacker News).
5. For every query, record:
   - the exact query string and UTC time;
   - the exit code, `total_count` and `incomplete_results`;
   - the top hits, up to ten (full_name, stars, created/pushed dates, one line on what each is);
   - a disposition for every relevant hit.

**Kill rule.** A hit kills a concept (N0/N1) only after I've read its README and at least one source file via `gh api`, as data (never cloned and run), and quoted what it does.
- Stars measure awareness, not existence. A 0-star repo that implements the core is prior art.
- A README-only repo with no implementation gets recorded but doesn't kill.

**Selective logging is [BLOCKING].** If a near-duplicate shows up in the results of the author's own logged query and isn't in the log, that concept's record is [BLOCKING].

**Prior art outside GitHub** (papers, well-known web tools, blog series) doesn't fail the mission's literal bar ("on GitHub"). It does cap novelty at N2, and the README must disclose it.

**Recall-only claims** ("I know of nothing like it") are UNVERIFIED, whichever lane makes them.

### 2.2 Reproduction

- **Pin.** I reproduce the commit hash from the GATE line, or HEAD when I start, recorded in the review header.
- **Clean start.** A fresh `git clone` into `tasks/reviewer-repro/<gate>-r<round>/`, then `git checkout <hash>`. The README's commands run verbatim under `env -i HOME=<fresh dir in the clone> PATH=/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8`, with `timeout` and `ulimit -c 0`. I add a memory cap wherever the README states expected usage.
- **Read before run.** I read every source file before executing it, looking for sudo, network use, writes outside the tree, and ptrace or memory access into foreign processes.
- **Then run under `strace -f`**, to confirm there are no write-mode file operations outside the clone and `/tmp`, no `connect` or `sendto`, and no exec of sudo. Any of these is [BLOCKING] unless the README declares it and it's benign.
- **Twice.** I run the full documented sequence twice in the same clone, which catches state left behind by the first run, plus `make clean` and a rebuild where a clean target exists.
- **Diff against RUN.md.** Byte-level, after normalizing only the fields that RUN.md or the README *declare* nondeterministic (ASLR addresses, timings, PIDs). An undeclared difference is [BLOCKING] if it changes a claim, otherwise a [nit].
- **Hygiene.**
  - The original tree's `git status --porcelain` is unchanged by my run.
  - The clone's status shows only declared or ignored artifacts.
  - No committed binary is a build input.
  - No absolute paths point into the author's tree.
- **Claims.** Every README claim gets one tag: VERIFIED (reproduced, with the evidence file named), UNVERIFIED (not reproduced or not testable here), or FALSE (I reproduced the contrary).

### 2.3 Correctness oracles

**x86-64:** native execution on this CPU, plus host GNU as/objdump 2.42.

**ARM64:**
- aarch64-linux-gnu-as/objdump 2.42 for encoding and decoding.
- qemu-aarch64 8.2.2 for user-mode execution semantics.
- Both are independent of the author's code. I've verified the encoding oracle against hand encodings (`probe-output.txt`).

**Differential testing.** Any author-written assembler, disassembler, emulator or encoder must be differentially tested against these oracles, on a sample **I** choose rather than one the author chooses:
- x86-64: at least 20 instructions.
- ARM64: at least 20 instructions across data-processing (immediate and register), loads and stores with every claimed addressing mode, branches (including CBZ and TBZ), and system/barrier instructions, plus SIMD if claimed.

**No oracle on this box** exists for ARM64 caches, timing or memory ordering (§0.2). Those claims are model-only and must be labelled as such.

**The Unreal-bundled toolchain** (clang 20.1.8 / GNU as 2.40 under `~/.local/opt/unreal-engine-5.8.2/…`):
- My position: it is allowed only as an optional third opinion when the system tools disagree on an encoding, and it must auto-skip when absent.
- It is never a build dependency or a test-pass dependency: the path is machine- and version-specific, it isn't on the approved toolchain list, and the system aarch64 binutils make it unnecessary.
- The author's proposed policy is compatible with this. I'll confirm it formally in REVIEW-01.

**External corpora**, such as LLVM `test/MC/AArch64/*.s` CHECK lines and binutils `gas/testsuite/gas/aarch64/*.d`, remain acceptable supplementary oracles when fetched with repo, commit SHA and path recorded.

**Visualizations.** The claimed observable must be machine-checkable in the emitted artifact (text, SVG or HTML I can grep or parse). HTML must be self-contained, with no CDN loads. If an artifact is claimed to render, I render it headless with the present firefox and a throwaway profile.

**Round trips.** Round-trip agreement between author-written tools is never an oracle.

### 2.4 Safety — the line I'll hold

**In scope:**
- Own-process code generation and patching of fixed, benign, author-written code (arithmetic, printing, a toy-language JIT).
- Assemblers, disassemblers and emulators.
- Tracing child processes the tool spawns itself.
- Visualizing benign files.
- Explaining hardware mechanisms such as coherence, pipelines and SMC penalties.

**[BLOCKING], whatever the framing:**
- Any component whose purpose or measured outcome is avoiding detection, hindering debugging or analysis, or hiding or encrypting code for later execution (packer or crypter behaviour).
- Writing into, or executing code inside, other processes.
- Privilege changes.
- A general-purpose transformer that rewrites arbitrary input binaries.
- Evaluation against security products.

"Studied defensively" passes only as analysis or visualization of toy, author-written snippets, where the deliverable is understanding or detection.

**Also [BLOCKING]:** network activity, sudo, or writes outside the project tree. I check these with strace (§2.2).

### 2.5 Verdict mechanics

- The header line works as described in §1.8.
- Issues are numbered and tagged [BLOCKING] or [nit], and each one cites a `file:line`, a logged query, or a reproduced output under `review/evidence/`.
- A gate clears when no [BLOCKING] issue is open.
- When APPROVE is earned, I'll say it plainly and give the reason.

### 2.6 REVIEW-FINAL ranking rubric, fixed now so it can't be tuned later

- **Novelty, 1–5:** levels N0–N4 shifted up by one.
- **Works, 1–5:**
  - 1 — doesn't build;
  - 2 — builds, but the demo fails or misstates;
  - 3 — works as the README says, with caveats;
  - 4 — also has an independent-oracle test;
  - 5 — clean reproduction twice, oracle tests, edge cases handled.
- **Interesting, 1–5:** does running it teach something about how machines work that a learner couldn't get from §3's prior art?
- **Score:** N × W × I, maximum 125. Ties are broken by W.

---

## 3. Pre-registered prior-art map

Everything below is [recall], written before I've seen CANDIDATES.md. I'll confirm each row by live search as candidates arrive, in `review/evidence/search/presearch-*.log`.

| Theme | A candidate must be distinguished from |
|---|---|
| Visualizing how computers work | Visual6502 / perfect6502 (transistor-level 6502); Ripes (RISC-V pipeline and cache visualizer); CPUlator (ARMv7/MIPS in the browser); VisUAL (ARM); RARS/MARS; Blink / Blinkenlights (x86-64 emulator with TUI memory and register panels); Compiler Explorer; uiCA and the llvm-mca timeline (x86 pipeline/port views); Konata (pipeline visualizer); Nand2Tetris; Ben Eater |
| Binary visualization | Cortesi's scurve / binvis.io (Hilbert-curve byte-class maps); Cantor.Dust (Battelle); Veles; ImHex; binwalk entropy plots |
| x86-64 encoding, JIT, codegen | asmjit; xbyak; Zydis; iced; Intel XED; DynASM; sljit; MIR; GNU lightning; copy-and-patch (Xu & Kjolstad 2021; the CPython 3.13 JIT); Raiter's teensy-ELF tutorial; Bendersky's JIT series; Haberman's "Hello, JIT World"; hundreds of BF JITs |
| ARM64 | dynarmic; Ryujinx ARMeilleure; box64; FEX; QEMU TCG; Unicorn; yaxpeax-arm; Arm's ASL interpreter; sail-arm; HelloSilicon (ARM64 asm on Apple Silicon); many Python ARM64 emulators and assemblers |
| ARM64 memory model | herdtools7 (herd7, litmus7, diy: litmus tests, plus execution-graph diagrams of allowed outcomes); the Arm "cats" model; Flur / RMEM (Cambridge) |
| Self-modifying code | Linux text_poke, static keys, alternatives and ftrace (production SMC); the MS hotpatch prologue; Intel SDM "Handling Self- and Cross-Modifying Code"; Arm ARM on concurrent modification and execution and I/D cache maintenance; `__builtin___clear_cache`; Intel `MACHINE_CLEARS.SMC`; QEMU translation-block invalidation; and, on GitHub, mostly obfuscators and packers (§1.15) |
| Esoteric VMs / weird machines | movfuscator; trapcc (page-fault-driven computation); Dolan's "mov is Turing-complete"; ELF-metadata computation (Shapiro/Bratus/Smith); REpsych; sectorforth, sectorlisp and bootOS; jonesforth |
| Execution tracing / time travel | rr; Pernosco; Qira; Tenet; uftrace; magic-trace (Intel PT with a timeline UI); perf intel_pt; libipt/ptxed; gdb `record btrace pt`; DynamoRIO; Pin; Frida Stalker; countless ptrace single-steppers |
| Microbenchmarks / PMU / hybrid cores | nanoBench; uops.info; Agner Fog's test programs; likwid; Chips and Cheese P-core vs E-core analyses; lmbench |
| KVM / hand-rolled VMMs | dpw/kvm-hello-world; LWN "Using the KVM API" (2015); kvmtool; sysprog21/kvm-host; Firecracker; crosvm |
| Metamorphic / polymorphic | Public engines exist (the smoke-test log shows several). Building an engine is out of scope (§2.4) and not novel anyway. Only analysis or visualization of toy snippets survives. |
| Hand-rolled assemblers / emulators | Saturated: CHIP-8, LC-3, 6502, RISC-V, "x86 assembler in N lines". Novelty has to come from what is shown, not from the fact that one exists. |

---

## 4. How I'll operate

- **Polling.** A background watcher (`until` loop) wakes me when:
  - STATUS-AUTHOR.md gets a `GATE … READY`, `FINAL READY` or fix-round line;
  - any BUILD-NN.md changes after its review;
  - anything appears under `parts/` before `review/REVIEW-01-research.md` exists, which would be a gate violation;
  - otherwise, on a heartbeat every 30 minutes or less.
- **Idle work.** I confirm the §3 rows by live search, themes most likely to be shortlisted first.
- **Reproductions** only in `tasks/reviewer-repro/`. Logs are copied to `review/evidence/<gate>/`.
- **Status.** STATUS-REVIEWER.md gets a timestamped line when each gate review starts and when it ends.
- **Commits** touch only `review/` and STATUS-REVIEWER.md, and always use `git commit -- <paths>`.
- **No interference.** I never build, `make clean`, or run state-changing git commands in the shared tree, and I never edit author or coordinator files.

---

## 5. Requests to the author (restated as conditions in REVIEW-01)

- **R1.** Every GATE READY line names its commit hash, and that commit exists before the line is written.
- **R2.** NOVELTY-LOG.md carries the item-5 fields from §2.1 for every query, including the queries that found a duplicate.
- **R3.** RUN.md declares which output fields are nondeterministic, or the runs are made deterministic (`setarch -R`, fixed seeds).
- **R4.** Each README names its novel observable (§1.12) and points to the RUN.md lines that show it.
- **R5.** Use distinct markers: `GATE 1 READY (research)` versus `GATE BUILD-01 READY`.
- **R6.** Any author-written encoder, decoder or emulator gets a differential test against the §2.3 oracles.
- **R7.** Commit only your own paths. Never `git add -A` or `commit -a`, which sweep in `review/`, STATUS-REVIEWER.md, the `run-*.sh` scripts, `install.log` and `tasks/`.
- **R8.** Each README carries a "Requirements" line listing every tool beyond gcc/binutils/make/python3-stdlib (qemu-aarch64, aarch64-linux-gnu-*, node, gdb-python, strace, firefox, setarch, taskset…).
- **R9.** Re-baseline your toolchain notes against TOOLCHAIN.md. The 22:14 "ABSENT … qemu-*, aarch64 cross tools" line is now false.
- **R10.** Label emulation honestly: "under qemu-aarch64", never "on ARM64". Hardware-only behaviour (caches, timing, memory ordering) is either explicitly modelled and labelled as a model, or deferred to SUMMARY's native-ARM64 v2 section.
- **R11.** Measurement claims follow §1.18.
