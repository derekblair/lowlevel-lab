GATE: build-02 | VERDICT: CHANGES REQUESTED | ROUND: 3 | AT: 2026-10-19 10:26 PDT | COMMIT: 71bb650 (round 1: CHANGES REQUESTED @21475a8; round 2: APPROVE @cc7e74d, re-opened by the author 10:20)

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

---

## Round 2: fix round 1 @ `cc7e74d`, APPROVE (2026-10-19 08:27 PDT)

I reviewed `cc7e74d` (GATE line 08:24; the working tree is identical). It was reproduced in a fresh clone, `tasks/reviewer-repro/build-02-r2`. Evidence is in `review/evidence/build-02/r2/`.

### Blockers

**B1 — FIXED.** `attribute.py` now uses a TSC+TMA-anchored, MTC-payload clock with 8-bit wrap handling: the documented algorithm, credited to my `payload_timekeyed.py`. `ptcap` logs both the patch and the exec `rdtsc`, so intervals are **measured in TSC ticks**.

My re-implementation agrees with `attribute.py` on **60/60** captures (`r2/clock-agreement.txt`). That shows there's no implementation slip. It isn't algorithmic independence, but the algorithm itself is the documented one.

The honest result reproduces across **6 clean runs** (`r2/make-6runs-summary.txt`, `r2/data-run{1..6}.csv`):
- coarse time-keyed attribution is **exact for intervals ~1.6×10³ to ~1.4×10⁵ TSC ticks**;
- it **fails at ≥2.85×10⁵** (run 6's delay-10⁵ spin happened to take 285,136 ticks and failed, as did every 10⁶ row, 1.15–2.87×10⁶ ticks);
- it **partially fails at the shortest intervals** (~340–1,400 ticks: 3–20 of 24 wrong).

The upper edge matches the mechanism the README gives. TSC/CTC = 192/2 = **96**, so the 8-bit coarse MTC payload wraps every 2,048 CTC = **196,608 TSC ticks**, which falls between the last exact interval (1.42×10⁵) and the first failing one (2.85×10⁵). The lower edge sits at about one MTC period, **768 TSC**, as the README notes.

Fine mode is exact on every row. PTW-fenced attribution is exact on every row (60/60 rows across 6 runs, 0 wrong, 0 missing fence).

**B2 — FIXED.** **6/6** consecutive clean `make` runs: `make_exit=0`, 7/7 VERDICTs PASS, 0 OVF rows. It **also passes under strace's perturbation**, which round 1 failed. RUN.md declares OVF and the jittery band edges.

### Nits

N1–N6 are all done:
- N1: the framer now treats the IP bit as "a separate FUP follows";
- N2: `truth.csv` is dropped;
- N3: the order is now stated as patch→fence→spin→exec;
- N4: the comment is corrected and `mfence/lfence` removed;
- N5: the BranchEn=0 scope is stated;
- N6: the interpretation text is rewritten.

**strace: CLEAN** (`r2/strace-audit.txt`, auditor v2).

**New nits, none blocking:**
- (a) `report.py`: two `check(…, True, …)` calls ("OVF rows excluded", "reported window") can't fail, so make them `INFO` lines. VERDICT 3 is named "middle band" but gates only "≥1 exact row". The lower edge is INFO by design, which is fine, so rename it to "exact over an interval band".
- (b) README, fine cap: "nothing is lost" should cite the evidence. In the round-1 captures, fine mode was exact at 10⁵ and 10⁶ too (`review/evidence/build-02/payload-vs-count.txt`); the cap only removes OVF risk.
- (c) README: state the predicted upper edge, 2^(mtc_period+8) CTC × TSC/CTC = 196,608 TSC ticks. That turns the band into a falsifiable prediction, and the data brackets it.
- (d) `ptcap` isn't pinned to a CPU. Band edges in *delay* units move with core speed (run 6), and MTC-skipping behaviour could differ by core class (R14). Pin it, or record the CPU per capture.

### Why APPROVE

The part now does what P2-3 asked for. It runs an exact in-band executed-PTWRITE fence head-to-head against the **strongest** time-keyed baseline the trace supports, scored against independent ground truth, and it reports a **real, mechanism-explained interval band** where time-keyed decoding fails below and above. It reproduces cleanly six times, and the safety audit is clean. It's an honest N2 contribution, and the corrected result is more interesting than the original claim.

**Gate BUILD-02 is CLEARED.**

---

## Round 3: post-clearance correction @ `71bb650`, CHANGES REQUESTED (2026-10-19 10:26 PDT)

**Context.** Applying my round-2 nit (d), which asked for the captures to be pinned, changed a cleared claim, and **the author re-opened the gate themselves** instead of folding the change in silently. That's the right call.

**Reproduced in:** a fresh clone at `tasks/reviewer-repro/build-02-r3`, under `env -i`.

**Evidence:** `review/evidence/build-02/r3/`.

### Reproduction

| Test | Result | Evidence |
|---|---|---|
| `make` ×3 (clean clone) | `make_exit=0`, **10/10 PASS** every run, 1–2 s each. Every sweep is pinned to CPU 0 (P), 4 (E) and 12 (LP-E) | `make-run{1,2,3}.txt`, `data-run{1,2,3}.csv` |
| `make` under strace | **10/10 PASS**. Audit **CLEAN**: the only hits are failed `connect`s to nscd (name lookup), info only. The `mktemp` workdir is removed (31 `unlinkat(AT_REMOVEDIR)`) | `strace-audit.txt`, `make-strace-stdout.txt` |
| extra pinned sweep, captures kept (`WORK`, delays 10⁵/10⁶ plus fine 10⁴) | same pattern | `keep-data.csv`, `keep-trace-hashes.txt` |

### Independent mechanism check

`ptframe.py` is my own minimal PT framer, written from the SDM packet tables; it doesn't use `ptdecode`. Every byte of every kept trace frames, and each trace is "framed complete". Results from `ptframe-per-class.txt`:

| Capture (coarse, mtc_period 3) | Trace bytes | MTC | TSC | MTC payload deltas (mod 256) |
|---|---|---|---|---|
| **P** (CPU 0), delay 10⁶ | **522,192** | **251,410** | 256 | **Δ1 ×251,404**, Δ2 ×4, Δ114 ×1 |
| **E** (CPU 4), delay 10⁶ | **1,100** | 319 | **1** | **Δ0 ×245**, then Δ3/Δ2/Δ4… |
| **LP-E** (CPU 12), delay 10⁶ | **960** | 248 | **1** | **Δ0 ×174**, … |
| P, delay 10⁵ | 72,208 | 34,488 | 36 | all Δ1 |
| E / LP-E, delay 10⁵ | 616 / 600 | 77 / 69 | 1 / 1 | mixed |

**VERIFIED, and sharper than "sporadic".**
- Cougar Cove emits one MTC per period.
- At long gaps, Darkmont's MTCs mostly arrive **exactly one 8-bit payload wrap apart** (Δ0). So each MTC repeats the previous payload, and the payload clock cannot see the 256-period wraps that elapsed. That is precisely the failure mechanism.

### Claims

| Claim (`71bb650`) | Tag | Basis |
|---|---|---|
| PTW-fenced exact on every row of every class | **VERIFIED** | 0 wrong, 0 missing fence, in all my runs and the extra sweep |
| Darkmont long-gap failure, with onset near the predicted 196,608 TSC | **VERIFIED** | LP-E is exact at 161,002–176,324 and fails at **205,796** (extra sweep) and 1.6–1.8×10⁶. E fails at **217,982–248,146** in every run. The bracket holds |
| Cougar Cove has no long-gap failure, out to ~10⁷ TSC | **VERIFIED** | Exact at 4.8–10.2×10⁶ TSC in all 4 of my sweeps |
| MTC density gap ≥100× | **VERIFIED independently** | Table above |
| "Below the band it mis-attributes **on every class**" (README:32–33); "it fails below that window **everywhere**" (README:66–68); BUILD-02 "Unchanged: time-keyed fails at short intervals everywhere" | **FALSE** | **P is exact on every short-interval row in 6/6 runs**: the author's three RUN.md runs, where the report's own INFO line reads "P: coarse time-keyed at short intervals (<band): all resolved this run", plus my three. P's shortest tested interval (848–2,188 TSC) is **above one MTC period (768 TSC)**, so this sweep never reaches a P lower edge at all |
| "Even a correctly implemented time-keyed correlation has a bounded window of correctness" (README:65–66), and fence advantage (a) "through both failure regimes" | **Darkmont only** | On P no failure was observed anywhere in the tested range (848 TSC to 1.0×10⁷ TSC) |

### Issues

**B3 [BLOCKING] (changed text): the per-class result over-generalizes the short-interval failure.**

The data say this, per class:

| Class | Short intervals | Long gaps | Fence advantage |
|---|---|---|---|
| Darkmont (E, LP-E) | fails | fails | accuracy, plus (b) and (c) |
| Cougar Cove (P) | exact at every tested interval | exact | **not** accuracy; (b) no timing packets and (c) no dependence on emission density |

The Cougar Cove exactness has a measured price: **~475× the trace volume** at the longest gap (522 KB vs 1.1 KB). That is the cost of MTC-every-period.

**Required:**
- Correct README:32–33 and 65–68, the "So the PTW-fence advantages" list, BUILD-02's "Unchanged" line, and `report.py`'s Interpretation text to say this.
- Rename P's VERDICT from "exact over an interval band" to "exact at every tested interval".
- If you want to claim a P lower edge, extend the P sweep below one MTC period. Otherwise, say it wasn't reached.
- Re-capture RUN.md.

This is text and report-only, and none of the measurements change.

**N7 [nit]:** describe Darkmont's long-gap MTCs as "about one per payload wrap: Δ0 deltas dominate (`ptframe` evidence)" rather than "sporadic". It explains the failure directly.

**N8 [nit]:** for E, the 2× onset VERDICT is satisfied by the failure side only: the largest exact interval, 25,324, is 7.8× below the edge. LP-E supplies the tight bracket. Say so in the VERDICT detail.

### Novelty in the implementation

The per-class correction makes the part *more* interesting. Hybrid Panther Lake cores differ in MTC emission under BranchEn=0, and that decides whether time-keyed SMC version attribution survives long gaps. As a hardware observation it's real and verified at the packet level. The N2 delta (the in-band executed fence) stands, but only once it's stated per class as above.

### What clears the gate

Fix B3 (text and report only), re-capture RUN.md, and post `GATE BUILD-02 READY (post-clearance correction, round 2) — commit <hash>`. I'll diff the text against `data-run*.csv` and re-run `make` ×3.
