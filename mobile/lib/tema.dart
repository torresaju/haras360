import 'package:flutter/material.dart';

// Mesma paleta do Portal Campo.
class Cores {
  static const fundo = Color(0xFFECEEE8);
  static const superficie = Color(0xFFFAFBF7);
  static const superficie2 = Color(0xFFF1F3ED);
  static const tinta = Color(0xFF1B231E);
  static const apagado = Color(0xFF58645C);
  static const linha = Color(0xFFD4D9CF);
  static const floresta = Color(0xFF1E3A2B);
  static const florestaTinta = Color(0xFFE8F0E9);
  static const florestaApagado = Color(0xFFA3BAA9);
  static const acento = Color(0xFF96541D);
  static const acentoSuave = Color(0xFFF2E4D4);
  static const atrasado = Color(0xFFB3261E);
  static const atrasadoSuave = Color(0xFFF9E2DF);
  static const breve = Color(0xFF9A6700);
  static const breveSuave = Color(0xFFFBEFD5);
  static const ok = Color(0xFF2E6B45);
  static const okSuave = Color(0xFFDDEFE3);
}

ThemeData tema() {
  final esquema = ColorScheme.fromSeed(seedColor: Cores.floresta, primary: Cores.floresta, secondary: Cores.acento, surface: Cores.superficie);
  return ThemeData(
    useMaterial3: true,
    colorScheme: esquema,
    scaffoldBackgroundColor: Cores.fundo,
    appBarTheme: const AppBarTheme(backgroundColor: Cores.floresta, foregroundColor: Cores.florestaTinta, elevation: 0),
    cardTheme: const CardTheme(
      color: Cores.superficie,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(side: BorderSide(color: Cores.linha), borderRadius: BorderRadius.all(Radius.circular(12))),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(backgroundColor: Cores.acento, foregroundColor: Colors.white, minimumSize: const Size(48, 48)),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48))),
    inputDecorationTheme: const InputDecorationTheme(
      border: OutlineInputBorder(),
      filled: true,
      fillColor: Colors.white,
      isDense: true,
    ),
    navigationBarTheme: const NavigationBarThemeData(backgroundColor: Cores.superficie, indicatorColor: Cores.acentoSuave),
  );
}

/// Etiqueta de situação (atrasado, hoje, próximos dias).
class Etiqueta extends StatelessWidget {
  final String texto;
  final Color cor;
  final Color fundo;
  const Etiqueta(this.texto, this.cor, this.fundo, {super.key});

  factory Etiqueta.status(String s, String rel) => switch (s) {
        'atrasado' => Etiqueta('Atrasado · $rel', Cores.atrasado, Cores.atrasadoSuave),
        'hoje' => const Etiqueta('Hoje', Cores.breve, Cores.breveSuave),
        'semana' => Etiqueta(rel, Cores.breve, Cores.breveSuave),
        _ => Etiqueta(rel, Cores.apagado, Cores.superficie2),
      };

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(color: fundo, borderRadius: BorderRadius.circular(99)),
        child: Text(texto, style: TextStyle(color: cor, fontSize: 12, fontWeight: FontWeight.w600)),
      );
}
