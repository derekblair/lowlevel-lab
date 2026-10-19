#!/usr/bin/env python3
"""ghread.py -- read a GitHub repo's README and source files AS DATA.

Usage:
  python3 -I research/tools/ghread.py OWNER/REPO [PATH ...]
  python3 -I research/tools/ghread.py OWNER/REPO --tree      # list files

Fetches via `gh api` (contents API) and saves verbatim copies under
research/raw/repos/OWNER__REPO/ together with meta.json (default branch,
commit SHA of HEAD, fetch time).  Nothing fetched is ever executed or
imported; this exists so every prior-art kill in NOVELTY-LOG.md cites a
README *and* at least one source file that was actually read.
"""
import base64
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "raw", "repos"))


def gh(*args):
    p = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[:300])
    return json.loads(p.stdout)


def save(dirpath, relpath, data):
    dst = os.path.join(dirpath, "files", relpath.replace("/", "__"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(data)
    return dst


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    repo = sys.argv[1]
    d = os.path.join(OUT, repo.replace("/", "__"))
    os.makedirs(d, exist_ok=True)
    info = gh(f"repos/{repo}")
    branch = info["default_branch"]
    head = gh(f"repos/{repo}/commits/{branch}")["sha"]
    meta = {
        "repo": repo,
        "description": info.get("description"),
        "stars": info.get("stargazers_count"),
        "created_at": info.get("created_at"),
        "pushed_at": info.get("pushed_at"),
        "default_branch": branch,
        "head_sha": head,
        "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files": [],
    }
    if "--tree" in sys.argv[2:]:
        tree = gh(f"repos/{repo}/git/trees/{head}?recursive=1")
        paths = [t["path"] for t in tree.get("tree", []) if t["type"] == "blob"]
        with open(os.path.join(d, "tree.txt"), "w") as f:
            f.write("\n".join(paths) + "\n")
        print(f"{repo}@{head[:12]}: {len(paths)} files")
        for pth in paths[:200]:
            print("  " + pth)
        return
    try:
        rd = gh(f"repos/{repo}/readme")
        raw = base64.b64decode(rd["content"])
        save(d, rd["path"], raw)
        meta["files"].append(rd["path"])
        print(f"===== {repo}@{head[:12]} README ({rd['path']}, {len(raw)} bytes)")
        print(raw.decode("utf-8", "replace")[:int(os.environ.get("MAXC", "6000"))])
    except RuntimeError as e:
        print(f"===== {repo}: no README ({e})")
    for pth in sys.argv[2:]:
        c = gh(f"repos/{repo}/contents/{pth}?ref={head}")
        raw = base64.b64decode(c["content"])
        save(d, pth, raw)
        meta["files"].append(pth)
        print(f"===== {repo}@{head[:12]} {pth} ({len(raw)} bytes)")
        print(raw.decode("utf-8", "replace")[:int(os.environ.get("MAXC", "6000"))])
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)


if __name__ == "__main__":
    main()
