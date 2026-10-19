#!/bin/bash
# run.sh — capture the self-modifying target across a patch->execute delay sweep
# at coarse and fine PT timing, run the attribution head-to-head on each, and
# emit CSV to stdout for report.py. Present tools only.
set -u
cd "$(dirname "$0")"
[ -x ./ptcap ] || { echo "build first: make" >&2; exit 1; }
VERSIONS="${VERSIONS:-24}"
# coarse sweeps to 1e6 for the long-gap (MTC-wrap) regime; fine is capped at 1e4
# because fine CYC floods the AUX ring at long delays -> OVF (REVIEW-02-build B2).
# Coarse delays 25 and 50 put each class's shortest row well below one MTC
# period (768 TSC), so the gated Darkmont short-interval failure never rests on
# a single execution near the edge (REVIEW-02 round 4, N9).
COARSE_DELAYS="${COARSE_DELAYS:-0 25 50 100 1000 10000 100000 1000000}"
FINE_DELAYS="${FINE_DELAYS:-0 100 1000 10000}"
# Every capture is PINNED, and the sweep runs once per core class (REVIEW-02
# round 2, nit d; R14): unpinned, the scheduler's choice of core class decided
# the long-gap result. Defaults: CPU 0 = Cougar Cove P, 4 = Darkmont E,
# 12 = Darkmont LP-E. Override with PT_CPUS="<cpu> ...".
PT_CPUS="${PT_CPUS:-0 4 12}"
own_work=0
if [ -z "${WORK:-}" ]; then WORK="$(mktemp -d)"; own_work=1; fi
trap 'if [ "$own_work" = 1 ]; then rm -rf "$WORK"; fi' EXIT   # no temp-dir litter

echo "# pt-truth head-to-head  $(date '+%Y-%m-%dT%H:%M:%S%z')  host=$(hostname)"
echo "# pinned: each sweep runs under taskset -c <cpu>, cpus: $PT_CPUS"
echo "# timing,delay,execs,median_interval_tsc,fenced_ok,fenced_wrong,fenced_nofence,tk_ok,tk_wrong,ovf,mtc_pkts,tsc_pkts,mtc_delta0,trace_bytes,cpu"
for cpu in $PT_CPUS; do
  for timing in coarse fine; do
    if [ "$timing" = coarse ]; then DELAYS="$COARSE_DELAYS"; else DELAYS="$FINE_DELAYS"; fi
    for d in $DELAYS; do
      o="$WORK/cpu$cpu-$timing-$d"; mkdir -p "$o"
      taskset -c "$cpu" ./ptcap "$VERSIONS" "$d" "$timing" "$o" 2>/dev/null
      echo "$(python3 attribute.py "$o" --csv "$timing" "$d"),$cpu"
    done
  done
done
# the coarse captures' clock parameters, for report.py's predicted MTC-wrap edge
first=${PT_CPUS%% *}
echo "# sideband coarse: $(grep -hE '^(cpuid15|mtc_period)' "$WORK/cpu$first-coarse-0/sideband.txt" | tr '\n' ' ')"
if [ "$own_work" = 1 ]; then echo "# workdir: temporary, removed"; else echo "# workdir: $WORK"; fi
