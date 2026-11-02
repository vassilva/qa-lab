#!/usr/bin/env bash
# Arranque do contentor qa-lab: espera pela base de dados, abre o terminal web e arranca a aplicação.
set -euo pipefail

LOG_DIR="${QA_LAB_LOG_DIR:-/var/log/qa-lab}"
mkdir -p "$LOG_DIR"

if [[ "${DATABASE_URL:-}" == postgres* ]]; then
  echo "[entrypoint] A aguardar pelo PostgreSQL..."
  for i in $(seq 1 30); do
    if pg_isready -d "$DATABASE_URL" >/dev/null 2>&1; then
      echo "[entrypoint] PostgreSQL disponível."
      break
    fi
    sleep 1
  done
fi

# Terminal Linux no browser (http://localhost:7681), sempre na pasta do projeto
echo "[entrypoint] A abrir o terminal web na porta 7681"
ttyd --port 7681 --writable --cwd /opt/qa-lab bash -l >> "$LOG_DIR/ttyd.log" 2>&1 &

echo "[entrypoint] A arrancar a aplicação na porta ${PORT:-8000} (modo desafio: ${QA_LAB_CHALLENGE:-0})"
exec python -m app.server >> "$LOG_DIR/server.log" 2>&1
