import 'package:flutter/material.dart';

import '../dados.dart';
import '../regras_app.dart';
import 'comum.dart';

/// Agenda do caseiro (v1.3.0): o que vence nos próximos 30 dias, calculado no celular.
class TelaAgenda extends StatelessWidget {
  final Future<void> Function([Map<String, dynamic>? pre]) registrar;
  const TelaAgenda({super.key, required this.registrar});

  @override
  Widget build(BuildContext context) {
    final hoje0 = hoje();
    final lim = hoje0.add(const Duration(days: 30));
    final ts = dados.tarefas.where((t) {
      final d = data(t['due'] as String?);
      return d != null && !d.isAfter(lim);
    }).toList();
    final grupos = <String, List<Map<String, dynamic>>>{
      'Atrasadas': ts.where((t) => t['status'] == 'atrasado').toList(),
      'Hoje': ts.where((t) => t['status'] == 'hoje').toList(),
      'Próximos 7 dias': ts.where((t) => t['status'] == 'semana').toList(),
      'Até 30 dias': ts.where((t) => t['status'] == 'futuro').toList(),
    };
    return Column(children: [
      const CabecalhoAba('Agenda', subtitulo: 'Próximos 30 dias'),
      Expanded(
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 32), children: [
          for (final e in grupos.entries)
            if (e.value.isNotEmpty) ...[
              Secao(e.key, e.value.map((t) => LinhaTarefa(t, onRegistrar: () => registrar(preDeTarefa(t)))).toList(), contador: '${e.value.length}'),
              const SizedBox(height: 12),
            ],
          if (ts.isEmpty) const Padding(padding: EdgeInsets.all(24), child: Text('Nada previsto para os próximos 30 dias.', textAlign: TextAlign.center)),
        ]),
      ),
    ]);
  }
}
