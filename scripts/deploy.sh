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
echo "==> ${ENV_NAME^^} is running version $VERSION"
