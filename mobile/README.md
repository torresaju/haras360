# App Android do caseiro (Flutter)

Especificação: `docs/ESPECIFICACAO-v1.1.0.md`.

```
lib/
  main.dart            início, WorkManager e escolha da primeira tela
  regras_app.dart      regras puras (datas, tarefas, formulário, QR Code), cobertas por test/
  api.dart             cliente HTTP (cabeçalhos X-Haras360 e Bearer)
  banco.dart           SQLite local (estado, fila de registros e de fotos) e credenciais no armazenamento seguro
  sincronizacao.dart   envio da fila e download do estado, somente no Wi-Fi; tarefa periódica
  dados.dart           estado das telas
  telas/               vincular, início, hoje, animais e ficha, avisos, envio, registro
test/                  testes de unidade (flutter test)
integration_test/      ponta a ponta no emulador contra a instância de demonstração
ferramentas/           preparar_android.py (completa a pasta android/) e teste_integracao.sh
recursos/icone/        ícone do app
```

A pasta `android/` não fica no repositório: o GitHub Actions roda `flutter create` e `ferramentas/preparar_android.py`
(identificador `br.com.haras360.campo`, Android 8+, permissões, HTTP liberado, assinatura pelas variáveis `H360_*`).

Para compilar localmente (Flutter 3.27.4):

```
cd mobile
flutter create --platforms=android --org br.com.haras360 --project-name haras360 .
rm test/widget_test.dart
python3 ferramentas/preparar_android.py
flutter test
flutter build apk --release --dart-define=APP_VERSAO=1.1.0 --dart-define=APP_CODIGO=10100
```
