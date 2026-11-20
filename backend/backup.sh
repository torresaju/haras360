#!/usr/bin/env bash
# Backup do banco e das fotos do Haras360. Mantém os últimos 14 dias.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
set -a; . ./.env; set +a
mkdir -p backups
QUANDO="$(date +%Y%m%d-%H%M)"
docker compose exec -T haras360 python -m app.backup_db \
  | gzip > "backups/banco-${QUANDO}.sql.gz"
tar czf "backups/fotos-${QUANDO}.tar.gz" -C dados fotos
chmod 600 backups/*
find backups -type f -mtime +14 -delete
echo "$(date '+%d/%m/%Y %H:%M') backup ok: banco-${QUANDO}.sql.gz e fotos-${QUANDO}.tar.gz"
