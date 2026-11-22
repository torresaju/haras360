import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../api.dart';
import '../banco.dart';
import '../dados.dart';
import '../regras_app.dart';
import '../tema.dart';
import 'animais.dart';
import 'comum.dart';

/// Relatórios no app do gestor (v1.5.0): os quatro relatórios do portal, com indicadores, gráficos,
/// tabelas principais e envio da planilha (Excel ou CSV) pelo compartilhar do Android. Só com internet.
class TelaRelatorios extends StatefulWidget {
  final Future<void> Function([Map<String, dynamic>? pre]) registrar;
  const TelaRelatorios({super.key, required this.registrar});
  @override
  State<TelaRelatorios> createState() => _TelaRelatoriosState();
}

class _TelaRelatoriosState extends State<TelaRelatorios> {
  static const abas = {'sanitario': 'Sanitário', 'reprodutivo': 'Reprodutivo', 'plantel': 'Plantel', 'campo': 'Campo', 'vendas': 'Vendas'};
  static const periodos = {'3': '3 meses', '12': '12 meses', 'ano': 'Este ano'};
  String _tipo = 'sanitario', _periodo = '12';
  Map<String, dynamic>? _rel;
  String? _erro;
  bool _carregando = false, _enviando = false;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  String get _query {
    final h = DateTime.now();
    final de = switch (_periodo) {
      '3' => DateTime(h.year, h.month - 3, h.day),
      'ano' => DateTime(h.year, 1, 1),
      _ => DateTime(h.year - 1, h.month, 1),
    };
    return 'de=${iso(de)}&ate=${iso(h)}';
  }

  Future<Api> _api() async {
    final c = await Credenciais.ler();
    if (c == null) throw ApiErro(401, 'Sessão encerrada. Entre de novo.');
    return Api(c.servidor, token: c.token);
  }

  Future<void> _carregar() async {
    setState(() {
      _carregando = true;
      _erro = null;
    });
    try {
      final r = await (await _api()).get('/api/relatorios/$_tipo?$_query');
      if (mounted) setState(() => _rel = r);
    } on ApiErro catch (e) {
      if (mounted) setState(() => _erro = e.semConexao ? 'Os relatórios precisam de internet. Conecte e tente de novo.' : e.mensagem);
    } finally {
      if (mounted) setState(() => _carregando = false);
    }
  }

  Future<void> _enviar(String formato) async {
    setState(() => _enviando = true);
    try {
      final bytes = await (await _api()).baixar('/api/relatorios/$_tipo/exportar?formato=$formato&$_query');
      final dir = await getTemporaryDirectory();
      final f = File(p.join(dir.path, 'haras360-$_tipo-${iso(DateTime.now())}.$formato'));
      await f.writeAsBytes(bytes);
      await Share.shareXFiles([
        XFile(f.path, mimeType: formato == 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
      ], subject: '${_rel?['titulo'] ?? 'Relatório'} · ${dados.haras['nome'] ?? 'Haras360'}');
    } on ApiErro catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.semConexao ? 'Sem internet para gerar a planilha.' : e.mensagem)));
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  void _menuEnviar() => showModalBottomSheet(
        context: context,
        builder: (c) => SafeArea(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            ListTile(
                leading: const Icon(Icons.table_chart_outlined, color: Cores.floresta),
                title: const Text('Planilha Excel (.xlsx)'),
                subtitle: const Text('Aba Resumo e uma aba por tabela'),
                onTap: () {
                  Navigator.pop(c);
                  _enviar('xlsx');
                }),
            ListTile(
                leading: const Icon(Icons.description_outlined, color: Cores.floresta),
                title: const Text('CSV'),
                subtitle: const Text('Texto separado por ponto e vírgula'),
                onTap: () {
                  Navigator.pop(c);
                  _enviar('csv');
                }),
          ]),
        ),
      );

  @override
  Widget build(BuildContext context) {
    if (!dados.relatoriosLiberado) {
      return const Column(children: [
        CabecalhoAba('Relatórios'),
        Expanded(child: Center(child: Padding(padding: EdgeInsets.all(24), child: Text('Os relatórios não estão incluídos no plano deste haras.', textAlign: TextAlign.center)))),
      ]);
    }
    final r = _rel;
    return Column(children: [
      CabecalhoAba('Relatórios',
          subtitulo: r == null ? null : '${br(r['periodo']['de'] as String?)} a ${br(r['periodo']['ate'] as String?)}',
          acoes: [
            IconButton(
              tooltip: 'Enviar planilha',
              onPressed: r == null || _enviando ? null : _menuEnviar,
              icon: _enviando
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Cores.florestaTinta))
                  : const Icon(Icons.ios_share, color: Cores.florestaTinta),
            ),
          ]),
      Expanded(
        child: RefreshIndicator(
          onRefresh: _carregar,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 32), children: [
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(children: [
                for (final e in abas.entries)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(e.value),
                      selected: _tipo == e.key,
                      onSelected: (_) {
                        setState(() => _tipo = e.key);
                        _carregar();
                      },
                    ),
                  ),
              ]),
            ),
            const SizedBox(height: 8),
            SegmentedButton<String>(
              segments: [for (final e in periodos.entries) ButtonSegment(value: e.key, label: Text(e.value))],
              selected: {_periodo},
              onSelectionChanged: (s) {
                setState(() => _periodo = s.first);
                _carregar();
              },
            ),
            const SizedBox(height: 12),
            if (_carregando) const Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator())),
            if (_erro != null)
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: Cores.atrasadoSuave, borderRadius: BorderRadius.circular(8)),
                child: Text(_erro!, style: const TextStyle(color: Cores.atrasado)),
              ),
            if (r != null && !_carregando) ..._conteudo(r),
          ]),
        ),
      ),
    ]);
  }

  List<Widget> _conteudo(Map<String, dynamic> r) => [
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 1.9,
          children: [
            for (final i in (r['indicadores'] as List).cast<Map>())
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: Cores.superficie, borderRadius: BorderRadius.circular(14), border: Border.all(color: Cores.linha)),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
                  FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text('${i['valor']}', style: const TextStyle(fontFamily: fonteTitulo, fontWeight: FontWeight.w800, fontSize: 22, color: Cores.floresta))),
                  Text('${i['rotulo']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5, color: Cores.apagado, fontWeight: FontWeight.w600)),
                ]),
              ),
          ],
        ),
        for (final g in (r['graficos'] as List).cast<Map>()) ...[const SizedBox(height: 12), _Grafico(g)],
        for (final t in (r['tabelas'] as List).cast<Map>()) ...[const SizedBox(height: 12), _tabela(t)],
      ];

  Widget _tabela(Map t) {
    final cols = (t['colunas'] as List).cast<String>();
    final linhas = (t['linhas'] as List).cast<List>();
    final links = (t['links'] as List?) ?? const [];
    return Secao(
      '${t['nome']}',
      [
        for (var i = 0; i < linhas.length && i < 20; i++)
          ListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            title: Text(linhas[i].take(2).join(' · '), style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text([for (var c = 2; c < cols.length; c++) if ('${linhas[i][c]}'.isNotEmpty && '${linhas[i][c]}' != '-') '${cols[c]}: ${linhas[i][c]}'].join(' · ')),
            trailing: i < links.length && links[i] != null ? const Icon(Icons.chevron_right) : null,
            onTap: i < links.length && links[i] != null && dados.animal(links[i] as String) != null
                ? () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TelaFicha(id: links[i] as String, registrar: widget.registrar)))
                : null,
          ),
        if (linhas.length > 20) Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Text('Mostrando 20 de ${linhas.length}. A planilha traz todas.', style: const TextStyle(color: Cores.apagado))),
      ],
      contador: '${linhas.length}',
      vazio: 'Nada no período.',
    );
  }
}

/// Gráficos simples em barras (linha e rosca do portal viram barras no celular, mais fáceis de ler).
class _Grafico extends StatelessWidget {
  final Map g;
  const _Grafico(this.g);

  @override
  Widget build(BuildContext context) {
    final serie = (g['serie'] as List).cast<Map>();
    final total = serie.fold<num>(0, (s, x) => s + (x['valor'] as num));
    final max = serie.fold<num>(1, (m, x) => (x['valor'] as num) > m ? x['valor'] as num : m);
    final linha = g['tipo'] == 'linha';
    final rosca = g['tipo'] == 'rosca';
    return Secao('${g['titulo']}', [
      if (total == 0)
        const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Text('Sem dados no período.', style: TextStyle(color: Cores.apagado)))
      else if (linha)
        SizedBox(
          height: 120,
          child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
            for (final x in serie)
              Expanded(
                child: Tooltip(
                  message: '${x['rotulo']}: ${x['valor']}',
                  child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
                    if ((x['valor'] as num) > 0) Text('${x['valor']}', style: const TextStyle(fontSize: 10, color: Cores.tinta)),
                    Container(
                      margin: const EdgeInsets.symmetric(horizontal: 1.5),
                      height: 80 * (x['valor'] as num) / max + 2,
                      decoration: BoxDecoration(color: Cores.floresta, borderRadius: BorderRadius.circular(3)),
                    ),
                    const SizedBox(height: 4),
                    Text('${x['rotulo']}'.split('/').first, style: const TextStyle(fontSize: 9, color: Cores.apagado)),
                  ]),
                ),
              ),
          ]),
        )
      else
        for (final x in serie)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(children: [
              SizedBox(width: 120, child: Text('${x['rotulo']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, color: Cores.apagado))),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(99),
                  child: LinearProgressIndicator(
                      value: (x['valor'] as num) / max, minHeight: 10, backgroundColor: Cores.linha, color: rosca ? Cores.dourado : Cores.floresta),
                ),
              ),
              SizedBox(
                  width: 64,
                  child: Text(rosca ? '${x['valor']} (${((x['valor'] as num) / total * 100).round()}%)' : '${x['valor']}',
                      textAlign: TextAlign.right, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13))),
            ]),
          ),
      const SizedBox(height: 6),
    ]);
  }
}
