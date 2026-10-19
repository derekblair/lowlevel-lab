# part 02 — pt-truth (AGENTS.md)

Part of **lowlevel-lab** (see ../../AGENTS.md). Author-lane build P2. Reshaped
to N2 at REVIEW-01 §2.2 (P2-1/2/3): version-attribution head-to-head, PTW-fence
vs time-keyed, for Intel-PT decoding of self-modifying code.

- **What:** `ptcap.c` (PT capture of a self-modifying target, emits in-band PTW
  fences + exec markers), `ptdecode.py` (from-scratch PT packet framer, stdlib),
  `attribute.py` (the two decoders + CPUID.15H MTC→TSC conversion),
  `verify_singlestep.c` (independent, no-PT ground truth via TF single-step),
  `run.sh` (core class × timing × delay sweep, each class pinned with
  `taskset`: CPU 0 P, 4 E, 12 LP-E), `report.py` (per-class VERDICTs). README
  explains it; RUN.md is the verbatim evidence.
- **Build/run:** `make` (ground-truth check + capture sweep + report). Present
  tools only: gcc, make, python3 stdlib, unprivileged `perf_event_open(intel_pt)`
  with PTW. No root, no libipt, no perf binary, no installs.
- **Novel observable (R4):** PTW-fenced attribution is exact at every timing,
  delay and core class, and needs no timing packets. The strongest TSC+MTC-
  payload time-keyed decoder is exact only over an interval band (at coarse
  timing). It fails at short intervals on every class. At long gaps it fails on
  Darkmont (E, LP-E), starting at the predicted 196,608-TSC MTC-payload wrap,
  because that trace carries sporadic MTCs; on Cougar Cove (P), whose trace
  carries an MTC every period, it does not. Fine timing is exact. Proven by the
  `VERDICT PASS` lines in RUN.md §3; ground truth confirmed in §2.
- **Oracle (R6):** independent of PT — `verify_singlestep` (EAX-at-ret ==
  EXEC_TAG+i) confirms which self-modified bytes ran; the PT framer self-checks
  by consuming the whole buffer and recovering every PTW.
- **Baseline (not the claim):** naive bytes-as-now PT misdecode is the known
  baseline, demonstrated in ../../research/probes/pt-smc-misdecode/.
- **Safety:** benign — own user-mode code only, no root/network/foreign process.
- **Limits:** CYC enabled-but-not-decoded in fine mode (fine time-keyed is a
  lower bound, stated); packet-level not full instruction decode; x86 model
  0xCC config constants. Details in README "Limits".
- **Artifacts:** `data.csv` generated (reproducible via `make`); `ptcap`,
  `verify_singlestep` are build outputs. `make clean`-able, not build inputs.
