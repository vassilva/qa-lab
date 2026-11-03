#!/usr/bin/env bash
# Post-deployment smoke test: a quick check that the essentials work.
# Runs inside the application container:  docker exec qa-lab-uat-app bash scripts/smoke.sh
#
# 1. /health responds UP and is connected to PostgreSQL
# 2. the Order Entry Gateway accepts an order (and cancels it, to keep the environment clean)
# 3. the integration is healthy: bus (Kafka), Settlement (consumer ready) and the T2S simulator
# 4. Settlement responds (business date and instructions)
# 5. Each database has exactly the expected tables: no leftovers from older versions (DEF-016)
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
pass() { echo "  [OK]    $*"; }
fail() { echo "  [FAIL]  $*" >&2; exit 1; }

echo "Smoke test on $BASE_URL"

health="$(curl -fsS "$BASE_URL/health")" || fail "/health does not respond"
[[ "$(jq -r .status <<<"$health")" == "UP" ]] || fail "service status: $(jq -r .status <<<"$health")"
[[ "$(jq -r .database <<<"$health")" == "postgresql" ]] || fail "not connected to PostgreSQL"
pass "service UP · environment $(jq -r .environment <<<"$health") · version $(jq -r .version <<<"$health")"

resp="$(curl -sS -X POST "$BASE_URL/api/orders" -H 'Content-Type: application/json' \
        -d '{"symbol":"NOS","side":"BUY","qty":1,"price":3.42}')"
order_id="$(jq -r .order.order_id <<<"$resp")"
status="$(jq -r .order.status <<<"$resp")"
case "$status" in
  NEW)
    curl -fsS -X DELETE "$BASE_URL/api/orders/$order_id" >/dev/null || fail "could not cancel $order_id"
    pass "test order $order_id accepted and cancelled" ;;
  FILLED|PARTIALLY_FILLED)
    pass "test order $order_id accepted and executed ($status)" ;;
  *)
    fail "test order with unexpected status: $resp" ;;
esac

integ="$(curl -fsS "$BASE_URL/api/integration")" || fail "integration status unavailable"
[[ "$(jq -r .bus_ok <<<"$integ")" == "true" ]] || fail "bus $(jq -r .bus <<<"$integ") unavailable"
[[ "$(jq -r .settlement.status <<<"$integ")" == "UP" ]] || fail "Settlement: $(jq -c .settlement <<<"$integ")"
[[ "$(jq -r .settlement.consumer_ready <<<"$integ")" == "true" ]] || fail "Settlement consumer not ready (no partition assigned yet)"
[[ "$(jq -r .t2s.mode <<<"$integ")" != "no response" ]] || fail "T2S simulator does not respond"
pass "integration: bus $(jq -r .bus <<<"$integ") · Settlement UP, consumer ready · T2S in $(jq -r .t2s.mode <<<"$integ") mode · outbox pending $(jq -r .outbox.pending <<<"$integ")"

bd="$(curl -fsS "$BASE_URL/api/business-date" | jq -r .business_date)" || fail "business date unavailable"
curl -fsS "$BASE_URL/api/settlement/instructions" >/dev/null || fail "settlement does not respond"
pass "settlement available · business date $bd"

[[ "$(jq -r .schema_ok <<<"$health")" == "true" ]] \
  || fail "Trading database schema: unexpected $(jq -c .unexpected_tables <<<"$health") · missing $(jq -c .missing_tables <<<"$health")"
[[ "$(jq -r .settlement.schema_ok <<<"$integ")" == "true" ]] \
  || fail "Settlement database schema: unexpected $(jq -c .settlement.unexpected_tables <<<"$integ") · missing $(jq -c .settlement.missing_tables <<<"$integ")"
pass "database schemas as expected (Trading and Settlement)"

echo "Smoke test passed"
