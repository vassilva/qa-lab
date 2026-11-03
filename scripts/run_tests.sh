#!/usr/bin/env bash
# Corre os testes automáticos e guarda os relatórios (JUnit XML) em reports/
#
# Uso: bash scripts/run_tests.sh <unit|bdd>
#   unit  testes pytest dos componentes, isolados (standalone), com base de dados temporária
#   bdd   cenários BDD (behave) contra o ambiente em execução (BASE_URL, por omissão localhost:8000)
set -uo pipefail

SUITE="${1:-unit}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p reports
status=0

case "$SUITE" in
  unit)
    python -m pytest tests -q --junitxml=reports/pytest-unit.xml || status=$?
    ;;
  bdd)
    if [[ -d features/steps ]]; then
      behave --junit --junit-directory reports/behave --format progress features || status=$?
    else
      echo "BDD: os cenários existem em features/, mas os passos automatizados chegam no Épico 1."
    fi
    ;;
  *)
    echo "Uso: $0 <unit|bdd>" >&2
    exit 2
    ;;
esac

exit "$status"
