import 'package:flutter/material.dart';

import '../api.dart';
import '../avisos_celular.dart';
import '../banco.dart';
import '../dados.dart';
import '../regras_app.dart';
import '../sincronizacao.dart';
import '../tema.dart';
import 'inicio_gestor.dart';

/// Entrada do gestor no app (v1.5.0): servidor, e-mail e senha, depois o código do autenticador (2FA).
class TelaEntrarGestor extends StatefulWidget {
  final String servidorInicial;
  const TelaEntrarGestor({super.key, this.servidorInicial = ''});
  @override
  State<TelaEntrarGestor> createState() => _TelaEntrarGestorState();
}

class _TelaEntrarGestorState extends State<TelaEntrarGestor> {
  late final _srv = TextEditingController(text: widget.servidorInicial);
  final _email = TextEditingController(), _senha = TextEditingController(), _codigo = TextEditingController();
  String? _desafio, _erro;
  bool _ocupado = false;

  Future<void> _tentar(Future<void> Function() f) async {
    setState(() {
      _ocupado = true;
      _erro = null;
    });
    try {
      await f();
    } on ApiErro catch (e) {
      setState(() => _erro = e.semConexao ? 'Não foi possível falar com o servidor. Confira a internet e o endereço.' : e.mensagem);
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  String get _servidor => normalizarServidor(_srv.text);

  Future<void> _entrar() => _tentar(() async {
        if (_srv.text.trim().isEmpty || _email.text.trim().isEmpty || _senha.text.isEmpty) {
          throw ApiErro(400, 'Preencha o servidor, o e-mail e a senha.');
        }
        final r = await Api(_servidor).post('/api/app/entrar', {'email': _email.text.trim(), 'senha': _senha.text, 'aparelho': 'Android'});
        setState(() => _desafio = r['desafio'] as String?);
      });

  Future<void> _confirmar() => _tentar(() async {
        final r = await Api(_servidor).post('/api/app/entrar/2fa', {'desafio': _desafio, 'codigo': _codigo.text.replaceAll(' ', '')});
        await Credenciais(_servidor, r['token'] as String, r['nome'] as String? ?? '', perfil: 'gestor').gravar();
        dados.desvinculado = false;
        await AvisosCelular.pedirPermissao();
        await Sincronizador.agendar();
        final s = await Sincronizador.executar();
        await dados.carregar();
        if (!mounted) return;
        Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const TelaInicioGestor(desbloqueado: true)), (_) => false);
        final restantes = r['restantes'];
        if (restantes != null) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Você usou um código de recuperação. Restam $restantes.')));
        } else if (!s.ok) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s.mensagem)));
        }
      });

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Entrar como gestor')),
        body: ListView(padding: const EdgeInsets.all(20), children: [
          if (_desafio == null) ...[
            const Text('Use o mesmo e-mail e senha do Portal do Gestor. Em seguida, o app pede o código do autenticador (2FA).',
                style: TextStyle(color: Cores.apagado)),
            const SizedBox(height: 16),
            TextField(controller: _srv, keyboardType: TextInputType.url, decoration: const InputDecoration(labelText: 'Servidor', hintText: 'Ex.: https://haras360.seudominio.com.br')),
            const SizedBox(height: 12),
            TextField(controller: _email, keyboardType: TextInputType.emailAddress, autocorrect: false, decoration: const InputDecoration(labelText: 'E-mail')),
            const SizedBox(height: 12),
            TextField(controller: _senha, obscureText: true, decoration: const InputDecoration(labelText: 'Senha'), onSubmitted: (_) => _entrar()),
          ] else ...[
            Text('Olá! Digite o código de 6 dígitos do aplicativo autenticador (ou um código de recuperação).', style: const TextStyle(color: Cores.apagado)),
            const SizedBox(height: 16),
            TextField(
                controller: _codigo,
                keyboardType: TextInputType.number,
                autofocus: true,
                decoration: const InputDecoration(labelText: 'Código do autenticador'),
                onSubmitted: (_) => _confirmar()),
          ],
          const SizedBox(height: 16),
          if (_erro != null)
            Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: Cores.atrasadoSuave, borderRadius: BorderRadius.circular(8)),
              child: Text(_erro!, style: const TextStyle(color: Cores.atrasado)),
            ),
          FilledButton(
            onPressed: _ocupado ? null : (_desafio == null ? _entrar : _confirmar),
            child: _ocupado
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : Text(_desafio == null ? 'Continuar' : 'Entrar'),
          ),
          if (_desafio != null)
            TextButton(onPressed: _ocupado ? null : () => setState(() => _desafio = null), child: const Text('Voltar')),
        ]),
      );
}
