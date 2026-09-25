#!/usr/bin/env bash
# Daily Postgres backup — RPO 24h.
# Usage: bash scripts/backup_db.sh  (reads POSTGRES_USER/DB from .env via docker compose)
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

docker compose exec -T db pg_dump -U "${POSTGRES_USER:-fordspy}" "${POSTGRES_DB:-fordspy}" \
  | gzip > "${BACKUP_DIR}/fordspy_${TIMESTAMP}.sql.gz"

echo "Backup written to ${BACKUP_DIR}/fordspy_${TIMESTAMP}.sql.gz"

find "$BACKUP_DIR" -name "*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
