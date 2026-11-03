#!/usr/bin/env bash
# Starts a QA Lab service. The SERVICE variable picks the service: trading (default), settlement or t2s.
set -euo pipefail

SERVICE="${SERVICE:-trading}"
LOG_DIR="${QA_LAB_LOG_DIR:-/var/log/qa-lab}"
mkdir -p "$LOG_DIR"

if [[ "${DATABASE_URL:-}" == postgres* ]]; then
  echo "[entrypoint] Waiting for PostgreSQL..."
  for _ in $(seq 1 30); do
    pg_isready -d "${DATABASE_URL%/*}/postgres" >/dev/null 2>&1 && break
    sleep 1
  done
fi

echo "[entrypoint] ${SERVICE} · environment ${ENV_NAME:-local} · version ${APP_VERSION:-local}"
case "$SERVICE" in
  trading)
    # Linux terminal in the browser (port 7681), in the project folder, as user qa
    ttyd --port 7681 --writable --cwd /opt/qa-lab bash -l >> "$LOG_DIR/ttyd.log" 2>&1 &
    exec python -m app.server >> "$LOG_DIR/trading.out" 2>&1 ;;
  settlement)
    exec python -m app.settlement_service >> "$LOG_DIR/settlement.out" 2>&1 ;;
  t2s)
    exec python -m app.t2s_simulator >> "$LOG_DIR/t2s-sim.out" 2>&1 ;;
  *)
    echo "Unknown SERVICE: $SERVICE (use trading, settlement or t2s)" >&2
    exit 2 ;;
esac
