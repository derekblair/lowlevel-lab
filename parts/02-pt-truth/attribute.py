#!/usr/bin/env python3
"""attribute.py — the version-attribution head-to-head (REVIEW-01-build P2-3).

On ONE captured trace, attribute each traced execution of the self-modifying
region to a code version two ways, and score both against ground truth (the
EXEC PTW payload, which the executing self-modified bytes produced):

  time-keyed : the method perf / libipt-sb / wilvk use — place the execution on
               the PT timeline from TSC(/MTC) packets, then pick the latest
               patch event (external patchlog, rdtsc) at or before it.
  ptw-fenced : read the in-band cooperative FENCE PTW that immediately precedes
               the execution in packet order. No timestamps.

Ground truth is independent of the PT decode path (it is the value the executed
code itself emitted), and is cross-checked by verify_singlestep.py.

usage: attribute.py OUTDIR    (expects trace.pt, patchlog.csv, truth.csv there)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ptdecode

MASK56 = (1 << 56) - 1


def read_sideband(path):
    """Return (mtc_tick_in_tsc, mtc_period). One MTC = 2^mtc_period CTC ticks,
    and TSC = CTC * numer/denom (CPUID.15H), so one MTC = that many TSC ticks."""
    d = {}
    for ln in open(path):
        for tok in ln.split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                try:
                    d[k] = int(v)
                except ValueError:
                    pass
    numer = d.get("cpuid15_ebx_numer", 0)
    denom = d.get("cpuid15_eax_denom", 1) or 1
    period = d.get("mtc_period", 0)
    tick = (1 << period) * numer // denom if numer else 0
    return tick, period


def read_patchlog(path):
    rows = []
    for ln in open(path):
        ln = ln.strip()
        if not ln or ln.startswith("version"):
            continue
        v, t = ln.split(",")
        rows.append((int(v), int(t) & MASK56))
    return rows  # [(version, tsc_at_patch_masked)] in version order


def attribute(outdir):
    buf = open(f"{outdir}/trace.pt", "rb").read()
    ovf = sum(1 for _, k, _ in ptdecode.iter_packets(buf) if k == "ovf")
    ev = ptdecode.events(buf)
    patches = read_patchlog(f"{outdir}/patchlog.csv")
    mtc_tick, _period = read_sideband(f"{outdir}/sideband.txt")
    # ground truth per exec = the version its own EXEC payload carries
    execs = [e for e in ev if e["type"] == "exec"]

    def pt_time(e):
        """Strongest TSC+MTC time-keyed clock in the TSC domain (CYC, enabled in
        fine mode, is NOT decoded here, so fine time-keyed accuracy is a LOWER
        bound — a CYC-using decoder would do at least as well)."""
        return (e["tsc"] or 0) + e["mtc"] * mtc_tick

    # ---- ptw-fenced: last preceding FENCE in packet order ----
    fenced_ok = fenced_bad = fenced_nofence = 0
    last_fence = None
    fence_pred = {}
    for e in ev:
        if e["type"] == "fence":
            last_fence = e["ver"]
        elif e["type"] == "exec":
            if last_fence is None:
                fenced_nofence += 1            # fence clipped at trace start
            elif last_fence == e["ver"]:
                fenced_ok += 1
            else:
                fenced_bad += 1

    # ---- time-keyed (strongest available: TSC + MTC, in the TSC domain) ----
    # Patch events are rdtsc in the same TSC domain as PT TSC packets. Attribute
    # each exec to the latest patch at or before the exec's PT time.
    tk_ok = tk_bad = tk_noclock = 0
    for e in execs:
        if e["tsc"] is None:
            tk_noclock += 1
            continue
        t = pt_time(e)
        pred = None
        for v, pt in patches:
            if pt <= t:
                pred = v
        if pred == e["ver"]:
            tk_ok += 1
        else:
            tk_bad += 1

    n = len(execs)
    # Resolution available to the TSC+MTC decoder = distinct (tsc, mtc) tuples
    # among the execs. Pigeonhole: it must mis-attribute >= n - resolution execs.
    resolution = len({(e["tsc"], e["mtc"]) for e in execs if e["tsc"] is not None})
    return {
        "n": n,
        "resolution": resolution,
        "mtc_tick": mtc_tick,
        "ovf": ovf,
        "fenced": (fenced_ok, fenced_bad, fenced_nofence),
        "timekeyed": (tk_ok, tk_bad, tk_noclock),
    }


if __name__ == "__main__":
    r = attribute(sys.argv[1])
    fo, fb, fn = r["fenced"]
    to, tb, tc = r["timekeyed"]
    if len(sys.argv) >= 5 and sys.argv[2] == "--csv":
        timing, delay = sys.argv[3], sys.argv[4]
        print(f"{timing},{delay},{r['n']},{r['resolution']},"
              f"{fo},{fb},{fn},{to},{tb},{r['ovf']}")
    else:
        print(f"execs={r['n']}  TSC+MTC resolution (distinct timestamps across burst)={r['resolution']}"
              f"  (1 MTC = {r['mtc_tick']} TSC ticks)")
        print(f"  ptw-fenced : correct={fo} wrong={fb} no-preceding-fence={fn}")
        print(f"  time-keyed : correct={to} wrong={tb} no-clock={tc}  (TSC+MTC)")
