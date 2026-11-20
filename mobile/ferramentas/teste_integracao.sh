#!/usr/bin/env bash
# Roda o teste de integração no emulador (chamado pelo workflow App Android).
set -euo pipefail
cd "$(dirname "$0")/.."
CODIGO="$(cat /tmp/codigo-vinculo)"
flutter drive --driver=test_driver/integration_test.dart --target=integration_test/app_test.dart \
  --dart-define=SERVIDOR=http://10.0.2.2:8090 --dart-define=CODIGO="$CODIGO" \
  --dart-define=APP_VERSAO="$(tr -d ' \r\n' < ../VERSION)" --dart-define=APP_CODIGO=1
