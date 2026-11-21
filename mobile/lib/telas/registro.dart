import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';

import '../banco.dart';
import '../config.dart';
import '../dados.dart';
import '../regras_app.dart';
import '../tema.dart';
import 'audio.dart';

/// Novo registro no prontuário. Grava no celular; o envio acontece no Wi-Fi.
class TelaRegistro extends StatefulWidget {
  final Map<String, dynamic> pre;
  const TelaRegistro({super.key, this.pre = const {}});
  @override
  State<TelaRegistro> createState() => _TelaRegistroState();
}

class _TelaRegistroState extends State<TelaRegistro> {
  late String? _animal = widget.pre['animalId'] as String?;
  late String _tipo = (widget.pre['tipo'] as String?) ?? 'vacina';
  late DateTime _data = hoje();
  late final Set<String> _prots = {...((widget.pre['protocolos'] as List?) ?? const []).cast<String>()};
  late String _dose = _doseInicial(widget.pre['dose']);
  final _obs = TextEditingController();
  late final Map<String, TextEditingController> _txt = {
    for (final k in ['produto', 'lote', 'ferrador', 'resultado', 'garanhao', 'titulo', 'sinais', 'foliculo']) k: TextEditingController(),
  };
  late final Map<String, String> _sel = {
    'procedimento': (widget.pre['procedimento'] as String?) ?? procedimentosOdonto.first,
    'exame': (widget.pre['exame'] as String?) ?? exames.first,
    'evento': (widget.pre['evento'] as String?) ?? eventosRepro.first,
    'gravidade': gravidades.first,
    'ovario': ovarios.first,
    'edema': edemas.first,
  };
  DateTime? _cobertura;
  final List<File> _fotos = [];
  AudioGravado? _audio;
  String? _erro;
  bool _salvando = false;

  static String _doseInicial(dynamic d) => d == null || d == 'unica' ? 'reforco' : '$d';

  Future<void> _foto(ImageSource origem) async {
    if (_fotos.length >= maxFotos) return;
    try {
      // Compressão no próprio celular: lado maior 1600 px, JPEG qualidade 75 (cerca de 300 a 500 KB).
      final x = await ImagePicker().pickImage(source: origem, maxWidth: 1600, maxHeight: 1600, imageQuality: 75);
      if (x != null) setState(() => _fotos.add(File(x.path)));
    } catch (_) {
      setState(() => _erro = 'Não foi possível abrir a câmera. Confira a permissão do app.');
    }
  }

  Future<void> _salvar() async {
    final a = dados.animal(_animal);
    try {
      final r = montarRegistro(
        id: const Uuid().v4(),
        animalId: _animal,
        sexoAnimal: a?['sexo'] as String?,
        dataIso: iso(_data),
        tipo: _tipo,
        protocolos: _prots.toList(),
        dose: _dose,
        obs: _obs.text,
        campos: {
          for (final e in _txt.entries) e.key: e.value.text,
          ..._sel,
          if (_cobertura != null) 'dataCobertura': iso(_cobertura!),
        },
      );
      setState(() => _salvando = true);
      await Banco.enfileirar(r, _fotos, audio: _audio?.arquivo, duracao: _audio?.duracao ?? 0);
      if (mounted) Navigator.of(context).pop(true);
    } on ErroValidacao catch (e) {
      setState(() => _erro = e.mensagem);
    } catch (e) {
      setState(() {
        _erro = 'Não foi possível salvar no celular: $e';
        _salvando = false;
      });
    }
  }

  Future<DateTime?> _escolherData(DateTime inicial) =>
      showDatePicker(context: context, initialDate: inicial, firstDate: DateTime(2000), lastDate: hoje(), helpText: 'Data');

  Widget _campo(String chave, String rotulo, {String? dica}) =>
      Padding(padding: const EdgeInsets.only(top: 12), child: TextField(controller: _txt[chave], decoration: InputDecoration(labelText: rotulo, hintText: dica)));

  Widget _lista(String chave, String rotulo, List<String> opcoes) => Padding(
        padding: const EdgeInsets.only(top: 12),
        child: DropdownButtonFormField<String>(
          value: opcoes.contains(_sel[chave]) ? _sel[chave] : opcoes.first,
          decoration: InputDecoration(labelText: rotulo),
          items: [for (final o in opcoes) DropdownMenuItem(value: o, child: Text(o))],
          onChanged: (v) => setState(() => _sel[chave] = v ?? opcoes.first),
        ),
      );

  List<Widget> _extras() {
    switch (_tipo) {
      case 'vacina':
        final vs = dados.protocolos.where((p) => p['cat'] == 'vacina').toList();
        return [
          const Padding(padding: EdgeInsets.only(top: 12), child: Text('Doenças cobertas (marque todas em vacinas multivalentes)')),
          Wrap(spacing: 8, children: [
            for (final v in vs)
              FilterChip(
                label: Text('${v['nome']}'),
                selected: _prots.contains(v['id']),
                onSelected: (s) => setState(() => s ? _prots.add(v['id'] as String) : _prots.remove(v['id'])),
              ),
          ]),
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: DropdownButtonFormField<String>(
              value: _dose,
              decoration: const InputDecoration(labelText: 'Dose'),
              items: const [
                DropdownMenuItem(value: '1', child: Text('1ª dose')),
                DropdownMenuItem(value: '2', child: Text('2ª dose')),
                DropdownMenuItem(value: '3', child: Text('3ª dose')),
                DropdownMenuItem(value: 'reforco', child: Text('Reforço')),
              ],
              onChanged: (v) => setState(() => _dose = v ?? 'reforco'),
            ),
          ),
          _campo('lote', 'Lote', dica: 'Ex.: RB2291'),
          _campo('produto', 'Produto / marca'),
        ];
      case 'vermifugacao':
        return [_campo('produto', 'Vermífugo (princípio ativo)', dica: 'Ex.: Ivermectina + praziquantel')];
      case 'odontologia':
        return [_lista('procedimento', 'Procedimento', procedimentosOdonto)];
      case 'ferrageamento':
        return [_campo('ferrador', 'Ferrador')];
      case 'exame':
        return [_lista('exame', 'Exame', exames), _campo('resultado', 'Resultado', dica: 'Ex.: Negativo')];
      case 'reprodutivo':
        return [
          _lista('evento', 'Evento', eventosRepro),
          if (_sel['evento'] == 'Cio') ...[
            _campo('sinais', 'Sinais observados', dica: 'Ex.: aceita o rufião, urina com frequência'),
            _lista('ovario', 'Ovário (exame)', ovarios),
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: TextField(
                  controller: _txt['foliculo'],
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Folículo (mm)')),
            ),
            _lista('edema', 'Edema uterino (0 a 3)', edemas),
          ] else
            _campo('garanhao', 'Garanhão'),
          if (_sel['evento'] == 'Diagnóstico positivo')
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: OutlinedButton.icon(
                icon: const Icon(Icons.event),
                label: Text(_cobertura == null ? 'Data da cobertura' : 'Cobertura em ${br(iso(_cobertura!))}'),
                onPressed: () async {
                  final d = await _escolherData(_cobertura ?? _data);
                  if (d != null) setState(() => _cobertura = d);
                },
              ),
            ),
        ];
      case 'ocorrencia':
        return [_campo('titulo', 'O que aconteceu', dica: 'Ex.: Mancando da pata traseira'), _lista('gravidade', 'Gravidade', gravidades)];
    }
    return const [];
  }

  @override
  Widget build(BuildContext context) {
    final animais = dados.animais;
    final tipos = cats.entries.where((e) => e.key != 'documental').toList();
    return Scaffold(
      appBar: AppBar(title: Text((widget.pre['titulo'] as String?) ?? 'Novo registro')),
      body: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 32), children: [
        DropdownButtonFormField<String>(
          value: animais.any((a) => a['id'] == _animal) ? _animal : null,
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Animal'),
          items: [for (final a in animais) DropdownMenuItem(value: a['id'] as String, child: Text(a['nome'] as String, overflow: TextOverflow.ellipsis))],
          onChanged: (v) => setState(() => _animal = v),
        ),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(
            child: DropdownButtonFormField<String>(
              value: _tipo,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Tipo de registro'),
              items: [for (final e in tipos) DropdownMenuItem(value: e.key, child: Text(e.value))],
              onChanged: (v) => setState(() => _tipo = v ?? 'vacina'),
            ),
          ),
          const SizedBox(width: 8),
          OutlinedButton(
            onPressed: () async {
              final d = await _escolherData(_data);
              if (d != null) setState(() => _data = d);
            },
            child: Text(br(iso(_data))),
          ),
        ]),
        ..._extras(),
        Padding(
          padding: const EdgeInsets.only(top: 12),
          child: TextField(controller: _obs, minLines: 2, maxLines: 5, decoration: const InputDecoration(labelText: 'Observações', hintText: 'Descreva o que foi feito ou observado')),
        ),
        const SizedBox(height: 12),
        Text('Fotos (${_fotos.length} de $maxFotos)', style: const TextStyle(color: Cores.apagado)),
        const SizedBox(height: 6),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (var i = 0; i < _fotos.length; i++)
            Stack(children: [
              ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.file(_fotos[i], width: 84, height: 84, fit: BoxFit.cover)),
              Positioned(
                right: 0,
                top: 0,
                child: IconButton.filledTonal(iconSize: 16, visualDensity: VisualDensity.compact, onPressed: () => setState(() => _fotos.removeAt(i)), icon: const Icon(Icons.close)),
              ),
            ]),
          if (_fotos.length < maxFotos) ...[
            OutlinedButton.icon(onPressed: () => _foto(ImageSource.camera), icon: const Icon(Icons.photo_camera_outlined), label: const Text('Câmera')),
            OutlinedButton.icon(onPressed: () => _foto(ImageSource.gallery), icon: const Icon(Icons.photo_library_outlined), label: const Text('Galeria')),
          ],
        ]),
        if (dados.audioLiberado) ...[
          const SizedBox(height: 16),
          GravadorAudio(maxSeg: dados.audioMaxSeg, aoMudar: (a) => _audio = a),
        ],
        if (_erro != null)
          Container(
            margin: const EdgeInsets.only(top: 16),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Cores.atrasadoSuave, borderRadius: BorderRadius.circular(8)),
            child: Text(_erro!, style: const TextStyle(color: Cores.atrasado)),
          ),
        const SizedBox(height: 20),
        FilledButton.icon(onPressed: _salvando ? null : _salvar, icon: const Icon(Icons.check), label: Text(_salvando ? 'Salvando...' : 'Salvar registro')),
      ]),
    );
  }
}
