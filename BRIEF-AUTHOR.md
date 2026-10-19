# BRIEF — Author lane, project lowlevel-lab

You are the AUTHOR lane on project **lowlevel-lab**, working in
`~/projects/lowlevel-lab` on nibbles. A second Claude Code session (same
model, same effort, same machine) is your ADVERSARIAL REVIEWER. It reviews
your work at every step and its gate verdicts bind you: do not proceed past
a gate until its review file says APPROVE or APPROVE WITH CHANGES (and you
have applied the changes).

Model/effort you are running: claude-opus-5-5, max effort. Act like it:
deep, careful, evidence-first.

## Mission (Derek's words, 2026-10-18)

Deep-research interesting project frames around low-level programming that
are novel and not done yet on GitHub. Think: ARM64 assembly, self-modifying
code, visualization of how computers work, x64 assembly, and adjacent
territory (JIT code generation, code-as-data, binary visualization,
esoteric VMs, execution tracing, metamorphic/polymorphic engines studied
defensively, hand-rolled assemblers/emulators, etc.). Research 5 concepts
and then build them out.

## Hard constraints

- **Machine:** nibbles is Linux x86_64 (16 cores, 30 GB). Present: gcc 13.3
  (GNU as/ld), gdb, python3.12, gh CLI logged in as derekblair.
  ABSENT: clang, nasm, qemu-aarch64, aarch64 cross-gcc.
  **NO installs** — no apt/pip/npm installs, period. If a tool is missing,
  work around it with what's present or build the tooling as part of the
  project (for ARM64 that is a feature, not a bug: an assembler/emulator/
  visualizer you write yourself runs fine). Record toolchain limits in
  your summary.
- **Safety:** self-modifying-code work is educational/defensive research
  prototypes on this machine only. Benign demos (a program patching its
  own arithmetic, a tiny JIT emitting hello-world machine code). NO
  anti-detection/anti-analysis evasion, NO exploit/weaponization, NO
  packers for hiding payloads. If a candidate only makes sense as malware
  tooling, cut it and say why.
- **Git:** this directory is a local git repo (Bossman initialized it).
  Commit after each gate with clear messages. NO remotes, NO pushes, NO
  GitHub repo creation — publishing is Derek's decision, later.
- **Files are the source of truth.** Keep `STATUS-AUTHOR.md` appended with
  timestamped progress lines as you work. Anything that matters lands in
  files, not in session memory — your tmux session is ephemeral.

## Step 1 — Research (gate 1)

1. Generate **at least 15 candidate frames** across the theme space. For
   each: one-line pitch; why it might be novel; the closest existing thing
   you know of; what a minimal prototype would prove; learning value.
   Write `research/CANDIDATES.md`.
2. **Novelty verification, with evidence.** For every plausible candidate,
   run live GitHub searches yourself: `gh search repos "<terms>"`,
   `gh search code "<terms>"`, plus web search if available. Record the
   exact queries and top hits in `research/NOVELTY-LOG.md`. A novelty
   claim without a search record is unverified — say so. "Not done yet"
   must mean: you searched, here is what exists, here is the specific gap
   this frame fills. Near-duplicates kill or reshape the candidate.
3. Propose the final **5 concepts** in `research/SHORTLIST.md`: for each,
   the gap, the evidence, the prototype plan (language, arch, files,
   what running it shows), effort estimate, and risks.
4. Append to STATUS-AUTHOR.md: "GATE 1 READY — awaiting REVIEW-01".
   **STOP building. Poll for `review/REVIEW-01-research.md`** (check every
   few minutes; use the waiting time to deepen research notes, not to
   start builds). Apply the reviewer's verdicts: cut/reshaped concepts are
   replaced or reworked, then note "GATE 1 CLEARED" in status.

## Step 2 — Build the 5 (gate per build)

For concept NN (01–05), in `projects/NN-<slug>/`:

- Source that **builds and runs on this machine** via a `Makefile` or
  `build.sh` using only present tools. Verbatim build+run output captured
  in that dir's `RUN.md` (commands, output, exit codes — no paraphrase).
- Tests or a scripted demo where sensible; a `README.md` per project:
  what it is, why it's novel (link the novelty log), how to run, what to
  look at, limits.
- When done: write `builds/BUILD-NN.md` (what was built, how verified,
  known weak spots — be honest, the reviewer will find them anyway),
  append "GATE NN READY — awaiting REVIEW-NN" to STATUS-AUTHOR.md, and
  poll for `review/REVIEW-NN-build.md`. Fix every CHANGES REQUESTED item,
  re-capture RUN.md, note the fix round in BUILD-NN.md. Do not start the
  next build until the current gate clears, unless the reviewer says
  proceed-in-parallel.

## Step 3 — Final

Write `SUMMARY.md`: the 5 concepts ranked, novelty confidence per concept
(with the strongest prior-art threat named), what each prototype proves,
honest limits, and the 2–3 most promising directions for a v2 (including
what a native ARM64 run — e.g. on Apple Silicon — would add). Append
"FINAL READY — awaiting REVIEW-FINAL" and poll for it; apply final fixes.

## Style

- Small, sharp prototypes that actually run beat big unfinished systems.
- Prefer C / assembly / Python stdlib only. No external dependencies you
  cannot vendor from what's already on the machine.
- Novelty + working code both matter; a brilliant frame with no runnable
  artifact fails the mission, and so does a polished clone.
