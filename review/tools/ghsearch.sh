#!/usr/bin/env bash
# ghsearch.sh — logged GitHub search for the lowlevel-lab reviewer lane.
#
# usage: review/tools/ghsearch.sh repos|code LOGFILE QUERY...
#
# Calls the REST search API through `gh api` (not `gh search --json`, which
# drops total_count) and appends one block per query to LOGFILE:
#
#   ### <UTC time> <kind> q=<exact query string>
#   exit=<gh exit code>
#   total_count=<n> incomplete=<true|false>
#     <top hits, at most 10>
#
# A non-zero exit (HTTP 403/429 rate limit, 422 bad query) is logged as such
# and is never to be read as "0 hits". Code search is the legacy REST index
# (default branch only, files < 384 KB, punctuation ignored): treat its
# silence as weak evidence. Pacing is the caller's job — the token is shared
# with the author lane (30 search/min, 10 code_search/min).
set -u
kind=${1:?repos|code}; log=${2:?logfile}; shift 2; q="$*"
case $kind in
  repos) ep=search/repositories
         f='"total_count=\(.total_count) incomplete=\(.incomplete_results)", (.items[] | "  \(.full_name)  *\(.stargazers_count)  created=\(.created_at[:10])  pushed=\(.pushed_at[:10])  \((.description // "") | .[:120])")' ;;
  code)  ep=search/code
         f='"total_count=\(.total_count) incomplete=\(.incomplete_results)", (.items[] | "  \(.repository.full_name)  \(.path)")' ;;
  *) echo "kind must be repos|code" >&2; exit 2 ;;
esac
ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
out=$(gh api -X GET "$ep" -f q="$q" -f per_page=10 --jq "$f" 2>&1); rc=$?
printf '### %s %s q=%s\nexit=%s\n%s\n\n' "$ts" "$kind" "$q" "$rc" "$out" >> "$log"
printf '%s\n' "$out" | head -1
exit $rc
