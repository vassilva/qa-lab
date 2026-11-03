#!/usr/bin/env bash
# Usado pelo Jenkins: corre os testes unitários e de API dentro da imagem acabada de construir
# (num contentor temporário, sem tocar nos ambientes) e copia os relatórios para reports/unit/.
#
# Uso: bash scripts/ci_unit_tests.sh <imagem>
set -uo pipefail

IMAGE="${1:?indica a imagem, ex.: qa-lab:0.2.0-1a2b3c4}"
NAME="qa-lab-unit-$$"

docker run --name "$NAME" --entrypoint bash "$IMAGE" scripts/run_tests.sh unit
status=$?
mkdir -p reports/unit
docker cp "$NAME":/opt/qa-lab/reports/. reports/unit/ || true
docker rm -f "$NAME" >/dev/null
exit "$status"
