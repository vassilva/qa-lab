#!/usr/bin/env bash
# Waits until a container is "healthy" (the Dockerfile defines a HEALTHCHECK on /health).
#
# Usage: bash scripts/wait_healthy.sh <container-name> [max-seconds]
set -euo pipefail

CONTAINER="${1:?give the container name}"
TIMEOUT="${2:-120}"
elapsed=0

while (( elapsed < TIMEOUT )); do
  state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$CONTAINER" 2>/dev/null || echo missing)"
  case "$state" in
    healthy)
      echo "$CONTAINER is healthy (${elapsed}s)"
      exit 0 ;;
    unhealthy|exited|dead|missing)
      echo "ERROR: $CONTAINER is '$state'. Last log lines:" >&2
      docker logs --tail 40 "$CONTAINER" >&2 || true
      exit 1 ;;
  esac
  sleep 3
  elapsed=$(( elapsed + 3 ))
done

echo "ERROR: $CONTAINER did not become healthy within ${TIMEOUT}s (last state: $state)" >&2
docker logs --tail 40 "$CONTAINER" >&2 || true
exit 1
