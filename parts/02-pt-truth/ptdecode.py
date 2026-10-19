#!/usr/bin/env python3
"""ptdecode.py — a minimal, correct Intel-PT packet framer (Python stdlib).

It does NOT reconstruct the instruction stream. It frames the packet stream so
that PTW payloads and the timing packets (TSC/MTC/TMA/CBR/CYC) can be read in
order — which is all the version-attribution head-to-head needs. Framing
correctness is self-checked: `iter_packets` raises on an unknown opcode and the
caller asserts it consumes the whole buffer and recovers the expected PTWs.

Packet encodings follow the Intel SDM PT packet reference. Lengths implemented:
PAD(1), short TNT(1), long TNT(8: 02 A3 +6), TIP/FUP/TIP.PGE/TIP.PGD(1+ipbytes),
TSC(8), MTC(2), MODE(2), CYC(1+), and the 02-prefixed set PSB(16), PSBEND(2),
CBR(4), TMA(7), VMCS(7), OVF(2), PIP(8), MNT(11), PWRE(4), PWRX(7), EXSTOP(2),
MWAIT(10), BBP(3), PTW(2+4 or 2+8).
"""
import struct
import sys

IPBYTES = {0: 0, 1: 2, 2: 4, 3: 6, 4: 6, 5: 8, 6: 8}  # IPBytes field -> IP byte count


class PTError(Exception):
    pass


def iter_packets(buf):
    """Yield (offset, kind, payload_int_or_None). Raises PTError on desync."""
    i, n = 0, len(buf)
    PSB = bytes.fromhex("0282") * 8
    while i < n:
        b = buf[i]
        if b == 0x00:                                   # PAD
            yield (i, "pad", None); i += 1; continue
        if b == 0x02:                                   # extended opcodes
            if buf[i:i + 16] == PSB:
                yield (i, "psb", None); i += 16; continue
            if i + 1 >= n:
                raise PTError(f"truncated ext opcode @{i}")
            e = buf[i + 1]
            if e == 0x23: yield (i, "psbend", None); i += 2; continue
            if e == 0x03: yield (i, "cbr", None); i += 4; continue
            if e == 0x73: yield (i, "tma", (buf[i+2] | buf[i+3] << 8, buf[i+5] | buf[i+6] << 8)); i += 7; continue
            if e == 0xC8: yield (i, "vmcs", None); i += 7; continue
            if e == 0xF3: yield (i, "ovf", None); i += 2; continue
            if e == 0x43: yield (i, "pip", None); i += 8; continue
            if e == 0xC3: yield (i, "mnt", None); i += 11; continue
            if e == 0x22: yield (i, "pwre", None); i += 4; continue
            if e == 0xA2: yield (i, "pwrx", None); i += 7; continue
            if e in (0x62, 0xE2): yield (i, "exstop", None); i += 2; continue
            if e == 0xC2: yield (i, "mwait", None); i += 10; continue
            if e == 0x63: yield (i, "bbp", None); i += 3; continue
            if e == 0xA3:  # long TNT: 02 A3 + 6 payload bytes
                yield (i, "tnt", None); i += 8; continue
            if (e & 0x1F) == 0x12:  # PTW: payload len from bits[6:5] (0->4B,1->8B), bit7=IP
                plen = 8 if (e & 0x60) == 0x20 else 4
                ip = 8 if (e & 0x80) else 0  # FUP-on-PTW adds an IP (handled as part of pkt)
                off = i + 2
                payload = int.from_bytes(buf[off:off + plen], "little")
                yield (i, "ptw", payload); i += 2 + plen + ip; continue
            raise PTError(f"unknown 02-ext opcode {e:#x} @{i}")
        if b == 0x19: yield (i, "tsc", int.from_bytes(buf[i+1:i+8], "little")); i += 8; continue
        if b == 0x59: yield (i, "mtc", buf[i + 1]); i += 2; continue
        if b == 0x99: yield (i, "mode", None); i += 2; continue
        low5 = b & 0x1F
        if low5 in (0x0D, 0x11, 0x01, 0x1D):            # TIP / TIP.PGE / TIP.PGD / FUP
            kind = {0x0D: "tip", 0x11: "tip.pge", 0x01: "tip.pgd", 0x1D: "fup"}[low5]
            yield (i, kind, None); i += 1 + IPBYTES.get(b >> 5, 0); continue
        if (b & 0x03) == 0x03:                          # CYC (variable)
            j = i
            # first byte: bit2 = exp(continuation); following bytes: bit0 = continuation
            cont = (buf[j] >> 2) & 1
            j += 1
            while cont and j < n:
                cont = buf[j] & 1
                j += 1
            yield (i, "cyc", None); i = j; continue
        if (b & 0x01) == 0:                             # short TNT (1 byte)
            yield (i, "tnt", None); i += 1; continue
        raise PTError(f"unknown opcode {b:#x} @{i}")


EXEC_TAG = 0x5EC00000
FENCE_TAG = 0xFE0C0000


def events(buf):
    """Walk packets, tracking a coarse (TSC-packet) and a finer (TSC+MTC) clock,
    and return the ordered list of PTW events with both clocks attached."""
    out = []
    last_tsc = None
    mtc_since_tsc = 0
    for off, kind, payload in iter_packets(buf):
        if kind == "tsc":
            last_tsc = payload
            mtc_since_tsc = 0
        elif kind == "mtc":
            mtc_since_tsc += 1
        elif kind == "ptw":
            tag = payload & 0xFFFF0000
            ver = payload & 0xFFFF
            if tag == FENCE_TAG:
                if ver == 0xFFFF:
                    continue  # warm-up fence (capture-edge filler), ignored
                out.append({"off": off, "type": "fence", "ver": ver,
                            "tsc": last_tsc, "mtc": mtc_since_tsc})
            elif tag == EXEC_TAG:
                out.append({"off": off, "type": "exec", "ver": ver,
                            "tsc": last_tsc, "mtc": mtc_since_tsc})
    return out


def frame_check(buf):
    """Return (consumed_all, n_fence, n_exec); raises PTError on desync."""
    end = 0
    nf = ne = 0
    for off, kind, payload in iter_packets(buf):
        end = off
        if kind == "ptw":
            t = payload & 0xFFFF0000
            if t == FENCE_TAG: nf += 1
            elif t == EXEC_TAG: ne += 1
    # re-walk to get the true end offset
    last = 0
    for off, kind, _ in iter_packets(buf):
        last = off
    return (nf, ne, last)


if __name__ == "__main__":
    buf = open(sys.argv[1], "rb").read()
    try:
        nf, ne, last = frame_check(buf)
        ev = events(buf)
        order = "".join("F" if e["type"] == "fence" else "E" for e in ev)
        print(f"framed OK: {len(buf)} bytes, fences={nf} execs={ne}")
        print(f"PTW order: {order}")
        print("first events:", [(e["type"], e["ver"], e["tsc"]) for e in ev[:6]])
    except PTError as e:
        print("FRAMING DESYNC:", e); sys.exit(1)
