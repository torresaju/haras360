import 'package:flutter/material.dart';
import 'package:workmanager/workmanager.dart';

import 'banco.dart';
import 'dados.dart';
import 'marca.dart';
import 'sincronizacao.dart';
import 'tema.dart';
import 'telas/inicio.dart';
import 'telas/vincular.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Workmanager().initialize(callbackDispatcher);
  final cred = await Credenciais.ler();
  await dados.carregar();
  await Marca.carregar();
  if (cred != null) {
    await Sincronizador.agendar();
  }
  runApp(Haras360App(vinculado: cred != null));
}

class Haras360App extends StatelessWidget {
  final bool vinculado;
  const Haras360App({super.key, required this.vinculado});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Haras360',
        debugShowCheckedModeBanner: false,
        theme: tema(),
        locale: const Locale('pt', 'BR'),
        home: vinculado ? const TelaInicio() : const TelaVincular(),
      );
}
