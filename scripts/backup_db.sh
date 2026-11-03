#!/usr/bin/env bash
# Backup da base de dados do ambiente (pg_dump comprimido), com rotação dos backups antigos.
# Corre dentro do contentor da aplicação:  docker exec qa-lab-uat-app bash scripts/backup_db.sh
#
# Variáveis: DATABASE_URL (obrigatória), BACKUP_DIR (por omissão /var/log/qa-lab/backups), KEEP (por omissão 7)
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL não definida (este script corre dentro do contentor QA ou UAT)}"
BACKUP_DIR="${BACKUP_DIR:-${QA_LAB_LOG_DIR:-/var/log/qa-lab}/backups}"
KEEP="${KEEP:-7}"
ENV_LABEL="$(echo "${ENV_NAME:-local}" | tr '[:upper:]' '[:lower:]')"
FILE="$BACKUP_DIR/qa_lab_${ENV_LABEL}_$(date +%Y%m%d_%H%M%S).sql.gz"

mkdir -p "$BACKUP_DIR"
echo "A criar backup de ${ENV_LABEL^^} em $FILE"
pg_dump --no-owner --no-privileges "$DATABASE_URL" | gzip > "$FILE"

# Verificação: o ficheiro não pode estar vazio e tem de conter as tabelas principais
if [[ ! -s "$FILE" ]] || ! gunzip -c "$FILE" | grep -q "CREATE TABLE public.trades"; then
  echo "ERRO: backup inválido: $FILE" >&2
  exit 1
fi
echo "Backup OK: $(du -h "$FILE" | cut -f1)"

# Rotação: mantém só os KEEP mais recentes
ls -1t "$BACKUP_DIR"/qa_lab_"${ENV_LABEL}"_*.sql.gz 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do
  echo "A apagar backup antigo: $old"
  rm -f -- "$old"
done
