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

usage: attribute.py OUTDIR    (expects trace.pt, patchlog.csv, sideband.txt there)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ptdecode

MASK56 = (1 << 56) - 1


def read_sideband_raw(path):
    """Parse sideband.txt 'k=v' tokens into an int dict (mtc_period, the
    CPUID.15H ratio fields, etc.)."""
    d = {}
    for ln in open(path):
        for tok in ln.split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                try:
                    d[k] = int(v)
                except ValueError:
                    pass
    return d


def read_patchlog(path):
    rows = []
    for ln in open(path):
        ln = ln.strip()
        if not ln or ln.startswith("version"):
            continue
        parts = ln.split(",")
        v = int(parts[0]); tp = int(parts[1]) & MASK56
        te = int(parts[2]) & MASK56 if len(parts) > 2 else tp
        rows.append((v, tp, te))
    return rows  # [(version, tsc_at_patch, tsc_at_exec)] in version order


def payload_clocked_execs(buf, period, numer, denom):
    """Reconstruct a TSC-domain timestamp for each EXEC PTW the way a real
    sideband decoder (perf / libipt-sb) does: anchor CTC at the TSC+TMA pair and
    advance it from each MTC's PAYLOAD (CTC[period+7:period], with 8-bit wrap),
    NOT by counting MTC packets. Returns [(exec_version, tsc_or_None), ...] in
    order. This is the strong time-keyed baseline (REVIEW-02-build B1).

    Cross-checked against the reviewer's independent payload_timekeyed.py, which
    implements the same documented algorithm."""
    base_tsc = base_ctc = ctc = None
    last_full_tsc = None
    out = []
    for off, k, p in ptdecode.iter_packets(buf):
        if k == "tsc":
            last_full_tsc = p
        elif k == "tma" and last_full_tsc is not None:
            ctc = p[0]                      # TMA carries CTC[15:0]
            base_ctc = ctc
            base_tsc = last_full_tsc
        elif k == "mtc" and ctc is not None:
            old = (ctc >> period) & 0xff
            new = p & 0xff
            ctc = (ctc & ~(0xff << period)) | (new << period)
            if new < old:                   # CTC[period+7:period] wrapped
                ctc += 1 << (period + 8)
            ctc &= ~((1 << period) - 1)      # MTC marks a period boundary
        elif k == "ptw" and (p & 0xFFFF0000) == ptdecode.EXEC_TAG:
            t = None if ctc is None else base_tsc + (ctc - base_ctc) * numer // denom
            out.append((p & 0xFFFF, t))
    return out


def attribute(outdir):
    buf = open(f"{outdir}/trace.pt", "rb").read()
    kinds = {}
    for _, k, _ in ptdecode.iter_packets(buf):
        kinds[k] = kinds.get(k, 0) + 1
    ovf = kinds.get("ovf", 0)
    ev = ptdecode.events(buf)
    patches = read_patchlog(f"{outdir}/patchlog.csv")
    sb = read_sideband_raw(f"{outdir}/sideband.txt")
    period = sb.get("mtc_period", 0)
    numer = sb.get("cpuid15_ebx_numer", 1)
    denom = sb.get("cpuid15_eax_denom", 1) or 1

    execs = [e for e in ev if e["type"] == "exec"]
    n = len(execs)

    # ---- ptw-fenced: last preceding FENCE in packet order (exact by construction) ----
    fenced_ok = fenced_bad = fenced_nofence = 0
    last_fence = None
    for e in ev:
        if e["type"] == "fence":
            last_fence = e["ver"]
        elif e["type"] == "exec":
            if last_fence is None:
                fenced_nofence += 1
            elif last_fence == e["ver"]:
                fenced_ok += 1
            else:
                fenced_bad += 1

    # ---- time-keyed: payload-reconstructed TSC clock (strong baseline) ----
    clocked = payload_clocked_execs(buf, period, numer, denom)
    tk_ok = tk_bad = tk_noclock = 0
    for ver, t in clocked:
        if t is None:
            tk_noclock += 1
            continue
        pred = None
        for v, tp, te in patches:
            if tp <= t:
                pred = v
        tk_ok += (pred == ver)
        tk_bad += (pred != ver)

    # measured patch->execute interval (median TSC ticks), from the patchlog
    intervals = sorted(te - tp for _v, tp, te in patches)
    median_interval = intervals[len(intervals) // 2] if intervals else 0
    return {
        "n": n,
        "ovf": ovf,
        "mtc": kinds.get("mtc", 0),      # timing-packet density: the core-class
        "tsc": kinds.get("tsc", 0),      # mechanism behind the long-gap result
        "median_interval_tsc": median_interval,
        "fenced": (fenced_ok, fenced_bad, fenced_nofence),
        "timekeyed": (tk_ok, tk_bad, tk_noclock),
    }


if __name__ == "__main__":
    r = attribute(sys.argv[1])
    fo, fb, fn = r["fenced"]
    to, tb, tc = r["timekeyed"]
    if len(sys.argv) >= 5 and sys.argv[2] == "--csv":
        timing, delay = sys.argv[3], sys.argv[4]
        print(f"{timing},{delay},{r['n']},{r['median_interval_tsc']},"
              f"{fo},{fb},{fn},{to},{tb},{r['ovf']},{r['mtc']},{r['tsc']}")
    else:
        print(f"execs={r['n']}  median patch->exec interval={r['median_interval_tsc']} TSC ticks  ovf={r['ovf']}")
        print(f"  ptw-fenced : correct={fo} wrong={fb} no-preceding-fence={fn}")
        print(f"  time-keyed : correct={to} wrong={tb} no-clock={tc}  (TMA+MTC-payload clock)")
