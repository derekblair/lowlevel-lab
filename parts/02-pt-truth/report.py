#!/usr/bin/env python3
"""report.py — aggregate the pt-truth sweep CSV into the head-to-head verdict.

Grep 'VERDICT'. Exit 0 iff all pass. Python stdlib only.

Headline (REVIEW-01-build P2-3; corrected per REVIEW-02-build B1; split by core
class after pinning, REVIEW-02 round 2 nit d / R14): an in-band executed-PTWRITE
fence attributes self-modified-code execution to its exact version across the
whole patch->execute interval range, on every core class, needing no timing
packets. The strong time-keyed baseline (TMA-anchored MTC-payload clock) is
exact only over an interval band. At LONG intervals it mis-attributes on
Darkmont (E, LP-E): with BranchEn=0 the trace there carries only sporadic MTC
packets, so the 8-bit payload wraps unobserved, and the failure onset agrees
with the predicted 2^(mtc_period+8) CTC edge. It does NOT mis-attribute on
Cougar Cove (P), which emits an MTC packet every period. Intervals are in TSC
ticks.

OVF rows are reported and EXCLUDED from time-keyed accuracy scoring (a lossy
trace is not a method result); PTW-fenced exactness holds regardless.
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
            "cls": cls_of(int(c[12])) if len(c) > 12 else "unpinned",
        })
    return rows, meta


def main():
    rows, meta = load(open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin)
    if not rows:
        print("no data"); return 1

    print("=" * 86)
    print("pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed")
    print("(time-keyed = TMA-anchored MTC-payload TSC clock; intervals in TSC ticks;")
    print(" each sweep pinned to one CPU: P = Cougar Cove, E / LP-E = Darkmont)")
    print("=" * 86)
    hdr = (f"{'class':5} {'timing':7} {'delay':>8} {'interval(TSC)':>13} {'ovf':>4} "
           f"{'MTC':>7} {'TSC':>5} | {'fenced ok/wrong':>15} | {'time-keyed ok/wrong':>19}")
    print(hdr); print("-" * len(hdr))
    for r in rows:
        print(f"{r['cls']:5} {r['timing']:7} {r['delay']:>8} {r['interval']:>13} {r['ovf']:>4} "
              f"{r['mtc']:>7} {r['tsc']:>5} | {r['fok']:>8}/{r['fwrong']:<6} | "
              f"{r['tkok']:>10}/{r['tkwrong']:<8}")

    clean = [r for r in rows if r["ovf"] == 0]
    ovf_rows = [r for r in rows if r["ovf"] > 0]
    classes = [c for c, _, _ in CLASSES if any(r["cls"] == c for r in rows)]
    pred = None
    if all(k in meta for k in ("mtc_period", "cpuid15_ebx_numer", "cpuid15_eax_denom")):
        pred = (2 ** (meta["mtc_period"] + 8) * meta["cpuid15_ebx_numer"]
                // meta["cpuid15_eax_denom"])

    print("\n" + "=" * 86)
    print("VERDICTS")
    print("=" * 86)
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
        print(f"INFO: predicted MTC-payload wrap edge = 2^(mtc_period+8) CTC x TSC/CTC = "
              f"2^({meta['mtc_period']}+8) x {meta['cpuid15_ebx_numer']}/"
              f"{meta['cpuid15_eax_denom']} = {pred} TSC ticks")

    # 2. Per class: the coarse time-keyed band, and what happens at long gaps.
    longest = {}
    for c in classes:
        coarse = sorted([r for r in clean if r["cls"] == c and r["timing"] == "coarse"],
                        key=lambda r: r["interval"])
        exact = [r for r in coarse if r["tkwrong"] == 0]
        wrong = [r for r in coarse if r["tkwrong"] > 0]
        lo = min((e["interval"] for e in exact), default=None)
        hi = max((e["interval"] for e in exact), default=None)
        short_fail = [r for r in wrong if lo is not None and r["interval"] < lo]
        long_fail = [r for r in wrong if hi is not None and r["interval"] > hi]
        longest[c] = coarse[-1] if coarse else None
        check(f"{c}: coarse time-keyed is exact over an interval band",
              len(exact) >= 1, f"exact at intervals(TSC) = {[e['interval'] for e in exact]}")
        # Short-interval behaviour is reported, not gated: the band's lower edge
        # sits near one MTC tick (~768 TSC), so it jitters run to run.
        print(f"INFO: {c}: coarse time-keyed at short intervals (<band): "
              f"{[(r['interval'], r['tkwrong']) for r in short_fail] or 'all resolved this run'}")
        if c == "P":
            # Cougar Cove: no long-gap failure, far past the predicted edge.
            far = longest[c]
            check("P: NO long-gap mis-attribution: exact at the longest interval, >= 10x the "
                  "predicted wrap edge (MTC every period, so the payload never wraps unseen)",
                  pred is not None and far is not None and far["tkwrong"] == 0
                  and far["interval"] >= 10 * pred and not long_fail,
                  f"longest coarse interval {far['interval'] if far else None} TSC: "
                  f"time-keyed wrong={far['tkwrong'] if far else None}; predicted edge {pred}")
        else:
            # Darkmont: the long-gap failure exists and starts at the predicted edge.
            onset = min((r["interval"] for r in long_fail), default=None)
            check(f"{c}: coarse time-keyed MIS-attributes at long gaps, onset at the predicted "
                  f"MTC-payload wrap (within 2x)",
                  pred is not None and onset is not None and hi is not None
                  and hi <= 2 * pred and onset >= pred / 2,
                  f"largest exact {hi} <= 2x{pred}; smallest long-gap failure {onset} >= "
                  f"{pred}/2; wrong at long intervals = "
                  f"{[(r['interval'], r['tkwrong']) for r in long_fail]}")

    # 3. The mechanism, from the packets: timing-packet density at the longest gap.
    if "P" in longest and longest["P"]:
        dm = [longest[c] for c in classes if c != "P" and longest[c]]
        check("mechanism: at the longest gap Cougar Cove's trace carries >= 100x the MTC "
              "packets of each Darkmont class (BranchEn=0)",
              bool(dm) and all(longest["P"]["mtc"] >= 100 * max(1, r["mtc"]) for r in dm),
              f"MTC packets per capture: P {longest['P']['mtc']}; "
              + "; ".join(f"{r['cls']} {r['mtc']}" for r in dm)
              + f" (TSC packets: P {longest['P']['tsc']}; "
              + "; ".join(f"{r['cls']} {r['tsc']}" for r in dm) + ")")

    # 4. Fine timing (dense MTC+CYC): time-keyed exact on OVF-free rows, every class.
    fine = [r for r in clean if r["timing"] == "fine"]
    check("FINE timing: time-keyed is exact on all OVF-free rows of every class "
          "(dense timing closes the short-interval gap)",
          all(r["tkwrong"] == 0 for r in fine) and len(fine) >= 1,
          f"fine time-keyed wrong = {[(r['cls'], r['tkwrong']) for r in fine]}")

    # 5. Head-to-head contrast: wherever time-keyed is wrong, PTW-fenced is right.
    check("wherever time-keyed mis-attributes, PTW-fenced is exact",
          all(r["fwrong"] == 0 for r in rows if r["tkwrong"] > 0),
          f"rows with time-keyed wrong: {sum(1 for r in rows if r['tkwrong'] > 0)}; "
          f"of those, fenced wrong: {sum(1 for r in rows if r['tkwrong'] > 0 and r['fwrong'] > 0)}")

    print("\nInterpretation: an executed in-band PTWRITE fence pins each traced")
    print("execution to its exact self-modified version in packet order, needing no")
    print("timestamps, on every core class. The strong time-keyed decoder (TMA + MTC")
    print("payloads) is exact only over an interval band. Below it there are too few")
    print("CTC ticks to place the exec after its patch. Above it, on Darkmont (E,")
    print("LP-E), the BranchEn=0 trace carries only sporadic MTC packets and a single")
    print("TSC, so the 8-bit MTC payload wraps unobserved and the high CTC bits are")
    print("lost, starting at the predicted 2^(mtc_period+8) CTC edge. On Cougar Cove")
    print("(P) the trace carries an MTC every period, so the payload never wraps unseen")
    print("and long gaps stay exact. Fine (dense) timing closes the low end. Ground")
    print("truth is the EXEC payload the executed bytes produced, confirmed")
    print("independently of PT by verify_singlestep.")
    print("\n" + ("ALL VERDICTS PASS" if allpass else "SOME VERDICTS FAILED"))
    return 0 if allpass else 1


if __name__ == "__main__":
    sys.exit(main())
