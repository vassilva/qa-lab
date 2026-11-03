#!/usr/bin/env bash
# Corre os testes automáticos e guarda os relatórios (JUnit XML) em reports/
#
# Uso: bash scripts/run_tests.sh <unit|bdd>
#   unit  testes pytest dos componentes, isolados (standalone), com base de dados temporária
#   bdd   cenários BDD (behave) contra o ambiente em execução
#
# Variáveis opcionais:
#   BASE_URL   ambiente a testar (por omissão http://localhost:8000)
#   BDD_TAGS   filtro de cenários, ex.: "@critico" ou "@critico or @alto" (por omissão: todos)
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
      echo "Filtro de cenários: $BDD_TAGS"
      args+=(--tags "$BDD_TAGS")
    fi
    behave "${args[@]}" features || status=$?
    ;;
  *)
    echo "Uso: $0 <unit|bdd>" >&2
    exit 2
    ;;
esac

exit "$status"
