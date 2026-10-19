#!/usr/bin/env bash
# stage_syscalls.sh BINARY [STDOUT_FILE] — list every syscall a relay stage makes (REVIEW-01 §6.1 C12-2).
# x86-64 ELF -> strace -f; AArch64 ELF -> qemu-aarch64 -strace. Prints the distinct syscall names
# and "ONLY-WRITE1-EXIT: yes|no" (yes iff the only syscalls are write(1,...) and exit/exit_group).
set -u
bin=${1:?binary}; out=${2:-/dev/null}
machine=$(readelf -h "$bin" | awk -F: '/Machine:/{gsub(/^ +/,"",$2); print $2}')
log=$(mktemp)
case "$machine" in
  *X86-64*)  strace -f -qq -o "$log" "$bin" > "$out"; rc=$?
             sed -i "1{/execve(/d}" "$log"   # drop strace's own launch of the stage (only line 1)
             calls=$(sed -E 's/^[0-9]+ +//' "$log" | grep -oE '^[a-z_0-9]+\(' | tr -d '(' | sort | uniq -c);
             bad=$(sed -E 's/^[0-9]+ +//' "$log" | grep -vE '^(write\(1,|exit\(|exit_group\(|\+\+\+ exited)' | grep -vE '^$' || true) ;;
  *AArch64*) qemu-aarch64 -strace "$bin" > "$out" 2> "$log"; rc=$?
             calls=$(grep -oE '^[0-9]+ [a-z_0-9]+\(' "$log" | awk '{print $2}' | tr -d '(' | sort | uniq -c);
             bad=$(grep -E '^[0-9]+ [a-z_0-9]+\(' "$log" | sed -E 's/^[0-9]+ //' | grep -vE '^(write\(1,|exit\(|exit_group\()' || true) ;;
  *) echo "unknown machine: $machine"; exit 2 ;;
esac
echo "binary=$bin machine=$machine exit=$rc stdout_bytes=$(wc -c < "$out" 2>/dev/null || echo 0)"
echo "$calls" | sed 's/^/  /'
# FAIL CLOSED (fixed 2026-10-19 at REVIEW-FINAL): an empty trace (exec failed, tracer
# failed) used to print "yes". Require a successful run that actually wrote and exited.
nw=$(echo "$calls" | awk '$2=="write"{print $1}'); ne=$(echo "$calls" | awk '$2=="exit"||$2=="exit_group"{s+=$1} END{print s+0}')
if [ "$rc" -ne 0 ] || [ -z "$nw" ] || [ "$ne" -lt 1 ]; then
  echo "ONLY-WRITE1-EXIT: no (run failed or traced nothing: exit=$rc writes=${nw:-0} exits=$ne)"
elif [ -z "$bad" ]; then echo "ONLY-WRITE1-EXIT: yes"; else echo "ONLY-WRITE1-EXIT: no"; echo "$bad" | head -5 | sed 's/^/  offending: /'; fi
rm -f "$log"
