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

## The result (RUN.md §3, grep `VERDICT`)

- **PTW-fenced attribution is exact at every delay and timing mode** (24/24,
  0 wrong, 0 dropped) and uses no timing packets.
- **At COARSE PT timing** (TSC + sparse MTC, no CYC) the strongest TSC+MTC
  time-keyed decoder **mis-attributes at every patch→execute interval tested**
  (≈23–24 of 24 wrong): an untraced interval emits too few timing packets to
  place an execution after its patch, so the newest timestamp it has is stale.
- **At FINE PT timing** (dense MTC + CYC) the time-keyed decoder **is exact.**
  We say so plainly: the PTW-fence win is specifically (a) at coarse timing and
  (b) that the fence needs **no** timing packets at all, where time-keyed always
  does.
- Ground truth is independent of the PT decode path: `verify_singlestep` TF-
  single-steps the same self-modifying target with **no** perf/PT and confirms
  the byte that executed at each step (EAX-at-`ret` == `EXEC_TAG+i`).

So the honest, surviving N2 claim (see ../../research/NOVELTY-LOG.md C03): an
*executed* `PTWRITE` fence gives exact, in-band, control-flow-ordered version
boundaries for same-address rewrites, where time-keyed correlation (perf/
libipt-sb/wilvk) depends on PT timing resolution and fails when it is coarse.

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
off** so the tunable spin can't flood the AUX ring). Per version *i* it logs the
patch `rdtsc`, patches the mutable region to `mov eax, EXEC_TAG+i ; ptwrite eax ;
ret`, optionally spins `DELAY` cycles, emits the in-band `PTWRITE(FENCE_TAG+i)`,
then executes the region — which emits `PTWRITE(EXEC_TAG+i)`; that payload was
produced by the self-modified bytes, so it is ground truth. `ptdecode.py` is a
minimal but **correct** PT packet framer (self-checked: it must consume the whole
buffer and recover every PTW); it extracts PTW payloads + TSC/MTC in order. It
does **not** reconstruct control flow — the attribution needs only the packet
stream, which keeps the decoder tractable in pure stdlib. `attribute.py` runs
both decoders; MTC is converted to the TSC domain with the CPUID.15H ratio that
`ptcap` records, giving the time-keyed decoder its strongest form.

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
  `02 12` for 4-byte.

## Limits / honesty

- **CYC is enabled in fine mode but not decoded** by the framer (variable-length
  cycle packets). So fine time-keyed accuracy here is a **lower bound** — a
  CYC-using decoder would do at least as well. This only *understates* the
  time-keyed decoder, never the PTW advantage, and fine time-keyed already comes
  out exact, so nothing rests on the gap.
- The "TSC+MTCres" column counts distinct `(tsc, mtc)` tuples; at coarse timing
  these can be distinct yet **stale** (an untraced spin emits few MTCs), which is
  exactly why time-keyed fails there despite "distinct" timestamps.
- **Packet-level, not a full PT instruction decoder.** The framer handles the
  packet subset these traces contain and self-checks by consuming the whole
  buffer; it is not a general libipt replacement.
- Per-delay coarse time-keyed wrong counts jitter by a few (scheduling/timing);
  the coarse-fails / fine-exact split and the fenced-exact result are stable.
- x86-only, this-model-specific config constants (family 6 model 0xCC).
- **Safety:** benign — traces only this process's own user-mode code; no root,
  no network, no foreign process, no writes outside the directory. The ground-
  truth single-stepper uses the trap flag on its own code (educational).
