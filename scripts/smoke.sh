#!/usr/bin/env bash
# Smoke test pós-deploy: verificação rápida de que o essencial funciona.
# Corre dentro do contentor da aplicação:  docker exec qa-lab-uat-app bash scripts/smoke.sh
#
# 1. /health responde UP e está ligado ao PostgreSQL
# 2. o Order Entry Gateway aceita uma ordem (e cancela-a, para não sujar o ambiente)
# 3. o Settlement responde (data de negócio e instruções)
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
pass() { echo "  [OK]    $*"; }
fail() { echo "  [FALHA] $*" >&2; exit 1; }

echo "Smoke test em $BASE_URL"

health="$(curl -fsS "$BASE_URL/health")" || fail "/health não responde"
[[ "$(jq -r .status <<<"$health")" == "UP" ]] || fail "estado do serviço: $(jq -r .status <<<"$health")"
[[ "$(jq -r .database <<<"$health")" == "postgresql" ]] || fail "não está ligado ao PostgreSQL"
pass "serviço UP · ambiente $(jq -r .environment <<<"$health") · versão $(jq -r .version <<<"$health")"

resp="$(curl -sS -X POST "$BASE_URL/api/orders" -H 'Content-Type: application/json' \
        -d '{"symbol":"NOS","side":"BUY","qty":1,"price":3.42}')"
order_id="$(jq -r .order.order_id <<<"$resp")"
status="$(jq -r .order.status <<<"$resp")"
case "$status" in
  NEW)
    curl -fsS -X DELETE "$BASE_URL/api/orders/$order_id" >/dev/null || fail "não consegui cancelar $order_id"
    pass "ordem de teste $order_id aceite e cancelada" ;;
  FILLED|PARTIALLY_FILLED)
    pass "ordem de teste $order_id aceite e executada ($status)" ;;
  *)
    fail "ordem de teste com estado inesperado: $resp" ;;
esac

bd="$(curl -fsS "$BASE_URL/api/business-date" | jq -r .business_date)" || fail "data de negócio indisponível"
curl -fsS "$BASE_URL/api/settlement/instructions" >/dev/null || fail "settlement não responde"
pass "settlement disponível · data de negócio $bd"

echo "Smoke test concluído com sucesso"
