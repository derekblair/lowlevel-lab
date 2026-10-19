#!/usr/bin/env python3
"""indep_lattice.py — reviewer's independent re-derivation for BUILD-05 (C09).

usage: python3 -I indep_lattice.py CLONE_PART_DIR OBJFILE SYMBOL
  CLONE_PART_DIR: the gate-commit part dir (author module imported READ-ONLY,
                  only to obtain *its* per-offset lengths for comparison).
  OBJFILE/SYMBOL: the region to analyse (a .o/ELF with symbols).

Independently of superset.py:
  * true boundaries from `objdump -d -w` (one line per instruction);
  * per-offset first-instruction length from `objdump -D -w -b binary` on the
    same isolated blob the author uses (so blob-end semantics are identical);
  * the author's resync definition, recomputed with those lengths.
Prints every offset where the author's objdump length differs from the -w one.
"""
import os, re, statistics as st, subprocess, sys, tempfile

LINEW = re.compile(r"^\s*([0-9a-f]+):\t((?:[0-9a-f]{2} )+)\s*\t?(.*)$")


def region(obj, sym):
    out = subprocess.run(["objdump", "-d", "-w", obj], capture_output=True, text=True, check=True).stdout
    raw, bounds, base, on = bytearray(), set(), None, False
    for ln in out.splitlines():
        if re.match(r"^[0-9a-f]+ <%s>:" % re.escape(sym), ln):
            on, base = True, int(ln.split()[0], 16); continue
        if on:
            if not ln.strip() or re.match(r"^[0-9a-f]+ <", ln):
                break
            m = LINEW.match(ln)
            if m:
                bounds.add(int(m.group(1), 16) - base)
                raw += bytes(int(x, 16) for x in m.group(2).split())
    bounds.add(len(raw))
    return bytes(raw), bounds


def wide_decode(blob, k):
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "r.bin"); open(f, "wb").write(blob)
        out = subprocess.run(["objdump", "-D", "-w", "-b", "binary", "-m", "i386:x86-64",
                              f"--start-address={k}", f"--stop-address={k + 16}", f],
                             capture_output=True, text=True, check=True).stdout
    for ln in out.splitlines():
        m = LINEW.match(ln)
        if m and int(m.group(1), 16) == k:
            return len(m.group(2).split()), m.group(3).strip() or "(bad)"
    return None, "(no decode)"


def resync(N, bounds, olen):
    res, never = [], 0
    for k in range(N):
        if k in bounds or olen[k] is None:
            continue
        pos, n = k, 0
        while pos < N and olen[pos] is not None and n < N:
            pos += olen[pos]; n += 1
            if pos in bounds:
                res.append((k, pos - k, n)); break
        else:
            never += 1
    return res, never


def summ(res, never):
    ins = [r[2] for r in res]; by = [r[1] for r in res]
    return (f"resync={len(res)} never={never} median={st.median(ins)} insns "
            f"le2={sum(x <= 2 for x in ins) / len(ins):.2f} max={max(ins)} byte_median={st.median(by)}")


def main():
    part, obj, sym = sys.argv[1:4]
    sys.path.insert(0, part)
    import superset  # author module, read in full before import; used only for objdump_len_at
    raw, bounds = region(obj, sym)
    N = len(raw)
    a_raw, a_bounds = superset.region_from_symbol(obj, sym)
    print(f"region {sym}: N={N} insns={len(bounds) - 1}; author region identical: "
          f"{a_raw == raw}; author bounds identical: {a_bounds == bounds}")
    wl, asm = zip(*[wide_decode(raw, k) for k in range(N)])
    al = [superset.objdump_len_at(raw, k) for k in range(N)]
    diffs = [k for k in range(N) if al[k] != wl[k]]
    print(f"per-offset objdump length, author (no -w) vs -w: {N - len(diffs)}/{N} agree; "
          f"differ at {len(diffs)} offsets")
    for k in diffs:
        print(f"  off {k:#05x}: author={al[k]} true={wl[k]}  {asm[k]}")
    longest = max(wl)
    print(f"longest decode at any offset (-w): {longest} bytes")
    bad = [k for k in range(N) if asm[k].startswith("(bad)")]
    print(f"offsets objdump decodes as (bad): {len(bad)} {[hex(k) for k in bad]}")
    r_a, n_a = resync(N, bounds, al); r_w, n_w = resync(N, bounds, list(wl))
    print("resync with author lengths:   " + summ(r_a, n_a))
    print("resync with correct lengths:  " + summ(r_w, n_w))
    # chains that pass through a (bad) decode, and resyncs that land exactly on N
    thru_bad = 0
    for k, b, n in r_w:
        pos = k
        for _ in range(n):
            if pos in bad:
                thru_bad += 1; break
            pos += wl[pos]
    at_end = sum(1 for k, b, n in r_w if k + b == N)
    print(f"correct-length resyncs whose chain passes through a (bad): {thru_bad}; "
          f"resyncs landing exactly on region end N: {at_end}")


if __name__ == "__main__":
    main()
