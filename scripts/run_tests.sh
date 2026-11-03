#!/usr/bin/env bash
# Runs the automated tests and stores the reports (JUnit XML) in reports/
#
# Usage: bash scripts/run_tests.sh <unit|bdd>
#   unit  pytest tests of the components, in isolation (standalone), with a temporary database
#   bdd   BDD scenarios (behave) against the running environment
#
# Optional variables:
#   BASE_URL   environment under test (default http://localhost:8000)
#   BDD_TAGS   scenario filter, e.g. "@critical" or "@critical or @high" (default: all)
set -uo pipefail

SUITE="${1:-unit}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p reports
status=0

case "$SUITE" in
  unit)
    cov=()
    if python -c "import pytest_cov" 2>/dev/null; then
      cov=(--cov=app --cov-report=term --cov-report=xml:reports/coverage/coverage.xml)
    fi
    python -m pytest tests -q --junitxml=reports/pytest-unit.xml "${cov[@]}" || status=$?
    ;;
  bdd)
    rm -rf reports/behave
    args=(--junit --junit-directory reports/behave --format progress)
    if [[ -n "${BDD_TAGS:-}" ]]; then
      echo "Scenario filter: $BDD_TAGS"
      args+=(--tags "$BDD_TAGS")
    fi
    behave "${args[@]}" features || status=$?
    ;;
  *)
    echo "Usage: $0 <unit|bdd>" >&2
    exit 2
    ;;
esac

exit "$status"
