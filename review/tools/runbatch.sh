#!/usr/bin/env bash
# runbatch.sh QUERIES.tsv — run reviewer pre-search queries with pacing.
# TSV lines: <id> TAB <repos|code> TAB <query>; '#' lines are comments.
# Each id logs to review/evidence/search/presearch-<id>.log via ghsearch.sh.
# Pacing: 5 s after repo queries, 12 s after code queries (half the shared budget).
cd "$(dirname "$0")/../.." || exit 1
grep -v '^#' "$1" | grep -v '^\s*$' | while IFS=$'\t' read -r id kind q; do
  first=$(review/tools/ghsearch.sh "$kind" "review/evidence/search/presearch-$id.log" "$q"); rc=$?
  printf '%-4s %-5s rc=%s %-28s %s\n' "$id" "$kind" "$rc" "$first" "$q"
  if [ "$rc" -ne 0 ]; then sleep 60; fi
  [ "$kind" = code ] && sleep 12 || sleep 5
done
echo BATCH_DONE
