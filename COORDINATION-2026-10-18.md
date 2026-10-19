# COORDINATION — 2026-10-18 ~22:15 PDT (from Bossman, coordinator)

Spec-compliance pass (Fleet Harness Spec v0.4) — read this before Gate 1
builds. Three changes and one heads-up:

1. **Builds live in `parts/NN-<slug>/`, not `projects/NN-<slug>/`** (Spec
   §4: concepts are this project's parts). Each part also carries its own
   `AGENTS.md`. BRIEF-AUTHOR.md has been updated to match. Research paths
   (`research/`, `builds/`, `review/`) are unchanged.
2. **Reviewer reproductions run in a task checkout** (Spec §13): clone the
   local repo fresh into `tasks/reviewer-repro/` and build there — never
   build inside the shared standing tree. BRIEF-REVIEWER.md updated.
3. **Project anatomy added:** `AGENTS.md` and `capabilities.yaml` now sit
   at the project root (writer discipline is in AGENTS.md — respect the
   one-writer-per-file table; coordinator files are Bossman's, status
   files are each lane's own). `state.yaml` lives on the desk copy.
4. **Heads-up — ARM64 toolchain:** Derek approved installing qemu-user +
   gcc-aarch64-linux-gnu on nibbles (2026-10-18 22:11 PDT). Install is in
   progress; when verified, a `TOOLCHAIN.md` will appear at the project
   root with versions and a verified qemu run. Until it lands, the
   no-install constraint in your briefs stands exactly as written.
