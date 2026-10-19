# pt-truth

Intel-PT decoders reconstruct the executed instruction stream from the code
bytes they find in the binary/memory image, so **self-modifying code is
decoded against the wrong bytes**. The known baseline — a naive "bytes as they
are now" decode is wrong — is already demonstrated in
`../../research/probes/pt-smc-misdecode/` (gdb + libipt show the *post-patch*
bytes for an execution that returned the *pre-patch* result).

This part is the **head-to-head** the baseline is not: when a trace passes
through several versions of the same self-modified address, **which version was
executing at each point?** Two decoders answer it, scored against ground truth:

- **time-keyed** — the method perf / libipt sideband / wilvk-asm-test use:
  place each execution on the PT timeline from TSC/MTC(/CYC) packets, then pick
  the latest external patch event (an `rdtsc`-stamped log) at or before it.
- **ptw-fenced** — the delta this part proposes: the executing thread emits an
  in-band `PTWRITE(version)` fence; the decoder reads the fence that
  immediately precedes the execution **in packet order**, using no timestamps.

## The result (RUN.md §3, grep `VERDICT`) — intervals in TSC ticks

- **PTW-fenced attribution is exact across the whole interval range** (24/24,
  0 wrong, 0 dropped, every row) and uses **no timing packets** — exact *by
  construction*, since the cooperative fence immediately precedes the exec in
  packet order.
- **The strong time-keyed baseline** (a real TMA-anchored MTC-**payload** TSC
  clock, the way perf / libipt-sb reconstruct time — *not* a packet count) is
  exact only for a **middle band of patch→execute intervals** (≈10³–10⁵ TSC
  ticks on this part). It **mis-attributes below the band** (too few CTC ticks
  to place the exec after its patch) and **above the band** (the 8-bit MTC
  payload wraps between the sparse TSC anchors under BranchEn=0, losing the high
  CTC bits — the long-gap regime at delay 10⁶). The report prints the measured
  band in TSC ticks.
- **Fine PT timing** (dense MTC + CYC) closes the low end: time-keyed is exact
  on all OVF-free rows. So the PTW-fence advantages are specifically (a) it holds
  across the *entire* interval range including both failure regimes, and (b) it
  needs **no** timing packets, where time-keyed always does.
- Ground truth is independent of the PT decode path: `verify_singlestep` TF-
  single-steps the same self-modifying target with **no** perf/PT and confirms
  the byte that executed at each step (EAX-at-`ret` == `EXEC_TAG+i`).

So the honest, surviving N2 claim (see ../../research/NOVELTY-LOG.md C03): an
*executed* `PTWRITE` fence gives exact, in-band, packet-ordered version
boundaries for same-address rewrites, where even a correctly-implemented
time-keyed correlation (perf/libipt-sb/wilvk) has a bounded interval window of
correctness and fails outside it. [Corrected per REVIEW-02-build B1: an earlier
version used a packet-*counting* MTC clock and wrongly reported time-keyed as
failing at *every* coarse interval; the real TMA+payload clock is exact in the
middle band, which is the honest — and more interesting — result.]

## Why this is novel / what it is NOT

Version-correct decoding of rewritten code already exists **by timestamp**:
wilvk/asm-test (`PERF_RECORD_TEXT_POKE` timeline), perf `intel_pt_text_poke`,
libipt `sideband/` (image-over-time at mapping granularity), DRAKVUF (injects
PTW packets). None uses an *executed* PTWRITE as the in-band version fence, and
this part shows the measurable difference against the time-keyed approach. The
baseline "naive decode is wrong" is **not** the contribution (it is well known).
Full prior-art dispositions: ../../research/NOVELTY-LOG.md C03.

## How it works (packet-level, not an instruction walk)

`ptcap.c` traces its own code with PT (`pt|ptw|tsc|mtc[|cyc]`, **branch tracing
off** — BranchEn=0 — so the tunable spin can't flood the AUX ring with TNT).
Per version *i* it records the patch `rdtsc`, patches the mutable region to
`mov eax, EXEC_TAG+i ; ptwrite eax ; ret`, emits the in-band
`PTWRITE(FENCE_TAG+i)`, **then spins `DELAY` cycles, then executes** the region
(order: patch → fence → spin → exec) and records the exec `rdtsc` so the real
patch→execute interval is measured in TSC ticks. Executing emits
`PTWRITE(EXEC_TAG+i)`, whose payload the self-modified bytes produced — ground
truth. The indirect call to the freshly written bytes is what satisfies the
SDM self-modifying-code rule (not the `mfence/lfence`); `verify_singlestep`
confirms the new byte runs.

`ptdecode.py` is a PT packet framer (self-checked: it must consume the whole
buffer and recover every PTW). `attribute.py` runs both decoders: ptw-fenced
reads packet order; time-keyed reconstructs a TSC-domain timestamp per exec the
way a real sideband decoder does — **anchor CTC at the TSC+TMA pair, advance it
from each MTC's payload** (CTC[period+7:period], 8-bit wrap handled), convert via
the CPUID.15H ratio `ptcap` records. It does **not** reconstruct control flow
(the attribution needs only the packet stream), keeping it tractable in stdlib.
This payload clock is cross-checked against the reviewer's independent
`payload_timekeyed.py` (same algorithm, same results).

## How to run

```
make            # verify ground truth, capture the sweep, print the report
# pieces:
make verify_singlestep && ./verify_singlestep 24   # independent ground truth
make ptcap && ./run.sh > data.csv                  # capture + attribute sweep
python3 report.py data.csv                         # VERDICTs; exit 0 iff all pass
```

## Requirements (R8)

- `gcc` (+ `<cpuid.h>`, `<ucontext.h>`), `make`, `python3` (stdlib only).
- Unprivileged Intel PT with PTWRITE: `perf_event_open(intel_pt)` for own task
  (`perf_event_paranoid=2`), PTW cap = 1. No root, no `perf` binary, no libipt
  (the framer is from scratch). `ptwrite` instruction (assembled by gcc).
- This model's config quirks are handled in `ptcap.c`: `mtc_period` 5 is
  rejected here (3/0 used); the PTW header is `02 32` for 8-byte payloads and
  `02 12` for 4-byte. The framer treats the PTW IP bit (`02 b2`) as "a separate
  FUP follows", per the SDM; `ptcap` does not set `fup_on_ptw`, so that path is
  not exercised here, but the framer handles it.

## Limits / honesty

- **The time-keyed baseline uses TSC+TMA+MTC payloads** (the standard
  reconstruction). **CYC is enabled in fine mode but not decoded** (variable-
  length); since fine time-keyed already comes out exact without CYC, decoding
  it could only confirm that — it cannot change the result. A CYC-using decoder
  would do at least as well, so this never overstates the PTW advantage.
- **The time-keyed failure regimes are real, not decoder bugs.** Short interval:
  too few CTC ticks between patch and exec. Long interval: the 8-bit MTC payload
  (CTC[period+7:period]) wraps between the sparse TSC packets that BranchEn=0
  produces, so the high CTC bits are lost. A branch-tracing capture emits TSC
  more often and would push the long-gap threshold out; measuring that is a v2.
- **Packet-level, not a full PT instruction decoder.** The framer handles the
  packet subset these traces contain and self-checks by consuming the whole
  buffer; it is not a general libipt replacement.
- The exact band *edges* jitter run to run (the lower edge sits near one MTC
  tick ≈768 TSC here); the band's existence, the long-gap failure, the
  fine-exact result and PTW-fenced exactness are stable (5/5 `make` runs).
- **OVF handling:** a lossy trace (AUX overflow) is reported per row and
  excluded from time-keyed scoring; `make` passes regardless. The 8 MiB ring
  plus capping fine delays at 10⁴ keeps OVF at 0 in practice.
- The comparison runs with **BranchEn=0** (PTW + timing only). An ordinary
  perf/libipt capture uses `branch=1`, where TSC/MTC emission is denser; the
  long-gap threshold is therefore specific to this low-rate configuration.
- x86-only, this-model-specific config constants (family 6 model 0xCC).
- **Safety:** benign — traces only this process's own user-mode code; no root,
  no network, no foreign process, no writes outside the directory. The ground-
  truth single-stepper uses the trap flag on its own code (educational).
