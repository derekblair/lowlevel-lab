#!/usr/bin/env python3
"""ptframe.py — reviewer's INDEPENDENT minimal Intel PT packet framer (written
from the Intel SDM Vol. 3 packet tables; does not import the author's ptdecode).

usage: python3 -I ptframe.py TRACE.pt [TRACE.pt ...]
Frames the whole buffer; any byte it cannot frame is reported (and framing
stops), so silence means every byte was accounted for. Prints per trace:
packet counts by kind, MTC payload-delta histogram (mod 256), TSC count.
"""
import sys
from collections import Counter

IPB = {0: 0, 1: 2, 2: 4, 3: 6, 4: 6, 6: 8}           # TIP/FUP IPBytes -> payload bytes
EXT = {0x23: ("psbend", 0), 0x03: ("cbr", 2), 0x73: ("tma", 5), 0x43: ("pip", 6),
       0xF3: ("ovf", 0), 0xA3: ("ltnt", 6), 0x83: ("tracestop", 0), 0xC8: ("vmcs", 5),
       0x62: ("exstop", 0), 0xE2: ("exstop", 0), 0xC2: ("mwait", 7), 0x22: ("pwre", 2),
       0xA2: ("pwrx", 5), 0x13: ("cfe", 2), 0x53: ("evd", 9)}


def frame(b):
    i, n, out = 0, len(b), []
    while i < n:
        h = b[i]
        if h == 0x00:
            out.append(("pad", i, b"")); i += 1
        elif h == 0x02:
            if i + 1 >= n: return out, i
            e = b[i + 1]
            if e == 0x82:                                   # PSB = (02 82) x 8
                if b[i:i + 16] != b"\x02\x82" * 8: return out, i
                out.append(("psb", i, b"")); i += 16
            elif e & 0x1F == 0x12:                          # PTW: bits[6:5] size, bit7 IP
                sz = 8 if (e >> 5) & 3 == 1 else 4
                out.append(("ptw", i, b[i + 2:i + 2 + sz])); i += 2 + sz
            elif e == 0xC3:                                 # MNT: 02 C3 88 + 8
                out.append(("mnt", i, b"")); i += 11
            elif e in EXT:
                k, ln = EXT[e]; out.append((k, i, b[i + 2:i + 2 + ln])); i += 2 + ln
            else:
                return out, i
        elif h == 0x19:
            out.append(("tsc", i, b[i + 1:i + 8])); i += 8
        elif h == 0x59:
            out.append(("mtc", i, b[i + 1:i + 2])); i += 2
        elif h == 0x99:
            out.append(("mode", i, b[i + 1:i + 2])); i += 2
        elif h & 3 == 3:                                    # CYC (variable length)
            j = i
            if h & 4:
                j += 1
                while j < n and b[j] & 1:
                    j += 1
            out.append(("cyc", i, b"")); i = j + 1
        elif h & 0x1F in (0x0D, 0x11, 0x01, 0x1D):         # TIP / TIP.PGE / TIP.PGD / FUP
            k = {0x0D: "tip", 0x11: "tip.pge", 0x01: "tip.pgd", 0x1D: "fup"}[h & 0x1F]
            ipb = h >> 5
            if ipb not in IPB: return out, i
            out.append((k, i, b"")); i += 1 + IPB[ipb]
        elif h & 1 == 0:                                    # short TNT (even, non-zero)
            out.append(("tnt", i, b"")); i += 1
        else:
            return out, i
    return out, n


def main():
    for p in sys.argv[1:]:
        b = open(p, "rb").read()
        pk, stop = frame(b)
        c = Counter(k for k, _, _ in pk)
        mtc = [x[2][0] for x in pk if x[0] == "mtc"]
        d = Counter((mtc[j] - mtc[j - 1]) % 256 for j in range(1, len(mtc)))
        tail = "complete" if stop == len(b) else f"STOPPED at byte {stop} of {len(b)} (0x{b[stop]:02x})"
        print(f"{p}: {len(b)} B framed {tail}; " + " ".join(f"{k}={v}" for k, v in sorted(c.items())))
        print(f"   MTC payload deltas (mod 256), top: {d.most_common(6)}")


if __name__ == "__main__":
    main()
