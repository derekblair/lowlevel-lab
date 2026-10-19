#!/bin/bash
# verify.sh — one relay cycle + inspection checks for the cross-ISA quine relay.
# Builds stage0, runs ONE cycle (stage0 native -> stage1, stage1 under
# qemu-aarch64 -> stage2), then inspects. Each stage only writes its successor to
# stdout; THIS harness saves that output, marks it executable and runs it once.
# No stage writes a file or executes anything itself. Exit 0 iff all VERDICTs pass.
set -u
cd "$(dirname "$0")"
fail=0
v() { if [ "$2" = 0 ]; then echo "VERDICT PASS: $1"; else echo "VERDICT FAIL: $1"; fail=1; fi; }

python3 -I build_fixpoint.py stage0 || exit 1
chmod +x stage0

# ---- one cycle ----
./stage0 > stage1; ec0=$?
chmod +x stage1        # harness marks the emitted file executable (qemu-user requires +x)
qemu-aarch64 ./stage1 > stage2; ec1=$?
echo "stage0 (x86-64, native) exit=$ec0 -> stage1 $(wc -c <stage1) bytes"
echo "stage1 (AArch64, under qemu-aarch64) exit=$ec1 -> stage2 $(wc -c <stage2) bytes"

# ---- C12-1: byte-exact fixed point ----
sha256sum stage0 stage1 stage2
cmp stage0 stage2; v "fixed point: stage2 is byte-identical to stage0 (cmp + sha256 above)" $?

# ---- C12-1: each stage is a single-ISA ELF ----
for s in stage0 stage1 stage2; do
  printf '%s: %s | %s\n' "$s" "$(readelf -h "$s" | awk -F: '/Machine/{gsub(/^ +/,"",$2);print $2}')" "$(file -b "$s" | cut -d, -f1-2)"
done
m0=$(readelf -h stage0 | grep -c 'X86-64'); m1=$(readelf -h stage1 | grep -c 'AArch64'); m2=$(readelf -h stage2 | grep -c 'X86-64')
[ "$m0" = 1 ] && [ "$m1" = 1 ] && [ "$m2" = 1 ]; v "stage0/stage2 are x86-64 ELFs, stage1 is an AArch64 ELF (readelf -h)" $?

# ---- C12-1: AArch64 stage disassembled with the system aarch64 objdump ----
echo "--- aarch64-linux-gnu-objdump of stage1's code (entry region):"
aarch64-linux-gnu-objdump -D -b binary -m aarch64 --start-address=120 --stop-address=232 stage1 \
  | grep -E '^ +[0-9a-f]+:'

# ---- C12-2 (safety): each stage makes ONLY write(1,...) + exit. FAIL CLOSED
# (REVIEW-03-build N2): require EXACTLY 3 write(1, + an exit + a successful
# tracer run + the expected output size; anything else (incl. a tracer that
# failed to attach, or an empty log) fails.
strace -f -o strace-stage0.txt ./stage0 > s0.out; s0rc=$?
xw=$(grep -cE ' write\(1,' strace-stage0.txt); xe=$(grep -cE ' exit(_group)?\(' strace-stage0.txt)
xbad=$(grep -E '^[0-9]+ +[a-z_]+\(' strace-stage0.txt | grep -vE ' (execve|write\(1,|exit)' | grep -c .)
echo "stage0: writes=$xw exits=$xe other=$xbad rc=$s0rc out=$(wc -c <s0.out)B"
[ "$xw" = 3 ] && [ "$xe" -ge 1 ] && [ "$xbad" = 0 ] && [ "$s0rc" = 0 ] && [ "$(wc -c <s0.out)" -gt 0 ]
v "C12-2 x86 stage0: exactly 3x write(1,..) + exit, no other syscalls (fail-closed)" $?
qemu-aarch64 -strace ./stage1 2>strace-stage1.txt > s1.out; s1rc=$?
aw=$(grep -cE ' write\(1,' strace-stage1.txt); ae=$(grep -cE ' exit(_group)?\(' strace-stage1.txt)
abad=$(grep -E ' [a-z_0-9]+\(' strace-stage1.txt | grep -vE ' (write\(1,|exit)' | grep -c .)
echo "stage1: writes=$aw exits=$ae other=$abad rc=$s1rc out=$(wc -c <s1.out)B"
[ "$aw" = 3 ] && [ "$ae" -ge 1 ] && [ "$abad" = 0 ] && [ "$s1rc" = 0 ] && [ "$(wc -c <s1.out)" -gt 0 ]
v "C12-2 AArch64 stage1 (qemu -strace): exactly 3x write(1,..) + exit (fail-closed)" $?
rm -f s0.out s1.out

# ---- R6: hand-emitted encodings decoded by GNU's decoders (independent oracle) ----
x_mn=$(objdump -D -b binary -m i386:x86-64 --start-address=120 --stop-address=200 stage0 \
  | awk -F'\t' '/^ +[0-9a-f]+:/{split($3,a," "); if (a[1]!="") print a[1]}' | tr '\n' ' ')
a_mn=$(aarch64-linux-gnu-objdump -D -M no-aliases -b binary -m aarch64 --start-address=120 --stop-address=232 stage1 \
  | awk -F'\t' '/^ +[0-9a-f]+:/{split($3,a," "); if (a[1]!="") print a[1]}' | tr '\n' ' ')
echo "x86 decode : $x_mn"
echo "a64 decode : $a_mn"
x_exp="mov mov movabs mov syscall mov movabs mov syscall mov movabs mov syscall mov xor syscall "
a_exp="movz movk movz movk movz movk movz movk svc movz movk movz movk movz movk svc movz movk movz movk movz movk svc movz movk movz movk svc "
[ "$x_mn" = "$x_exp" ]; v "R6 x86 code decodes (GNU objdump) to the intended mov/movabs/syscall sequence" $?
[ "$a_mn" = "$a_exp" ]; v "R6 AArch64 code decodes (GNU aarch64 objdump) to the intended movz/movk/svc sequence" $?

[ $fail = 0 ] && echo "ALL VERDICTS PASS" || echo "SOME VERDICTS FAILED"
exit $fail
