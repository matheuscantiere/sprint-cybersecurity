#!/usr/bin/env bash
# Restore a Postgres backup produced by backup_db.sh.
# Usage: bash scripts/restore_db.sh backups/fordspy_20260924_030000.sql.gz
set -euo pipefail

FILE="${1:?Usage: bash $0 <path-to-backup.sql.gz>}"

gunzip -c "$FILE" | docker compose exec -T db psql -U "${POSTGRES_USER:-fordspy}" "${POSTGRES_DB:-fordspy}"

echo "Restored ${FILE}"
