# lowlevel-lab — project context

Novel low-level programming project frames (ARM64 assembly, x64 assembly,
self-modifying code, visualization of how computers work), researched for
genuine GitHub novelty, then built as working prototypes under adversarial
review. Derek's commission, 2026-10-18.

## Zones (one slug: `lowlevel-lab`)

- Desk: `~/workspace/projects/lowlevel-lab/` (coordinator VM) — records,
  briefs, `state.yaml` (coordinator is its only writer, Spec §12)
- Workshop: `~/projects/lowlevel-lab/` on nibbles — the working git repo,
  all builds run here
- Shelf: none. Nothing is promoted to Dropbox without Derek's word.

## Who works here — two lanes, one tree, strict writer discipline

- **Author lane** — tmux `lowlevel-lab-author` on nibbles, Claude Code,
  claude-opus-5-5 / max effort. Brief: `BRIEF-AUTHOR.md`. Writes:
  `research/`, `builds/`, `parts/`, `SUMMARY.md`, `STATUS-AUTHOR.md`.
- **Adversarial reviewer lane** — tmux `lowlevel-lab-reviewer` on nibbles,
  same model/effort. Brief: `BRIEF-REVIEWER.md`. Writes ONLY `review/` and
  `STATUS-REVIEWER.md`. Build reproductions run in its own task checkout
  `tasks/reviewer-repro/` (Spec §13), never in the shared standing tree.
- **Coordinator (Bossman)** writes: this file, `README.md`,
  `capabilities.yaml`, `state.yaml` (desk), the briefs, and dated
  `COORDINATION-*.md` notes. Bossman never edits a lane's files.
- One writer per file. Gate verdicts live in `review/`; a gate is cleared
  only by the reviewer's file, never by chat.

## Layout

- `research/` — candidates + novelty evidence log (author)
- `builds/` — per-concept build handoffs (author)
- `review/` — REVIEW-00/01/NN/FINAL verdicts (reviewer)
- `parts/NN-<slug>/` — the 5 built concepts (Spec §4 parts); each part
  carries its own `AGENTS.md`, `README.md`, `RUN.md`, and build system
- `tasks/` — disposable task checkouts (reviewer reproductions); not state

## Off-limits

- No installs or removals on nibbles beyond Derek's approved list
  (2026-10-18: qemu-user + gcc-aarch64-linux-gnu). No GitHub repo creation,
  no pushes, no remotes — publication is a human gate (Spec §9, reserved).
- No secrets in this folder, ever. Nothing goes to the shelf from here.
- Self-modifying-code work stays benign/educational: own-process patching
  and tiny JIT demos only — no evasion, packing, or exploit tooling.
