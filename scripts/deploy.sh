#!/usr/bin/env bash
# Faz o deploy de uma versão (imagem já construída) no ambiente QA ou UAT.
#
# Uso:    bash scripts/deploy.sh <qa|uat> <versão>
# Exemplo: bash scripts/deploy.sh uat 0.2.0-1a2b3c4
#
# Usado pelo Jenkins. A imagem qa-lab:<versão> tem de existir (docker build -t qa-lab:<versão> .).
set -euo pipefail

ENV_NAME="${1:-}"
VERSION="${2:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "$ENV_NAME" != "qa" && "$ENV_NAME" != "uat" ]] || [[ -z "$VERSION" ]]; then
  echo "Uso: $0 <qa|uat> <versão>" >&2
  exit 2
fi

export APP_IMAGE="qa-lab:${VERSION}"
export APP_VERSION="$VERSION"

if ! docker image inspect "$APP_IMAGE" >/dev/null 2>&1; then
  echo "ERRO: a imagem $APP_IMAGE não existe. Constrói-a primeiro: docker build -t $APP_IMAGE ." >&2
  exit 1
fi

docker network inspect qa-lab-net >/dev/null 2>&1 || docker network create qa-lab-net >/dev/null

echo "==> Deploy da versão $VERSION no ambiente ${ENV_NAME^^}"
docker compose -p "qa-lab-${ENV_NAME}" \
  --env-file "$ROOT/envs/${ENV_NAME}.env" \
  -f "$ROOT/docker-compose.env.yml" \
  up -d --remove-orphans

bash "$ROOT/scripts/wait_healthy.sh" "qa-lab-${ENV_NAME}-app" 120
echo "==> ${ENV_NAME^^} a correr a versão $VERSION"
