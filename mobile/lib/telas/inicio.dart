import 'package:flutter/material.dart';

import '../dados.dart';
import '../sincronizacao.dart';
import '../tema.dart';
import 'animais.dart';
import 'agenda.dart';
import 'mais.dart';
import 'hoje.dart';
import 'registro.dart';
import 'vincular.dart';

class TelaInicio extends StatefulWidget {
  const TelaInicio({super.key});
  @override
  State<TelaInicio> createState() => _TelaInicioState();
}

class _TelaInicioState extends State<TelaInicio> with WidgetsBindingObserver {
  int _aba = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _aoAbrir();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed) _aoAbrir();
  }

  /// Sempre que o app abre no Wi-Fi, sincroniza em silêncio.
  Future<void> _aoAbrir() async {
    await dados.carregar();
    if (await Sincronizador.noWifi()) await dados.sincronizar();
    if (dados.desvinculado && mounted) _avisarDesvinculo();
  }

  void _avisarDesvinculo() => showDialog(
        context: context,
        builder: (c) => AlertDialog(
          title: const Text('Celular desvinculado'),
          content: const Text('O gestor encerrou o acesso deste celular ou o seu usuário foi desativado. Os registros que ainda não foram enviados continuam guardados. Peça um novo QR Code para vincular de novo.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c), child: const Text('Depois')),
            FilledButton(
              onPressed: () => Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const TelaVincular()), (_) => false),
              child: const Text('Vincular de novo'),
            ),
          ],
        ),
      );

  Future<void> registrar([Map<String, dynamic>? pre]) async {
    final ok = await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => TelaRegistro(pre: pre ?? const {})));
    if (ok == true) {
      await dados.carregar();
      if (!mounted) return;
      final wifi = await Sincronizador.noWifi();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(wifi ? 'Registro salvo. Enviando pelo Wi-Fi...' : 'Registro salvo no celular. Vai para o servidor quando houver Wi-Fi.')));
      if (wifi) dados.sincronizar();
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: dados,
        builder: (context, _) {
          final pend = (dados.contagem['registros'] ?? 0) + (dados.contagem['fotos'] ?? 0) + (dados.contagem['audios'] ?? 0);
          final alertaMais = pend > 0 || dados.atualizacaoDisponivel || dados.avisos.isNotEmpty;
          final telas = [TelaHoje(registrar: registrar), TelaAnimais(registrar: registrar), TelaAgenda(registrar: registrar), TelaMais(registrar: registrar)];
          return Scaffold(
            body: dados.estado == null
                ? SafeArea(
                    child: Center(
                        child: Padding(
                            padding: const EdgeInsets.all(24),
                            child: Column(mainAxisSize: MainAxisSize.min, children: [
                              const Text('Ainda sem dados do haras. Conecte ao Wi-Fi e sincronize.', textAlign: TextAlign.center),
                              const SizedBox(height: 16),
                              FilledButton.icon(onPressed: dados.sincronizando ? null : dados.sincronizar, icon: const Icon(Icons.sync), label: const Text('Sincronizar agora')),
                            ]))))
                : telas[_aba],
            floatingActionButton: _aba >= 2 || dados.estado == null
                ? null
                : FloatingActionButton.extended(onPressed: () => registrar(), icon: const Icon(Icons.add), label: const Text('Registrar'), backgroundColor: Cores.floresta, foregroundColor: Colors.white),
            bottomNavigationBar: NavigationBar(
              selectedIndex: _aba,
              onDestinationSelected: (i) => setState(() => _aba = i),
              destinations: [
                const NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: 'Hoje'),
                const NavigationDestination(icon: Icon(Icons.pets_outlined), selectedIcon: Icon(Icons.pets), label: 'Animais'),
                const NavigationDestination(icon: Icon(Icons.calendar_month_outlined), selectedIcon: Icon(Icons.calendar_month), label: 'Agenda'),
                NavigationDestination(icon: Badge(isLabelVisible: alertaMais, label: Text(pend > 0 ? '$pend' : '!'), child: const Icon(Icons.more_horiz)), label: 'Mais'),
              ],
            ),
          );
        },
      );
}
