import 'dart:io';

import 'package:flutter/material.dart';

import '../dados.dart';
import '../regras_app.dart';
import '../tema.dart';
import 'audio.dart';
import 'comum.dart';

class TelaAnimais extends StatefulWidget {
  final Future<void> Function([Map<String, dynamic>? pre]) registrar;
  const TelaAnimais({super.key, required this.registrar});
  @override
  State<TelaAnimais> createState() => _TelaAnimaisState();
}

class _TelaAnimaisState extends State<TelaAnimais> {
  String _busca = '';

  String _norm(String s) => s.toLowerCase();

  @override
  Widget build(BuildContext context) {
    final ts = dados.tarefas;
    final lista = dados.animais.where((a) => _busca.isEmpty || _norm(a['nome'] as String).contains(_norm(_busca)) || '${a['registro']}'.contains(_busca)).toList();
    return ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 96), children: [
      TextField(decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Buscar por nome ou registro'), onChanged: (v) => setState(() => _busca = v.trim())),
      const SizedBox(height: 12),
      Card(
        child: Column(children: [
          for (final a in lista)
            ListTile(
              title: Text(a['nome'] as String, style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text([a['sexo'] == 'F' ? 'Fêmea' : 'Macho', idadeTxt(a['nascimento'] as String?), if (dados.gestacao(a['id'] as String) != null) 'Gestante'].where((x) => x.isNotEmpty).join(' · ')),
              trailing: _pend(ts.where((t) => t['animalId'] == a['id']).toList()),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TelaFicha(id: a['id'] as String, registrar: widget.registrar))),
            ),
          if (lista.isEmpty) const Padding(padding: EdgeInsets.all(20), child: Text('Nenhum animal encontrado.', style: TextStyle(color: Cores.apagado))),
        ]),
      ),
    ]);
  }

  Widget? _pend(List<Map<String, dynamic>> l) {
    final at = l.where((t) => t['status'] == 'atrasado').length;
    final pr = l.where((t) => t['status'] == 'hoje' || t['status'] == 'semana').length;
    if (at > 0) return Etiqueta('$at atrasada(s)', Cores.atrasado, Cores.atrasadoSuave);
    if (pr > 0) return Etiqueta('$pr na semana', Cores.breve, Cores.breveSuave);
    return null;
  }
}

class TelaFicha extends StatelessWidget {
  final String id;
  final Future<void> Function([Map<String, dynamic>? pre]) registrar;
  const TelaFicha({super.key, required this.id, required this.registrar});

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: dados,
        builder: (context, _) {
          final a = dados.animal(id);
          if (a == null) return Scaffold(appBar: AppBar(), body: const Center(child: Text('Animal não encontrado.')));
          final ts = dados.tarefas.where((t) => t['animalId'] == id).toList();
          final g = dados.gestacao(id);
          final hist = dados.historico(id);
          return Scaffold(
            appBar: AppBar(title: Text(a['nome'] as String)),
            floatingActionButton: FloatingActionButton.extended(
                onPressed: () => registrar({'animalId': id}), icon: const Icon(Icons.add), label: const Text('Registrar'), backgroundColor: Cores.acento, foregroundColor: Colors.white),
            body: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 96), children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Wrap(spacing: 24, runSpacing: 8, children: [
                    _dado('Sexo', a['sexo'] == 'F' ? 'Fêmea' : 'Macho'),
                    _dado('Nascimento', '${br(a['nascimento'] as String?)} (${idadeTxt(a['nascimento'] as String?)})'),
                    if ('${a['registro']}'.isNotEmpty) _dado('Registro ABCCMM', '${a['registro']}'),
                    if ('${a['pelagem']}'.isNotEmpty) _dado('Pelagem', '${a['pelagem']}'),
                    if ('${a['chip']}'.isNotEmpty) _dado('Chip', '${a['chip']}'),
                  ]),
                ),
              ),
              if (g != null) ...[
                const SizedBox(height: 12),
                Card(
                  color: Cores.acentoSuave,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text('Gestante · ${g['mes']}º mês. Parto previsto para ${br(g['parto'] as String?)} (${relativo(g['parto'] as String?)}).',
                        style: const TextStyle(fontWeight: FontWeight.w600)),
                  ),
                ),
              ],
              const SizedBox(height: 12),
              Secao('Próximas etapas', ts.take(8).map((t) => LinhaTarefa(t, mostrarAnimal: false, onRegistrar: () => registrar(preDeTarefa(t)))).toList(), vazio: 'Nada previsto.'),
              const SizedBox(height: 12),
              Secao(
                'Histórico',
                hist.take(40).map((r) {
                  final local = r['_enviado'] != null;
                  return ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(tituloRegistro(r, dados.protocolos)),
                    subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text([br(r['data'] as String?), if (doseTxt(r['dose']).isNotEmpty) doseTxt(r['dose']), '${r['autor'] ?? ''}', if ('${r['obs'] ?? ''}'.isNotEmpty) '${r['obs']}']
                          .where((x) => x.isNotEmpty)
                          .join(' · ')),
                      if (r['_audio'] is Map)
                        TocadorAudio(arquivo: File((r['_audio'] as Map)['caminho'] as String), duracao: (r['_audio'] as Map)['duracao'] as int)
                      else if (r['audio'] is Map)
                        TocadorAudio(url: (r['audio'] as Map)['url'] as String, duracao: ((r['audio'] as Map)['duracao'] as num).toInt()),
                    ]),
                    trailing: local
                        ? (r['_erro'] != null
                            ? const Etiqueta('Recusado', Cores.atrasado, Cores.atrasadoSuave)
                            : r['_enviado'] == true
                                ? const Etiqueta('Enviado', Cores.ok, Cores.okSuave)
                                : const Etiqueta('No celular', Cores.breve, Cores.breveSuave))
                        : null,
                  );
                }).toList(),
                vazio: 'Sem registros.',
              ),
            ]),
          );
        },
      );

  static Widget _dado(String l, String v) => Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Text(l, style: const TextStyle(fontSize: 12, color: Cores.apagado)),
        Text(v, style: const TextStyle(fontWeight: FontWeight.w600)),
      ]);
}
