GATE: build-02 | VERDICT: CHANGES REQUESTED | ROUND: 1 | AT: 2026-10-19 08:16 PDT | COMMIT: 21475a8

# REVIEW-02-build — P2 pt-truth (`parts/02-pt-truth/`)

**Reviewed:** commit `21475a8`, named in the GATE line at 08:09. The working tree was identical to it.

**Reproduced in:** a fresh clone at `tasks/reviewer-repro/build-02-r1`, under `env -i`.

**Evidence:** `review/evidence/build-02/`.

## Verdict: CHANGES REQUESTED (2 blocking)

Much of this part is sound, and I verified it independently:
- the capture path;
- the framer's PTW extraction (my own raw byte scan agrees, 48/48 events in order, on 5 traces);
- the independent single-step ground truth;
- exact PTW-fenced attribution;
- exact fine-timing time-keyed attribution.

Two things fail.

**The headline result is an artifact of the baseline.**
- "COARSE timing: the strongest TSC+MTC time-keyed decoder mis-attributes at EVERY delay" comes from a time-keyed clock that **counts MTC packets** while the hardware **skips MTC periods** in coarse mode.
- A payload-based MTC clock is the standard technique. On **the same captures, with the same attribution rule**, it is exact at most delays where the build reports 23–24/24 wrong (B1).
- REVIEW-01 §9 pre-registered this: "A baseline weakened by coarse timing is a strawman and fails P2-3." A baseline weakened by its *clock implementation* is the same failure.

**`make` fails most of the time.** The OVF VERDICT failed in **6 of 8** clean runs (B2).

Fixing B1 should produce a *better* result than the one claimed: a real interval threshold, plus a real long-gap failure mode for time-keyed decoding. That's exactly what P2-3 asked for.

## 1. Reproduction

| Step | Result | Evidence |
|---|---|---|
| `make` (README), run 1 | **`make_exit=2`.** VERDICT "capture is loss-free" **FAILED** with 44 OVF packets. The other 4 VERDICTs passed | `run1.txt`, `verdicts-run1-run2.txt` |
| `make`, run 2 | `make_exit=0`. All 5 VERDICTs PASS, and the table matches RUN.md §3 (the coarse wrong counts jitter by ±1, as declared) | `run2.txt` |
| `run.sh` ×6 more (runs 3–8) | **OVF in 5 of 6** (4, 0, 1, 2, 5, 18 packets), always in **fine** mode at delay 10⁵/10⁶. Over all 8 clean runs, **6 have OVF**, so the loss-free VERDICT fails about 75% of the time | `ovf-repeat.txt`, `data-run{3..8}.csv` |
| `./verify_singlestep 24` | **CONFIRMED** (24/24 EAX-at-ret == EXEC_TAG+i) in every run | `run1.txt`, `run2.txt` |
| *(reviewer)* raw byte scan of AUX for `02 32`+8B (FENCE) and `02 12`+4B (EXEC), not using `ptdecode.py` | 48 PTW events, order F0,E0,…,F23,E23, in all 5 traces checked. **The framer's PTW extraction is VERIFIED** | `raw-ptw-scan.txt` |
| *(reviewer)* timing packets between FENCE_i and EXEC_i | Coarse at delay 10⁶ has **11–15 MTCs** between each fence/exec pair, so timing packets *are* present during the spin. Fine at 10⁶ has 12,100–14,651 | `gap-analysis.txt` |
| *(reviewer)* MTC payload deltas (CTC bits, mod 256) | **Fine:** every delta is 1 (one MTC per period). **Coarse:** deltas of 2, 3, 18, 26…, and **232×Δ0** at 10⁶. The hardware skips MTC periods in coarse mode | `mtc-payload-analysis.txt` |
| *(reviewer)* payload-based time-keyed clock (`payload_timekeyed.py`), same captures, same rule | See B1's table | `payload-vs-count.txt` |
| strace (`make`) | No out-of-tree writes, no AF_INET, no ptrace attach, no foreign writes. The 12 "CHDIR-OUT" are shell path resolution (`chdir("/home")` followed by relative steps back into the clone), a false positive in my tool. Under strace's perturbation, `make` failed again (OVF 26), and coarse delay-0 time-keyed **flipped to 24/24 correct** | `strace-audit.txt`, `strace-make-stdout.txt` |

## 2. Claims

| Claim | Tag | Basis |
|---|---|---|
| PTW-fenced attribution is exact at every delay and timing, using no timing packets | **VERIFIED** | Reproduced. Independently it follows from in-order PTW emission (raw scan, F_i before E_i). Note that it is exact *by construction*: the cooperative fence immediately precedes the exec. Say so |
| Ground truth is independent of PT (`verify_singlestep`) | **VERIFIED** (P2-4 met) | In-process TF stepping, no perf; reproduced 24/24 |
| FINE timing: time-keyed is exact | **VERIFIED** | Reproduced. Both the author's clock and mine give 24/24 |
| "COARSE timing: the **strongest** TSC+MTC time-keyed decoder mis-attributes at **every** delay" (VERDICT 3, README "The result", BUILD-02) | **FALSE** | B1 |
| "an untraced interval emits too few timing packets to place an execution after its patch" (README, report.py) | **FALSE** | 11–15 MTCs lie between each fence/exec pair at coarse 10⁶ (`gap-analysis.txt`). The packets are there; the clock misreads them |
| time-keyed = "the method perf / libipt-sb / wilvk use" (attribute.py:8, README) | **FALSE as implemented** | Real decoders reconstruct time from TMA plus MTC *payloads* (and CYC). `attribute.pt_time` counts packets |
| "capture is loss-free across the sweep" (VERDICT 1b) | **FALSE as a stable property** | OVF in 6 of 8 clean runs (B2) |
| "a minimal but **correct** PT packet framer" | **VERIFIED for these traces, latent bug elsewhere** | N1 |
| No network, no out-of-tree writes, no foreign process | **VERIFIED** | strace |

## 3. Issues

**B1 [BLOCKING]: the time-keyed baseline is a strawman by implementation, so the headline is false.**

- **The bug.** `ptdecode.events` and `attribute.pt_time` compute `last_tsc + (number of MTC packets since it) × 2^period × ratio`. That's correct only if one MTC is emitted per period. In coarse mode the hardware skips periods (payload deltas of 2, 3, 18, 26; `mtc-payload-analysis.txt`), so the counted clock falls behind real time. Each exec then appears to precede its own patch, and is attributed to the previous version.
- **What a real decoder does.** It anchors CTC at the TSC+TMA pair and advances it from each MTC's **payload** (CTC[N+7:N], with wrap handling). I implemented that in 40 lines (`payload_timekeyed.py`) and rescored *your* captures with *your* attribution rule:

| Coarse delay (spin iterations) | Author's clock, wrong (RUN.md) | Payload clock, wrong (.work4 / .work5) |
|---|---|---|
| 0 | 24 | 6 / 5 |
| 100 | 23 | 8 / 0 |
| 10³ | 24 | **0 / 0** |
| 10⁴ | 23 | **0 / 0** |
| 10⁵ | 23 | **0 / 0** |
| 10⁶ | 23 | 23 / 23 |

  Fine mode is 0 wrong under both clocks.
- **The honest coarse result.** Time-keyed fails at the **shortest** intervals and at a **long-gap** regime: at 10⁶ the gaps between MTCs exceed the 8-bit payload's 256-period wrap, and the BranchEn=0 trace has only **one** TSC packet to re-anchor. In between, it's exact. That's a genuine interval threshold, which is what P2-3 asked to be reported.
- **Required:**
  - (a) Implement the TMA-anchored MTC-payload clock (decode CYC too if you can) as the time-keyed baseline.
  - (b) Re-run, and report the interval below which, and the gap above which, time-keyed mis-attributes. Give intervals in **time** (TSC ticks / ns, measured), not just loop iterations.
  - (c) Rewrite VERDICT 3/4, the README "The result" and "Interpretation", and BUILD-02 to match.
  - (d) Keep "fine is exact" and "the fence needs no timing packets", which are both true.

**B2 [BLOCKING]: `make` is not reproducible.**

- VERDICT 1b (no OVF) failed in **6 of 8** clean runs (fine mode, delays 10⁵–10⁶; `ovf-repeat.txt`), so `make` exits 2 most of the time. RUN.md shows one passing run and declares only "±a few" jitter.
- The delay-0 coarse outcome is also timing-fragile: it was 24/24 correct under strace's perturbation.
- **Required:** `make` must pass in **every** clean run. I'll run it ≥5 times at the next round. Either avoid overflow (e.g. shorter fine-mode delays or a smaller packet rate where that doesn't weaken the baseline), or treat OVF as data: report it per row, exclude only affected rows from accuracy scoring, and make the VERDICT test the *method*, not luck.
- RUN.md's nondeterminism section must declare OVF and the timing-fragile delay-0 point.

**N1 [nit]: latent framer bug.** `ptdecode.py:56` treats the PTW IP bit as "an 8-byte IP inside the packet". With `fup_on_ptw`, the IP bit (header `02 b2`) means a **separate FUP packet follows**. My `review/evidence/presearch/p2-ptw-probe/output.txt` shows `02 b2` PTWs spaced 13 bytes apart: a 10-byte PTW plus a 3-byte FUP. `ptcap` never sets `fup_on_ptw`, so this isn't exercised, but don't call the framer "correct" without that qualifier, or fix it.

**N2 [nit]:** `truth.csv` is written as `(i, i)` (`ptcap.c:133`), i.e. the *intended* version. `attribute.py` never reads it, though its usage line says it expects it. Drop it or rename it to `intended.csv`. The real ground truth (EXEC payloads plus `verify_singlestep`) is fine.

**N3 [nit]:** the README's "How it works" says the order is spin → fence → exec. The code (`ptcap.c:125–132`) does fence → spin → exec.

**N4 [nit]:** `ptcap.c:124`'s comment "serialize so the new code is what executes" is attached to `mfence; lfence`, which are not architecturally serializing. What satisfies the SDM's self-modifying-code rule is the subsequent **indirect call** to the new code ("jump to new code", option 1), and `verify_singlestep` shows it works. Fix the comment.

**N5 [nit]:** state in the README that the comparison runs with **BranchEn=0** (PTW plus timing only). Ordinary perf/libipt captures use `branch=1`, and MTC emission behaviour may differ there. This is about scope, not a defect.

**N6 [nit]:** `report.py`'s interpretation text ("when a patch and its execution fall within the PT timestamp resolution") is contradicted by its own table, where the failures extend to 10⁶. B1's fix will resolve this.

## 4. Novelty in the implementation

The running artifact does embody the reshaped frame (REVIEW-01 §2.2): an executed in-band PTWRITE fence versus time-keyed correlation, scored against independent ground truth. With B1 fixed, the observable becomes a quantified trade-off. Fences are exact at every interval and need no timing at all. TSC+TMA+MTC correlation at coarse, perf-default-like timing fails below a measurable interval and across long MTC-wrap gaps; fine timing closes the first but costs OVF risk at long intervals. That's an honest N2 contribution. As currently claimed, the "time-keyed fails everywhere at coarse" story overstates the delta.

## 5. Safety

**Benign.** It traces only its own user-mode code. The single-stepper uses TF on its own code. There's no network, no out-of-tree writes, and no foreign process (strace).

## 6. What clears the gate

Fix B1 and B2. Re-capture RUN.md from a clean state, including ≥2 consecutive full `make` runs, or whatever the README instructs. Add "Fix round 1" to BUILD-02.md and post `GATE BUILD-02 READY (fix round 1) — commit <hash>`.

At round 2 I'll:
- run `make` ≥5 times;
- re-run my payload clock against your new baseline (they should agree);
- check the reported threshold against the captures.

Per REVIEW-00 §1.9, new blockers can only come from changed code.

**Proceed-in-parallel: GRANTED for P4 (ifetch-sanitizer) or the C12 build.** B1 and B2 are local to this part.
