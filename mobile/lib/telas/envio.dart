import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../banco.dart';
import '../config.dart';
import '../dados.dart';
import '../tema.dart';
import 'hoje.dart' show quando;
import 'vincular.dart';

/// Situação do envio: fila, última sincronização, erros, atualização do app e vínculo.
class TelaEnvio extends StatelessWidget {
  const TelaEnvio({super.key});

  Future<void> _sincronizar(BuildContext context) async {
    final r = await dados.sincronizar();
    if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(r.mensagem)));
  }

  Future<void> _atualizar(BuildContext context) async {
    final cred = await Credenciais.ler();
    final url = '${cred?.servidor ?? ''}${dados.app?['url'] ?? '/app/haras360.apk'}';
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(listenable: dados, builder: (context, _) => _corpo(context));

  Widget _corpo(BuildContext context) {
    final c = dados.contagem;
    final locais = dados.locais.where((r) => r['_erro'] != null).toList();
    return ListView(padding: const EdgeInsets.all(16), children: [
      if (dados.atualizacaoDisponivel) ...[
        Card(
          color: Cores.acentoSuave,
          child: ListTile(
            leading: const Icon(Icons.system_update, color: Cores.acento),
            title: Text('Nova versão do app: ${dados.app?['versao']}'),
            subtitle: const Text('Baixe e instale por cima. Seus registros guardados não se perdem.'),
            trailing: FilledButton(onPressed: () => _atualizar(context), child: const Text('Baixar')),
          ),
        ),
        const SizedBox(height: 12),
      ],
      Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Text('Envio para o servidor', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
            const SizedBox(height: 12),
            _linha('Registros aguardando envio', '${c['registros']}'),
            _linha('Fotos aguardando envio', '${c['fotos']}'),
            _linha('Áudios aguardando envio', '${c['audios'] ?? 0}'),
            _linha('Última sincronização', dados.ultimaSinc == null ? 'nunca' : quando(dados.ultimaSinc!)),
            if (dados.ultimoErro.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text('Último problema: ${dados.ultimoErro}', style: const TextStyle(color: Cores.atrasado))),
            const SizedBox(height: 12),
            Text(
                dados.gestor
                    ? 'O envio acontece sozinho, a cada 15 minutos, no Wi-Fi ou nos dados móveis.'
                    : 'O envio acontece sozinho, a cada hora, quando o celular está no Wi-Fi. Dados móveis (3G/4G) não são usados.',
                style: const TextStyle(color: Cores.apagado)),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: dados.sincronizando ? null : () => _sincronizar(context),
              icon: dados.sincronizando ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.sync),
              label: Text(dados.sincronizando ? 'Sincronizando...' : 'Sincronizar agora'),
            ),
          ]),
        ),
      ),
      if (locais.isNotEmpty) ...[
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Text('Recusados pelo servidor', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: Cores.atrasado)),
              const SizedBox(height: 4),
              const Text('Mostre ao gestor. Depois de corrigido no portal, toque em Tentar de novo.', style: TextStyle(color: Cores.apagado)),
              for (final r in locais)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('${dados.animal(r['animalId'] as String?)?['nome'] ?? 'Animal'} · ${r['data']}'),
                  subtitle: Text('${r['_erro']}'),
                  trailing: IconButton(
                    tooltip: 'Descartar',
                    icon: const Icon(Icons.delete_outline),
                    onPressed: () => _descartar(context, r['id'] as String),
                  ),
                ),
              OutlinedButton(
                onPressed: () async {
                  await Banco.reabrirErros();
                  if (context.mounted) await _sincronizar(context);
                },
                child: const Text('Tentar de novo'),
              ),
            ]),
          ),
        ),
      ],
      const SizedBox(height: 12),
      Card(
        child: Column(children: [
          ListTile(title: const Text('Versão do app'), trailing: Text(appVersao)),
          ListTile(
            title: const Text('Vincular de novo'),
            subtitle: const Text('Use se o gestor encerrou o acesso deste celular.'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const TelaVincular())),
          ),
        ]),
      ),
    ]);
  }

  Future<void> _descartar(BuildContext context, String id) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Descartar este registro?'),
        content: const Text('Ele será apagado do celular e não irá para o servidor. Não é possível desfazer.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Descartar')),
        ],
      ),
    );
    if (ok == true) {
      await Banco.descartar(id);
      await dados.carregar();
    }
  }

  static Widget _linha(String l, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(children: [Expanded(child: Text(l)), Text(v, style: const TextStyle(fontWeight: FontWeight.w700))]),
      );
}
