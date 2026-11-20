import 'package:flutter_test/flutter_test.dart';
import 'package:haras360/regras_app.dart';

void main() {
  final agora = DateTime(2026, 11, 20, 15, 30);

  group('datas', () {
    test('formata e calcula distâncias', () {
      expect(br('2026-11-05'), '05/11/2026');
      expect(brCurta('2026-03-09'), '09 mar');
      expect(relativo('2026-11-20', agora), 'hoje');
      expect(relativo('2026-11-21', agora), 'amanhã');
      expect(relativo('2026-11-17', agora), 'há 3 dias');
      expect(relativo('2026-12-01', agora), 'em 11 dias');
      expect(idadeTxt('2026-01-15', agora), '10 meses');
      expect(idadeTxt('2017-01-13', agora), '9 anos');
    });

    test('situação da tarefa é recalculada com o dia de hoje do celular', () {
      expect(statusTarefa({'due': '2026-11-19'}, agora), 'atrasado');
      expect(statusTarefa({'due': '2026-11-20'}, agora), 'hoje');
      expect(statusTarefa({'due': '2026-11-27'}, agora), 'semana');
      expect(statusTarefa({'due': '2026-11-28'}, agora), 'futuro');
      expect(statusTarefa({'due': '2026-11-01', 'doc': true}, agora), 'pendente');
      // a lista baixada numa segunda-feira continua certa no sábado, sem internet
      expect(statusTarefa({'due': '2026-11-22'}, DateTime(2026, 11, 28)), 'atrasado');
    });
  });

  group('tarefas e registros offline', () {
    final tarefas = [
      {'id': 'a1:raiva', 'animalId': 'a1', 'animal': 'AURORA', 'protocoloId': 'raiva', 'cat': 'vacina', 'titulo': 'Raiva', 'due': '2026-11-18', 'dose': 'reforco'},
      {'id': 'a1:vermi', 'animalId': 'a1', 'animal': 'AURORA', 'protocoloId': 'vermi', 'cat': 'vermifugacao', 'titulo': 'Vermifugação', 'due': '2026-11-22'},
      {'id': 'a2:raiva', 'animalId': 'a2', 'animal': 'DOURADO', 'protocoloId': 'raiva', 'cat': 'vacina', 'titulo': 'Raiva', 'due': '2026-11-20'},
      {'id': 'a1:parto', 'animalId': 'a1', 'animal': 'AURORA', 'protocoloId': null, 'cat': 'reprodutivo', 'titulo': 'Previsão de parto', 'due': '2027-01-10', 'parto': true},
      {'id': 'a2:dna', 'animalId': 'a2', 'animal': 'DOURADO', 'cat': 'documental', 'titulo': 'DNA', 'due': '2026-11-20', 'doc': true},
    ];

    test('registro feito no celular tira a tarefa da lista antes do envio', () {
      final locais = [
        {'animalId': 'a1', 'tipo': 'vacina', 'protocolos': ['raiva', 'tetano']},
      ];
      final p = tarefasPendentes(tarefas, locais, agora);
      expect(p.map((t) => t['id']), ['a2:raiva', 'a1:vermi', 'a1:parto']);
      expect(p.first['status'], 'hoje');
    });

    test('vacina de outro animal não atende', () {
      expect(registroAtende(tarefas[0], {'animalId': 'a2', 'tipo': 'vacina', 'protocolos': ['raiva']}), isFalse);
    });

    test('parto atende a previsão de parto', () {
      expect(registroAtende(tarefas[3], {'animalId': 'a1', 'tipo': 'reprodutivo', 'evento': 'Parto'}), isTrue);
      expect(registroAtende(tarefas[3], {'animalId': 'a1', 'tipo': 'reprodutivo', 'evento': 'Cobertura'}), isFalse);
    });

    test('pré-preenchimento a partir da tarefa', () {
      final p = preDeTarefa(tarefas[0]);
      expect(p['animalId'], 'a1');
      expect(p['tipo'], 'vacina');
      expect(p['protocolos'], ['raiva']);
      expect(p['dose'], 'reforco');
      expect(preDeTarefa(tarefas[3])['evento'], 'Parto');
    });
  });

  group('formulário de registro', () {
    Map<String, dynamic> montar(String tipo, {List<String> prots = const [], Map<String, String> campos = const {}, String data = '2026-11-20', String sexo = 'F'}) =>
        montarRegistro(id: 'id-teste-123', animalId: 'a1', sexoAnimal: sexo, dataIso: data, tipo: tipo, protocolos: prots, campos: campos, agora: agora);

    test('vacina exige ao menos uma doença', () {
      expect(() => montar('vacina'), throwsA(isA<ErroValidacao>()));
      final r = montar('vacina', prots: ['raiva', 'tetano'], campos: {'lote': 'RB1'});
      expect(r['protocolos'], ['raiva', 'tetano']);
      expect(r['dose'], 'reforco');
      expect(r['lote'], 'RB1');
      expect(r.containsKey('produto'), isFalse);
    });

    test('data futura é recusada', () {
      expect(() => montar('vermifugacao', data: '2026-11-21'), throwsA(isA<ErroValidacao>()));
    });

    test('protocolos derivados do tipo, como no Portal Campo', () {
      expect(montar('vermifugacao')['protocolos'], ['vermi']);
      expect(montar('ferrageamento')['protocolos'], ['ferrag']);
      expect(montar('odontologia', campos: {'procedimento': 'Retorno de aparelho'})['protocolos'], ['aparelho']);
      expect(montar('exame', campos: {'exame': 'Mormo'})['protocolos'], ['mormo']);
    });

    test('reprodução: eventos de gestação só em fêmeas e cobertura no diagnóstico', () {
      expect(() => montar('reprodutivo', campos: {'evento': 'Parto'}, sexo: 'M'), throwsA(isA<ErroValidacao>()));
      expect(montar('reprodutivo', campos: {'evento': 'Cobertura', 'garanhao': 'trovão'}, sexo: 'M')['garanhao'], 'TROVÃO');
      expect(() => montar('reprodutivo', campos: {'evento': 'Diagnóstico positivo'}), throwsA(isA<ErroValidacao>()));
      expect(() => montar('reprodutivo', campos: {'evento': 'Diagnóstico positivo', 'dataCobertura': '2026-11-20'}, data: '2026-11-10'), throwsA(isA<ErroValidacao>()));
      expect(montar('reprodutivo', campos: {'evento': 'Diagnóstico positivo', 'dataCobertura': '2026-10-01'})['dataCobertura'], '2026-10-01');
    });

    test('ocorrência exige descrição', () {
      expect(() => montar('ocorrencia'), throwsA(isA<ErroValidacao>()));
      expect(montar('ocorrencia', campos: {'titulo': 'Mancando'})['gravidade'], 'Leve');
    });

    test('sem animal é recusado', () {
      expect(() => montarRegistro(id: 'x', animalId: null, sexoAnimal: null, dataIso: '2026-11-20', tipo: 'vacina', agora: agora), throwsA(isA<ErroValidacao>()));
    });
  });

  group('vínculo e atualização', () {
    test('lê o QR Code gerado em Equipe', () {
      final v = lerQrVinculo('haras360://vincular?s=http%3A%2F%2F129.80.10.20%3A8090&c=AbCdEfGhIjKlMnOpQrStUvWx');
      expect(v, isNotNull);
      expect(v!.servidor, 'http://129.80.10.20:8090');
      expect(v.codigo, 'AbCdEfGhIjKlMnOpQrStUvWx');
    });

    test('recusa QR Codes de outros sistemas', () {
      expect(lerQrVinculo('https://exemplo.com'), isNull);
      expect(lerQrVinculo('otpauth://totp/Haras360:a@b?secret=X'), isNull);
      expect(lerQrVinculo('haras360://vincular?s=javascript%3Aalert(1)&c=AbCdEfGhIjKlMnOpQrSt'), isNull);
      expect(lerQrVinculo('haras360://vincular?s=http%3A%2F%2F1.2.3.4&c=curto'), isNull);
    });

    test('normaliza o endereço digitado', () {
      expect(normalizarServidor(' 10.0.0.5:8090/ '), 'http://10.0.0.5:8090');
      expect(normalizarServidor('https://h.exemplo.com'), 'https://h.exemplo.com');
    });

    test('compara a versão do APK pelo código de build', () {
      expect(haAtualizacao({'codigo': 10101}, 10100), isTrue);
      expect(haAtualizacao({'codigo': 10100}, 10100), isFalse);
      expect(haAtualizacao(null, 10100), isFalse);
    });

    test('duração do áudio', () {
      expect(duracaoTxt(0), '0:00');
      expect(duracaoTxt(42), '0:42');
      expect(duracaoTxt(120), '2:00');
      expect(duracaoTxt(-3), '0:00');
    });

    test('título do registro', () {
      final prots = [
        {'id': 'raiva', 'nome': 'Raiva'},
        {'id': 'tetano', 'nome': 'Tétano'}
      ];
      expect(tituloRegistro({'tipo': 'vacina', 'protocolos': ['raiva', 'tetano']}, prots), 'Vacina Raiva + Tétano');
      expect(tituloRegistro({'tipo': 'ocorrencia', 'titulo': 'Corte'}, prots), 'Corte');
      expect(doseTxt(2), '2ª dose');
      expect(doseTxt('reforco'), 'Reforço');
    });
  });
}
