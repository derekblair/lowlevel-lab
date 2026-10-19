#!/usr/bin/env python3
"""icache_model.py — a small AArch64 instruction/data cache model.

It is driven by the instructions the interpreter ACTUALLY EXECUTES (REVIEW-04
B1): the interpreter calls store()/dc()/ic()/dsb()/isb() as it decodes STR / DC
CVAU / DSB / IC IVAU / ISB, and reads the self-modified slot back through
fetch_word(). The model holds the stale instruction bytes in an I-cache and
decides fresh-vs-stale from the executed maintenance, so the verdict depends on
the program, not on any recipe. Everything here is MODEL output (R10).

The maintenance rule follows the Arm requirement and the Linux implementation
(quoted in sanitize.py ARM_REF): to make a store visible to fetch you need, in
order, DC CVAU (unless IDC) then a DSB, then IC IVAU (unless DIC) then a DSB (if
IC was done), then an ISB — and crucially the BARRIERS ARE KEPT even when IDC/DIC
let you skip the cache op (Linux cache.S keeps `dsb ishst` on the IDC path and
`isb` on the DIC path). DC/IC only count for the slot if their address lies in
the slot's line under the configured line sizes (so a wrong flush stride is
caught). Python stdlib only.
"""
from dataclasses import dataclass


@dataclass
class Config:
    idc: int = 0            # CTR_EL0.IDC
    dic: int = 0            # CTR_EL0.DIC  (DIC=1 requires IDC=1, per the Arm ARM)
    dminline: int = 64      # bytes; 2^(DminLine+2)
    iminline: int = 64      # bytes; 2^(IminLine+2)

    def name(self):
        return f"IDC={self.idc},DIC={self.dic}"


class Machine:
    def __init__(self, code, cfg: Config, coherent=False):
        self.mem = bytearray(code)     # Point-of-Unification-settled bytes
        self.cfg = cfg
        self.coherent = coherent       # True => x86/qemu-like coherent I-fetch
        self.dirty = {}                # off -> byte: store buffer, not yet at PoU
        self.icache = {}               # iline_base -> {off: byte} cached (stale) copy
        self.maint = []                # executed ops: ('str'|'dc'|'ic'|'dsb'|'isb', off|None)

    def _iline(self, off):
        return off - off % self.cfg.iminline

    def _dline(self, off):
        return off - off % self.cfg.dminline

    # ---- effects of executed instructions ----
    def store(self, off, byte):
        self.maint.append(("str", off))
        if self.coherent or self.cfg.idc:
            self.mem[off] = byte       # reaches PoU directly (IDC) / coherent
        else:
            self.dirty[off] = byte     # sits in the data cache; PoU still old

    def dc(self, off):
        self.maint.append(("dc", off))
        line = self._dline(off)
        for a in [a for a in self.dirty if self._dline(a) == line]:
            self.mem[a] = self.dirty.pop(a)   # clean this D-line to PoU

    def ic(self, off):
        self.maint.append(("ic", off))
        self.icache.pop(self._iline(off), None)   # invalidate this I-line

    def dsb(self):
        self.maint.append(("dsb", None))

    def isb(self):
        self.maint.append(("isb", None))

    def warm(self, off):
        """Execute-once seeding: snapshot the CURRENT (pre-patch) instruction
        word at off -- what the core holds in its I-cache AND its prefetch/
        pipeline after first running it. Until the full maintenance (incl. ISB)
        completes, a re-fetch still observes this snapshot."""
        line = self._iline(off)
        self.icache[line] = {a: self.mem[a] for a in range(line, line + self.cfg.iminline)
                             if 0 <= a < len(self.mem)}
        self.old_word = {off + i: self.mem[off + i] for i in range(4)}

    # ---- the maintenance rule (barriers kept per Linux cache.S) ----
    def required(self):
        req = []
        if not self.cfg.idc:
            req.append("dc")
        req.append("dsb")                 # kept even under IDC (dsb ishst)
        if not self.cfg.dic:
            req += ["ic", "dsb"]
        req.append("isb")                 # kept even under DIC
        return req

    def diagnose(self, slot_off):
        """(fresh, missing_step) for the slot, from the EXECUTED maintenance,
        counting DC/IC only where their address covers the slot's line."""
        iline, dline = self._iline(slot_off), self._dline(slot_off)
        performed = []
        for op, off in self.maint:
            if op == "dc" and (off is None or self._dline(off) != dline):
                continue                  # DC that missed the slot's D-line
            if op == "ic" and (off is None or self._iline(off) != iline):
                continue                  # IC that missed the slot's I-line
            if op == "str":
                continue
            performed.append(op)
        req = self.required()
        i = 0
        for p in performed:
            if i < len(req) and p == req[i]:
                i += 1
        if i == len(req):
            return True, None
        return False, req[i]

    def fetch_word(self, slot_off):
        """Fetch the 4-byte instruction word at slot_off, honoring staleness.
        Coherent (x86/qemu-like): always the latest bytes. Otherwise: the newly
        written bytes ONLY if the full maintenance ran (diagnose fresh); else the
        pre-patch snapshot the stale I-cache / un-synchronized prefetch holds —
        so omitting ANY required step (incl. the final ISB, even after DC+IC) is
        observed as stale."""
        latest = int.from_bytes(bytes(self.dirty.get(slot_off + i, self.mem[slot_off + i])
                                      for i in range(4)), "little")
        if self.coherent:
            return latest
        fresh, _ = self.diagnose(slot_off)
        if fresh:
            return latest
        if getattr(self, "old_word", None) and all((slot_off + i) in self.old_word for i in range(4)):
            return int.from_bytes(bytes(self.old_word[slot_off + i] for i in range(4)), "little")
        return latest   # not warmed (shouldn't happen for the slot)
