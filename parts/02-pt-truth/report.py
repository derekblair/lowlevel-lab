#!/usr/bin/env python3
"""report.py — aggregate the pt-truth sweep CSV into the head-to-head verdict.

Grep 'VERDICT'. Exit 0 iff all pass. Python stdlib only.

Headline (REVIEW-01-build P2-3; corrected per REVIEW-02-build B1; stated PER
CORE CLASS after pinning, REVIEW-02 round 2 nit d / round 3 B3 / R14):

* An in-band executed-PTWRITE fence attributes self-modified-code execution to
  its exact version at every tested interval, on every core class, needing no
  timing packets.
* The strong time-keyed baseline (TMA-anchored MTC-payload clock) depends on
  the core class.
  - Darkmont (E, LP-E): exact only over an interval band. It fails at short
    intervals, and at long gaps once they pass the predicted 2^(mtc_period+8)
    CTC payload-wrap edge. Under BranchEn=0, Darkmont's MTCs arrive about one
    per payload wrap (delta 0 mod 256 dominates), so the clock cannot see the
    wraps that elapsed.
  - Cougar Cove (P): the trace carries an MTC every period, so the clock
    resolves one period and P's lower edge sits at about one MTC period (768
    TSC here; RUN.md §5). It is exact at every tested interval >= 2 periods,
    including every long gap. The price is ~10^2-10^3x the trace volume.
* So the fence's accuracy advantage is on Darkmont (short and long gaps), and on
  P only near or below one MTC period. On every class it has (b) no timing
  packets and (c) no dependence on how densely a core emits them.

Intervals are in TSC ticks. OVF rows are reported and EXCLUDED from time-keyed
accuracy scoring (a lossy trace is not a method result).
"""
import sys

CLASSES = [("P", "Cougar Cove", range(0, 4)), ("E", "Darkmont", range(4, 12)),
           ("LP-E", "Darkmont", range(12, 16))]


def cls_of(cpu):
    for short, _arch, r in CLASSES:
        if cpu in r:
            return short
    return f"cpu{cpu}"


def load(f):
    """Rows of the sweep CSV, plus the coarse captures' clock parameters from
    the '# sideband coarse:' comment line (CPUID.15H ratio, mtc_period)."""
    rows, meta = [], {}
    for line in f:
        line = line.strip()
        if line.startswith("# sideband coarse:"):
            for tok in line.split(":", 1)[1].split():
                k, _, val = tok.partition("=")
                if val.isdigit():
                    meta[k] = int(val)
            continue
        if not line or line.startswith("#"):
            continue
        c = line.split(",")
        rows.append({
            "timing": c[0], "delay": int(c[1]), "execs": int(c[2]),
            "interval": int(c[3]),
            "fok": int(c[4]), "fwrong": int(c[5]), "fnofence": int(c[6]),
            "tkok": int(c[7]), "tkwrong": int(c[8]),
            "ovf": int(c[9]) if len(c) > 9 else 0,
            "mtc": int(c[10]) if len(c) > 10 else -1,
            "tsc": int(c[11]) if len(c) > 11 else -1,
            "d0": int(c[12]) if len(c) > 14 else -1,
            "bytes": int(c[13]) if len(c) > 14 else -1,
            "cls": cls_of(int(c[-1])) if len(c) > 12 else "unpinned",
        })
    return rows, meta


def main():
    rows, meta = load(open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin)
    if not rows:
        print("no data"); return 1

    print("=" * 96)
    print("pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed")
    print("(time-keyed = TMA-anchored MTC-payload TSC clock; intervals in TSC ticks;")
    print(" each sweep pinned to one CPU: P = Cougar Cove, E / LP-E = Darkmont)")
    print("=" * 96)
    hdr = (f"{'class':5} {'timing':7} {'delay':>8} {'interval(TSC)':>13} {'ovf':>4} "
           f"{'MTC':>7} {'MTCd0':>6} {'TSC':>5} {'bytes':>8} | {'fenced ok/wrong':>15} | "
           f"{'time-keyed ok/wrong':>19}")
    print(hdr); print("-" * len(hdr))
    for r in rows:
        print(f"{r['cls']:5} {r['timing']:7} {r['delay']:>8} {r['interval']:>13} {r['ovf']:>4} "
              f"{r['mtc']:>7} {r['d0']:>6} {r['tsc']:>5} {r['bytes']:>8} | "
              f"{r['fok']:>8}/{r['fwrong']:<6} | {r['tkok']:>10}/{r['tkwrong']:<8}")

    clean = [r for r in rows if r["ovf"] == 0]
    ovf_rows = [r for r in rows if r["ovf"] > 0]
    classes = [c for c, _, _ in CLASSES if any(r["cls"] == c for r in rows)]
    pred = period = None
    if all(k in meta for k in ("mtc_period", "cpuid15_ebx_numer", "cpuid15_eax_denom")):
        ratio = meta["cpuid15_ebx_numer"] / meta["cpuid15_eax_denom"]
        pred = int(2 ** (meta["mtc_period"] + 8) * ratio)       # one 8-bit payload wrap
        period = int(2 ** meta["mtc_period"] * ratio)           # one MTC period

    print("\n" + "=" * 96)
    print("VERDICTS")
    print("=" * 96)
    allpass = True

    def check(name, cond, detail=""):
        nonlocal allpass
        allpass = allpass and cond
        print(f"VERDICT {'PASS' if cond else 'FAIL'}: {name}" + (f"  [{detail}]" if detail else ""))

    # 1. PTW-fenced is exact on EVERY row of EVERY class (exact by construction:
    #    the cooperative fence immediately precedes the exec in packet order).
    fwrong = sum(r["fwrong"] for r in rows)
    fnofence = sum(r["fnofence"] for r in rows)
    check("PTW-fenced attribution is exact on every row of every core class, needs no timing packets",
          fwrong == 0 and fnofence == 0 and len(classes) >= 1,
          f"fenced wrong total = {fwrong}; no-preceding-fence = {fnofence} over {len(rows)} rows, "
          f"classes {classes}")
    print(f"INFO: OVF rows excluded from time-keyed scoring (lossy trace != method result): "
          f"{len(ovf_rows)} of {len(rows)}: "
          f"{[(r['cls'], r['timing'], r['delay'], r['ovf']) for r in ovf_rows] or 'none'}")
    if pred:
        print(f"INFO: one MTC period = 2^{meta['mtc_period']} CTC x TSC/CTC = {period} TSC; "
              f"one 8-bit payload wrap (predicted long-gap edge) = 2^({meta['mtc_period']}+8) CTC x "
              f"{meta['cpuid15_ebx_numer']}/{meta['cpuid15_eax_denom']} = {pred} TSC")

    # 2. Per class: the coarse time-keyed result.
    longest = {}
    for c in classes:
        coarse = sorted([r for r in clean if r["cls"] == c and r["timing"] == "coarse"],
                        key=lambda r: r["interval"])
        longest[c] = coarse[-1] if coarse else None
        exact = [r for r in coarse if r["tkwrong"] == 0]
        wrong = [r for r in coarse if r["tkwrong"] > 0]
        hi = max((e["interval"] for e in exact), default=None)
        long_fail = [r for r in wrong if hi is not None and r["interval"] > hi]
        if c == "P":
            # Cougar Cove: an MTC every period, so the clock resolves ONE period and
            # P's lower edge sits at about one MTC period. `interval` is the median
            # of 24 per-exec intervals, so a row whose median is just above one
            # period still holds execs inside it (RUN.md §5 probe). Rows with a
            # median >= 2 periods are clear of that edge and must be exact.
            clear = 2 * period if period else None
            above = [r for r in coarse if clear and r["interval"] >= clear]
            near = [r for r in coarse if clear and r["interval"] < clear]
            check("P: coarse time-keyed is exact at EVERY tested interval >= 2 MTC periods "
                  "(clear of its one-period resolution edge), incl. every long gap",
                  bool(above) and all(r["tkwrong"] == 0 for r in above),
                  f"{sum(1 for r in above if r['tkwrong'] == 0)}/{len(above)} rows exact, "
                  f"intervals {above[0]['interval'] if above else None}.."
                  f"{above[-1]['interval'] if above else None} TSC (one MTC period = {period})")
            print(f"INFO: P below 2 MTC periods (around its lower edge, ~1 period): "
                  f"{[(r['interval'], r['tkwrong']) for r in near] or 'not reached this run'}")
            far = longest[c]
            check("P: NO long-gap mis-attribution: exact at the longest interval, >= 10x the "
                  "predicted wrap edge (an MTC every period, so the payload never wraps unseen)",
                  pred is not None and far is not None and far["tkwrong"] == 0
                  and far["interval"] >= 10 * pred,
                  f"longest coarse interval {far['interval'] if far else None} TSC "
                  f"(= {far['interval'] / pred:.0f}x the edge {pred}): time-keyed wrong="
                  f"{far['tkwrong'] if far else None}")
        else:
            # Darkmont: exact over a band; fails at the shortest interval and at long gaps.
            check(f"{c}: coarse time-keyed is exact over an interval band",
                  len(exact) >= 1, f"exact at intervals(TSC) = {[e['interval'] for e in exact]}")
            shortest = coarse[0] if coarse else None
            check(f"{c}: coarse time-keyed MIS-attributes at the shortest tested interval",
                  shortest is not None and shortest["tkwrong"] > 0,
                  f"shortest interval {shortest['interval'] if shortest else None} TSC: "
                  f"wrong {shortest['tkwrong'] if shortest else None}/"
                  f"{shortest['execs'] if shortest else None}; all short failures (<band): "
                  f"{[(r['interval'], r['tkwrong']) for r in wrong if hi is not None and r['interval'] < min(e['interval'] for e in exact)]}")
            onset = min((r["interval"] for r in long_fail), default=None)
            ok = (pred is not None and onset is not None and hi is not None
                  and hi <= 2 * pred and onset >= pred / 2)
            tight = ("failure side" if onset and onset < 2 * pred else "") + \
                    (" and " if onset and onset < 2 * pred and hi and hi > pred / 2 else "") + \
                    ("exact side" if hi and hi > pred / 2 else "")
            check(f"{c}: coarse time-keyed MIS-attributes at long gaps, onset at the predicted "
                  f"MTC-payload wrap (within 2x)",
                  ok,
                  f"largest exact {hi} (= {pred / hi:.1f}x below the edge) <= 2x{pred}; smallest "
                  f"long-gap failure {onset} (= {onset / pred:.2f}x the edge) >= {pred}/2; within "
                  f"2x of the edge on: {tight or 'neither side'}" if ok else
                  f"largest exact {hi}; smallest long-gap failure {onset}; edge {pred}")

    # 3. The mechanism, from the packets, at the longest gap: density, payload
    #    wraps, and the price of density.
    if "P" in longest and longest["P"]:
        P = longest["P"]
        dm = [longest[c] for c in classes if c != "P" and longest[c]]
        d0frac = {r["cls"]: r["d0"] / max(1, r["mtc"] - 1) for r in dm}
        # A random 8-bit payload delta is 0 with probability 1/256; a delta-0 share
        # >= 10% (~25x chance) means MTCs arrive whole payload wraps apart, which
        # the payload clock cannot see. Cougar Cove, with an MTC every period,
        # must have none.
        check("mechanism: at the longest gap Cougar Cove carries >= 100x Darkmont's MTCs with "
              "no delta-0 payload steps, while >= 10% of Darkmont's MTC steps are a whole "
              "payload wrap (delta 0 mod 256, ~25x the 1/256 chance level)",
              bool(dm) and all(P["mtc"] >= 100 * max(1, r["mtc"]) for r in dm)
              and P["d0"] == 0 and all(f >= 0.10 for f in d0frac.values()),
              f"MTC per capture: P {P['mtc']}; " + "; ".join(f"{r['cls']} {r['mtc']}" for r in dm)
              + "; delta-0 share: " + "; ".join(f"{k} {v:.0%}" for k, v in d0frac.items())
              + f"; P delta-0 {P['d0']} of {P['mtc'] - 1}")
        print(f"INFO: the price of Cougar Cove's exactness at the longest gap: trace volume "
              f"P {P['bytes']} B vs " + ", ".join(f"{r['cls']} {r['bytes']} B "
              f"({P['bytes'] / max(1, r['bytes']):.0f}x)" for r in dm))

    # 4. Fine timing (dense MTC+CYC): time-keyed exact on OVF-free rows, every class.
    fine = [r for r in clean if r["timing"] == "fine"]
    check("FINE timing: time-keyed is exact on all OVF-free rows of every class "
          "(dense timing closes Darkmont's short-interval gap; P had none)",
          all(r["tkwrong"] == 0 for r in fine) and len(fine) >= 1,
          f"fine time-keyed wrong = {[(r['cls'], r['tkwrong']) for r in fine]}")

    # 5. Head-to-head contrast: wherever time-keyed is wrong, PTW-fenced is right.
    check("wherever time-keyed mis-attributes, PTW-fenced is exact",
          all(r["fwrong"] == 0 for r in rows if r["tkwrong"] > 0),
          f"rows with time-keyed wrong: {sum(1 for r in rows if r['tkwrong'] > 0)}; "
          f"of those, fenced wrong: {sum(1 for r in rows if r['tkwrong'] > 0 and r['fwrong'] > 0)}")

    print("\nInterpretation, per core class:")
    print("* PTW-fenced: an executed in-band PTWRITE fence pins each traced execution to")
    print("  its exact self-modified version in packet order, with no timestamps, on every")
    print("  core class and at every tested interval.")
    print("* Darkmont (E, LP-E): with BranchEn=0, the trace carries few MTCs, and at long")
    print("  gaps they arrive about one per 8-bit payload wrap (delta 0 dominates). So the")
    print("  payload clock fails at short intervals (too coarse to place the exec after")
    print("  its patch) and at long gaps from the predicted 2^(mtc_period+8) CTC edge (the")
    print("  wraps it cannot see). Dense (fine) timing closes the short-interval gap.")
    print("* Cougar Cove (P): the trace carries an MTC every period, so time-keyed resolves")
    print("  one MTC period: its lower edge sits at about one period. It is exact at every")
    print("  tested interval >= 2 periods, including every long gap, at the price of a much")
    print("  larger trace.")
    print("* So the fence buys accuracy on Darkmont at short and long gaps, and on P only")
    print("  near or below one MTC period. On every class it needs no timing packets and")
    print("  does not depend on how densely the core emits them.")
    print("Ground truth is the EXEC payload the executed bytes produced, confirmed")
    print("independently of PT by verify_singlestep.")
    print("\n" + ("ALL VERDICTS PASS" if allpass else "SOME VERDICTS FAILED"))
    return 0 if allpass else 1


if __name__ == "__main__":
    sys.exit(main())
