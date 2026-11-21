import 'package:flutter/material.dart';
import 'package:workmanager/workmanager.dart';

import 'avisos_celular.dart';
import 'banco.dart';
import 'dados.dart';
import 'marca.dart';
import 'sincronizacao.dart';
import 'tema.dart';
import 'telas/inicio_gestor.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Workmanager().initialize(callbackDispatcher);
  final cred = await Credenciais.ler();
  await dados.carregar();
  await Marca.carregar();
  if (cred != null) {
    await Sincronizador.agendar();
    if (cred.gestor) await AvisosCelular.iniciar(); // toque numa notificação abre a ficha
  }
  runApp(Haras360App(inicial: await telaInicial()));
}

class Haras360App extends StatelessWidget {
  final Widget inicial;
  const Haras360App({super.key, required this.inicial});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Haras360',
        debugShowCheckedModeBanner: false,
        theme: tema(),
        locale: const Locale('pt', 'BR'),
        home: inicial,
      );
}
