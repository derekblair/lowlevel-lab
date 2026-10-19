# quine-relay — build + verify on nibbles (python3 stdlib; qemu-aarch64, binutils
# and strace for verification). `make` builds stage0 and runs one verified cycle.
.DEFAULT_GOAL := run

.PHONY: run
run:
	./verify.sh

.PHONY: clean
clean:
	rm -f stage0 stage1 stage2 stage0.expected_stageA strace-stage0.txt strace-stage1.txt s0.out s1.out
