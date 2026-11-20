import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';
import 'package:uuid/uuid.dart';

/// Endereço do servidor e token do aparelho, no armazenamento seguro do Android.
class Credenciais {
  static const _s = FlutterSecureStorage(aOptions: AndroidOptions(encryptedSharedPreferences: true));
  final String servidor;
  final String token;
  final String nome;
  Credenciais(this.servidor, this.token, this.nome);

  static Future<Credenciais?> ler() async {
    final v = await _s.readAll();
    if ((v['servidor'] ?? '').isEmpty || (v['token'] ?? '').isEmpty) return null;
    return Credenciais(v['servidor']!, v['token']!, v['nome'] ?? '');
  }

  Future<void> gravar() async {
    await _s.write(key: 'servidor', value: servidor);
    await _s.write(key: 'token', value: token);
    await _s.write(key: 'nome', value: nome);
  }

  /// Esquece só o token: a fila de envio continua guardada para o próximo vínculo.
  static Future<void> esquecerToken() => _s.delete(key: 'token');
}

/// Banco local (SQLite): último estado recebido do servidor, fila de registros e fila de fotos.
class Banco {
  static Database? _db;

  static Future<Database> abrir() async {
    if (_db != null) return _db!;
    final caminho = p.join(await getDatabasesPath(), 'haras360.db');
    _db = await openDatabase(caminho, version: 1, onCreate: (db, _) async {
      await db.execute('CREATE TABLE estado (chave TEXT PRIMARY KEY, valor TEXT NOT NULL)');
      await db.execute('CREATE TABLE fila (id TEXT PRIMARY KEY, corpo TEXT NOT NULL, criado TEXT NOT NULL, '
          'enviado INTEGER NOT NULL DEFAULT 0, erro TEXT)');
      await db.execute('CREATE TABLE fotos (id TEXT PRIMARY KEY, registro_id TEXT NOT NULL, caminho TEXT NOT NULL, '
          'ordem INTEGER NOT NULL, enviada INTEGER NOT NULL DEFAULT 0, erro TEXT)');
    });
    return _db!;
  }

  // ---------- estado e preferências ----------
  static Future<String?> ler(String chave) async {
    final r = await (await abrir()).query('estado', where: 'chave = ?', whereArgs: [chave]);
    return r.isEmpty ? null : r.first['valor'] as String;
  }

  static Future<void> gravar(String chave, String valor) async =>
      (await abrir()).insert('estado', {'chave': chave, 'valor': valor}, conflictAlgorithm: ConflictAlgorithm.replace);

  static Future<Map<String, dynamic>?> estado() async {
    final s = await ler('snapshot');
    return s == null ? null : jsonDecode(s) as Map<String, dynamic>;
  }

  static Future<void> gravarEstado(Map<String, dynamic> e) async {
    await gravar('snapshot', jsonEncode(e));
    await gravar('ultimaSincronizacao', DateTime.now().toIso8601String());
  }

  // ---------- fila de registros ----------
  static Future<void> enfileirar(Map<String, dynamic> registro, List<File> fotos) async {
    final db = await abrir();
    final pasta = Directory(p.join((await getApplicationDocumentsDirectory()).path, 'fotos'));
    await pasta.create(recursive: true);
    await db.transaction((tx) async {
      await tx.insert('fila', {'id': registro['id'], 'corpo': jsonEncode(registro), 'criado': DateTime.now().toIso8601String()});
      for (var i = 0; i < fotos.length; i++) {
        final id = const Uuid().v4().replaceAll('-', '');
        final destino = p.join(pasta.path, '$id.jpg');
        await fotos[i].copy(destino);
        await tx.insert('fotos', {'id': id, 'registro_id': registro['id'], 'caminho': destino, 'ordem': i});
      }
    });
  }

  /// Registros feitos no aparelho e ainda não refletidos no estado baixado do servidor.
  static Future<List<Map<String, dynamic>>> registrosLocais() async {
    final r = await (await abrir()).query('fila', orderBy: 'criado');
    return r.map((x) {
      final m = jsonDecode(x['corpo'] as String) as Map<String, dynamic>;
      m['_enviado'] = x['enviado'] == 1;
      m['_erro'] = x['erro'];
      m['autor'] = 'Você (neste celular)';
      m['origem'] = 'App';
      return m;
    }).toList();
  }

  static Future<List<Map<String, Object?>>> filaPendente() async =>
      (await abrir()).query('fila', where: 'enviado = 0 AND erro IS NULL', orderBy: 'criado');

  static Future<List<Map<String, Object?>>> fotosPendentes() async => (await abrir()).rawQuery(
      'SELECT f.* FROM fotos f JOIN fila r ON r.id = f.registro_id WHERE f.enviada = 0 AND f.erro IS NULL AND r.enviado = 1 ORDER BY r.criado, f.ordem');

  static Future<void> marcarEnviado(String id) async => (await abrir()).update('fila', {'enviado': 1, 'erro': null}, where: 'id = ?', whereArgs: [id]);

  static Future<void> marcarErro(String id, String erro) async => (await abrir()).update('fila', {'erro': erro}, where: 'id = ?', whereArgs: [id]);

  static Future<void> marcarFotoEnviada(String id) async {
    final db = await abrir();
    final r = await db.query('fotos', where: 'id = ?', whereArgs: [id]);
    await db.update('fotos', {'enviada': 1}, where: 'id = ?', whereArgs: [id]);
    if (r.isNotEmpty) {
      final f = File(r.first['caminho'] as String);
      if (await f.exists()) await f.delete();
    }
  }

  static Future<void> marcarFotoErro(String id, String erro) async => (await abrir()).update('fotos', {'erro': erro}, where: 'id = ?', whereArgs: [id]);

  /// Depois de baixar o estado do servidor, os registros já enviados (com todas as fotos) saem da fila local.
  static Future<void> limparEnviados() async {
    final db = await abrir();
    await db.rawDelete('DELETE FROM fotos WHERE enviada = 1 AND registro_id IN (SELECT id FROM fila WHERE enviado = 1)');
    await db.rawDelete('DELETE FROM fila WHERE enviado = 1 AND id NOT IN (SELECT registro_id FROM fotos WHERE enviada = 0)');
  }

  /// Tenta de novo os itens recusados (por exemplo depois de o gestor cadastrar o animal).
  static Future<void> reabrirErros() async {
    final db = await abrir();
    await db.update('fila', {'erro': null}, where: 'erro IS NOT NULL');
    await db.update('fotos', {'erro': null}, where: 'erro IS NOT NULL');
  }

  static Future<void> descartar(String id) async {
    final db = await abrir();
    final fs = await db.query('fotos', where: 'registro_id = ?', whereArgs: [id]);
    for (final f in fs) {
      final a = File(f['caminho'] as String);
      if (await a.exists()) await a.delete();
    }
    await db.delete('fotos', where: 'registro_id = ?', whereArgs: [id]);
    await db.delete('fila', where: 'id = ?', whereArgs: [id]);
  }

  static Future<Map<String, int>> contagem() async {
    final db = await abrir();
    int n(List<Map<String, Object?>> r) => (r.first.values.first as int?) ?? 0;
    return {
      'registros': n(await db.rawQuery('SELECT COUNT(*) FROM fila WHERE enviado = 0 AND erro IS NULL')),
      'fotos': n(await db.rawQuery('SELECT COUNT(*) FROM fotos WHERE enviada = 0 AND erro IS NULL')),
      'erros': n(await db.rawQuery('SELECT COUNT(*) FROM fila WHERE erro IS NOT NULL')) +
          n(await db.rawQuery('SELECT COUNT(*) FROM fotos WHERE erro IS NOT NULL')),
    };
  }
}
