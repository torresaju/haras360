import 'package:flutter/material.dart';

import '../dados.dart';
import '../regras_app.dart';
import '../tema.dart';

class TelaAvisos extends StatelessWidget {
  final Future<void> Function([Map<String, dynamic>? pre]) registrar;
  const TelaAvisos({super.key, required this.registrar});

  @override
  Widget build(BuildContext context) {
    final l = dados.avisos;
    if (l.isEmpty) return const Center(child: Text('Nenhum aviso.', style: TextStyle(color: Cores.apagado)));
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
      itemCount: l.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (_, i) {
        final n = l[i] as Map;
        final critico = n['sev'] == 'critico';
        final t = n['tarefa'] as Map?;
        return Card(
          child: ListTile(
            leading: Icon(critico ? Icons.error_outline : Icons.notifications_none, color: critico ? Cores.atrasado : Cores.breve),
            title: Text('${n['titulo']}', style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text('${n['texto']}'),
            trailing: t == null ? null : TextButton(onPressed: () => registrar(preDeTarefa(t)), child: const Text('Registrar')),
          ),
        );
      },
    );
  }
}
