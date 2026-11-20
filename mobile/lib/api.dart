import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

class ApiErro implements Exception {
  final int status;
  final String mensagem;
  ApiErro(this.status, this.mensagem);

  /// Sem resposta do servidor (sem rede, servidor fora do ar, tempo esgotado).
  bool get semConexao => status == 0;

  /// O aparelho perdeu o acesso (sessão encerrada pelo gestor, usuário desativado).
  bool get desvinculado => status == 401 || status == 403;

  /// O servidor recusou o conteúdo; reenviar igual não adianta.
  bool get recusado => status == 400 || status == 404 || status == 409 || status == 422;

  @override
  String toString() => mensagem;
}

class Api {
  final String servidor;
  final String? token;
  final http.Client _c;
  static const tempo = Duration(seconds: 30);

  Api(this.servidor, {this.token, http.Client? cliente}) : _c = cliente ?? http.Client();

  Map<String, String> get _cab => {
        'X-Haras360': '1',
        'X-Portal': 'app',
        'Accept': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Uri _u(String caminho) => Uri.parse('$servidor$caminho');

  Future<Map<String, dynamic>> get(String caminho) => _exec(() => _c.get(_u(caminho), headers: _cab));

  Future<Map<String, dynamic>> post(String caminho, Map<String, dynamic> corpo) =>
      _exec(() => _c.post(_u(caminho), headers: {..._cab, 'Content-Type': 'application/json'}, body: jsonEncode(corpo)));

  Future<Map<String, dynamic>> enviarFoto(String registroId, String fotoId, int ordem, File arquivo) => _exec(() async {
        final req = http.MultipartRequest('POST', _u('/api/app/fotos'))
          ..headers.addAll(_cab)
          ..fields['registroId'] = registroId
          ..fields['fotoId'] = fotoId
          ..fields['ordem'] = '$ordem'
          ..files.add(await http.MultipartFile.fromPath('arquivo', arquivo.path, filename: '$fotoId.jpg'));
        return http.Response.fromStream(await _c.send(req).timeout(const Duration(minutes: 2)));
      });

  Future<Map<String, dynamic>> _exec(Future<http.Response> Function() f) async {
    http.Response r;
    try {
      r = await f().timeout(const Duration(minutes: 2));
    } on SocketException {
      throw ApiErro(0, 'Sem conexão com o servidor.');
    } on HttpException {
      throw ApiErro(0, 'Sem conexão com o servidor.');
    } on http.ClientException {
      throw ApiErro(0, 'Sem conexão com o servidor.');
    } on TimeoutException {
      throw ApiErro(0, 'O servidor demorou a responder.');
    }
    dynamic corpo;
    try {
      corpo = r.body.isEmpty ? {} : jsonDecode(utf8.decode(r.bodyBytes));
    } on FormatException {
      corpo = {};
    }
    if (r.statusCode >= 200 && r.statusCode < 300) {
      return corpo is Map<String, dynamic> ? corpo : {'dados': corpo};
    }
    final msg = corpo is Map && corpo['detail'] is String ? corpo['detail'] as String : 'Erro ${r.statusCode} no servidor.';
    throw ApiErro(r.statusCode, msg);
  }
}
