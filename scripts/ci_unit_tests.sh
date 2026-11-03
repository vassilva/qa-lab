#!/usr/bin/env bash
# Used by Jenkins: runs the unit and API tests inside the freshly built image
# (in a temporary container, without touching the environments) and copies the reports to reports/unit/.
#
# Usage: bash scripts/ci_unit_tests.sh <image>
set -uo pipefail

IMAGE="${1:?give the image, e.g. qa-lab:0.2.0-1a2b3c4}"
NAME="qa-lab-unit-$$"

docker run --name "$NAME" --entrypoint bash "$IMAGE" scripts/run_tests.sh unit
status=$?
mkdir -p reports/unit
docker cp "$NAME":/opt/qa-lab/reports/. reports/unit/ || true
docker rm -f "$NAME" >/dev/null
exit "$status"
