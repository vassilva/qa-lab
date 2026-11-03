#!/usr/bin/env bash
# Backup of the environment's database (compressed pg_dump), with rotation of old backups.
# Runs inside a service container:
#   docker exec qa-lab-uat-app bash scripts/backup_db.sh          → Trading database (qa_lab)
#   docker exec qa-lab-uat-settlement bash scripts/backup_db.sh   → Settlement database (settlement)
#
# Variables: DATABASE_URL (required), BACKUP_DIR (default /var/log/qa-lab/backups), KEEP (default 7)
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is not set (this script runs inside the QA or UAT containers)}"
BACKUP_DIR="${BACKUP_DIR:-${QA_LAB_LOG_DIR:-/var/log/qa-lab}/backups}"
KEEP="${KEEP:-7}"
ENV_LABEL="$(echo "${ENV_NAME:-local}" | tr '[:upper:]' '[:lower:]')"
DB_NAME="${DATABASE_URL##*/}"
FILE="$BACKUP_DIR/${DB_NAME}_${ENV_LABEL}_$(date +%Y%m%d_%H%M%S).sql.gz"

mkdir -p "$BACKUP_DIR"
echo "Creating backup of ${DB_NAME} (${ENV_LABEL^^}) in $FILE"
pg_dump --no-owner --no-privileges "$DATABASE_URL" | gzip > "$FILE"

# Check: the file must not be empty and must contain the tables
if [[ ! -s "$FILE" ]] || ! gunzip -c "$FILE" | grep -q "CREATE TABLE public."; then
  echo "ERROR: invalid backup: $FILE" >&2
  exit 1
fi
echo "Backup OK: $(du -h "$FILE" | cut -f1)"

# Rotation: keep only the KEEP most recent backups of this database
ls -1t "$BACKUP_DIR"/"${DB_NAME}"_"${ENV_LABEL}"_*.sql.gz 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do
  echo "Deleting old backup: $old"
  rm -f -- "$old"
done
