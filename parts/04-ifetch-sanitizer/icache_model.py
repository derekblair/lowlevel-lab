#!/usr/bin/env python3
"""icache_model.py — a small AArch64 execution model with a MODELLED
instruction/data cache hierarchy, for diagnosing missing cache maintenance in
self-modifying / JIT code.

Everything about caches and staleness here is MODEL OUTPUT (REVIEW-01 §2.4 P4-4 /
R10), labelled as such; it is not a measurement of silicon. The model encodes
the Arm ARM (DDI 0487) rules for making a data write visible to instruction
fetch (B2.7.* "Caches and memory hierarchy" / the A64 cache-maintenance
instructions, and the CTR_EL0.{IDC,DIC} fields):

  To execute instructions written by data stores, software must, unless the
  relevant CTR_EL0 field says otherwise:
      DC CVAU, addr   ; clean data cache to Point of Unification   (skip iff IDC==1)
      DSB ISH
      IC IVAU, addr   ; invalidate instruction cache to PoU        (skip iff DIC==1)
      DSB ISH
      ISB             ; synchronize the fetched instruction stream
  Maintenance is by cache line; the stride must use CTR_EL0.DminLine /
  IminLine. A loop striding by the WRONG line size leaves some lines un-cleaned
  or un-invalidated (the classic big.LITTLE JIT bug).

The model is deliberately small: a byte-addressed memory, a D-cache that holds
dirty store bytes until cleaned to PoU, and an I-cache of fetched instruction
words. It is driven by the subset interpreter below.
"""
from dataclasses import dataclass, field


@dataclass
class Config:
    idc: int = 0            # CTR_EL0.IDC: 1 => D-cache clean to PoU not required
    dic: int = 0            # CTR_EL0.DIC: 1 => I-cache invalidate to PoU not required
    dminline: int = 64      # D-cache line (bytes) to the Point of Unification
    iminline: int = 64      # I-cache line (bytes)

    def name(self):
        return f"IDC={self.idc} DIC={self.dic} Dline={self.dminline} Iline={self.iminline}"


class Machine:
    """Byte memory + modelled D-cache (dirty bytes not yet at PoU) + I-cache
    (instruction words the fetcher has cached, possibly stale)."""

    def __init__(self, mem: bytearray, cfg: Config):
        self.mem = mem                 # architectural "settled" bytes (== PoU when clean)
        self.cfg = cfg
        self.dirty = {}                # addr -> byte written but not yet cleaned to PoU
        self.icache = {}               # line_base -> {off: word} cached instruction words
        self.x = [0] * 32
        self.stale_events = []         # (pc, addr) where a stale fetch occurred

    # ---- data side ----
    def store_byte(self, addr, val):
        # A store lands in the D-cache (dirty) and, per the architecture, is NOT
        # automatically visible to instruction fetch. If IDC==1 the data cache
        # is transparently clean to PoU, so the byte reaches PoU immediately.
        if self.cfg.idc:
            self.mem[addr] = val & 0xFF
        else:
            self.dirty[addr] = val & 0xFF

    def load_byte(self, addr):
        return self.dirty.get(addr, self.mem[addr])

    def dc_cvau(self, addr):
        base = addr - (addr % self.cfg.dminline)
        for a in range(base, base + self.cfg.dminline):
            if a in self.dirty:
                self.mem[a] = self.dirty.pop(a)   # clean this line to PoU

    def ic_ivau(self, addr):
        base = addr - (addr % self.cfg.iminline)
        self.icache.pop(base, None)               # invalidate this I-cache line

    # ---- instruction side ----
    def fetch_word(self, pc):
        """Return the instruction word the FETCHER sees at pc (possibly stale)."""
        line = pc - (pc % self.cfg.iminline)
        cached = self.icache.get(line)
        if cached is not None and pc in cached:
            return cached[pc]                      # stale if the line wasn't invalidated
        # miss: fill from the Point of Unification == settled memory (self.mem).
        # If IDC==0 and the store is still dirty (not cleaned), PoU holds the OLD
        # byte, so even a fresh fill is stale until DC CVAU runs.
        word = int.from_bytes(self.mem[pc:pc + 4], "little")
        self.icache.setdefault(line, {})[pc] = word
        return word
