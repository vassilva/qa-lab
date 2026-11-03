#!/usr/bin/env bash
# End of Day (EOD) from the command line, like a batch job in a financial system:
# 1) checks the service, 2) runs the EOD, 3) validates the CSV report, 4) prints the summary.
#
# Usage: bash scripts/eod.sh            (inside the QA or UAT Trading container)
# Exit codes: 0 = OK · 1 = service unavailable · 2 = EOD failed · 3 = report missing or inconsistent
set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EOD_DIR="${QA_LAB_LOG_DIR:-/var/log/qa-lab}/eod"

curl -fsS "$BASE_URL/health" >/dev/null || { echo "ERROR: service unavailable at $BASE_URL" >&2; exit 1; }

result="$(curl -fsS -X POST "$BASE_URL/api/eod")" || { echo "ERROR: the end of day failed" >&2; exit 2; }
bd="$(jq -r .business_date <<<"$result")"
settled="$(jq -r .settled <<<"$result")"
pending="$(jq -r .not_settled <<<"$result")"
next_bd="$(jq -r .next_business_date <<<"$result")"
t2s="$(jq -r .t2s <<<"$result")"

report="$EOD_DIR/settlement_${bd//-/}.csv"
if [[ ! -f "$report" ]]; then
  echo "ERROR: report $report not found" >&2
  exit 3
fi
# The report must have one row per instruction processed (+1 header row)
rows=$(( $(wc -l < "$report") - 1 ))
if (( rows != settled + pending )); then
  echo "ERROR: the report has $rows rows, but the EOD processed $((settled + pending)) instructions" >&2
  exit 3
fi

echo "EOD for $bd finished: $settled settled · $pending not settled · T2S: $t2s · report $report"
echo "Next business date: $next_bd"
