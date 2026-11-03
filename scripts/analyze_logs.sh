#!/usr/bin/env bash
# Summary of the service logs: activity by component, rejections by reason, trades by symbol,
# errors and failed settlements. Useful to investigate defects and for the daily report.
#
# Usage: bash scripts/analyze_logs.sh [log-file] [YYYY-MM-DD]
#        (default: every *.log in /var/log/qa-lab — Trading, Settlement and T2S — all dates)
set -euo pipefail

LOG_DIR="${QA_LAB_LOG_DIR:-/var/log/qa-lab}"
if [[ -n "${1:-}" ]]; then LOGS=("$1"); else LOGS=("$LOG_DIR"/*.log); fi
DAY="${2:-}"

for f in "${LOGS[@]}"; do
  [[ -r "$f" ]] || { echo "ERROR: cannot read log $f" >&2; exit 1; }
done

# Filter by date, if given (lines start with YYYY-MM-DD)
lines() { if [[ -n "$DAY" ]]; then cat "${LOGS[@]}" | grep "^$DAY" || true; else cat "${LOGS[@]}"; fi; }

section() { printf '\n== %s\n' "$1"; }

echo "Analysis of ${LOGS[*]}${DAY:+ (day $DAY)} · $(lines | wc -l) lines"

section "Lines by component and level"
lines | awk '{print $4, $3}' | sort | uniq -c | sort -rn

section "Rejected orders by reason"
lines | grep "REJECTED: " | grep "\[OEG\]" | sed -E 's/.*REJECTED: ([^(]+) \(.*/\1/' | sort | uniq -c | sort -rn || true

section "Trades by symbol (number of trades · shares)"
lines | grep -E "\[ME\] Trade " | awk '{sym=$8; qty=$7; n[sym]++; q[sym]+=qty} END {for (s in n) printf "%-6s %4d trades · %8d shares\n", s, n[s], q[s]}' | sort || true

section "Instructions not settled on their intended date (on hold)"
lines | grep "NOT settled" || echo "none"

section "Instructions that failed at T2S"
lines | grep "FAILED at T2S" || echo "none"

section "Events rejected by the contract (dead letter queue)"
lines | grep "Event REJECTED" || echo "none"

section "Errors"
lines | grep -E " (ERROR|CRITICAL) " || echo "none"
