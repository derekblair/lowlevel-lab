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
COARSE_DELAYS="${COARSE_DELAYS:-0 100 1000 10000 100000 1000000}"
FINE_DELAYS="${FINE_DELAYS:-0 100 1000 10000}"
WORK="${WORK:-$(mktemp -d)}"

echo "# pt-truth head-to-head  $(date '+%Y-%m-%dT%H:%M:%S%z')  host=$(hostname)"
echo "# timing,delay,execs,median_interval_tsc,fenced_ok,fenced_wrong,fenced_nofence,tk_ok,tk_wrong,ovf"
for timing in coarse fine; do
  if [ "$timing" = coarse ]; then DELAYS="$COARSE_DELAYS"; else DELAYS="$FINE_DELAYS"; fi
  for d in $DELAYS; do
    o="$WORK/$timing-$d"; mkdir -p "$o"
    ./ptcap "$VERSIONS" "$d" "$timing" "$o" 2>/dev/null
    python3 attribute.py "$o" --csv "$timing" "$d"
  done
done
echo "# workdir: $WORK"
