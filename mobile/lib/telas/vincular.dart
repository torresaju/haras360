import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../api.dart';
import '../banco.dart';
import '../dados.dart';
import '../regras_app.dart';
import '../sincronizacao.dart';
import '../tema.dart';
import 'inicio.dart';

/// Primeiro acesso: vínculo do celular pelo QR Code do gestor (ou e-mail e senha). Exige conexão.
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
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Spacer(),
              Center(child: ClipRRect(borderRadius: BorderRadius.circular(18), child: Image.asset('recursos/icone/mipmap-xxxhdpi/ic_launcher.png', width: 88, height: 88))),
              const SizedBox(height: 16),
              const Text('Haras360 Campo', textAlign: TextAlign.center, style: TextStyle(color: Cores.florestaTinta, fontSize: 28, fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              const Text('Peça ao gestor o QR Code em Equipe › Vincular celular. Faça o vínculo no Wi-Fi do haras; depois o app funciona sem internet.',
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
                onPressed: _ocupado ? null : _lerQr,
                icon: _ocupado ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.qr_code_scanner),
                label: Text(_ocupado ? 'Vinculando...' : 'Ler QR Code'),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: _ocupado ? null : _digitar,
                child: const Text('Sem câmera? Digitar código ou entrar com e-mail', style: TextStyle(color: Cores.florestaTinta)),
              ),
            ]),
          ),
        ),
      );
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
