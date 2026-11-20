// Teste de ponta a ponta no emulador, contra a instância de demonstração:
// vínculo pelo código, telas offline, registro sem Wi-Fi, envio no Wi-Fi e capturas para o manual.
//
// flutter drive --driver=test_driver/integration_test.dart --target=integration_test/app_test.dart \
//   --dart-define=SERVIDOR=http://10.0.2.2:8090 --dart-define=CODIGO=<código de haras360 vincular-celular>
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haras360/main.dart' as app;
import 'package:haras360/sincronizacao.dart';
import 'package:integration_test/integration_test.dart';
import 'package:workmanager/workmanager.dart';

const servidor = String.fromEnvironment('SERVIDOR');
const codigo = String.fromEnvironment('CODIGO');

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  Future<void> esperar(WidgetTester t, Finder f, {int segundos = 60}) async {
    for (var i = 0; i < segundos * 4; i++) {
      await t.pump(const Duration(milliseconds: 250));
      if (f.evaluate().isNotEmpty) return;
    }
    throw TestFailure('Não apareceu na tela: $f');
  }

  Future<void> esperarSumir(WidgetTester t, Finder f, {int segundos = 60}) async {
    for (var i = 0; i < segundos * 4; i++) {
      await t.pump(const Duration(milliseconds: 250));
      if (f.evaluate().isEmpty) return;
    }
    throw TestFailure('Continuou na tela: $f');
  }

  var preparado = false;
  Future<void> captura(WidgetTester t, String nome) async {
    if (!preparado) {
      await binding.convertFlutterSurfaceToImage();
      preparado = true;
    }
    await t.pump(const Duration(milliseconds: 600));
    await binding.takeScreenshot(nome);
  }

  Future<void> aba(WidgetTester t, String nome) async {
    await t.tap(find.descendant(of: find.byType(NavigationBar), matching: find.text(nome)));
    await t.pump(const Duration(milliseconds: 500));
  }

  testWidgets('caseiro vincula, trabalha offline e envia no Wi-Fi', (t) async {
    expect(servidor, isNotEmpty, reason: 'Informe --dart-define=SERVIDOR');
    expect(codigo, isNotEmpty, reason: 'Informe --dart-define=CODIGO');
    Sincronizador.redeForcada = true;
    await app.main();
    await esperar(t, find.text('Ler QR Code'));
    await captura(t, 'app-vincular');

    // vínculo pelo código (o mesmo do QR Code)
    await t.tap(find.text('Sem câmera? Digitar código ou entrar com e-mail'));
    await esperar(t, find.widgetWithText(TextField, 'Servidor'));
    await t.enterText(find.widgetWithText(TextField, 'Servidor'), servidor);
    await t.enterText(find.widgetWithText(TextField, 'Código do QR Code'), codigo);
    await t.tap(find.widgetWithText(FilledButton, 'Vincular'));
    await esperar(t, find.byType(NavigationBar), segundos: 90);
    await esperar(t, find.text('Atrasadas'), segundos: 60);
    await esperarSumir(t, find.byType(CircularProgressIndicator));
    // o envio em segundo plano não interfere no roteiro do teste
    await Workmanager().cancelAll();
    expect(find.text('Haras Demonstração'), findsOneWidget);
    await captura(t, 'app-hoje');

    await aba(t, 'Animais');
    await esperar(t, find.text('AURORA DO VALE VERDE'));
    await captura(t, 'app-animais');
    await t.tap(find.text('AURORA DO VALE VERDE'));
    await esperar(t, find.text('Próximas etapas'));
    await captura(t, 'app-ficha');
    await t.pageBack();
    await t.pump(const Duration(milliseconds: 500));

    // registro no pasto, sem Wi-Fi
    Sincronizador.redeForcada = false;
    await aba(t, 'Hoje');
    await t.tap(find.text('Registrar ocorrência'));
    await esperar(t, find.widgetWithText(TextField, 'O que aconteceu'));
    await t.tap(find.byType(DropdownButtonFormField<String>).first);
    await t.pump(const Duration(milliseconds: 600));
    await t.tap(find.text('BRISA DA SERRA AZUL').last);
    await t.pump(const Duration(milliseconds: 600));
    await t.enterText(find.widgetWithText(TextField, 'O que aconteceu'), 'Pisou em prego no piquete');
    await t.enterText(find.widgetWithText(TextField, 'Observações'), 'Limpei e passei iodo. Teste automático do app.');
    FocusManager.instance.primaryFocus?.unfocus();
    await t.pump(const Duration(milliseconds: 600));
    await captura(t, 'app-registro');
    await t.ensureVisible(find.text('Salvar registro'));
    await t.tap(find.text('Salvar registro'));
    await esperar(t, find.textContaining('Vai para o servidor quando houver Wi-Fi'));
    await esperar(t, find.textContaining('aguardando o Wi-Fi'));

    await aba(t, 'Envio');
    await esperar(t, find.text('Sincronizar agora'));
    await captura(t, 'app-envio-pendente');

    // de volta ao Wi-Fi da sede
    Sincronizador.redeForcada = true;
    await t.tap(find.text('Sincronizar agora'));
    await esperar(t, find.textContaining('Enviado: 1 registro'), segundos: 90);
    await t.pump(const Duration(seconds: 2));
    await captura(t, 'app-envio-ok');

    await aba(t, 'Avisos');
    await t.pump(const Duration(seconds: 1));
    await captura(t, 'app-avisos');
  });
}
