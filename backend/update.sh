#!/usr/bin/env bash
# Aplica uma nova versão do Haras360 mantendo .env, banco e fotos.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
[ "$(id -u)" -eq 0 ] || { echo "Rode com sudo: sudo ./update.sh"; exit 1; }
[ -f .env ] || { echo "Instalação não encontrada. Rode primeiro o install.sh"; exit 1; }
PORTA="$(grep -E '^PORTA=' .env | cut -d= -f2)"
echo "==> Backup antes da atualização"
./backup.sh
echo "==> Reconstruindo e reiniciando"
docker compose build
docker compose up -d
for i in $(seq 1 60); do
  curl -fsS "http://127.0.0.1:${PORTA}/api/saude" && { echo; echo "==> Atualizado"; exit 0; }
  sleep 2
done
docker compose logs --tail 40
echo "A aplicação não respondeu após a atualização. Veja os logs acima." >&2
exit 1
