import 'package:flutter_test/flutter_test.dart';
import 'package:haras360/avisos_celular.dart';

void main() {
  group('avisos no celular do gestor (v1.5.0)', () {
    final prefs = <String, dynamic>{for (final t in AvisosCelular.tipos.keys) t: true, 'silencioDe': 21, 'silencioAte': 6};

    test('horário de silêncio atravessa a meia-noite', () {
      expect(AvisosCelular.emSilencio(22, 21, 6), isTrue);
      expect(AvisosCelular.emSilencio(3, 21, 6), isTrue);
      expect(AvisosCelular.emSilencio(6, 21, 6), isFalse);
      expect(AvisosCelular.emSilencio(14, 21, 6), isFalse);
      expect(AvisosCelular.emSilencio(13, 12, 14), isTrue);
      expect(AvisosCelular.emSilencio(10, 8, 8), isFalse);
    });

    test('tipos: atrasado, parto em até 7 dias, cio de hoje, ABCCMM crítica e ocorrência grave', () {
      const h = '2026-11-21';
      expect(AvisosCelular.tipoDe({'tipo': 'atrasado'}, h), 'atrasado');
      expect(AvisosCelular.tipoDe({'tipo': 'ocorrencia'}, h), 'ocorrencia');
      expect(AvisosCelular.tipoDe({'tipo': 'financeiro'}, h), 'financeiro');
      expect(AvisosCelular.tipoDe({'tipo': 'parto', 'tarefa': {'due': '2026-11-27'}}, h), 'parto');
      expect(AvisosCelular.tipoDe({'tipo': 'parto', 'tarefa': {'due': '2026-12-20'}}, h), isNull);
      expect(AvisosCelular.tipoDe({'tipo': 'semana', 'tarefa': {'cio': true, 'due': h}}, h), 'cio');
      expect(AvisosCelular.tipoDe({'tipo': 'semana', 'tarefa': {'cio': true, 'due': '2026-11-23'}}, h), isNull);
      expect(AvisosCelular.tipoDe({'tipo': 'semana', 'tarefa': {'due': h}}, h), isNull);
      expect(AvisosCelular.tipoDe({'tipo': 'documental', 'sev': 'critico'}, h), 'documental');
      expect(AvisosCelular.tipoDe({'tipo': 'documental', 'sev': 'info'}, h), isNull);
      expect(AvisosCelular.tipoDe({'tipo': 'campo'}, h), isNull);
    });

    test('não repete, respeita os tipos desligados e o silêncio', () {
      final ns = [
        {'id': 'a', 'tipo': 'atrasado'},
        {'id': 'b', 'tipo': 'ocorrencia'},
        {'id': 'c', 'tipo': 'campo'},
      ];
      final dia = DateTime(2026, 11, 21, 10);
      expect(AvisosCelular.selecionar(ns, prefs, {}, dia).map((n) => n['id']), ['a', 'b']);
      expect(AvisosCelular.selecionar(ns, prefs, {'a'}, dia).map((n) => n['id']), ['b']);
      expect(AvisosCelular.selecionar(ns, {...prefs, 'ocorrencia': false}, {}, dia).map((n) => n['id']), ['a']);
      expect(AvisosCelular.selecionar(ns, prefs, {}, DateTime(2026, 11, 21, 23)), isEmpty);
    });
  });
}
