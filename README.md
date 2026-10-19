# lowlevel-lab

Novel low-level programming project frames — ARM64 assembly, x64 assembly,
self-modifying code, visualization of how computers work — researched for
genuine novelty (not already done on GitHub), then built out as working
prototypes under adversarial review at every step.

- **Slug:** `lowlevel-lab` (same in all three zones, per project-storage standard)
- **Desk (this VM):** `~/workspace/projects/lowlevel-lab/` — briefs, README, mirrored findings
- **Workshop (nibbles):** `~/projects/lowlevel-lab/` — git repo, all builds run here
- **Shelf:** none yet — finished material only, when Derek approves
- **GitHub:** no repo yet — local git on nibbles only; publishing is Derek's call

## Lanes (Fleet Harness Spec §13 — interactive tmux over SSH, task checkout)

| Lane | tmux session (nibbles) | Harness | Model / effort | Pool |
|---|---|---|---|---|
| Author | `lowlevel-lab-author` | Claude Code 2.1.286 | `claude-opus-5-5` / `--effort max` | claude-max-gmail |
| Adversarial reviewer | `lowlevel-lab-reviewer` | Claude Code 2.1.286 | `claude-opus-5-5` / `--effort max` | claude-max-gmail (same pool/machine — Derek's explicit instruction for this project; an exception to the scheme's author≠reviewer pool rule, recorded 2026-10-18) |

## Machine facts (verified live 2026-10-18 ~21:57–22:05 PDT)

- nibbles: Linux x86_64, 16 cores, 30 GB RAM — x64 assembly runs natively
- Present: gcc 13.3 (GNU as/ld), gdb, python3 3.12, gh (logged in as derekblair)
- Absent (no installs without Derek's per-machine OK): clang, nasm,
  qemu-aarch64, aarch64 cross-gcc — so ARM64 prototypes must run via tooling
  the project builds itself (assembler/emulator/visualizer in Python/C),
  not via a preinstalled cross toolchain

## Gates

1. Research: ≥15 candidate frames → GitHub-evidenced novelty → proposed 5.
   Reviewer attacks novelty independently → **REVIEW-01** gate.
2. Build each of the 5 (builds + runs captured). Reviewer reproduces and
   verdicts **per build** → fix loop.
3. Final: reviewer full re-check → **SUMMARY.md** with novelty confidence.
