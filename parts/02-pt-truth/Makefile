# pt-truth — build + run on nibbles (gcc 13.3, python3 stdlib, present tools only)
CC ?= gcc
CFLAGS ?= -O1 -Wall -Wextra
VERSIONS ?= 24

.DEFAULT_GOAL := run

ptcap: ptcap.c
	$(CC) $(CFLAGS) -o $@ $<

verify_singlestep: verify_singlestep.c
	$(CC) $(CFLAGS) -o $@ $<

# Independent ground truth (no PT), then the capture+attribution sweep + report.
.PHONY: run
run: ptcap verify_singlestep
	./verify_singlestep $(VERSIONS)
	VERSIONS=$(VERSIONS) ./run.sh > data.csv
	python3 report.py data.csv

# Reproduce the known baseline (PT silently misdecodes SMC) from the research probe.
.PHONY: baseline
baseline:
	@echo "baseline (PT misdecodes SMC) is in ../../research/probes/pt-smc-misdecode/"

.PHONY: clean
clean:
	rm -f ptcap verify_singlestep data.csv
