import 'package:flutter/material.dart';

import '../api.dart';
import '../banco.dart';
import '../dados.dart';
import '../regras_app.dart';
import '../tema.dart';

/// Vendas no app do gestor (v1.6.0): parcelas de cada venda, registro de pagamento e da
/// transferência na ABCCMM. Consultar funciona sem internet; registrar precisa de internet.
class TelaVendas extends StatefulWidget {
  const TelaVendas({super.key});
  @override
  State<TelaVendas> createState() => _TelaVendasState();
}

class _TelaVendasState extends State<TelaVendas> {
  bool _soPendentes = true, _enviando = false;

  static const meios = ['Pix', 'Transferência', 'Boleto', 'Cheque', 'Dinheiro', 'Cartão'];

  Future<void> _post(String caminho, Map<String, dynamic> corpo) async {
    setState(() => _enviando = true);
    final msg = ScaffoldMessenger.of(context);
    try {
      final c = await Credenciais.ler();
      if (c == null) throw ApiErro(401, 'Sessão encerrada. Entre de novo.');
      final r = await Api(c.servidor, token: c.token).post(caminho, corpo);
      await dados.sincronizar();
      msg.showSnackBar(SnackBar(content: Text('${r['resumo'] ?? 'Alteração salva.'}')));
    } on ApiErro catch (e) {
      msg.showSnackBar(SnackBar(content: Text(e.semConexao ? 'Sem internet. Registrar pagamentos precisa de conexão.' : e.mensagem)));
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  Future<void> _pagar(Map v, Map p) async {
    final valor = TextEditingController(text: ((p['valor'] as num) / 100).toStringAsFixed(2).replaceAll('.', ','));
    String meio = meios.contains(v['meio']) ? v['meio'] as String : meios.first;
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Registrar pagamento'),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${v['animal']} · ${_rotulo(v, p)} · vence ${br('${p['vencimento']}')}', style: const TextStyle(color: Cores.apagado)),
            const SizedBox(height: 12),
            TextField(controller: valor, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Valor recebido (R\$)')),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: meio,
              decoration: const InputDecoration(labelText: 'Meio'),
              items: [for (final m in meios) DropdownMenuItem(value: m, child: Text(m))],
              onChanged: (x) => set(() => meio = x ?? meio),
            ),
            const SizedBox(height: 8),
            Text('Pago hoje, ${br(iso(hoje()))}.', style: const TextStyle(fontSize: 12, color: Cores.apagado)),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancelar')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Registrar')),
          ],
        ),
      ),
    );
    if (ok == true) await _post('/api/parcelas/${p['id']}/pagar', {'data': iso(hoje()), 'valor': valor.text, 'meio': meio});
  }

  static String _rotulo(Map v, Map p) {
    if (p['numero'] == 0) return 'Entrada';
    if (v['forma'] == 'avista') return 'À vista';
    final n = (v['parcelas'] as List).where((x) => (x['numero'] as int) > 0).length;
    return 'Parcela ${p['numero']}/$n';
  }

  Widget _situacao(String s) => switch (s) {
        'paga' => const Etiqueta('Paga', Cores.ok, Cores.okSuave),
        'atrasada' => const Etiqueta('Atrasada', Cores.atrasado, Cores.atrasadoSuave),
        'vence' => const Etiqueta('Vence em 7 dias', Cores.breve, Cores.breveSuave),
        _ => const Etiqueta('Em aberto', Cores.apagado, Cores.superficie2),
      };

  @override
  Widget build(BuildContext context) {
    final todas = dados.vendas.cast<Map>();
    final lista = todas.where((v) => !_soPendentes || (v['saldo'] as num) > 0 || v['transferenciaEm'] == null).toList();
    final abertas = todas.expand((v) => (v['parcelas'] as List).cast<Map>()).where((p) => p['pagoEm'] == null).toList();
    final atrasadas = abertas.where((p) => p['situacao'] == 'atrasada');
    num soma(Iterable<Map> l) => l.fold<num>(0, (s, p) => s + (p['valor'] as num));
    return Stack(children: [
      RefreshIndicator(
        onRefresh: () => dados.sincronizar(),
        child: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 32), children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(reais(soma(abertas)), style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800, color: Cores.floresta)),
                Text('a receber em ${abertas.length} parcela(s)', style: const TextStyle(color: Cores.apagado)),
                if (atrasadas.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text('${atrasadas.length} em atraso: ${reais(soma(atrasadas))}', style: const TextStyle(color: Cores.atrasado, fontWeight: FontWeight.w600)),
                ],
              ]),
            ),
          ),
          const SizedBox(height: 8),
          Row(children: [
            ChoiceChip(label: const Text('Com pendência'), selected: _soPendentes, onSelected: (_) => setState(() => _soPendentes = true)),
            const SizedBox(width: 8),
            ChoiceChip(label: const Text('Todas'), selected: !_soPendentes, onSelected: (_) => setState(() => _soPendentes = false)),
          ]),
          const SizedBox(height: 8),
          if (lista.isEmpty)
            Padding(
              padding: const EdgeInsets.all(24),
              child: Text(todas.isEmpty ? 'Nenhuma venda registrada. As vendas são registradas no portal, em Dar baixa › Venda.' : 'Nenhuma venda com pendência.',
                  textAlign: TextAlign.center, style: const TextStyle(color: Cores.apagado)),
            ),
          for (final v in lista) _cartao(v),
        ]),
      ),
      if (_enviando) const Positioned(left: 0, right: 0, top: 0, child: LinearProgressIndicator()),
    ]);
  }

  Widget _cartao(Map v) {
    final ps = (v['parcelas'] as List).cast<Map>();
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${v['animal']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
          Text('para ${v['comprador']} · ${br('${v['data']}')}', style: const TextStyle(color: Cores.apagado)),
          const SizedBox(height: 4),
          Text('Total ${reais(v['total'] as num)} · recebido ${reais(v['recebido'] as num)}${(v['saldo'] as num) > 0 ? ' · saldo ${reais(v['saldo'] as num)}' : ' · quitada'}'),
          const SizedBox(height: 6),
          if (v['transferenciaEm'] == null)
            Row(children: [
              const Expanded(child: Etiqueta('Comunicar a transferência na ABCCMM', Cores.breve, Cores.breveSuave)),
              TextButton(onPressed: _enviando ? null : () => _post('/api/vendas/${v['id']}/transferencia', {'feita': true}), child: const Text('Feita')),
            ])
          else
            Etiqueta('Transferência comunicada em ${br('${v['transferenciaEm']}')}', Cores.ok, Cores.okSuave),
          const Divider(),
          for (final p in ps)
            ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              title: Text('${_rotulo(v, p)} · ${reais(p['valor'] as num)}'),
              subtitle: Text(p['pagoEm'] != null ? 'Pago em ${br('${p['pagoEm']}')}${'${p['meio'] ?? ''}'.isNotEmpty ? ' · ${p['meio']}' : ''}' : 'Vence em ${br('${p['vencimento']}')}'),
              trailing: p['pagoEm'] != null
                  ? _situacao('paga')
                  : Row(mainAxisSize: MainAxisSize.min, children: [
                      _situacao('${p['situacao']}'),
                      IconButton(tooltip: 'Registrar pagamento', icon: const Icon(Icons.payments_outlined, color: Cores.floresta), onPressed: _enviando ? null : () => _pagar(v, p)),
                    ]),
            ),
        ]),
      ),
    );
  }
}
