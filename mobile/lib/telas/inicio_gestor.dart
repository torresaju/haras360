import 'package:flutter/material.dart';

import '../avisos_celular.dart';
import '../banco.dart';
import '../bloqueio.dart';
import '../dados.dart';
import '../sincronizacao.dart';
import '../tema.dart';
import 'agenda.dart';
import 'animais.dart';
import 'dashboard.dart';
import 'inicio.dart';
import 'mais.dart';
import 'registro.dart';
import 'relatorios.dart';
import 'vincular.dart';

/// App do gestor (v1.5.0): Dashboard, Animais, Agenda, Relatórios e Mais, protegido por digital ou PIN.
class TelaInicioGestor extends StatefulWidget {
  final bool desbloqueado;
  const TelaInicioGestor({super.key, this.desbloqueado = false});
  @override
  State<TelaInicioGestor> createState() => _TelaInicioGestorState();
}

class _TelaInicioGestorState extends State<TelaInicioGestor> with WidgetsBindingObserver {
  int _aba = 0;
  late bool _liberado = widget.desbloqueado || semBloqueio;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    AvisosCelular.animalTocado.addListener(_abrirDoAviso);
    if (_liberado) _aoAbrir();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    AvisosCelular.animalTocado.removeListener(_abrirDoAviso);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.paused) Bloqueio.foiParaSegundoPlano();
    if (s == AppLifecycleState.resumed) {
      if (Bloqueio.precisaAoVoltar()) {
        setState(() => _liberado = false);
      } else if (_liberado) {
        _aoAbrir();
      }
    }
  }

  void _liberar() {
    setState(() => _liberado = true);
    _aoAbrir();
  }

  /// Ao abrir com internet (Wi-Fi ou 4G), sincroniza em silêncio.
  Future<void> _aoAbrir() async {
    await dados.carregar();
    if (await Sincronizador.redeLiberada(gestor: true)) await dados.sincronizar();
    if (dados.desvinculado && mounted) _avisarSaida();
    _abrirDoAviso();
  }

  void _abrirDoAviso() {
    final id = AvisosCelular.animalTocado.value;
    if (id == null || !_liberado || !mounted || dados.animal(id) == null) return;
    AvisosCelular.animalTocado.value = null;
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => TelaFicha(id: id, registrar: registrar)));
  }

  void _avisarSaida() => showDialog(
        context: context,
        barrierDismissible: false,
        builder: (c) => AlertDialog(
          title: const Text('Sessão encerrada'),
          content: const Text('A sessão deste celular expirou ou foi encerrada (troca de senha, 2FA redefinido ou acesso desativado). '
              'Os registros que ainda não foram enviados continuam guardados. Entre de novo com e-mail, senha e 2FA.'),
          actions: [
            FilledButton(
              onPressed: () => Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const TelaVincular()), (_) => false),
              child: const Text('Entrar de novo'),
            ),
          ],
        ),
      );

  Future<void> registrar([Map<String, dynamic>? pre]) async {
    final ok = await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => TelaRegistro(pre: pre ?? const {})));
    if (ok == true) {
      await dados.carregar();
      if (!mounted) return;
      final rede = await Sincronizador.redeLiberada(gestor: true);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(rede ? 'Registro salvo. Enviando...' : 'Registro salvo no celular. Vai para o servidor quando a internet voltar.')));
      if (rede) dados.sincronizar();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_liberado) return TelaBloqueio(liberado: _liberar);
    return ListenableBuilder(
      listenable: dados,
      builder: (context, _) {
        final pend = (dados.contagem['registros'] ?? 0) + (dados.contagem['fotos'] ?? 0) + (dados.contagem['audios'] ?? 0);
        final alertaMais = pend > 0 || dados.atualizacaoDisponivel;
        final telas = [
          TelaDashboard(registrar: registrar),
          TelaAnimais(registrar: registrar),
          TelaAgenda(registrar: registrar),
          TelaRelatorios(registrar: registrar),
          TelaMais(registrar: registrar),
        ];
        return Scaffold(
          body: dados.estado == null
              ? SafeArea(
                  child: Center(
                      child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Column(mainAxisSize: MainAxisSize.min, children: [
                            const Text('Ainda sem dados do haras. Conecte à internet e sincronize.', textAlign: TextAlign.center),
                            const SizedBox(height: 16),
                            FilledButton.icon(onPressed: dados.sincronizando ? null : dados.sincronizar, icon: const Icon(Icons.sync), label: const Text('Sincronizar agora')),
                          ]))))
              : telas[_aba],
          floatingActionButton: (_aba == 0 || _aba == 1) && dados.estado != null
              ? FloatingActionButton.extended(
                  onPressed: () => registrar(), icon: const Icon(Icons.add), label: const Text('Registrar'), backgroundColor: Cores.floresta, foregroundColor: Colors.white)
              : null,
          bottomNavigationBar: NavigationBar(
            selectedIndex: _aba,
            onDestinationSelected: (i) => setState(() => _aba = i),
            destinations: [
              const NavigationDestination(icon: Icon(Icons.dashboard_outlined), selectedIcon: Icon(Icons.dashboard), label: 'Dashboard'),
              const NavigationDestination(icon: Icon(Icons.pets_outlined), selectedIcon: Icon(Icons.pets), label: 'Animais'),
              const NavigationDestination(icon: Icon(Icons.calendar_month_outlined), selectedIcon: Icon(Icons.calendar_month), label: 'Agenda'),
              const NavigationDestination(icon: Icon(Icons.bar_chart_outlined), selectedIcon: Icon(Icons.bar_chart), label: 'Relatórios'),
              NavigationDestination(icon: Badge(isLabelVisible: alertaMais, label: Text(pend > 0 ? '$pend' : '!'), child: const Icon(Icons.more_horiz)), label: 'Mais'),
            ],
          ),
        );
      },
    );
  }
}

/// Primeira tela conforme o perfil gravado no celular.
Future<Widget> telaInicial() async {
  final c = await Credenciais.ler();
  if (c == null) return const TelaVincular();
  return c.gestor ? const TelaInicioGestor() : const TelaInicio();
}
