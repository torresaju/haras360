import 'package:flutter/material.dart';

import '../config.dart';
import '../dados.dart';
import '../tema.dart';
import 'avisos.dart';
import 'comum.dart';
import 'envio.dart';
import 'vincular.dart';

/// Aba "Mais" (v1.3.0): avisos, envio para o servidor, versão e vínculo.
class TelaMais extends StatelessWidget {
  final Future<void> Function([Map<String, dynamic>? pre]) registrar;
  const TelaMais({super.key, required this.registrar});

  void _abrir(BuildContext context, String titulo, Widget corpo) => Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => Scaffold(appBar: AppBar(title: Text(titulo)), body: ListenableBuilder(listenable: dados, builder: (_, __) => corpo))));

  @override
  Widget build(BuildContext context) {
    final c = dados.contagem;
    final pend = (c['registros'] ?? 0) + (c['fotos'] ?? 0) + (c['audios'] ?? 0);
    Widget item(IconData ic, String t, String sub, VoidCallback onTap, {Widget? fim}) => ListTile(
          leading: Icon(ic, color: Cores.floresta),
          title: Text(t, style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Text(sub),
          trailing: fim ?? const Icon(Icons.chevron_right),
          onTap: onTap,
        );
    return Column(children: [
      const CabecalhoAba('Mais'),
      Expanded(
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Card(
            child: Column(children: [
              item(Icons.notifications_outlined, 'Avisos', '${dados.avisos.length} aviso(s) da última sincronização',
                  () => _abrir(context, 'Avisos', TelaAvisos(registrar: registrar)),
                  fim: dados.avisos.isEmpty ? null : Badge(label: Text('${dados.avisos.length}'))),
              const Divider(height: 1),
              item(Icons.sync, 'Envio', pend > 0 ? '$pend item(ns) aguardando o Wi-Fi' : 'Tudo enviado', () => _abrir(context, 'Envio', const TelaEnvio()),
                  fim: pend > 0 || dados.atualizacaoDisponivel ? Badge(label: Text(pend > 0 ? '$pend' : '!')) : null),
            ]),
          ),
          const SizedBox(height: 12),
          Card(
            child: Column(children: [
              ListTile(leading: const Icon(Icons.info_outline, color: Cores.floresta), title: const Text('Versão do app'), trailing: Text(appVersao)),
              const Divider(height: 1),
              item(Icons.qr_code_scanner, 'Vincular de novo', 'Use se o gestor encerrou o acesso deste celular',
                  () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const TelaVincular()))),
            ]),
          ),
        ]),
      ),
    ]);
  }
}
