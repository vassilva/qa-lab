#!/usr/bin/env bash
# Arranque do contentor: espera pela base de dados, abre o terminal web e arranca a aplicação.
set -euo pipefail

LOG_DIR="${QA_LAB_LOG_DIR:-/var/log/qa-lab}"
mkdir -p "$LOG_DIR"

if [[ "${DATABASE_URL:-}" == postgres* ]]; then
  echo "[entrypoint] A aguardar pelo PostgreSQL..."
  for _ in $(seq 1 30); do
    pg_isready -d "$DATABASE_URL" >/dev/null 2>&1 && break
    sleep 1
  done
fi

# Terminal Linux no browser (porta 7681 dentro do contentor), na pasta do projeto, como utilizador qa
ttyd --port 7681 --writable --cwd /opt/qa-lab bash -l >> "$LOG_DIR/ttyd.log" 2>&1 &

echo "[entrypoint] Ambiente ${ENV_NAME:-local} · versão ${APP_VERSION:-local} · a arrancar a aplicação"
exec python -m app.server >> "$LOG_DIR/server.log" 2>&1
