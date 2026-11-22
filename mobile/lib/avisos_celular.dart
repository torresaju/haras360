import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import 'banco.dart';
import 'regras_app.dart';

/// Avisos no celular do gestor (v1.5.0), sem Firebase: depois de cada sincronização (a cada 15 minutos
/// em segundo plano), as notificações novas do servidor viram notificações do Android.
class AvisosCelular {
  static final _plugin = FlutterLocalNotificationsPlugin();
  static bool _iniciado = false;

  /// Tipos que o gestor pode ligar ou desligar em Mais › Avisos no celular.
  static const tipos = {
    'atrasado': 'Procedimentos atrasados',
    'parto': 'Parto previsto em até 7 dias',
    'cio': 'Cio previsto para hoje',
    'documental': 'Pendências da ABCCMM',
    'ocorrencia': 'Ocorrência grave do caseiro',
    'financeiro': 'Parcelas a receber',
  };

  /// Toque numa notificação: id do animal a abrir (lido pela tela inicial do gestor).
  static final animalTocado = ValueNotifier<String?>(null);

  static Future<void> iniciar() async {
    if (_iniciado) return;
    await _plugin.initialize(
      const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')),
      onDidReceiveNotificationResponse: (r) => animalTocado.value = r.payload,
    );
    final lancou = await _plugin.getNotificationAppLaunchDetails();
    if (lancou?.didNotificationLaunchApp == true) animalTocado.value = lancou?.notificationResponse?.payload;
    _iniciado = true;
  }

  /// Android 13 ou mais novo: pede a permissão de notificação (uma vez, no primeiro acesso do gestor).
  static Future<bool> pedirPermissao() async {
    await iniciar();
    final a = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    return await a?.requestNotificationsPermission() ?? true;
  }

  // ---------- preferências (no celular) ----------
  static Future<Map<String, dynamic>> preferencias() async {
    final p = <String, dynamic>{for (final t in tipos.keys) t: true, 'silencioDe': 21, 'silencioAte': 6};
    final s = await Banco.ler('avisos_prefs');
    if (s != null && s.isNotEmpty) p.addAll(jsonDecode(s) as Map<String, dynamic>);
    return p;
  }

  static Future<void> gravarPreferencias(Map<String, dynamic> p) => Banco.gravar('avisos_prefs', jsonEncode(p));

  /// Hora dentro do silêncio (padrão 21h às 6h; atravessa a meia-noite quando "de" > "até").
  @visibleForTesting
  static bool emSilencio(int hora, int de, int ate) {
    if (de == ate) return false;
    return de < ate ? (hora >= de && hora < ate) : (hora >= de || hora < ate);
  }

  /// Tipo do aviso no celular, a partir da notificação do servidor (null = não vira notificação).
  @visibleForTesting
  static String? tipoDe(Map n, String hoje) {
    switch (n['tipo']) {
      case 'atrasado':
        return 'atrasado';
      case 'ocorrencia':
        return 'ocorrencia';
      case 'financeiro': // v1.6.0: parcela de venda vencendo em 7 dias ou vencida
        return 'financeiro';
      case 'documental':
        return n['sev'] == 'critico' ? 'documental' : null;
      case 'parto':
        final t = n['tarefa'] as Map?;
        final due = '${t?['due'] ?? ''}';
        if (due.isEmpty) return 'parto';
        return dias(DateTime.parse(hoje), DateTime.parse(due)) <= 7 ? 'parto' : null;
      case 'semana':
        final t = n['tarefa'] as Map?;
        return t?['cio'] == true && t?['due'] == hoje ? 'cio' : null;
    }
    return null;
  }

  /// Escolhe o que notificar: só os tipos ligados, fora do silêncio, e cada aviso uma única vez.
  @visibleForTesting
  static List<Map> selecionar(List notifs, Map<String, dynamic> prefs, Set<String> vistos, DateTime agora) {
    final hoje = iso(agora);
    if (emSilencio(agora.hour, prefs['silencioDe'] as int, prefs['silencioAte'] as int)) return const [];
    return notifs
        .cast<Map>()
        .where((n) => !vistos.contains(n['id']))
        .where((n) {
          final t = tipoDe(n, hoje);
          return t != null && prefs[t] != false;
        })
        .toList();
  }

  static Future<void> processar(Map<String, dynamic> estado) async {
    final notifs = (estado['notificacoes'] as List?) ?? const [];
    final vistosTxt = await Banco.ler('avisos_vistos');
    final vistos = <String>{...(vistosTxt == null || vistosTxt.isEmpty ? const [] : (jsonDecode(vistosTxt) as List).cast<String>())};
    final primeira = vistosTxt == null;
    final prefs = await preferencias();
    final agora = DateTime.now();
    // No horário de silêncio nada é marcado como visto: os avisos chegam quando o silêncio acabar.
    if (!primeira && emSilencio(agora.hour, prefs['silencioDe'] as int, prefs['silencioAte'] as int)) return;
    final novos = selecionar(notifs, prefs, vistos, agora);
    // Na primeira sincronização do gestor, marca tudo como visto: não despeja o histórico de avisos de uma vez.
    if (!primeira && novos.isNotEmpty) {
      await iniciar();
      for (final n in novos.take(5)) {
        final critico = n['sev'] == 'critico';
        await _plugin.show(
          (n['id'] as String).hashCode & 0x7fffffff,
          '${n['titulo']}',
          '${n['texto']}',
          NotificationDetails(
            android: AndroidNotificationDetails(
              critico ? 'haras360-criticos' : 'haras360-avisos',
              critico ? 'Avisos urgentes' : 'Avisos do haras',
              channelDescription: 'Avisos do Haras360 para o gestor',
              importance: critico ? Importance.high : Importance.defaultImportance,
              priority: critico ? Priority.high : Priority.defaultPriority,
              styleInformation: BigTextStyleInformation('${n['texto']}'),
            ),
          ),
          payload: n['animalId'] as String?,
        );
      }
    }
    // Guarda os ids atuais (vistos ou não notificados por preferência) para não repetir.
    final atuais = notifs.cast<Map>().map((n) => n['id'] as String).toSet();
    await Banco.gravar('avisos_vistos', jsonEncode([...vistos.intersection(atuais), ...atuais].toSet().toList()));
  }
}
