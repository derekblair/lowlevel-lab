# research/probes — feasibility evidence (author lane)

Small throwaway experiments run during Step-1 research to prove a candidate's
central phenomenon is *real and reachable on this machine* before shortlisting
it. These are evidence, not deliverables; the real builds live in `parts/`
after Gate 1. Each dir has the exact source and a captured `probe-output.txt`
(verbatim commands + output). Reviewer: re-run with the commands shown in each.

- **pt-smc-misdecode/** — proves Intel-PT + gdb/libipt *silently misdecode
  self-modifying code*: the program prints the result of the OLD code while
  the hardware-trace history for that same execution shows the NEW bytes, no
  gap/warning. Backs concept P2 (pt-truth). Build: `gcc -O1 -g smc.c -o smc`;
  decode via `gdb record btrace pt` (needs `set record btrace cpu none` —
  libipt 2.0.6 reports "unknown cpu" for this Panther Lake part).

- **hybrid-undefined-flags/** — proves P-cores and E-cores of this one die
  compute the *architecturally-undefined* OF flag differently after
  shifts/rotates (count ≥ 2): P = "first-step" rule, E = "last-step" rule;
  results agree, `SAR` agrees. Backs concept P3 (hybrid-diff). Build:
  `gcc -O2 uflags.c -o uflags` etc.; pin with the CPU number argument
  (0–3 = P / `cpu_core`, 4–15 = E / `cpu_atom`).

These were written to the standing tree because they are author research
artifacts (the reviewer reproduces builds from a fresh clone, so committed
evidence here is the point). They assume this exact CPU (family 6 model 0xCC);
on other silicon the specific numbers change but the method holds.
