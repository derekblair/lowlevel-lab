#!/usr/bin/env bash
# final_rerun.sh LABEL COMMIT [RUNS] — REVIEW-FINAL clean re-run of every part.
# Clones COMMIT fresh (review/tools/repro.sh), then for each parts/NN-*/ runs the
# README's documented `make` RUNS times (default 2) under env -i with a timeout,
# capturing full output and a one-line summary per run:
#   <part> run=<n> exit=<code> PASS=<n> FAIL=<n> secs=<s>
# Summary goes to tasks/reviewer-repro/LABEL/.evidence/final-summary.txt.
set -u
label=${1:?label}; commit=${2:?commit}; runs=${3:-2}
top=$(cd "$(dirname "$0")/../.." && pwd)
"$top/review/tools/repro.sh" "$label" "$commit" >/dev/null || exit 1
C=$top/tasks/reviewer-repro/$label; E=$C/.evidence
: > "$E/final-summary.txt"
for d in "$C"/parts/*/; do
  p=$(basename "$d")
  for n in $(seq 1 "$runs"); do
    t0=$(date +%s)
    (cd "$d" && TIMEOUT=1200 ../../.envrun make) > "$E/$p-run$n.txt" 2>&1; ec=$?
    t1=$(date +%s)
    printf '%-24s run=%s exit=%s PASS=%s FAIL=%s secs=%s\n' "$p" "$n" "$ec" \
      "$(grep -c 'VERDICT PASS' "$E/$p-run$n.txt")" "$(grep -c 'VERDICT FAIL' "$E/$p-run$n.txt")" \
      "$((t1 - t0))" | tee -a "$E/final-summary.txt"
  done
done
echo "clone: $C"
