import 'package:flutter/material.dart';

import '../dados.dart';
import '../regras_app.dart';
import '../tema.dart';
import 'comum.dart';

class TelaHoje extends StatelessWidget {
  final Future<void> Function([Map<String, dynamic>? pre]) registrar;
  const TelaHoje({super.key, required this.registrar});

  @override
  Widget build(BuildContext context) {
    final ts = dados.tarefas;
    final at = ts.where((t) => t['status'] == 'atrasado').toList();
    final hj = ts.where((t) => t['status'] == 'hoje').toList();
    final sm = ts.where((t) => t['status'] == 'semana').toList();
    const dias = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo'];
    final h = DateTime.now();
    final pend = dados.contagem['registros'] ?? 0;
    Widget bloco(String tit, List<Map<String, dynamic>> l, String vazio) =>
        Secao(tit, l.map((t) => LinhaTarefa(t, onRegistrar: () => registrar(preDeTarefa(t)))).toList(), contador: '${l.length}', vazio: vazio);
    return RefreshIndicator(
      onRefresh: dados.sincronizar,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 96), children: [
        Text('${dias[h.weekday - 1]}, ${h.day} de ${const ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'][h.month - 1]}',
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        Text(
          pend > 0 ? '$pend registro(s) aguardando o Wi-Fi para enviar.' : 'Tudo enviado${dados.ultimaSinc != null ? ' · sincronizado ${_quando(dados.ultimaSinc!)}' : ''}.',
          style: TextStyle(color: pend > 0 ? Cores.breve : Cores.apagado),
        ),
        const SizedBox(height: 12),
        Row(children: [
          _contador('${at.length}', 'Atrasadas', Cores.atrasado),
          const SizedBox(width: 8),
          _contador('${hj.length}', 'Para hoje', Cores.breve),
          const SizedBox(width: 8),
          _contador('${sm.length}', 'Próximos 7 dias', Cores.tinta),
        ]),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: () => registrar({'tipo': 'ocorrencia', 'titulo': 'Registrar ocorrência'}),
          icon: const Icon(Icons.warning_amber_outlined),
          label: const Text('Registrar ocorrência'),
        ),
        const SizedBox(height: 12),
        bloco('Atrasadas', at, 'Nada atrasado. Bom trabalho.'),
        const SizedBox(height: 12),
        bloco('Para hoje', hj, 'Nada marcado para hoje.'),
        const SizedBox(height: 12),
        bloco('Próximos 7 dias', sm, 'Nada previsto para a semana.'),
      ]),
    );
  }

  static Widget _contador(String n, String l, Color c) => Expanded(
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(n, style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700, color: c)),
              Text(l, style: const TextStyle(fontSize: 12, color: Cores.apagado)),
            ]),
          ),
        ),
      );
}

String _quando(DateTime d) {
  final h = DateTime.now();
  final hm = '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
  if (d.year == h.year && d.month == h.month && d.day == h.day) return 'hoje às $hm';
  return 'em ${br(iso(d))} às $hm';
}

String quando(DateTime d) => _quando(d);
