// App do gestor (v1.5.0) no emulador, contra a instância de demonstração:
// entrada com e-mail, senha e 2FA, Dashboard, ficha, registro sem internet, envio, relatórios e capturas para o manual.
//
// flutter drive --driver=test_driver/integration_test.dart --target=integration_test/gestor_test.dart \
//   --dart-define=SERVIDOR=http://10.0.2.2:8090 --dart-define=EMAIL=gestor@demonstracao.local \
//   --dart-define=SENHA=demonstracao123 --dart-define=SEGREDO=<segredo do 2FA> --dart-define=SEM_BLOQUEIO=true
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haras360/main.dart' as app;
import 'package:haras360/sincronizacao.dart';
import 'package:integration_test/integration_test.dart';
import 'package:workmanager/workmanager.dart';

const servidor = String.fromEnvironment('SERVIDOR');
const email = String.fromEnvironment('EMAIL');
const senha = String.fromEnvironment('SENHA');
const segredo = String.fromEnvironment('SEGREDO');

/// Código TOTP (RFC 6238, SHA-1, 6 dígitos, 30 s), igual ao do aplicativo autenticador.
String totp(String base32, DateTime agora) {
  const alfa = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  var bits = '';
  for (final c in base32.toUpperCase().replaceAll('=', '').split('')) {
    bits += alfa.indexOf(c).toRadixString(2).padLeft(5, '0');
  }
  final chave = Uint8List.fromList([for (var i = 0; i + 8 <= bits.length; i += 8) int.parse(bits.substring(i, i + 8), radix: 2)]);
  var contador = agora.millisecondsSinceEpoch ~/ 1000 ~/ 30;
  final msg = Uint8List(8);
  for (var i = 7; i >= 0; i--) {
    msg[i] = contador & 0xff;
    contador >>= 8;
  }
  final h = Hmac(sha1, chave).convert(msg).bytes;
  final o = h.last & 0xf;
  final n = ((h[o] & 0x7f) << 24) | (h[o + 1] << 16) | (h[o + 2] << 8) | h[o + 3];
  return (n % 1000000).toString().padLeft(6, '0');
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  Future<void> esperar(WidgetTester t, Finder f, {int segundos = 60}) async {
    for (var i = 0; i < segundos * 4; i++) {
      await t.pump(const Duration(milliseconds: 250));
      if (f.evaluate().isNotEmpty) return;
    }
    throw TestFailure('Não apareceu na tela: $f');
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
    await t.pump(const Duration(milliseconds: 600));
  }

  void limparAvisos(WidgetTester t) {
    for (final m in t.stateList<ScaffoldMessengerState>(find.byType(ScaffoldMessenger))) {
      m.clearSnackBars();
    }
  }

  testWidgets('gestor entra com 2FA, consulta, registra offline, envia e vê relatórios', (t) async {
    expect(servidor, isNotEmpty);
    expect(segredo, isNotEmpty, reason: 'Informe --dart-define=SEGREDO');
    expect(totp('JBSWY3DPEHPK3PXP', DateTime.fromMillisecondsSinceEpoch(59000, isUtc: true)), '996554'); // confere o cálculo
    Sincronizador.redeForcada = true;
    await app.main();
    await esperar(t, find.text('Sou gestor: entrar com e-mail e 2FA'));
    await t.tap(find.text('Sou gestor: entrar com e-mail e 2FA'));
    await esperar(t, find.widgetWithText(TextField, 'E-mail'));
    await t.enterText(find.widgetWithText(TextField, 'Servidor'), servidor);
    await t.enterText(find.widgetWithText(TextField, 'E-mail'), email);
    await t.enterText(find.widgetWithText(TextField, 'Senha'), senha);
    FocusManager.instance.primaryFocus?.unfocus();
    await t.pump(const Duration(milliseconds: 400));
    await captura(t, 'app-gestor-entrar');
    await t.tap(find.widgetWithText(FilledButton, 'Continuar'));
    await esperar(t, find.widgetWithText(TextField, 'Código do autenticador'));
    await t.enterText(find.widgetWithText(TextField, 'Código do autenticador'), totp(segredo, DateTime.now()));
    await t.tap(find.widgetWithText(FilledButton, 'Entrar'));
    await esperar(t, find.text('Animais ativos'), segundos: 90);
    await Workmanager().cancelAll(); // o envio em segundo plano não interfere no roteiro
    await esperar(t, find.text('Atenção agora'));
    limparAvisos(t);
    await captura(t, 'app-gestor-dashboard');

    await aba(t, 'Animais');
    await esperar(t, find.text('AURORA DO VALE VERDE'));
    await t.tap(find.text('Baixados'));
    await esperar(t, find.text('FAROL DA VEREDA'));
    await t.tap(find.text('Ativos'));
    await t.pump(const Duration(milliseconds: 400));
    await t.tap(find.text('AURORA DO VALE VERDE'));
    await esperar(t, find.text('Próximas etapas'));
    await captura(t, 'app-gestor-ficha');
    await t.pageBack();
    await t.pump(const Duration(milliseconds: 500));

    // registro sem internet: o gestor também trabalha offline
    Sincronizador.redeForcada = false;
    await aba(t, 'Dashboard');
    await t.tap(find.widgetWithText(FloatingActionButton, 'Registrar'));
    await esperar(t, find.text('Salvar registro'));
    await t.tap(find.byType(DropdownButtonFormField<String>).at(0));
    await t.pump(const Duration(milliseconds: 600));
    await t.tap(find.text('BRISA DA SERRA AZUL').last);
    await t.pump(const Duration(milliseconds: 600));
    await t.tap(find.byType(DropdownButtonFormField<String>).at(1));
    await t.pump(const Duration(milliseconds: 600));
    await t.tap(find.text('Ocorrência').last);
    await t.pump(const Duration(milliseconds: 600));
    await t.enterText(find.widgetWithText(TextField, 'O que aconteceu'), 'Cerca do piquete 3 caída');
    FocusManager.instance.primaryFocus?.unfocus();
    await t.pump(const Duration(milliseconds: 400));
    await t.ensureVisible(find.text('Salvar registro'));
    await t.tap(find.text('Salvar registro'));
    await esperar(t, find.textContaining('quando a internet voltar'));
    limparAvisos(t);

    // a internet volta: envio pelo Mais › Envio
    Sincronizador.redeForcada = true;
    await aba(t, 'Mais');
    await t.tap(find.text('Envio'));
    await esperar(t, find.text('Sincronizar agora'));
    await t.tap(find.text('Sincronizar agora'));
    await esperar(t, find.textContaining('Enviado: 1 registro(s)'), segundos: 90);
    await t.pageBack();
    await t.pump(const Duration(milliseconds: 600));
    limparAvisos(t);
    await captura(t, 'app-gestor-mais');
    await t.tap(find.text('Avisos no celular'));
    await esperar(t, find.text('Horário de silêncio'));
    await captura(t, 'app-gestor-avisos');
    await t.pageBack();
    await t.pump(const Duration(milliseconds: 600));
    // v1.6.0: Mais › Vendas abre mesmo sem venda registrada
    await t.tap(find.text('Vendas'));
    await esperar(t, find.textContaining('a receber em'));
    await t.pageBack();
    await t.pump(const Duration(milliseconds: 600));

    await aba(t, 'Relatórios');
    await esperar(t, find.text('Animais em dia'), segundos: 60);
    await captura(t, 'app-gestor-relatorios');
    await t.tap(find.text('Reprodutivo'));
    await esperar(t, find.text('Taxa de prenhez'), segundos: 60);
    expect(find.text('Cios registrados'), findsOneWidget);
  });
}
