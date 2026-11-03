#!/usr/bin/env bash
# Fecho do dia (End of Day) pela linha de comandos, como um job batch de um sistema financeiro:
# 1) verifica o serviço, 2) corre o EOD, 3) valida o relatório CSV, 4) mostra o resumo.
#
# Uso: bash scripts/eod.sh            (dentro do contentor QA ou UAT)
# Códigos de saída: 0 = OK · 1 = serviço indisponível · 2 = EOD falhou · 3 = relatório em falta ou inconsistente
set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EOD_DIR="${QA_LAB_LOG_DIR:-/var/log/qa-lab}/eod"

curl -fsS "$BASE_URL/health" >/dev/null || { echo "ERRO: serviço indisponível em $BASE_URL" >&2; exit 1; }

result="$(curl -fsS -X POST "$BASE_URL/api/eod")" || { echo "ERRO: o fecho do dia falhou" >&2; exit 2; }
bd="$(jq -r .business_date <<<"$result")"
settled="$(jq -r .settled <<<"$result")"
pending="$(jq -r .not_settled <<<"$result")"
next_bd="$(jq -r .next_business_date <<<"$result")"

report="$EOD_DIR/settlement_${bd//-/}.csv"
if [[ ! -f "$report" ]]; then
  echo "ERRO: relatório $report não encontrado" >&2
  exit 3
fi
# O relatório tem de ter uma linha por instrução tratada (+1 de cabeçalho)
rows=$(( $(wc -l < "$report") - 1 ))
if (( rows != settled + pending )); then
  echo "ERRO: o relatório tem $rows linhas, mas o EOD tratou $((settled + pending)) instruções" >&2
  exit 3
fi

echo "EOD de $bd concluído: $settled liquidadas · $pending por liquidar · relatório $report"
echo "Próxima data de negócio: $next_bd"
