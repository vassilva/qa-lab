#!/usr/bin/env bash
# Deploys a version (an image that is already built) to the QA or UAT environment.
#
# Usage:   bash scripts/deploy.sh <qa|uat> <version>
# Example: bash scripts/deploy.sh uat 0.2.0-1a2b3c4
#
# Used by Jenkins. The image qa-lab:<version> must exist (docker build -t qa-lab:<version> .).
set -euo pipefail

ENV_NAME="${1:-}"
VERSION="${2:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "$ENV_NAME" != "qa" && "$ENV_NAME" != "uat" ]] || [[ -z "$VERSION" ]]; then
  echo "Usage: $0 <qa|uat> <version>" >&2
  exit 2
fi

export APP_IMAGE="qa-lab:${VERSION}"
export APP_VERSION="$VERSION"

if ! docker image inspect "$APP_IMAGE" >/dev/null 2>&1; then
  echo "ERROR: image $APP_IMAGE does not exist. Build it first: docker build -t $APP_IMAGE ." >&2
  exit 1
fi

docker network inspect qa-lab-net >/dev/null 2>&1 || docker network create qa-lab-net >/dev/null

# Migration: old versions used the groups "qa-lab-qa" / "qa-lab-uat". Remove them once, if they exist.
if [[ -n "$(docker ps -aq --filter "label=com.docker.compose.project=qa-lab-${ENV_NAME}")" ]]; then
  echo "==> Removing the old group qa-lab-${ENV_NAME} (now called ${ENV_NAME})"
  docker compose -p "qa-lab-${ENV_NAME}" -f "$ROOT/docker-compose.env.yml" --env-file "$ROOT/envs/${ENV_NAME}.env" down -v
fi

# Challenge mode (hidden defects): only allowed in QA
export QA_LAB_CHALLENGE="${QA_LAB_CHALLENGE:-0}"
if [[ "$ENV_NAME" == "uat" ]]; then
  QA_LAB_CHALLENGE=0
fi
[[ "$QA_LAB_CHALLENGE" == "1" ]] && echo "==> WARNING: challenge mode ON in ${ENV_NAME^^} (hidden defects active)"

echo "==> Deploying version $VERSION to ${ENV_NAME^^}"
docker compose -p "${ENV_NAME}" \
  --env-file "$ROOT/envs/${ENV_NAME}.env" \
  -f "$ROOT/docker-compose.env.yml" \
  up -d --remove-orphans

for svc in app settlement t2s; do
  bash "$ROOT/scripts/wait_healthy.sh" "qa-lab-${ENV_NAME}-${svc}" 180
done

# Readiness (DEF-015): "healthy" means the service answers; Settlement is only READY when its Kafka consumer
# has been assigned the partition. After a redeploy that can take 10-20 s (Kafka waits for the old consumer to expire).
SETTLEMENT="qa-lab-${ENV_NAME}-settlement"
for i in $(seq 1 90); do
  if [[ "$(docker exec "$SETTLEMENT" curl -fsS localhost:8001/health 2>/dev/null | jq -r .consumer_ready)" == "true" ]]; then
    echo "==> Settlement consumer ready (${i}s)"
    break
  fi
  if [[ "$i" == "90" ]]; then
    echo "ERROR: the Settlement consumer has no Kafka partition after 90 s. Last log lines:" >&2
    docker logs --tail 20 "$SETTLEMENT" >&2 || true
    exit 1
  fi
  sleep 1
done

# kafka-init is a one-off job (it creates the Kafka topics and exits). Check that it succeeded, then remove it
# so the environment shows only long-running services (fully green group in Docker Desktop).
INIT="qa-lab-${ENV_NAME}-kafka-init"
if docker container inspect "$INIT" >/dev/null 2>&1; then
  INIT_EXIT="$(docker inspect -f '{{.State.ExitCode}}' "$INIT")"
  if [[ "$INIT_EXIT" != "0" ]]; then
    echo "ERROR: $INIT exited with code $INIT_EXIT (Kafka topics not created). Log:" >&2
    docker logs "$INIT" >&2 || true
    exit 1
  fi
  echo "==> Kafka topics: $(docker exec "qa-lab-${ENV_NAME}-kafka" /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list | tr '\n' ' ')"
  docker rm "$INIT" >/dev/null
  echo "==> $INIT finished successfully and was removed"
fi
echo "==> ${ENV_NAME^^} is running version $VERSION"
