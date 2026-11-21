import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:workmanager/workmanager.dart';

import '../api.dart';
import '../avisos_celular.dart';
import '../banco.dart';
import '../config.dart';
import '../dados.dart';
import '../marca.dart';
import '../tema.dart';
import 'avisos.dart';
import 'comum.dart';
import 'envio.dart';
import 'vincular.dart';

/// Aba "Mais" (v1.3.0): avisos, envio para o servidor, versão e vínculo.
/// v1.5.0: preferências de avisos no celular (gestor) e Sair (um perfil por celular).
class TelaMais extends StatelessWidget {
  final Future<void> Function([Map<String, dynamic>? pre]) registrar;
  const TelaMais({super.key, required this.registrar});

  void _abrir(BuildContext context, String titulo, Widget corpo) => Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => Scaffold(appBar: AppBar(title: Text(titulo)), body: ListenableBuilder(listenable: dados, builder: (_, __) => corpo))));

  @override
  Widget build(BuildContext context) {
    final c = dados.contagem;
    final pend = (c['registros'] ?? 0) + (c['fotos'] ?? 0) + (c['audios'] ?? 0);
    Widget item(IconData ic, String t, String sub, VoidCallback onTap, {Widget? fim}) => ListTile(
          leading: Icon(ic, color: Cores.floresta),
          title: Text(t, style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Text(sub),
          trailing: fim ?? const Icon(Icons.chevron_right),
          onTap: onTap,
        );
    return Column(children: [
      const CabecalhoAba('Mais'),
      Expanded(
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Card(
            child: Column(children: [
              item(Icons.notifications_outlined, 'Avisos', '${dados.avisos.length} aviso(s) da última sincronização',
                  () => _abrir(context, 'Avisos', TelaAvisos(registrar: registrar)),
                  fim: dados.avisos.isEmpty ? null : Badge(label: Text('${dados.avisos.length}'))),
              const Divider(height: 1),
              item(Icons.sync, 'Envio', pend > 0 ? '$pend item(ns) aguardando ${dados.gestor ? 'a internet' : 'o Wi-Fi'}' : 'Tudo enviado',
                  () => _abrir(context, 'Envio', const TelaEnvio()),
                  fim: pend > 0 || dados.atualizacaoDisponivel ? Badge(label: Text(pend > 0 ? '$pend' : '!')) : null),
              if (dados.gestor) ...[
                const Divider(height: 1),
                item(Icons.notifications_active_outlined, 'Avisos no celular', 'Tipos de aviso e horário de silêncio',
                    () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const TelaPrefsAvisos()))),
                if (((dados.estado?['normas'] as List?) ?? const []).isNotEmpty) ...[
                  const Divider(height: 1),
                  item(Icons.menu_book_outlined, 'Normas da ABCCMM', 'Estatuto e Regulamento do Registro Genealógico', () => normas(context)),
                ],
              ],
            ]),
          ),
          const SizedBox(height: 12),
          Card(
            child: Column(children: [
              ListTile(leading: const Icon(Icons.info_outline, color: Cores.floresta), title: const Text('Versão do app'), trailing: Text(appVersao)),
              const Divider(height: 1),
              if (!dados.gestor) ...[
                item(Icons.qr_code_scanner, 'Vincular de novo', 'Use se o gestor encerrou o acesso deste celular',
                    () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const TelaVincular()))),
                const Divider(height: 1),
              ],
              item(Icons.logout, 'Sair', dados.gestor ? 'Encerra a sessão do gestor neste celular' : 'Desvincula este celular (para trocar de perfil)',
                  () => sair(context, pend)),
            ]),
          ),
        ]),
      ),
    ]);
  }
}


/// Sair (v1.5.0): só com tudo enviado; encerra a sessão no servidor e apaga os dados deste celular.
Future<void> sair(BuildContext context, int pendentes) async {
  if (pendentes > 0) {
    await showDialog(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Ainda há itens no celular'),
        content: Text('$pendentes item(ns) ainda não foram para o servidor. Envie antes de sair, ou eles serão perdidos.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: const Text('Fechar')),
          FilledButton(
              onPressed: () {
                Navigator.pop(c);
                dados.sincronizar();
              },
              child: const Text('Enviar agora')),
        ],
      ),
    );
    return;
  }
  final ok = await showDialog<bool>(
    context: context,
    builder: (c) => AlertDialog(
      title: const Text('Sair deste celular?'),
      content: Text(dados.gestor
          ? 'A sessão do gestor é encerrada e os dados do haras saem deste celular. Para voltar, entre com e-mail, senha e 2FA.'
          : 'O celular é desvinculado e os dados do haras saem dele. Para voltar, peça um novo QR Code ao gestor.'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancelar')),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Sair')),
      ],
    ),
  );
  if (ok != true) return;
  final c = await Credenciais.ler();
  if (c != null) {
    try {
      await Api(c.servidor, token: c.token).post('/api/app/sair', {});
    } on ApiErro catch (_) {
      // sem internet: a sessão expira sozinha no servidor; o gestor pode encerrá-la em Equipe
    }
  }
  await Workmanager().cancelAll();
  await Banco.limparTudo();
  await Credenciais.apagar();
  await Marca.carregar();
  await dados.carregar();
  if (!context.mounted) return;
  Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const TelaVincular()), (_) => false);
}

/// Preferências dos avisos no celular do gestor (v1.5.0).
class TelaPrefsAvisos extends StatefulWidget {
  const TelaPrefsAvisos({super.key});
  @override
  State<TelaPrefsAvisos> createState() => _TelaPrefsAvisosState();
}

class _TelaPrefsAvisosState extends State<TelaPrefsAvisos> {
  Map<String, dynamic>? _p;

  @override
  void initState() {
    super.initState();
    AvisosCelular.preferencias().then((p) => setState(() => _p = p));
  }

  Future<void> _mudar(String k, dynamic v) async {
    setState(() => _p![k] = v);
    await AvisosCelular.gravarPreferencias(_p!);
  }

  @override
  Widget build(BuildContext context) {
    final p = _p;
    String h(int x) => '${x.toString().padLeft(2, '0')}h';
    return Scaffold(
      appBar: AppBar(title: const Text('Avisos no celular')),
      body: p == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              const Text('O app consulta o servidor a cada 15 minutos e avisa o que for novo. Com o celular em economia de bateria, o Android pode atrasar.',
                  style: TextStyle(color: Cores.apagado)),
              const SizedBox(height: 12),
              Card(
                child: Column(children: [
                  for (final e in AvisosCelular.tipos.entries)
                    SwitchListTile(title: Text(e.value), value: p[e.key] != false, onChanged: (v) => _mudar(e.key, v)),
                ]),
              ),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Text('Horário de silêncio', style: TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 4),
                    const Text('Os avisos desse período chegam quando o silêncio acabar.', style: TextStyle(color: Cores.apagado)),
                    const SizedBox(height: 8),
                    Row(children: [
                      const Text('Das '),
                      DropdownButton<int>(
                          value: p['silencioDe'] as int,
                          items: [for (var i = 0; i < 24; i++) DropdownMenuItem(value: i, child: Text(h(i)))],
                          onChanged: (v) => _mudar('silencioDe', v)),
                      const Text('  às '),
                      DropdownButton<int>(
                          value: p['silencioAte'] as int,
                          items: [for (var i = 0; i < 24; i++) DropdownMenuItem(value: i, child: Text(h(i)))],
                          onChanged: (v) => _mudar('silencioAte', v)),
                    ]),
                    const Text('Horários iguais desligam o silêncio.', style: TextStyle(color: Cores.apagado, fontSize: 12)),
                  ]),
                ),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                  onPressed: () async {
                    final ok = await AvisosCelular.pedirPermissao();
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok ? 'Notificações permitidas.' : 'Permita as notificações do Haras360 nas configurações do Android.')));
                    }
                  },
                  icon: const Icon(Icons.notifications_outlined),
                  label: const Text('Permitir notificações')),
            ]),
    );
  }
}


/// Normas oficiais da ABCCMM (v1.5.1): links do administrador, abertos no navegador do celular.
void normas(BuildContext context) => showModalBottomSheet(
      context: context,
      builder: (c) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 18, 20, 4),
            child: Text('Normas oficiais da ABCCMM', style: TextStyle(fontFamily: fonteTitulo, fontWeight: FontWeight.w800, fontSize: 18)),
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 0, 20, 8),
            child: Text('Abre no navegador. Os documentos são mantidos pela ABCCMM.', style: TextStyle(color: Cores.apagado)),
          ),
          for (final n in ((dados.estado?['normas'] as List?) ?? const []).cast<Map>())
            ListTile(
              leading: const Icon(Icons.description_outlined, color: Cores.floresta),
              title: Text('${n['titulo']}'),
              trailing: const Icon(Icons.open_in_new, size: 18),
              onTap: () {
                Navigator.pop(c);
                launchUrl(Uri.parse('${n['url']}'), mode: LaunchMode.externalApplication);
              },
            ),
          const SizedBox(height: 8),
        ]),
      ),
    );
