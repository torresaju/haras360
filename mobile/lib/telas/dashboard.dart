import 'package:flutter/material.dart';

import '../dados.dart';
import '../regras_app.dart';
import '../tema.dart';
import 'animais.dart';
import 'comum.dart';

/// Dashboard do gestor no app (v1.5.0): os indicadores do portal, Atenção agora, próximos eventos e o campo.
class TelaDashboard extends StatelessWidget {
  final Future<void> Function([Map<String, dynamic>? pre]) registrar;
  const TelaDashboard({super.key, required this.registrar});

  @override
  Widget build(BuildContext context) {
    final ts = dados.tarefas;
    final vac = ts.where((t) => t['cat'] == 'vacina');
    final gest = ((dados.estado?['gestacoes'] as Map?) ?? const {}).values.whereType<Map>().toList();
    final h = hoje();
    final partos30 = gest.where((g) {
      final p = DateTime.tryParse('${g['parto']}');
      return p != null && dias(h, p) >= 0 && dias(h, p) <= 30;
    }).length;
    final notifs = ((dados.estado?['notificacoes'] as List?) ?? const []).cast<Map>();
    final atencao = notifs.where((n) => n['sev'] == 'critico' || n['sev'] == 'alerta').where((n) => n['tipo'] != 'campo').take(5).toList();
    final proximos = ts.where((t) => t['status'] == 'hoje' || t['status'] == 'semana').take(6).toList();
    final campo = dados.registros.cast<Map>().where((r) => r['origem'] == 'App' || r['origem'] == 'Portal Cliente').toList()
      ..sort((a, b) => '${b['data']}'.compareTo('${a['data']}'));
    final sinc = dados.ultimaSinc;

    Widget kpi(String n, String rot, {Color cor = Cores.floresta}) => Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: Cores.superficie, borderRadius: BorderRadius.circular(14), border: Border.all(color: Cores.linha)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(n, style: TextStyle(fontFamily: fonteTitulo, fontWeight: FontWeight.w800, fontSize: 24, color: cor)),
            const SizedBox(height: 2),
            Text(rot, style: const TextStyle(fontSize: 12.5, color: Cores.apagado, fontWeight: FontWeight.w600)),
          ]),
        );

    void abrirFicha(String? id) {
      if (id == null || dados.animal(id) == null) return;
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => TelaFicha(id: id, registrar: registrar)));
    }

    return Column(children: [
      CabecalhoAba('Dashboard',
          subtitulo: [
            '${dados.haras['nome'] ?? 'Haras360'}',
            if (dados.sincronizando) 'sincronizando...' else if (sinc != null) 'atualizado ${_hora(sinc)}',
          ].join(' · ')),
      Expanded(
        child: RefreshIndicator(
          onRefresh: dados.sincronizar,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 96), children: [
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 10,
              crossAxisSpacing: 10,
              childAspectRatio: 2.1,
              children: [
                kpi('${dados.animais.length}', 'Animais ativos'),
                kpi('${vac.where((t) => t['status'] == 'atrasado').length}', 'Vacinas vencidas', cor: Cores.atrasado),
                kpi('${vac.where((t) => t['status'] == 'hoje' || t['status'] == 'semana').length}', 'Vacinas em 7 dias', cor: Cores.breve),
                kpi('${gest.length}', 'Gestações ativas', cor: Cores.repro),
                kpi('$partos30', 'Partos em 30 dias', cor: Cores.repro),
                kpi('${ts.where((t) => t['status'] == 'atrasado').length}', 'Tarefas atrasadas', cor: Cores.atrasado),
              ],
            ),
            const SizedBox(height: 12),
            Secao(
              'Atenção agora',
              atencao
                  .map((n) => ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(n['sev'] == 'critico' ? Icons.error_outline : Icons.warning_amber_rounded,
                            color: n['sev'] == 'critico' ? Cores.atrasado : Cores.breve),
                        title: Text('${n['titulo']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                        subtitle: Text('${n['texto']}'),
                        onTap: () => abrirFicha(n['animalId'] as String?),
                      ))
                  .toList(),
              vazio: 'Nada urgente.',
            ),
            const SizedBox(height: 12),
            Secao('Próximos 7 dias', proximos.map((t) => LinhaTarefa(t, onRegistrar: () => registrar(preDeTarefa(t)))).toList(),
                contador: '${proximos.length}', vazio: 'Nada previsto.'),
            const SizedBox(height: 12),
            Secao(
              'Últimos registros do campo',
              campo.take(5).map((r) {
                final a = dados.animal(r['animalId'] as String?);
                final fotos = (r['fotos'] as List?)?.length ?? 0;
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('${tituloRegistro(r, dados.protocolos)} · ${a?['nome'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: Text([br(r['data'] as String?), '${r['autor'] ?? ''}', r['origem'] == 'App' ? 'app' : 'Portal Campo'].join(' · ')),
                  trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                    if (fotos > 0) ...[const Icon(Icons.photo_outlined, size: 18, color: Cores.apagado), Text(' $fotos ')],
                    if (r['audio'] is Map) const Icon(Icons.mic_none, size: 18, color: Cores.apagado),
                  ]),
                  onTap: () => abrirFicha(r['animalId'] as String?),
                );
              }).toList(),
              vazio: 'O caseiro ainda não registrou nada.',
            ),
          ]),
        ),
      ),
    ]);
  }

  static String _hora(DateTime d) {
    final h = DateTime.now();
    final mesmoDia = d.year == h.year && d.month == h.month && d.day == h.day;
    final hm = '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
    return mesmoDia ? 'às $hm' : 'em ${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')} às $hm';
  }
}
