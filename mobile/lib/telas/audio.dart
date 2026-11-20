import 'dart:async';
import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import '../api.dart';
import '../banco.dart';
import '../regras_app.dart';
import '../tema.dart';

/// Áudio gravado no formulário, ainda não salvo.
class AudioGravado {
  final File arquivo;
  final int duracao;
  AudioGravado(this.arquivo, this.duracao);
}

/// Gravação de áudio no registro: AAC mono, cerca de 32 kbps, até [maxSeg] segundos.
class GravadorAudio extends StatefulWidget {
  final int maxSeg;
  final ValueChanged<AudioGravado?> aoMudar;
  const GravadorAudio({super.key, required this.maxSeg, required this.aoMudar});

  /// Só para o teste de integração: o emulador não tem microfone; a "gravação" usa este arquivo.
  @visibleForTesting
  static File? simulado;

  @override
  State<GravadorAudio> createState() => _GravadorAudioState();
}

class _GravadorAudioState extends State<GravadorAudio> {
  final _rec = AudioRecorder();
  Timer? _timer;
  int _seg = 0;
  bool _gravando = false;
  AudioGravado? _audio;
  String? _erro;

  @override
  void dispose() {
    _timer?.cancel();
    _rec.dispose();
    super.dispose();
  }

  Future<String> _novoCaminho() async {
    final dir = await getTemporaryDirectory();
    return p.join(dir.path, 'gravacao-${DateTime.now().millisecondsSinceEpoch}.m4a');
  }

  Future<void> _iniciar() async {
    setState(() => _erro = null);
    try {
      if (GravadorAudio.simulado == null) {
        if (!await _rec.hasPermission()) {
          setState(() => _erro = 'Permita o uso do microfone para gravar áudio (Configurações › Apps › Haras360 › Permissões).');
          return;
        }
        await _rec.start(const RecordConfig(encoder: AudioEncoder.aacLc, bitRate: 32000, sampleRate: 22050, numChannels: 1), path: await _novoCaminho());
      }
      setState(() {
        _gravando = true;
        _seg = 0;
      });
      _timer = Timer.periodic(const Duration(seconds: 1), (_) {
        setState(() => _seg++);
        if (_seg >= widget.maxSeg) _parar();
      });
    } catch (e) {
      setState(() => _erro = 'Não foi possível gravar: $e');
    }
  }

  Future<void> _parar() async {
    _timer?.cancel();
    String? caminho;
    if (GravadorAudio.simulado != null) {
      caminho = await _novoCaminho();
      await GravadorAudio.simulado!.copy(caminho);
    } else {
      caminho = await _rec.stop();
    }
    final dur = _seg < 1 ? 1 : _seg;
    setState(() {
      _gravando = false;
      _audio = caminho == null ? null : AudioGravado(File(caminho), dur);
    });
    widget.aoMudar(_audio);
  }

  Future<void> _apagar() async {
    final a = _audio;
    setState(() => _audio = null);
    widget.aoMudar(null);
    if (a != null && await a.arquivo.exists()) await a.arquivo.delete();
  }

  @override
  Widget build(BuildContext context) {
    final a = _audio;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('Áudio (até ${duracaoTxt(widget.maxSeg)})', style: const TextStyle(color: Cores.apagado)),
      const SizedBox(height: 6),
      if (_gravando)
        Row(children: [
          const Icon(Icons.fiber_manual_record, color: Cores.atrasado),
          const SizedBox(width: 6),
          Text('Gravando ${duracaoTxt(_seg)} de ${duracaoTxt(widget.maxSeg)}', style: const TextStyle(fontWeight: FontWeight.w600)),
          const Spacer(),
          FilledButton.icon(onPressed: _parar, icon: const Icon(Icons.stop), label: const Text('Parar')),
        ])
      else if (a != null)
        Row(children: [
          Expanded(child: TocadorAudio(arquivo: a.arquivo, duracao: a.duracao)),
          IconButton(tooltip: 'Apagar áudio', onPressed: _apagar, icon: const Icon(Icons.delete_outline)),
        ])
      else
        Align(
          alignment: Alignment.centerLeft,
          child: OutlinedButton.icon(onPressed: _iniciar, icon: const Icon(Icons.mic_none), label: const Text('Gravar áudio')),
        ),
      if (_erro != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_erro!, style: const TextStyle(color: Cores.atrasado))),
    ]);
  }
}

/// Toca um áudio do celular ou, se ainda não estiver no celular, baixa do servidor (precisa de conexão).
class TocadorAudio extends StatefulWidget {
  final File? arquivo;
  final String? url;
  final int duracao;
  const TocadorAudio({super.key, this.arquivo, this.url, required this.duracao});
  @override
  State<TocadorAudio> createState() => _TocadorAudioState();
}

class _TocadorAudioState extends State<TocadorAudio> {
  final _player = AudioPlayer();
  bool _tocando = false;
  bool _baixando = false;
  StreamSubscription? _fim;

  @override
  void initState() {
    super.initState();
    _fim = _player.onPlayerComplete.listen((_) {
      if (mounted) setState(() => _tocando = false);
    });
  }

  @override
  void dispose() {
    _fim?.cancel();
    _player.dispose();
    super.dispose();
  }

  Future<File?> _arquivo() async {
    if (widget.arquivo != null) return widget.arquivo;
    final dir = await getTemporaryDirectory();
    final nome = p.basename(widget.url!);
    final f = File(p.join(dir.path, 'audio-$nome.m4a'));
    if (await f.exists()) return f;
    final cred = await Credenciais.ler();
    if (cred == null) return null;
    setState(() => _baixando = true);
    try {
      await f.writeAsBytes(await Api(cred.servidor, token: cred.token).baixar(widget.url!));
      return f;
    } finally {
      if (mounted) setState(() => _baixando = false);
    }
  }

  Future<void> _alternar() async {
    if (_tocando) {
      await _player.stop();
      setState(() => _tocando = false);
      return;
    }
    try {
      final f = await _arquivo();
      if (f == null) return;
      await _player.play(DeviceFileSource(f.path));
      setState(() => _tocando = true);
    } on ApiErro catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.semConexao ? 'Para ouvir este áudio, conecte ao Wi-Fi.' : e.mensagem)));
    }
  }

  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [
        IconButton.filledTonal(
          tooltip: _tocando ? 'Parar' : 'Ouvir',
          onPressed: _baixando ? null : _alternar,
          icon: _baixando
              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
              : Icon(_tocando ? Icons.stop : Icons.play_arrow),
        ),
        const SizedBox(width: 6),
        Text('Áudio · ${duracaoTxt(widget.duracao)}'),
      ]);
}
