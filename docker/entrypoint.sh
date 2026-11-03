#!/usr/bin/env bash
# Arranque de um serviço do QA Lab. A variável SERVICE escolhe o serviço: trading (por omissão), settlement ou t2s.
set -euo pipefail

SERVICE="${SERVICE:-trading}"
LOG_DIR="${QA_LAB_LOG_DIR:-/var/log/qa-lab}"
mkdir -p "$LOG_DIR"

if [[ "${DATABASE_URL:-}" == postgres* ]]; then
  echo "[entrypoint] A aguardar pelo PostgreSQL..."
  for _ in $(seq 1 30); do
    pg_isready -d "${DATABASE_URL%/*}/postgres" >/dev/null 2>&1 && break
    sleep 1
  done
fi

echo "[entrypoint] ${SERVICE} · ambiente ${ENV_NAME:-local} · versão ${APP_VERSION:-local}"
case "$SERVICE" in
  trading)
    # Terminal Linux no browser (porta 7681), na pasta do projeto, como utilizador qa
    ttyd --port 7681 --writable --cwd /opt/qa-lab bash -l >> "$LOG_DIR/ttyd.log" 2>&1 &
    exec python -m app.server >> "$LOG_DIR/trading.out" 2>&1 ;;
  settlement)
    exec python -m app.settlement_service >> "$LOG_DIR/settlement.out" 2>&1 ;;
  t2s)
    exec python -m app.t2s_simulator >> "$LOG_DIR/t2s-sim.out" 2>&1 ;;
  *)
    echo "SERVICE desconhecido: $SERVICE (usa trading, settlement ou t2s)" >&2
    exit 2 ;;
esac
