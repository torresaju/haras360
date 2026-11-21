import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:local_auth/local_auth.dart';

import 'tema.dart';

/// Só para o teste no emulador (sem digital nem PIN configurados): --dart-define=SEM_BLOQUEIO=true
const semBloqueio = bool.fromEnvironment('SEM_BLOQUEIO');

/// Proteção do app do gestor (v1.5.0): digital ou bloqueio de tela do Android ao abrir
/// e ao voltar depois de 5 minutos em segundo plano.
class Bloqueio {
  static final _auth = LocalAuthentication();
  static DateTime? _saiu;
  static const espera = Duration(minutes: 5);

  static void foiParaSegundoPlano() => _saiu = DateTime.now();

  /// Precisa pedir de novo ao voltar?
  static bool precisaAoVoltar() => !semBloqueio && _saiu != null && DateTime.now().difference(_saiu!) >= espera;

  /// null = liberado; texto = motivo de não liberar.
  static Future<String?> pedir() async {
    if (semBloqueio) return null;
    try {
      if (!await _auth.isDeviceSupported()) {
        return 'Ative um bloqueio de tela (PIN, padrão ou digital) nas configurações do Android para usar o app do gestor.';
      }
      final ok = await _auth.authenticate(
        localizedReason: 'Confirme que é você para abrir o Haras360',
        options: const AuthenticationOptions(biometricOnly: false, stickyAuth: true),
      );
      if (ok) _saiu = null;
      return ok ? null : 'Não confirmado. Toque em Desbloquear para tentar de novo.';
    } on PlatformException catch (e) {
      if (e.code == 'NotAvailable' || e.code == 'PasscodeNotSet' || e.code == 'NotEnrolled') {
        return 'Ative um bloqueio de tela (PIN, padrão ou digital) nas configurações do Android para usar o app do gestor.';
      }
      return 'Não foi possível confirmar (${e.message ?? e.code}). Tente de novo.';
    }
  }
}

/// Tela de bloqueio: mostrada antes do conteúdo do gestor até a confirmação.
class TelaBloqueio extends StatefulWidget {
  final VoidCallback liberado;
  const TelaBloqueio({super.key, required this.liberado});
  @override
  State<TelaBloqueio> createState() => _TelaBloqueioState();
}

class _TelaBloqueioState extends State<TelaBloqueio> {
  String? _msg;
  bool _ocupado = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _pedir());
  }

  Future<void> _pedir() async {
    if (_ocupado) return;
    setState(() => _ocupado = true);
    final r = await Bloqueio.pedir();
    if (!mounted) return;
    setState(() {
      _ocupado = false;
      _msg = r;
    });
    if (r == null) widget.liberado();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Cores.floresta,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Center(child: Image.asset('recursos/logo-claro.png', width: 96, height: 96)),
              const SizedBox(height: 16),
              const Icon(Icons.lock_outline, color: Cores.dourado, size: 36),
              const SizedBox(height: 12),
              const Text('App do gestor protegido', textAlign: TextAlign.center,
                  style: TextStyle(fontFamily: fonteTitulo, fontWeight: FontWeight.w800, fontSize: 22, color: Cores.florestaTinta)),
              const SizedBox(height: 8),
              Text(_msg ?? 'Use a digital ou o bloqueio de tela do celular.', textAlign: TextAlign.center, style: const TextStyle(color: Cores.florestaApagado)),
              const SizedBox(height: 28),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: Cores.dourado, foregroundColor: Cores.tinta, minimumSize: const Size(48, 54)),
                onPressed: _ocupado ? null : _pedir,
                icon: const Icon(Icons.fingerprint),
                label: const Text('Desbloquear'),
              ),
            ]),
          ),
        ),
      );
}
