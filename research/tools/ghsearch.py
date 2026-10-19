#!/usr/bin/env python3
"""ghsearch.py -- reproducible GitHub novelty searches for lowlevel-lab.

Usage:
  python3 research/tools/ghsearch.py run    research/queries.tsv [--force]
  python3 research/tools/ghsearch.py render research/queries.tsv [CAND ...]

queries.tsv: one query per line, tab-separated:
    <candidate-id> <TAB> <repos|code> <TAB> <query>
Lines starting with '#' are comments.

Each query is executed with `gh api -X GET search/repositories` (or
search/code) with q=<query>, per_page=10.  That is the same REST endpoint
`gh search repos` / `gh search code` call, so every result is logged with
the equivalent replay command.  Raw results (including total_count, which
`gh search` does not print) are saved under research/raw/gh/ so the log
can be re-rendered and audited without re-querying.

Python stdlib only; requires the gh CLI to be logged in.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.normpath(os.path.join(HERE, "..", "raw", "gh"))
# GitHub search API limits: 30 req/min (repos), 10 req/min (code).
DELAY = {"repos": 2.3, "code": 6.5}
ENDPOINT = {"repos": "search/repositories", "code": "search/code"}


def load(path):
    out = []
    with open(path) as f:
        for ln, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 3 or parts[1] not in ENDPOINT:
                sys.exit(f"{path}:{ln}: bad line: {line!r}")
            out.append(tuple(parts))
    return out


def raw_path(cand, kind, query):
    h = hashlib.sha1(f"{kind}\0{query}".encode()).hexdigest()[:10]
    return os.path.join(RAW, f"{cand}-{kind}-{h}.json")


def replay_cmd(kind, query):
    q = query.replace("'", "'\\''")
    return f"gh search {kind} '{q}' --limit 10"


def trim(kind, item):
    if kind == "repos":
        return {
            "full_name": item.get("full_name"),
            "url": item.get("html_url"),
            "description": item.get("description"),
            "stars": item.get("stargazers_count"),
            "language": item.get("language"),
            "created_at": item.get("created_at"),
            "pushed_at": item.get("pushed_at"),
            "topics": item.get("topics", []),
        }
    repo = item.get("repository") or {}
    return {
        "full_name": repo.get("full_name"),
        "path": item.get("path"),
        "url": item.get("html_url"),
        "description": repo.get("description"),
    }


def gh_query(kind, query):
    cmd = ["gh", "api", "-X", "GET", ENDPOINT[kind],
           "-f", f"q={query}", "-f", "per_page=10"]
    for attempt in range(6):
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0:
            return json.loads(p.stdout)
        err = (p.stderr + p.stdout).strip()
        if "rate limit" in err.lower() or "HTTP 403" in err or "HTTP 429" in err:
            wait = 20 * (attempt + 1)
            print(f"  rate-limited; sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        return {"error": err[:500]}
    return {"error": "gave up after repeated rate limiting"}


def run(path, force):
    os.makedirs(RAW, exist_ok=True)
    for cand, kind, query in load(path):
        rp = raw_path(cand, kind, query)
        if os.path.exists(rp) and not force:
            continue
        time.sleep(DELAY[kind])
        res = gh_query(kind, query)
        rec = {
            "candidate": cand,
            "kind": kind,
            "query": query,
            "executed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "api_call": f"gh api -X GET {ENDPOINT[kind]} -f q='{query}' -f per_page=10",
            "replay": replay_cmd(kind, query),
        }
        if "error" in res:
            rec["error"] = res["error"]
        else:
            rec["total_count"] = res.get("total_count")
            rec["incomplete_results"] = res.get("incomplete_results")
            rec["items"] = [trim(kind, it) for it in res.get("items", [])]
        with open(rp, "w") as f:
            json.dump(rec, f, indent=1)
        tc = rec.get("total_count", "ERR")
        print(f"{cand:5s} {kind:5s} total={tc!s:>7}  {query}", file=sys.stderr)


def md_escape(s):
    return (s or "").replace("|", "\\|").replace("\n", " ").strip()


def render(path, only):
    by_cand = {}
    for cand, kind, query in load(path):
        by_cand.setdefault(cand, []).append((kind, query))
    for cand, qs in by_cand.items():
        if only and cand not in only:
            continue
        print(f"#### GitHub search record — {cand}\n")
        for kind, query in qs:
            rp = raw_path(cand, kind, query)
            if not os.path.exists(rp):
                print(f"- `{replay_cmd(kind, query)}` — NOT YET RUN\n")
                continue
            rec = json.load(open(rp))
            if "error" in rec:
                print(f"- `{rec['replay']}` — ERROR: {md_escape(rec['error'])}\n")
                continue
            items = rec["items"]
            print(f"- `{rec['replay']}` — **total_count={rec['total_count']}** "
                  f"(run {rec['executed_at']})")
            for it in items[:5]:
                if kind == "repos":
                    print(f"  - [{it['full_name']}]({it['url']}) ★{it['stars']} "
                          f"({(it['pushed_at'] or '')[:10]}) — "
                          f"{md_escape(it['description'])[:110]}")
                else:
                    print(f"  - [{it['full_name']}/{it['path']}]({it['url']}) — "
                          f"{md_escape(it['description'])[:90]}")
            if not items:
                print("  - (no hits)")
            print()


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("run", "render"):
        sys.exit(__doc__)
    if sys.argv[1] == "run":
        run(sys.argv[2], "--force" in sys.argv[3:])
    else:
        render(sys.argv[2], set(sys.argv[3:]))


if __name__ == "__main__":
    main()
