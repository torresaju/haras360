import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../api.dart';
import '../banco.dart';
import '../dados.dart';
import '../regras_app.dart';
import '../sincronizacao.dart';
import '../marca.dart';
import '../tema.dart';
import 'entrar_gestor.dart';
import 'inicio.dart';

/// Primeiro acesso: caseiro vincula pelo QR Code do gestor (ou código, ou e-mail e senha);
/// gestor entra com e-mail, senha e 2FA (v1.5.0). Exige conexão.
class TelaVincular extends StatefulWidget {
  const TelaVincular({super.key});
  @override
  State<TelaVincular> createState() => _TelaVincularState();
}

class _TelaVincularState extends State<TelaVincular> {
  bool _ocupado = false;
  String? _erro;

  Future<void> _concluir(String servidor, Map<String, dynamic> r) async {
    await Credenciais(servidor, r['token'] as String, r['nome'] as String? ?? '').gravar();
    dados.desvinculado = false;
    await Sincronizador.agendar();
    final s = await Sincronizador.executar();
    await dados.carregar();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const TelaInicio()), (_) => false);
    if (!s.ok) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Celular vinculado. ${s.mensagem}')));
    }
  }

  Future<void> _tentar(Future<void> Function() f) async {
    setState(() {
      _ocupado = true;
      _erro = null;
    });
    try {
      await f();
    } on ApiErro catch (e) {
      setState(() => _erro = e.semConexao ? 'Não foi possível falar com o servidor. Confira o Wi-Fi e o endereço.' : e.mensagem);
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  Future<void> _vincular(DadosVinculo v) => _tentar(() async {
        final r = await Api(v.servidor).post('/api/app/vincular', {'codigo': v.codigo, 'aparelho': 'Android'});
        await _concluir(v.servidor, r);
      });

  Future<void> _lerQr() async {
    final lido = await Navigator.of(context).push<String>(MaterialPageRoute(builder: (_) => const _Leitor()));
    if (lido == null) return;
    final v = lerQrVinculo(lido);
    if (v == null) {
      setState(() => _erro = 'Este QR Code não é de vínculo do Haras360. No portal do gestor: Equipe › Vincular celular.');
      return;
    }
    await _vincular(v);
  }

  void _digitar() => showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        builder: (_) => _FormDigitar(onCodigo: (s, c) => _vincular(DadosVinculo(normalizarServidor(s), c.trim())), onSenha: (s, e, p) {
          final srv = normalizarServidor(s);
          return _tentar(() async {
            final r = await Api(srv).post('/api/login', {'email': e.trim(), 'senha': p, 'app': true});
            await _concluir(srv, r);
          });
        }),
      );

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Cores.floresta,
        body: Stack(fit: StackFit.expand, children: [
          const FundoMarca(),
          const DecoratedBox(
              decoration: BoxDecoration(
                  gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [Color(0xF2102419), Color(0x80102419), Color(0xF5102419)], stops: [0, .5, .85]))),
          SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const SizedBox(height: 24),
              Center(child: Image.asset('recursos/logo-claro.png', width: 110, height: 110)),
              const SizedBox(height: 8),
              const Text.rich(TextSpan(children: [
                TextSpan(text: 'Haras', style: TextStyle(color: Cores.florestaTinta)),
                TextSpan(text: '360', style: TextStyle(color: Cores.dourado)),
              ]), textAlign: TextAlign.center, style: TextStyle(fontFamily: fonteTitulo, fontSize: 38, fontWeight: FontWeight.w800)),
              const Text('GESTÃO DE HARAS', textAlign: TextAlign.center, style: TextStyle(color: Cores.florestaApagado, fontSize: 12, letterSpacing: 4)),
              const Spacer(),
              const SizedBox(height: 8),
              const Text('Sou caseiro: peça ao gestor o QR Code em Equipe › Vincular celular. Faça o vínculo no Wi-Fi do haras; depois o app funciona sem internet.',
                  textAlign: TextAlign.center, style: TextStyle(color: Cores.florestaApagado)),
              const Spacer(),
              if (_erro != null)
                Container(
                  margin: const EdgeInsets.only(bottom: 16),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: Cores.atrasadoSuave, borderRadius: BorderRadius.circular(8)),
                  child: Text(_erro!, style: const TextStyle(color: Cores.atrasado)),
                ),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: Cores.dourado, foregroundColor: Cores.tinta, minimumSize: const Size(48, 54)),
                onPressed: _ocupado ? null : _lerQr,
                icon: _ocupado ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Cores.tinta)) : const Icon(Icons.qr_code_scanner),
                label: Text(_ocupado ? 'Vinculando...' : 'Ler QR Code'),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: _ocupado ? null : _digitar,
                child: const Text('Sem câmera? Digitar código ou entrar com e-mail', style: TextStyle(color: Cores.florestaTinta)),
              ),
              const SizedBox(height: 4),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(foregroundColor: Cores.florestaTinta, side: const BorderSide(color: Cores.florestaApagado), minimumSize: const Size(48, 50)),
                onPressed: _ocupado ? null : () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const TelaEntrarGestor())),
                icon: const Icon(Icons.manage_accounts_outlined),
                label: const Text('Sou gestor: entrar com e-mail e 2FA'),
              ),
            ]),
          ),
        ),
      ]));
}

class _Leitor extends StatefulWidget {
  const _Leitor();
  @override
  State<_Leitor> createState() => _LeitorState();
}

class _LeitorState extends State<_Leitor> {
  final _ctrl = MobileScannerController(formats: const [BarcodeFormat.qrCode]);
  bool _lido = false;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Aponte para o QR Code')),
        body: MobileScanner(
          controller: _ctrl,
          onDetect: (c) {
            final v = c.barcodes.isEmpty ? null : c.barcodes.first.rawValue;
            if (v == null || _lido) return;
            _lido = true;
            Navigator.of(context).pop(v);
          },
        ),
      );
}

class _FormDigitar extends StatefulWidget {
  final void Function(String servidor, String codigo) onCodigo;
  final Future<void> Function(String servidor, String email, String senha) onSenha;
  const _FormDigitar({required this.onCodigo, required this.onSenha});
  @override
  State<_FormDigitar> createState() => _FormDigitarState();
}

class _FormDigitarState extends State<_FormDigitar> {
  final _srv = TextEditingController(), _cod = TextEditingController(), _email = TextEditingController(), _senha = TextEditingController();
  bool _porSenha = false;

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.fromLTRB(20, 20, 20, 20 + MediaQuery.of(context).viewInsets.bottom),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          SegmentedButton<bool>(
            segments: const [ButtonSegment(value: false, label: Text('Código')), ButtonSegment(value: true, label: Text('E-mail e senha'))],
            selected: {_porSenha},
            onSelectionChanged: (s) => setState(() => _porSenha = s.first),
          ),
          const SizedBox(height: 16),
          TextField(controller: _srv, keyboardType: TextInputType.url, decoration: const InputDecoration(labelText: 'Servidor', hintText: 'Ex.: 129.80.10.20:8090')),
          const SizedBox(height: 12),
          if (!_porSenha) TextField(controller: _cod, decoration: const InputDecoration(labelText: 'Código do QR Code')),
          if (_porSenha) ...[
            TextField(controller: _email, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'E-mail')),
            const SizedBox(height: 12),
            TextField(controller: _senha, obscureText: true, decoration: const InputDecoration(labelText: 'Senha')),
          ],
          const SizedBox(height: 16),
          FilledButton(
            onPressed: () {
              Navigator.of(context).pop();
              if (_porSenha) {
                widget.onSenha(_srv.text, _email.text, _senha.text);
              } else {
                widget.onCodigo(_srv.text, _cod.text);
              }
            },
            child: const Text('Vincular'),
          ),
        ]),
      );
}
