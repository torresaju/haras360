#!/usr/bin/env bash
# Gera haras360-X.Y.Z.tar.gz a partir de um commit do repositório.
# Uso: deploy/gerar-pacote.sh [commit] [pasta-de-saída]
# Com APK_DIR apontando para a pasta do build Android (haras360.apk e versao.json), o APK
# entra no pacote e passa a ser servido pelo servidor em /app/haras360.apk.
# A versão vem do arquivo VERSION do commit. O pacote leva um manifesto SHA256SUMS.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."
REPO="$(pwd)"

COMMIT="${1:-HEAD}"
SAIDA="$(readlink -f "${2:-dist}")"
VERSAO="$(git show "$COMMIT:VERSION" | tr -d ' \r\n')"
echo "$VERSAO" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || { echo "VERSION inválido: $VERSAO" >&2; exit 1; }
NOME="haras360-$VERSAO"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git archive --format=tar --prefix="$NOME/" "$COMMIT" VERSION README.md backend deploy docs/HISTORICO.md | tar -x -C "$TMP"
cd "$TMP/$NOME"

# Sem arquivos de desenvolvimento no pacote.
find . -name '__pycache__' -prune -exec rm -rf {} +
rm -f deploy/assinar-pacote.py.bak

# Conferência mínima: páginas montadas presentes e chave pública, se houver, em formato PEM.
for p in entrar gestor campo admin ajuda; do [ -s "backend/app/static/$p.html" ] || { echo "Falta backend/app/static/$p.html (rode python web/build.py)" >&2; exit 1; }; done
# A chave pública de atualização precisa ir no pacote: sem ela, o servidor recusa todas as atualizações.
[ -f deploy/chave-publica.pem ] || { echo "deploy/chave-publica.pem ausente do commit (confira o .gitignore)" >&2; exit 1; }
grep -q "BEGIN PUBLIC KEY" deploy/chave-publica.pem || { echo "deploy/chave-publica.pem inválida" >&2; exit 1; }

if [ -n "${APK_DIR:-}" ]; then
  [ -s "$APK_DIR/haras360.apk" ] && [ -s "$APK_DIR/versao.json" ] || { echo "APK_DIR sem haras360.apk e versao.json" >&2; exit 1; }
  mkdir -p backend/app/static/app
  cp "$APK_DIR/haras360.apk" "$APK_DIR/versao.json" backend/app/static/app/
  echo "APK incluído: $(cat backend/app/static/app/versao.json)"
fi

echo "$(git -C "$REPO" rev-parse "$COMMIT" 2>/dev/null || echo "$COMMIT")" > COMMIT
find . -type f ! -name SHA256SUMS | sed 's#^\./##' | LC_ALL=C sort | while read -r f; do sha256sum "$f"; done > SHA256SUMS

mkdir -p "$SAIDA"
cd "$TMP"
tar --owner=0 --group=0 --numeric-owner --mtime="@$(git -C "$REPO" log -1 --format=%ct "$COMMIT" 2>/dev/null || date +%s)" -czf "$SAIDA/$NOME.tar.gz" "$NOME"
( cd "$SAIDA" && sha256sum "$NOME.tar.gz" > "$NOME.tar.gz.sha256" )
echo "Pacote: $SAIDA/$NOME.tar.gz"
cat "$SAIDA/$NOME.tar.gz.sha256"
