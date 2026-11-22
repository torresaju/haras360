import 'dart:io';

import 'package:flutter/material.dart';

import '../api.dart';
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
  String _sit = 'ativos'; // v1.5.0, gestor: ativos, baixados ou todos

  String _norm(String s) => s.toLowerCase();

  @override
  Widget build(BuildContext context) {
    final ts = dados.tarefas;
    final base = !dados.gestor || _sit == 'ativos'
        ? dados.animais
        : _sit == 'baixados'
            ? dados.doHaras.where((a) => a['baixa'] != null).toList()
            : dados.doHaras;
    final lista = base.where((a) => _busca.isEmpty || _norm(a['nome'] as String).contains(_norm(_busca)) || '${a['registro']}'.contains(_busca)).toList();
    return Column(children: [
      CabecalhoAba('Animais', subtitulo: '${dados.animais.length} no plantel'),
      Expanded(child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 96), children: [
      TextField(decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Buscar por nome ou registro'), onChanged: (v) => setState(() => _busca = v.trim())),
      if (dados.gestor) ...[
        const SizedBox(height: 10),
        SegmentedButton<String>(
          segments: const [ButtonSegment(value: 'ativos', label: Text('Ativos')), ButtonSegment(value: 'baixados', label: Text('Baixados')), ButtonSegment(value: 'todos', label: Text('Todos'))],
          selected: {_sit},
          onSelectionChanged: (v) => setState(() => _sit = v.first),
        ),
      ],
      const SizedBox(height: 12),
      Card(
        child: Column(children: [
          for (final a in lista)
            ListTile(
              title: Text(a['nome'] as String, style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text([
                a['sexo'] == 'F' ? 'Fêmea' : 'Macho',
                idadeTxt(a['nascimento'] as String?),
                if (dados.gestacao(a['id'] as String) != null) 'Gestante',
                if (a['baixa'] is Map) '${(a['baixa'] as Map)['motivo']} em ${br((a['baixa'] as Map)['data'] as String?)}',
              ].where((x) => x.isNotEmpty).join(' · ')),
              trailing: _pend(ts.where((t) => t['animalId'] == a['id']).toList()),
              onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TelaFicha(id: a['id'] as String, registrar: widget.registrar))),
            ),
          if (lista.isEmpty) const Padding(padding: EdgeInsets.all(20), child: Text('Nenhum animal encontrado.', style: TextStyle(color: Cores.apagado))),
        ]),
      ),
    ]))]);
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
          final baixa = a['baixa'] as Map?;
          final ativo = a['vivo'] == true && baixa == null;
          return Scaffold(
            appBar: AppBar(title: Text(a['nome'] as String), actions: [
              if (dados.gestor && baixa == null)
                PopupMenuButton<String>(
                  onSelected: (_) => _darBaixa(context, a),
                  itemBuilder: (_) => const [PopupMenuItem(value: 'baixa', child: Text('Dar baixa'))],
                ),
            ]),
            floatingActionButton: ativo
                ? FloatingActionButton.extended(
                    onPressed: () => registrar({'animalId': id}), icon: const Icon(Icons.add), label: const Text('Registrar'), backgroundColor: Cores.acento, foregroundColor: Colors.white)
                : null,
            body: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 96), children: [
              if (baixa != null) ...[
                Card(
                  color: Cores.breveSuave,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('Fora do plantel ativo: ${baixa['motivo']} em ${br(baixa['data'] as String?)}', style: const TextStyle(fontWeight: FontWeight.w700)),
                      if ('${baixa['destino'] ?? ''}'.isNotEmpty) Text('Destino: ${baixa['destino']}'),
                      if ('${baixa['obs'] ?? ''}'.isNotEmpty) Text('${baixa['obs']}'),
                      if (dados.gestor) ...[
                        const SizedBox(height: 8),
                        OutlinedButton(onPressed: () => _desfazerBaixa(context, a), child: const Text('Desfazer baixa')),
                      ],
                    ]),
                  ),
                ),
                const SizedBox(height: 12),
              ],
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
                      if (dados.gestor && (r['fotos'] as List?)?.isNotEmpty == true) FotosRemotas((r['fotos'] as List).cast<String>()),
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

  // ---------- baixa (v1.5.0, só gestor e com internet) ----------
  static Future<Api?> _api(BuildContext context) async {
    final c = dados.cred;
    if (c == null) return null;
    return Api(c.servidor, token: c.token);
  }

  static Future<void> _executar(BuildContext context, Future<Map<String, dynamic>> Function(Api api) f) async {
    final api = await _api(context);
    if (api == null) return;
    try {
      final r = await f(api);
      await dados.sincronizar();
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${r['resumo'] ?? 'Feito.'}')));
    } on ApiErro catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.semConexao ? 'A baixa precisa de internet. Conecte e tente de novo.' : e.mensagem)));
      }
    }
  }

  void _darBaixa(BuildContext context, Map a) {
    var data = DateTime.now();
    var motivo = 'Venda';
    final destino = TextEditingController(), obs = TextEditingController();
    showDialog(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: Text('Dar baixa em ${a['nome']}'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              OutlinedButton.icon(
                icon: const Icon(Icons.event),
                label: Text('Data: ${br(iso(data))}'),
                onPressed: () async {
                  final d = await showDatePicker(context: c, initialDate: data, firstDate: DateTime(2000), lastDate: DateTime.now());
                  if (d != null) set(() => data = d);
                },
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: motivo,
                decoration: const InputDecoration(labelText: 'Motivo'),
                items: const ['Venda', 'Morte', 'Doação', 'Transferência'].map((m) => DropdownMenuItem(value: m, child: Text(m))).toList(),
                onChanged: (v) => set(() => motivo = v ?? motivo),
              ),
              const SizedBox(height: 12),
              TextField(controller: destino, decoration: const InputDecoration(labelText: 'Destino ou comprador (opcional)')),
              const SizedBox(height: 12),
              TextField(controller: obs, maxLines: 2, decoration: const InputDecoration(labelText: 'Observação')),
              const SizedBox(height: 12),
              const Text('O animal sai do plantel ativo, da agenda e do app do caseiro. O prontuário continua guardado.', style: TextStyle(color: Cores.apagado, fontSize: 13)),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c), child: const Text('Cancelar')),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Cores.atrasado),
              onPressed: () {
                Navigator.pop(c);
                _executar(context, (api) => api.post('/api/animais/${a['id']}/baixa', {'data': iso(data), 'motivo': motivo, 'destino': destino.text, 'obs': obs.text}));
              },
              child: const Text('Confirmar baixa'),
            ),
          ],
        ),
      ),
    );
  }

  void _desfazerBaixa(BuildContext context, Map a) => showDialog(
        context: context,
        builder: (c) => AlertDialog(
          title: const Text('Desfazer a baixa?'),
          content: Text('${a['nome']} volta ao plantel ativo e à agenda.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c), child: const Text('Cancelar')),
            FilledButton(
              onPressed: () {
                Navigator.pop(c);
                _executar(context, (api) => api.delete('/api/animais/${a['id']}/baixa'));
              },
              child: const Text('Confirmar'),
            ),
          ],
        ),
      );

  static Widget _dado(String l, String v) => Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Text(l, style: const TextStyle(fontSize: 12, color: Cores.apagado)),
        Text(v, style: const TextStyle(fontWeight: FontWeight.w600)),
      ]);
}


/// Fotos do prontuário vindas do servidor (gestor, v1.5.0), baixadas com o token do celular.
class FotosRemotas extends StatelessWidget {
  final List<String> urls;
  const FotosRemotas(this.urls, {super.key});

  @override
  Widget build(BuildContext context) {
    final c = dados.cred;
    if (c == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Wrap(spacing: 6, runSpacing: 6, children: [
        for (final u in urls)
          GestureDetector(
            onTap: () => Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => Scaffold(
                    backgroundColor: Colors.black,
                    appBar: AppBar(backgroundColor: Colors.black),
                    body: Center(child: InteractiveViewer(child: Image.network('${c.servidor}$u', headers: {'Authorization': 'Bearer ${c.token}'})))))),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.network('${c.servidor}$u',
                  headers: {'Authorization': 'Bearer ${c.token}'},
                  width: 72,
                  height: 72,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(width: 72, height: 72, color: Cores.linha, child: const Icon(Icons.image_not_supported_outlined))),
            ),
          ),
      ]),
    );
  }
}
