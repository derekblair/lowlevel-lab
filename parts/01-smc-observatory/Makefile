# smc-observatory — build + run on nibbles (gcc 13.3, present tools only)
CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -pthread
REPEATS ?= 5
CPUS ?= 0 5 13

smcobs: smcobs.c
	$(CC) $(CFLAGS) -o $@ $<

# Capture a full sweep to data.csv, then render the report.
.PHONY: run
run: smcobs
	CPUS="$(CPUS)" REPEATS=$(REPEATS) ./run.sh > data.csv
	python3 -I report.py data.csv

# Smoke test: a handful of points that must reproduce the reviewer reference.
.PHONY: smoke
smoke: smcobs
	@./smcobs sweep 0 0 8 smc    # P  same 64B line -> 2.0
	@./smcobs sweep 0 0 64 smc   # P  next line     -> 0
	@./smcobs sweep 5 0 512 smc  # E  same 1KiB     -> 1.0
	@./smcobs sweep 5 0 1024 smc # E  next 1KiB     -> 0
	@./smcobs sweep 13 0 512 smc # LP-E same 1KiB   -> 1.0

.PHONY: clean
clean:
	rm -f smcobs data.csv
