#!/usr/bin/env bash
# Roda os testes de integração no emulador (chamado pelo workflow App Android):
# primeiro o caseiro (vínculo por código), depois o gestor (e-mail, senha e 2FA, v1.5.0).
set -euo pipefail
cd "$(dirname "$0")/.."
CODIGO="$(cat /tmp/codigo-vinculo)"
VERSAO="$(tr -d ' \r\n' < ../VERSION)"
flutter drive --driver=test_driver/integration_test.dart --target=integration_test/app_test.dart \
  --dart-define=SERVIDOR=http://10.0.2.2:8090 --dart-define=CODIGO="$CODIGO" \
  --dart-define=APP_VERSAO="$VERSAO" --dart-define=APP_CODIGO=1
# um perfil por celular: o gestor começa num app limpo
adb uninstall br.com.haras360.campo >/dev/null 2>&1 || true
flutter drive --driver=test_driver/integration_test.dart --target=integration_test/gestor_test.dart \
  --dart-define=SERVIDOR=http://10.0.2.2:8090 --dart-define=EMAIL=gestor@demonstracao.local --dart-define=SENHA=demonstracao123 \
  --dart-define=SEGREDO="$(cat /tmp/segredo-gestor)" --dart-define=SEM_BLOQUEIO=true \
  --dart-define=APP_VERSAO="$VERSAO" --dart-define=APP_CODIGO=1
