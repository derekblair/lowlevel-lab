#!/usr/bin/env python3
"""report.py — aggregate the pt-truth sweep CSV into the head-to-head verdict.

Grep 'VERDICT'. Exit 0 iff all pass. Python stdlib only.

Headline (REVIEW-01-build P2-3): an in-band executed-PTWRITE fence attributes
self-modified-code execution to its exact code version regardless of timing,
while a time-keyed decoder (TSC/MTC) mis-attributes below a patch->execute
interval set by the PT timestamp resolution.
"""
import sys


def load(f):
    rows = []
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        c = line.split(",")
        rows.append({
            "timing": c[0], "delay": int(c[1]), "execs": int(c[2]),
            "resolution": int(c[3]),
            "fok": int(c[4]), "fwrong": int(c[5]), "fnofence": int(c[6]),
            "tkok": int(c[7]), "tkwrong": int(c[8]),
            "ovf": int(c[9]) if len(c) > 9 else 0,
        })
    return rows


def main():
    rows = load(open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin)
    if not rows:
        print("no data"); return 1

    print("=" * 74)
    print("pt-truth: version attribution of self-modifying code, PTW-fenced vs time-keyed")
    print("=" * 74)
    hdr = f"{'timing':7} {'delay':>8} {'execs':>6} {'TSC+MTCres':>10} | {'fenced(ok/wrong)':>16} | {'time-keyed(ok/wrong)':>20}"
    print(hdr); print("-" * len(hdr))
    for r in rows:
        print(f"{r['timing']:7} {r['delay']:>8} {r['execs']:>6} {r['resolution']:>10} | "
              f"{r['fok']:>7}/{r['fwrong']:<8} | {r['tkok']:>9}/{r['tkwrong']:<10}")

    print("\n" + "=" * 74)
    print("VERDICTS")
    print("=" * 74)
    allpass = True

    def check(name, cond, detail=""):
        nonlocal allpass
        allpass = allpass and cond
        print(f"VERDICT {'PASS' if cond else 'FAIL'}: {name}" + (f"  [{detail}]" if detail else ""))

    # 1. PTW-fenced attribution is EXACT everywhere (0 wrong; no-fence is a
    #    capture-edge count, which the warm-up drives to 0).
    fwrong = sum(r["fwrong"] for r in rows)
    fnofence = sum(r["fnofence"] for r in rows)
    check("PTW-fenced attribution is exact at every delay & timing (0 wrong)",
          fwrong == 0, f"total fenced wrong across {len(rows)} runs = {fwrong}; no-preceding-fence = {fnofence}")

    # 1b. The capture is loss-free (no OVF): fenced exactness is a method result,
    #     not luck. (Branch tracing is off so the spin loop can't flood the ring.)
    ovf = sum(r["ovf"] for r in rows)
    check("capture is loss-free across the sweep (no OVF packets)",
          ovf == 0, f"total OVF packets across {len(rows)} runs = {ovf}")

    # 2. COARSE timing (sparse TSC + MTC, no CYC): the strongest TSC+MTC
    #    time-keyed decoder still mis-attributes at every delay, because an
    #    untraced interval emits too few timing packets to place an execution
    #    after its patch. This is the core result: fenced beats time-keyed.
    coarse = [r for r in rows if r["timing"] == "coarse"]
    coarse_tk_wrong_all = all(r["tkwrong"] > 0 for r in coarse)
    check("COARSE timing: TSC+MTC time-keyed mis-attributes at EVERY delay, "
          "while PTW-fenced is exact",
          coarse_tk_wrong_all and all(r["fwrong"] == 0 for r in coarse),
          f"coarse time-keyed wrong per delay = {[r['tkwrong'] for r in coarse]}; "
          f"fenced wrong = {[r['fwrong'] for r in coarse]}")

    # 3. FINE timing (dense MTC + CYC): here the time-keyed decoder IS exact.
    #    State it plainly (REVIEW-01 P2-3). The PTW fence still needed no timing.
    fine = [r for r in rows if r["timing"] == "fine"]
    fine_tk_exact = all(r["tkwrong"] == 0 for r in fine)
    check("FINE timing (CYC on): TSC+MTC time-keyed is exact -- so the PTW win is "
          "specifically at coarse timing; the fence needs NO timing packets either way",
          fine_tk_exact,
          f"fine time-keyed wrong per delay = {[r['tkwrong'] for r in fine]}")

    # 4. Head-to-head contrast at the hardest point (coarse, smallest interval).
    c0 = next((r for r in coarse if r["delay"] == 0), None)
    if c0:
        check("at coarse+delay0: PTW-fenced correct on all, time-keyed correct on almost none",
              c0["fwrong"] == 0 and c0["tkwrong"] >= c0["execs"] - 1,
              f"fenced {c0['fok']}/{c0['execs']} correct; time-keyed {c0['tkok']}/{c0['execs']} correct")

    print("\nInterpretation: the in-band executed PTWRITE fence pins each traced")
    print("execution to its exact self-modified version in packet order, with no")
    print("timestamps; the time-keyed method (perf/libipt-sb/wilvk) can only place")
    print("executions by PT timestamp, so when a patch and its execution fall within")
    print("the PT timestamp resolution it attributes the wrong version. Ground truth")
    print("is the EXEC payload the executed bytes produced, confirmed independently")
    print("of PT by verify_singlestep (EAX-at-ret == EXEC_TAG+i).")
    print("\n" + ("ALL VERDICTS PASS" if allpass else "SOME VERDICTS FAILED"))
    return 0 if allpass else 1


if __name__ == "__main__":
    sys.exit(main())
