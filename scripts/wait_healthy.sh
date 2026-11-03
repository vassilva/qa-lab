#!/usr/bin/env bash
# Espera até um contentor ficar "healthy" (o Dockerfile define um HEALTHCHECK a /health).
#
# Uso: bash scripts/wait_healthy.sh <nome-do-contentor> [segundos-máximos]
set -euo pipefail

CONTAINER="${1:?indica o nome do contentor}"
TIMEOUT="${2:-120}"
elapsed=0

while (( elapsed < TIMEOUT )); do
  state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$CONTAINER" 2>/dev/null || echo missing)"
  case "$state" in
    healthy)
      echo "$CONTAINER está saudável (${elapsed}s)"
      exit 0 ;;
    unhealthy|exited|dead|missing)
      echo "ERRO: $CONTAINER está '$state'. Últimas linhas do log:" >&2
      docker logs --tail 40 "$CONTAINER" >&2 || true
      exit 1 ;;
  esac
  sleep 3
  elapsed=$(( elapsed + 3 ))
done

echo "ERRO: $CONTAINER não ficou saudável em ${TIMEOUT}s (último estado: $state)" >&2
docker logs --tail 40 "$CONTAINER" >&2 || true
exit 1
