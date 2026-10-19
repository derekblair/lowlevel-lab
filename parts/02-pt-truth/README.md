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

## The result (RUN.md, grep `VERDICT`) — intervals in TSC ticks

Every sweep is **pinned to one CPU per core class**: CPU 0 is a Cougar Cove
P-core, CPU 4 a Darkmont E-core, and CPU 12 a Darkmont LP-E core (R14).

- **PTW-fenced attribution is exact across the whole interval range on every
  core class** (24/24, 0 wrong, 0 dropped, every row). It uses **no timing
  packets**, and it is exact *by construction*, since the cooperative fence
  immediately precedes the exec in packet order.
- **The strong time-keyed baseline** (a real TMA-anchored MTC-**payload** TSC
  clock, the way perf / libipt-sb reconstruct time, *not* a packet count)
  behaves **per core class** (REVIEW-02 round 3, B3):
  - **Darkmont (E, LP-E): exact only over an interval band.**
    - It mis-attributes at the **shortest** tested interval in every run (E at
      192–318 TSC, 3–15 wrong of 24; LP-E at 248–536, 7–14 wrong). Coarse
      delays 25/50 keep that row well below one MTC period (768 TSC), so the
      gated failure never rests on a single execution (N9). It also fails at
      some rows above one period (LP-E at 870 TSC here; up to ~950 in earlier
      captures).
    - It mis-attributes at **long gaps**, from the **predicted edge**. The 8-bit
      MTC payload CTC[period+7:period] wraps every 2^(mtc_period+8) CTC ticks:
      2¹¹ × 96 (CPUID.15H TSC/CTC = 192/2) = **196,608 TSC ticks**. This is a
      prediction, not a fit.
    - In RUN.md the first failing long rows land at 2.1–2.2×10⁵ TSC (LP-E),
      or by 1.2–2.1×10⁶ when the sweep's 10⁵ step lands below the edge. The
      last exact long rows reach 1.23×10⁵ (1.85×10⁵ in an earlier capture), so
      the edge lies between. A VERDICT requires the onset to match the
      prediction within 2×. Its detail names which side was tight in that run
      (N8); that depends on where each run's 10⁵ step lands relative to the
      edge.
  - **Cougar Cove (P): exact at every tested interval ≥ 2 MTC periods**
    (1,536 TSC), from ~2×10³ TSC up to the longest gap swept (up to ~6×10⁶ TSC
    in RUN.md; the VERDICT requires ≥ 10× the edge). No long-gap failure ever
    appeared. In RUN.md §3 the P rows below 2 periods include failures from
    274 to 936 TSC (16 of 24 wrong at 312), and every row from 1,024 TSC up is
    exact.
    - Its **lower edge sits at about one MTC period**, the resolution of a
      clock that ticks once per period. A dedicated short-delay probe (RUN.md
      §5) ran 20 coarse rows. The 8 that mis-attribute (1–4 of 24 executions)
      all have median intervals below ~1.2 periods (298–914 TSC), and every
      row at ≥ 970 TSC is exact. (`interval` is a median, so a row just above
      one period still holds executions inside it.)
- **Mechanism, read from the packets** (BranchEn=0, at the longest gap):
  - Cougar Cove's trace carries an MTC **every period**: ~1.1–1.9×10⁵ MTCs per
    capture, every payload step +1, **zero** whole-wrap (Δ0) steps.
  - Darkmont's carries ~200–300 MTCs and a **single** TSC, and **63–71%** of its
    consecutive MTC steps in RUN.md are **Δ0** (43–77% across all of today's
    pinned runs): the next MTC came a whole 8-bit payload
    wrap later. A random delta would be 0 with probability only 1/256.
  - So on Darkmont the clock cannot see the wraps that elapsed. That is the
    long-gap failure, and the sparse MTCs are also why Darkmont's short-interval
    edge sits above one period. A VERDICT checks the ≥100× density gap, P's
    zero Δ0, and Darkmont's ≥10% Δ0 share (~25× chance). The reviewer's own
    SDM-table framer found the same.
  - **The price of Cougar Cove's exactness:** its trace is **~220–380× larger**
    at the longest gap (~2.4–3.9×10⁵ bytes vs ~1×10³).
- **Fine PT timing** (dense MTC + CYC) is exact on all OVF-free rows of every
  class, including four P fine rows below one coarse period (318–710 TSC, §5).
- **So the PTW-fence advantages are specifically:**
  - (a) **accuracy where time-keyed fails**: on Darkmont through both failure
    regimes; on Cougar Cove only near or below one MTC period;
  - (b) it needs **no** timing packets, where time-keyed always does;
  - (c) it does not depend on how densely a given core class emits them, or on
    paying ~300× trace volume for that density.
- Ground truth is independent of the PT decode path: `verify_singlestep` TF-
  single-steps the same self-modifying target with **no** perf/PT and confirms
  the byte that executed at each step (EAX-at-`ret` == `EXEC_TAG+i`).

So the honest, surviving N2 claim (see ../../research/NOVELTY-LOG.md C03): an
*executed* `PTWRITE` fence gives exact, in-band, packet-ordered version
boundaries for same-address rewrites. Even a correctly implemented time-keyed
correlation (perf/libipt-sb/wilvk) has a bounded window of correctness:
- On **Darkmont**, whose BranchEn=0 trace carries few MTCs, the window is a band
  that fails at short intervals and at long gaps.
- On **Cougar Cove**, which emits an MTC every period, the window covers every
  tested interval from about one MTC period up, at ~300× the trace volume.

Three corrections are on record:
- **REVIEW-02-build B1:** an earlier version used a packet-*counting* MTC clock
  and wrongly reported time-keyed as failing at every coarse interval.
- **After clearance (REVIEW-02 nit d):** pinning each sweep showed that the
  long-gap failure is **Darkmont-specific**. The cleared runs were unpinned,
  and evidently ran their long-gap captures on Darkmont cores; a Cougar Cove
  capture is exact there.
- **REVIEW-02 round 3 (B3):** the first per-class text said time-keyed fails at
  short intervals on *every* class. In fact Cougar Cove is exact down to about
  one MTC period, an edge that only the dedicated short-delay probe (§5)
  reliably reaches.

## Why this is novel / what it is NOT

Version-correct decoding of rewritten code already exists **by timestamp**:
wilvk/asm-test (`PERF_RECORD_TEXT_POKE` timeline), perf `intel_pt_text_poke`,
libipt `sideband/` (image-over-time at mapping granularity), DRAKVUF (injects
PTW packets), and `avisi-group/icewind`. Per REVIEW-FINAL §2, as read by the
reviewer, icewind's brig DBT emits `PTWRITE(block_start_pc)` per translated
block for guest-PC tracing: in-band PTW annotation, the same class as DRAKVUF,
with no SMC version attribution and no time-keyed comparison. None uses an
*executed* PTWRITE as the in-band version fence, and
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

`run.sh` runs the whole sweep once per core class, pinned with `taskset -c`
(defaults: CPUs 0, 4, 12), and tags every CSV row with its CPU. `attribute.py`
also records each capture's MTC and TSC packet counts, the mechanism evidence.

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
- **The time-keyed failure regimes are real, not decoder bugs.**
  - Short interval: too few CTC ticks between the patch and the exec.
  - Long interval, Darkmont only: the 8-bit MTC payload (CTC[period+7:period])
    wraps between Darkmont's MTC packets, which at long gaps arrive about one
    per payload wrap (Δ0 steps dominate), so the high CTC bits are
    lost. A branch-tracing capture emits timing packets more often and would
    push that threshold out; measuring it is a v2.
- **The core-class difference is an observation on this part, in this
  configuration** (BranchEn=0, `mtc_period` 3). The mechanism is inferred from
  the packet counts, not from Intel documentation. Each class is represented by
  **one** CPU (0, 4, 12), not swept over all 16; `PT_CPUS="<cpu> …"` runs
  others.
- **Packet-level, not a full PT instruction decoder.** The framer handles the
  packet subset these traces contain and self-checks by consuming the whole
  buffer; it is not a general libipt replacement.
- The exact band *edges* jitter run to run, and measured intervals vary widely
  (P's especially). So whether a P row lands near P's lower edge (about one
  MTC tick, ≈768 TSC) is reported as INFO; the edge itself is characterized by
  the dedicated probe in RUN.md §5. These results are stable across 3/3 pinned
  `make` runs covering all three classes:
  - Darkmont's band, its shortest-interval failure, and its long-gap failure
    at the predicted edge;
  - Cougar Cove's exactness at every interval ≥ 2 MTC periods;
  - the mechanism (density, Δ0);
  - the fine-exact result and PTW-fenced exactness.
- **OVF handling:** a lossy trace (AUX overflow) is reported per row and
  excluded from time-keyed scoring; `make` passes regardless. The 8 MiB ring
  plus capping fine delays at 10⁴ keeps OVF at 0 in practice. **The cap loses no
  result** (REVIEW-02 nit b): before it existed, fine mode was also exact at
  delays 10⁵ and 10⁶ (24/0 at both; `review/evidence/build-02/payload-vs-count.txt`).
  The cap only removes the OVF risk.
- The comparison runs with **BranchEn=0** (PTW + timing only). An ordinary
  perf/libipt capture uses `branch=1`, where TSC/MTC emission is denser; the
  long-gap threshold is therefore specific to this low-rate configuration.
- x86-only, this-model-specific config constants (family 6 model 0xCC).
- **Safety:** benign — traces only this process's own user-mode code; no root,
  no network, no foreign process, no writes outside the directory. The ground-
  truth single-stepper uses the trap flag on its own code (educational).
