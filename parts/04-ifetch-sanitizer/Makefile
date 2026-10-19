# ifetch-sanitizer — build/run on nibbles. python3 stdlib + aarch64-linux-gnu
# binutils (encoder oracle) + qemu-aarch64 (semantic oracle). No installs.
.DEFAULT_GOAL := run

.PHONY: run
run:
	python3 a64asm.py          # encoder differential test vs aarch64-linux-gnu-as
	python3 sanitize.py        # semantic oracle + the diagnosis matrix + VERDICTs

.PHONY: clean
clean:
	rm -rf __pycache__
