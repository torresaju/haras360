import 'dart:convert';
import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:workmanager/workmanager.dart';

import 'api.dart';
import 'banco.dart';
import 'config.dart';

class ResultadoSinc {
  final bool ok;
  final String mensagem;
  final int enviados;
  final int fotos;
  final bool desvinculado;
  ResultadoSinc(this.ok, this.mensagem, {this.enviados = 0, this.fotos = 0, this.desvinculado = false});
}

/// Envia a fila e baixa o estado do haras. Só roda no Wi-Fi (rede sem medição).
class Sincronizador {
  static bool _rodando = false;

  static Future<bool> noWifi() async {
    final r = await Connectivity().checkConnectivity();
    return r.contains(ConnectivityResult.wifi) || r.contains(ConnectivityResult.ethernet);
  }

  static Future<ResultadoSinc> executar() async {
    if (_rodando) return ResultadoSinc(false, 'A sincronização já está em andamento.');
    // Trava entre o app aberto e o envio em segundo plano (processos diferentes).
    final trava = DateTime.tryParse(await Banco.ler('travaSinc') ?? '');
    if (trava != null && DateTime.now().difference(trava).inMinutes < 10) {
      return ResultadoSinc(false, 'A sincronização já está em andamento.');
    }
    if (!await noWifi()) return ResultadoSinc(false, 'Sem Wi-Fi. Os registros ficam guardados no celular e vão quando houver Wi-Fi.');
    final cred = await Credenciais.ler();
    if (cred == null) return ResultadoSinc(false, 'Celular não vinculado.', desvinculado: true);
    _rodando = true;
    await Banco.gravar('travaSinc', DateTime.now().toIso8601String());
    final api = Api(cred.servidor, token: cred.token);
    var enviados = 0, fotos = 0;
    try {
      for (final item in await Banco.filaPendente()) {
        final id = item['id'] as String;
        try {
          await api.post('/api/registros', jsonDecode(item['corpo'] as String) as Map<String, dynamic>);
          await Banco.marcarEnviado(id);
          enviados++;
        } on ApiErro catch (e) {
          if (e.recusado) {
            await Banco.marcarErro(id, e.mensagem);
            continue;
          }
          rethrow;
        }
      }
      for (final f in await Banco.fotosPendentes()) {
        final id = f['id'] as String;
        final arq = File(f['caminho'] as String);
        if (!await arq.exists()) {
          await Banco.marcarFotoErro(id, 'Arquivo da foto não encontrado no celular.');
          continue;
        }
        try {
          await api.enviarFoto(f['registro_id'] as String, id, f['ordem'] as int, arq);
          await Banco.marcarFotoEnviada(id);
          fotos++;
        } on ApiErro catch (e) {
          if (e.recusado) {
            await Banco.marcarFotoErro(id, e.mensagem);
            continue;
          }
          rethrow;
        }
      }
      final estado = await api.get('/api/app/sincronizar');
      await Banco.gravarEstado(estado);
      await Banco.limparEnviados();
      await Banco.gravar('ultimoErro', '');
      final partes = [if (enviados > 0) '$enviados registro(s)', if (fotos > 0) '$fotos foto(s)'];
      return ResultadoSinc(true, partes.isEmpty ? 'Tudo em dia.' : 'Enviado: ${partes.join(' e ')}.', enviados: enviados, fotos: fotos);
    } on ApiErro catch (e) {
      await Banco.gravar('ultimoErro', e.mensagem);
      if (e.desvinculado && !e.recusado) {
        await Credenciais.esquecerToken();
        return ResultadoSinc(false, '${e.mensagem} Peça ao gestor um novo QR Code. Seus registros continuam guardados.', desvinculado: true);
      }
      return ResultadoSinc(false, e.mensagem, enviados: enviados, fotos: fotos);
    } finally {
      _rodando = false;
      await Banco.gravar('travaSinc', '');
    }
  }

  /// Agenda o envio em segundo plano: a cada hora, somente em rede sem medição (Wi-Fi).
  static Future<void> agendar() => Workmanager().registerPeriodicTask(
        tarefaSincronizacao,
        tarefaSincronizacao,
        frequency: intervaloSincronizacao,
        constraints: Constraints(networkType: NetworkType.unmetered),
        existingWorkPolicy: ExistingWorkPolicy.keep,
        backoffPolicy: BackoffPolicy.exponential,
        backoffPolicyDelay: const Duration(minutes: 5),
      );
}

@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((tarefa, _) async {
    try {
      final r = await Sincronizador.executar();
      return r.ok || r.desvinculado || r.mensagem.startsWith('Sem Wi-Fi') || r.mensagem.contains('andamento');
    } catch (_) {
      return false; // o WorkManager tenta de novo mais tarde
    }
  });
}
