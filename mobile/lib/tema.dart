import 'package:flutter/material.dart';

// Identidade v1.3.0 (mesma dos portais): verde haras, dourado, areia, grafite e verde sálvia.
class Cores {
  static const fundo = Color(0xFFF3F1E9); // areia
  static const superficie = Color(0xFFFFFFFF);
  static const superficie2 = Color(0xFFF7F5EE);
  static const tinta = Color(0xFF292F2B); // grafite
  static const apagado = Color(0xFF5C6A61);
  static const linha = Color(0xFFE2DED1);
  static const floresta = Color(0xFF193D30); // verde haras
  static const floresta2 = Color(0xFF22503F);
  static const florestaTinta = Color(0xFFF3F1E9);
  static const florestaApagado = Color(0xFFA9BBAF);
  static const salvia = Color(0xFF82978A);
  static const dourado = Color(0xFFD5A064);
  static const douradoTexto = Color(0xFF8A5E26);
  static const acento = floresta; // botões principais
  static const acentoSuave = Color(0xFFF6EBDC);
  static const atrasado = Color(0xFFB3261E);
  static const atrasadoSuave = Color(0xFFF9E3DF);
  static const breve = Color(0xFF8F5A0B);
  static const breveSuave = Color(0xFFFBEED7);
  static const ok = Color(0xFF2E6B45);
  static const okSuave = Color(0xFFDDEFE3);
  static const repro = Color(0xFF6B4E8C);
  static const reproSuave = Color(0xFFEEE8F5);
}

const fonteTitulo = 'Manrope';

ThemeData tema() {
  final esquema = ColorScheme.fromSeed(seedColor: Cores.floresta, primary: Cores.floresta, secondary: Cores.acento, surface: Cores.superficie);
  final base = ThemeData(useMaterial3: true, colorScheme: esquema, fontFamily: 'Inter');
  TextStyle? t(TextStyle? x) => x?.copyWith(fontFamily: fonteTitulo, fontWeight: FontWeight.w800, color: Cores.tinta);
  return base.copyWith(
    textTheme: base.textTheme.copyWith(
      headlineLarge: t(base.textTheme.headlineLarge),
      headlineMedium: t(base.textTheme.headlineMedium),
      headlineSmall: t(base.textTheme.headlineSmall),
      titleLarge: t(base.textTheme.titleLarge),
    ),
    scaffoldBackgroundColor: Cores.fundo,
    appBarTheme: const AppBarTheme(backgroundColor: Cores.floresta, foregroundColor: Cores.florestaTinta, elevation: 0,
        titleTextStyle: TextStyle(fontFamily: fonteTitulo, fontWeight: FontWeight.w800, fontSize: 19, color: Cores.florestaTinta)),
    cardTheme: const CardTheme(
      color: Cores.superficie,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(side: BorderSide(color: Cores.linha), borderRadius: BorderRadius.all(Radius.circular(16))),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(backgroundColor: Cores.floresta, foregroundColor: Colors.white, minimumSize: const Size(48, 48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)), textStyle: const TextStyle(fontWeight: FontWeight.w700)),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48))),
    inputDecorationTheme: const InputDecorationTheme(
      border: OutlineInputBorder(),
      filled: true,
      fillColor: Colors.white,
      isDense: true,
    ),
    navigationBarTheme: const NavigationBarThemeData(backgroundColor: Cores.superficie, indicatorColor: Cores.acentoSuave, surfaceTintColor: Colors.transparent),
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
