#!/usr/bin/env python3
"""icache_model.py — a small AArch64 instruction/data coherence model.

It is driven by the instructions the interpreter ACTUALLY EXECUTES (REVIEW-04
B1): the interpreter calls store()/dc()/ic()/dsb()/isb() as it decodes STR / DC
CVAU / IC IVAU / DSB / ISB, and reads a self-modified word back through
fetch_word(). Everything here is MODEL output (R10).

ORDER MATTERS (REVIEW-04 round 2, B5). The required maintenance is anchored
AFTER THE LATEST STORE to each patched word: every STR to a word resets that
word's progress, so maintenance executed before the store ("flush, then
write"), a second unmaintained store after a completed sequence, and a DC
issued before the STR all leave the word un-maintained. For each patched word
the model walks the executed ops in program order through the required
sequence (below); an op only counts when it is the next required one and, for
DC/IC, when its address lies in the word's line under the configured line
sizes (so a wrong flush stride is caught).

THE FETCH READS MODEL STATE. `iview` is the instruction side's GUARANTEED view
of each word: it starts as the loaded image and is advanced to the word's
latest bytes only when the anchored sequence completes. Where the architecture
does not guarantee the new bytes (any required step missing after the latest
store), fetch_word() returns the last guaranteed bytes -- the worst case a
stale I-cache, a still-dirty D-line or an un-synchronised prefetch can show.
So "not guaranteed" is reported as STALE, never as a lucky fresh fetch.

The required sequence follows the Arm requirement and the Linux implementation
(quoted in sanitize.py ARM_REF): DC CVAU (unless IDC), DSB, IC IVAU (unless
DIC), DSB (if IC was done), ISB -- and the BARRIERS ARE KEPT even when IDC/DIC
let you skip the cache op (Linux cache.S keeps `dsb ishst` on the IDC path and
`isb` on the DIC path). Python stdlib only.
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
        self.image = bytes(code)       # the loaded program (what the loader made coherent)
        self.mem = bytearray(code)     # Point-of-Unification bytes
        self.cfg = cfg
        self.coherent = coherent       # True => x86/qemu-like coherent I-fetch
        self.dirty = {}                # off -> byte: in the D-cache, not yet at PoU (IDC=0)
        self.iview = {}                # word -> 4 bytes the I-side is GUARANTEED to fetch
        self.maint = []                # executed ops: ('str'|'dc'|'ic'|'dsb'|'isb', off|None)
        self.stage = {}                # word -> index into required() after its latest store
        self.cause = {}                # word -> step named by an ordering error
        self.note = {}                 # word -> human-readable reason (ordering errors)
        self.last_store = {}           # word -> index in maint of its latest store
        self.warmed = set()

    def _iline(self, off):
        return off - off % self.cfg.iminline

    def _dline(self, off):
        return off - off % self.cfg.dminline

    def _latest(self, w):
        return bytes(self.dirty.get(w + i, self.mem[w + i]) for i in range(4))

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

    def _step(self, op, off):
        """Advance every patched word whose next required step is `op`."""
        req = self.required()
        for w, i in list(self.stage.items()):
            if i >= len(req):
                continue
            covers = (op == "dc" and self._dline(off) == self._dline(w)) or \
                     (op == "ic" and self._iline(off) == self._iline(w)) or \
                     op in ("dsb", "isb")
            if op == req[i] and covers:
                self.stage[w] = i + 1
                if i + 1 == len(req):                 # sequence complete after the store
                    self.iview[w] = self._latest(w)
            elif (op == "ic" and covers and req[i] == "dsb"
                  and "ic" in req[i + 1:] and w not in self.cause):
                # IC issued before the DSB that completes the clean / the store
                self.cause[w] = "dsb"
                self.note[w] = "IC IVAU issued before a DSB completed the clean"

    # ---- effects of executed instructions ----
    def store(self, off, byte):
        self.maint.append(("str", off))
        w = off & ~3
        if self.coherent or self.cfg.idc:
            self.mem[off] = byte       # reaches PoU directly (IDC) / coherent
        else:
            self.dirty[off] = byte     # sits in the data cache; PoU still old
        self.stage[w] = 0              # this store must now be maintained from scratch
        self.last_store[w] = len(self.maint) - 1
        self.cause.pop(w, None)
        self.note.pop(w, None)

    def dc(self, off):
        self.maint.append(("dc", off))
        line = self._dline(off)
        for a in [a for a in self.dirty if self._dline(a) == line]:
            self.mem[a] = self.dirty.pop(a)   # clean this D-line to PoU
        self._step("dc", off)

    def ic(self, off):
        self.maint.append(("ic", off))
        self._step("ic", off)

    def dsb(self):
        self.maint.append(("dsb", None))
        self._step("dsb", None)

    def isb(self):
        self.maint.append(("isb", None))
        self._step("isb", None)

    def warm(self, off):
        """Execute-once seeding: the slot has been fetched and run once, so the
        core holds its current guaranteed bytes (I-cache + prefetch)."""
        self.warmed.add(off & ~3)

    # ---- the verdict ----
    def diagnose(self, slot_off):
        """(fresh, missing_step) for the word at slot_off, from the EXECUTED ops
        in program order, anchored after the word's latest store."""
        w = slot_off & ~3
        if w not in self.stage:
            return True, None                 # never patched: nothing to maintain
        req = self.required()
        i = self.stage[w]
        if i >= len(req):
            return True, None
        return False, self.cause.get(w, req[i])

    def explain(self, slot_off):
        """Why the word is (not) guaranteed fresh, read from the executed trace."""
        w = slot_off & ~3
        fresh, miss = self.diagnose(slot_off)
        if fresh:
            return "fresh"
        if w in self.note:
            return self.note[w]
        before = self.maint[:self.last_store[w]]
        def hits(op, off):
            if op != miss:
                return False
            if op == "dc":
                return self._dline(off) == self._dline(w)
            if op == "ic":
                return self._iline(off) == self._iline(w)
            return True
        if w in self.iview and self.iview[w] != self._latest(w):
            return ("re-patched after its maintenance completed: the later store "
                    f"is unmaintained (no {miss} after it)")
        if any(hits(op, off) for op, off in before):
            return f"{miss} executed only BEFORE the latest store (flush, then write)"
        return f"no {miss} after the latest store"

    def fetch_word(self, slot_off):
        """Fetch the 4-byte instruction word at slot_off from the model state.
        Coherent (x86/qemu-like): always the latest bytes. Otherwise the
        instruction side's guaranteed view: the loaded image, advanced only when
        the anchored maintenance sequence completed after the latest store."""
        w = slot_off & ~3
        if self.coherent:
            b = self._latest(w)
        else:
            b = self.iview.get(w, self.image[w:w + 4])
        return int.from_bytes(b, "little")
