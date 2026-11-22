import 'package:flutter/foundation.dart';

import 'banco.dart';
import 'config.dart';
import 'regras_app.dart';
import 'sincronizacao.dart';

/// Estado da tela: último retrato do servidor + registros feitos no aparelho.
class Dados extends ChangeNotifier {
  Map<String, dynamic>? estado;
  List<Map<String, dynamic>> locais = [];
  Map<String, int> contagem = {'registros': 0, 'fotos': 0, 'audios': 0, 'erros': 0};
  DateTime? ultimaSinc;
  String ultimoErro = '';
  bool sincronizando = false;
  bool desvinculado = false;

  /// Perfil deste celular (v1.5.0): "operador" (caseiro) ou "gestor".
  String perfil = 'operador';
  /// Servidor e token deste celular (para baixar fotos e áudios do prontuário).
  Credenciais? cred;
  bool get gestor => perfil == 'gestor';

  List get animais => (estado?['animais'] as List?)?.where((a) => a['vivo'] == true).toList() ?? const [];
  /// Todos os animais, inclusive inativos e baixados (filtro do gestor).
  List get todosAnimais => (estado?['animais'] as List?) ?? const [];
  /// Animais do haras, sem os externos (v1.6.0: garanhões e éguas de fora, só para reprodução).
  List get doHaras => todosAnimais.where((a) => a['externo'] != true).toList();
  /// Vendas com parcelas (v1.6.0, só o gestor recebe).
  List get vendas => (estado?['vendas'] as List?) ?? const [];
  bool get relatoriosLiberado => estado?['relatorios'] == true;
  List get registros => (estado?['registros'] as List?) ?? const [];
  List get protocolos => (estado?['protocolos'] as List?) ?? const [];
  /// Avisos da última sincronização, sem os de campo e documentação e sem os já atendidos neste celular.
  List get avisos => ((estado?['notificacoes'] as List?) ?? const [])
      .where((n) => n['tipo'] != 'campo' && n['tipo'] != 'documental')
      .where((n) => n['tarefa'] == null || !locais.any((r) => r['_erro'] == null && registroAtende(n['tarefa'] as Map, r)))
      .toList();
  Map get haras => (estado?['haras'] as Map?) ?? const {};
  Map? get app => estado?['app'] as Map?;

  /// Áudio nos registros: liberado pelo plano e duração máxima (parametrização global).
  bool get audioLiberado => (estado?['audio'] as Map?)?['liberado'] != false;
  int get audioMaxSeg => ((estado?['audio'] as Map?)?['maxSeg'] as int?) ?? 120;
  bool get atualizacaoDisponivel => haAtualizacao(app, appCodigo);

  List<Map<String, dynamic>> get tarefas => tarefasPendentes((estado?['tarefas'] as List?) ?? const [], locais.where((r) => r['_erro'] == null).toList());

  Map? animal(String? id) => todosAnimais.cast<Map?>().firstWhere((a) => a?['id'] == id, orElse: () => null);

  /// Histórico do animal: registros do servidor e os feitos neste celular, mais recentes primeiro.
  List<Map> historico(String id) {
    final srv = ((estado?['registros'] as List?) ?? const []).cast<Map>().where((r) => r['animalId'] == id);
    final ids = srv.map((r) => r['id']).toSet();
    final loc = locais.where((r) => r['animalId'] == id && !ids.contains(r['id']));
    final l = [...loc, ...srv];
    l.sort((a, b) => (b['data'] as String).compareTo(a['data'] as String));
    return l;
  }

  Map? gestacao(String id) => (estado?['gestacoes'] as Map?)?[id] as Map?;

  Future<void> carregar() async {
    perfil = await Credenciais.perfilSalvo();
    cred = await Credenciais.ler();
    estado = await Banco.estado();
    locais = await Banco.registrosLocais();
    contagem = await Banco.contagem();
    ultimaSinc = DateTime.tryParse(await Banco.ler('ultimaSincronizacao') ?? '');
    ultimoErro = await Banco.ler('ultimoErro') ?? '';
    notifyListeners();
  }

  Future<ResultadoSinc> sincronizar() async {
    sincronizando = true;
    notifyListeners();
    try {
      final r = await Sincronizador.executar();
      if (r.desvinculado) desvinculado = true;
      return r;
    } finally {
      sincronizando = false;
      await carregar();
    }
  }
}

final dados = Dados();
