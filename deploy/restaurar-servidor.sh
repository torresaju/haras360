#!/usr/bin/env bash
# Reconstrói o Haras360 em uma VM Ubuntu nova a partir de um backup completo.
# Uso:
#   tar xzf haras360-backup-AAAAMMDD-HHMMSS.tar.gz
#   cd haras360-backup-AAAAMMDD-HHMMSS
#   sudo ./restaurar-servidor.sh .
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Rode como administrador: sudo $0 <pasta-do-backup>" >&2; exit 1; }
DIR="$(readlink -f "${1:-.}")"
[ -f "$DIR/banco.sql.gz" ] && [ -d "$DIR/config/etc-haras360" ] || { echo "Pasta de backup inválida: $DIR" >&2; exit 1; }
PAC="$(ls -1 "$DIR"/haras360-[0-9]*.tar.gz 2>/dev/null | head -1)"
[ -n "$PAC" ] || { echo "O backup não traz o pacote da versão em uso (haras360-X.Y.Z.tar.gz)." >&2; exit 1; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
tar -xzf "$PAC" -C "$TMP" --no-same-owner
RAIZ="$(ls -1d "$TMP"/haras360-*/ | head -1)"
echo "Restaurando a versão $(cat "$RAIZ/VERSION") a partir de $(basename "$DIR")"
H360_RESTAURAR="$DIR" bash "$RAIZ/deploy/instalar-servidor.sh"
echo "Restauração concluída. Os usuários entram com as mesmas senhas e o mesmo 2FA de antes."
