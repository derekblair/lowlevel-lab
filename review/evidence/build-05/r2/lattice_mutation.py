#!/usr/bin/env python3
"""lattice_mutation.py — is superset._check_lattice (the B3 VERDICT) non-vacuous?
usage: python3 -I lattice_mutation.py CLONE_PART_DIR LATTICE_HTML GT_OBJ WORKDIR
Rebuilds the headline analysis the author's way (object_sections + analyze on
work()), then runs _check_lattice on the real file and on mutated copies."""
import json, os, re, sys
sys.path.insert(0, sys.argv[1])
import superset as S
html_path, gt_obj, wd = sys.argv[2], sys.argv[3], sys.argv[4]
sec = [s for s in S.object_sections(gt_obj) if s[0] == ".text"][0]
name, raw, funcs = sec
s0 = funcs["work"]; e0 = min([x for x in funcs.values() if x > s0] or [len(raw)])
r = S.analyze(raw[s0:e0], "work", True, {"work": 0})
orig = open(html_path, encoding="utf-8").read()
corpus = json.loads(re.search(r'<script id=data type=application/json>(.*?)</script>', orig, re.S).group(1))["corpus"]


def check(label, text):
    p = os.path.join(wd, "m.html"); open(p, "w", encoding="utf-8").write(text)
    ok, why = S._check_lattice(p, r, corpus)
    print(f"{label:58} -> {'PASS' if ok else 'FAIL'}  [{why}]")


check("unmodified lattice.html", orig)
# (a) drop one misaligned arc from the drawing
i = orig.index('<path class="e mis"'); j = orig.index("/>", i) + 2
check("(a) one misaligned arc deleted from the SVG", orig[:i] + orig[j:])
# (b) drop one merge marker
i = orig.index('<circle class="merge"'); j = orig.index("/>", i) + 2
check("(b) one merge marker deleted", orig[:i] + orig[j:])
# (c) falsify the embedded histogram
d = json.loads(re.search(r'<script id=data type=application/json>(.*?)</script>', orig, re.S).group(1))
d2 = json.loads(json.dumps(d)); k = sorted(d2["resync_insn_hist"])[0]; d2["resync_insn_hist"][k] += 1
check("(c) embedded histogram count +1", orig.replace(json.dumps(d), json.dumps(d2)))
# (d) falsify one per-offset length in the embedded data (drawing unchanged)
d3 = json.loads(json.dumps(d)); idx = next(p["off"] for p in d3["per_offset"] if not p["boundary"] and p["objlen"] == 2)
d3["per_offset"][idx]["objlen"] = 3
check(f"(d) embedded objlen at off {idx}: 2 -> 3 (drawing unchanged)", orig.replace(json.dumps(d), json.dumps(d3)))
# (e) drop one histogram bar
i = orig.index('<rect class="bar"'); j = orig.index("</text>", orig.index("</text>", i) + 7) + 7
check("(e) one histogram bar deleted", orig[:i] + orig[j:])
# (f) move one misaligned arc's END POINT (counts unchanged): is geometry checked?
m = re.search(r'<path class="e mis" d="M(\d+),(\d+) A([\d.]+),([\d.]+) 0 0,0 (\d+),(\d+)"/>', orig)
x1 = int(m.group(5)); moved = m.group(0).replace(f" {x1},", f" {x1 + 11},")
check("(f) one misaligned arc's endpoint moved by one byte (11 px)", orig.replace(m.group(0), moved, 1))
