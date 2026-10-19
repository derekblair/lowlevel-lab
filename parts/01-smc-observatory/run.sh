#!/bin/bash
# run.sh — drive smcobs over the three core classes and emit raw CSV to stdout.
# Deterministic point set; REPEATS runs per point for median/spread (REVIEW-00
# §1.18). One representative CPU per class, chosen to match the reviewer's
# reference probe so clear-counts compare directly:
#   P = cpu0 (Cougar Cove), E = cpu5 (Darkmont), LP-E = cpu13 (Darkmont, no L3).
# Override with: CPUS="0 5 13" REPEATS=5 ./run.sh
set -u
cd "$(dirname "$0")"
CPUS="${CPUS:-0 5 13}"
REPEATS="${REPEATS:-5}"
BIN=./smcobs
[ -x "$BIN" ] || { echo "build first: make" >&2; exit 1; }

echo "# smcobs raw CSV  $(date '+%Y-%m-%dT%H:%M:%S%z')  host=$(hostname)"
echo "# kind,cpu,class,pmu/writer_cpu,code_off/writer_class,store_off/event,event/clears_pm,clears_per_iter/tsc,tsc_per_iter/writes,sum"
echo "# sweep rows: kind,cpu,class,pmu,code_off,store_off,event,clears_per_iter,tsc_per_iter,sum"

# Placement A: code line- and subpage-aligned at offset 0.
#   brackets the P 64B line boundary (64) and the E/LP-E 1KB subpage boundary (1024).
A_OFFS="8 32 63 64 128 256 512 1023 1024 1536 2047 2048 4096 8192"
# Placement B: code shifted into the SECOND 1KB subpage (offset 1536), to prove
#   the detection window tracks the code's own line/subpage, not the page base.
#   code occupies [1536,1542); stores avoid that span.
B_OFFS="8 512 1023 1024 1472 1543 1600 2000 2047 2048 3072"

for cpu in $CPUS; do
  for ev in smc; do
    for r in $(seq 1 "$REPEATS"); do
      for off in $A_OFFS;  do $BIN sweep "$cpu" 0    "$off" "$ev"; done
      for off in $B_OFFS;  do $BIN sweep "$cpu" 1536 "$off" "$ev"; done
    done
  done
done

# Cross-modifying code: writer on a P-core, executor on each class; count XMC
# (Darkmont only) and SMC on the executor. Benign: threads of one process.
for pair in "0 5 smc" "0 5 xmc" "0 13 smc" "0 13 xmc" "0 1 smc" "4 0 smc"; do
  for r in $(seq 1 "$REPEATS"); do $BIN xcore $pair; done
done

# Torn-fetch: writer flips an instruction straddling a 64B line; executor counts
# any read that is neither old nor new value.
for pair in "0 5" "0 13" "4 0"; do
  for r in $(seq 1 "$REPEATS"); do $BIN torn $pair; done
done
