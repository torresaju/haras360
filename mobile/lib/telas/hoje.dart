import 'package:flutter/material.dart';

import '../dados.dart';
import '../marca.dart';
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
    final nomeHaras = (dados.haras['nome'] as String?) ?? 'Haras360';
    final municipio = (dados.haras['municipio'] as String?) ?? '';
    final dataTxt = '${dias[h.weekday - 1][0].toUpperCase()}${dias[h.weekday - 1].substring(1)}, ${h.day} de ${const ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'][h.month - 1]}';
    return RefreshIndicator(
      onRefresh: dados.sincronizar,
      child: ListView(padding: EdgeInsets.zero, children: [
        // Cabeçalho com a imagem do haras (ou a ilustração padrão), o logotipo e o nome
        SizedBox(
          height: 210 + MediaQuery.of(context).padding.top,
          child: Stack(fit: StackFit.expand, children: [
            const FundoMarca(),
            const DecoratedBox(
                decoration: BoxDecoration(
                    gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [Color(0xE6102419), Color(0x66102419), Color(0xEB102419)]))),
            Padding(
              padding: EdgeInsets.fromLTRB(16, MediaQuery.of(context).padding.top + 14, 16, 16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  const LogoHaras(tamanho: 44),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(nomeHaras, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontFamily: fonteTitulo, fontWeight: FontWeight.w800, fontSize: 21, color: Colors.white)),
                      if (municipio.isNotEmpty) Text(municipio, style: const TextStyle(color: Color(0xFFDDE6DF), fontSize: 13)),
                    ]),
                  ),
                  if (dados.sincronizando) const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)),
                ]),
                const Spacer(),
                Text(dataTxt, style: const TextStyle(fontFamily: fonteTitulo, fontWeight: FontWeight.w800, fontSize: 24, color: Colors.white)),
                const SizedBox(height: 4),
                Row(children: [
                  Icon(pend > 0 ? Icons.cloud_upload_outlined : Icons.check_circle, size: 16, color: pend > 0 ? Cores.dourado : const Color(0xFF8FD4A8)),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(pend > 0 ? '$pend registro(s) aguardando o Wi-Fi para enviar.' : 'Tudo enviado${dados.ultimaSinc != null ? ' · sincronizado ${_quando(dados.ultimaSinc!)}' : ''}.',
                        style: const TextStyle(color: Color(0xFFE8EEE9), fontSize: 13)),
                  ),
                ]),
              ]),
            ),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            FilledButton.icon(
              onPressed: () => registrar({'tipo': 'ocorrencia', 'titulo': 'Registrar ocorrência'}),
              style: FilledButton.styleFrom(minimumSize: const Size(48, 54)),
              icon: const Icon(Icons.add),
              label: const Text('Registrar ocorrência', style: TextStyle(fontSize: 16)),
            ),
            const SizedBox(height: 12),
            Row(children: [
              _contador('${at.length}', 'Atrasadas', Cores.atrasado),
              const SizedBox(width: 8),
              _contador('${hj.length}', 'Para hoje', Cores.breve),
              const SizedBox(width: 8),
              _contador('${sm.length}', 'Próximos 7 dias', Cores.floresta),
            ]),
            const SizedBox(height: 12),
            bloco('Atrasadas', at, 'Nada atrasado. Bom trabalho.'),
            const SizedBox(height: 12),
            bloco('Para hoje', hj, 'Nada marcado para hoje.'),
            const SizedBox(height: 12),
            bloco('Próximos 7 dias', sm, 'Nada previsto para a semana.'),
          ]),
        ),
      ]),
    );
  }

  static Widget _contador(String n, String l, Color c) => Expanded(
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(n, style: TextStyle(fontFamily: fonteTitulo, fontSize: 26, fontWeight: FontWeight.w800, color: c)),
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
