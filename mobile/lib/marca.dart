import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import 'api.dart';
import 'banco.dart';

/// Imagens de personalização (v1.3.0): fundo do app e logotipo do haras, baixados na
/// sincronização pelo Wi-Fi e guardados no celular para funcionar offline.
class Marca {
  static File? fundoApp;
  static File? logoHaras;

  static Future<Directory> _pasta() async {
    final d = Directory(p.join((await getApplicationDocumentsDirectory()).path, 'marca'));
    await d.create(recursive: true);
    return d;
  }

  /// Lê do celular o que já foi baixado.
  static Future<void> carregar() async {
    fundoApp = await _arquivo('img_app');
    logoHaras = await _arquivo('img_logo');
  }

  static Future<File?> _arquivo(String chave) async {
    final c = await Banco.ler('$chave:arquivo');
    if (c == null || c.isEmpty) return null;
    final f = File(c);
    return await f.exists() ? f : null;
  }

  /// Baixa só o que mudou. Falhas aqui não atrapalham a sincronização dos registros.
  static Future<void> atualizar(Api api, Map<String, dynamic> estado) async {
    final imagens = (estado['imagens'] as Map?) ?? const {};
    final app = imagens['app'] as Map?;
    await _sincronizar(api, 'img_app', app?['url'] as String?);
    final logo = (estado['haras'] as Map?)?['logo'] as String?;
    await _sincronizar(api, 'img_logo', (logo == null || logo.isEmpty) ? null : logo);
    await carregar();
  }

  static Future<void> _sincronizar(Api api, String chave, String? url) async {
    final atual = await Banco.ler('$chave:url') ?? '';
    if ((url ?? '') == atual) return;
    final anterior = await Banco.ler('$chave:arquivo');
    if (url == null) {
      await Banco.gravar('$chave:url', '');
      await Banco.gravar('$chave:arquivo', '');
    } else {
      final bytes = await api.baixar(url);
      final destino = File(p.join((await _pasta()).path, '$chave-${DateTime.now().millisecondsSinceEpoch}'));
      await destino.writeAsBytes(bytes);
      await Banco.gravar('$chave:url', url);
      await Banco.gravar('$chave:arquivo', destino.path);
    }
    if (anterior != null && anterior.isNotEmpty) {
      final f = File(anterior);
      if (await f.exists()) await f.delete();
    }
  }
}

/// Fundo com a imagem do haras (ou da plataforma) ou a ilustração padrão do Haras360.
class FundoMarca extends StatelessWidget {
  final bool faixa;
  const FundoMarca({super.key, this.faixa = false});

  @override
  Widget build(BuildContext context) {
    final f = Marca.fundoApp;
    if (f != null) return Image.file(f, fit: BoxFit.cover, alignment: Alignment.center, errorBuilder: (_, __, ___) => _padrao());
    return _padrao();
  }

  Widget _padrao() => Image.asset(faixa ? 'recursos/ilustracao-cabecalho.png' : 'recursos/ilustracao-app.png',
      fit: BoxFit.cover, alignment: faixa ? Alignment.center : Alignment.bottomCenter);
}

/// Logotipo do haras (se houver) ou o símbolo do Haras360.
class LogoHaras extends StatelessWidget {
  final double tamanho;
  const LogoHaras({super.key, this.tamanho = 44});

  @override
  Widget build(BuildContext context) {
    final f = Marca.logoHaras;
    if (f == null) return Image.asset('recursos/logo-claro.png', width: tamanho, height: tamanho);
    return Container(
      height: tamanho,
      constraints: BoxConstraints(minWidth: tamanho, maxWidth: tamanho * 2.4),
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(10)),
      child: Image.file(f, fit: BoxFit.contain, errorBuilder: (_, __, ___) => Image.asset('recursos/logo-claro.png')),
    );
  }
}
