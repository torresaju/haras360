// Regras puras do app (sem banco nem rede), cobertas pelos testes de unidade.

const cats = <String, String>{
  'vacina': 'Vacinação',
  'vermifugacao': 'Vermifugação',
  'odontologia': 'Odontologia',
  'ferrageamento': 'Ferrageamento',
  'exame': 'Exame clínico',
  'reprodutivo': 'Reprodução',
  'ocorrencia': 'Ocorrência',
  'documental': 'Documentação',
};

const eventosRepro = ['Cobertura', 'Inseminação', 'Diagnóstico positivo', 'Diagnóstico negativo', 'Parto', 'Aborto'];
const procedimentosOdonto = ['Avaliação', 'Avaliação e correção', 'Aparelho dentário instalado', 'Retorno de aparelho', 'Extração', 'Outro'];
const exames = ['Anemia Infecciosa (AIE)', 'Mormo', 'Hemograma', 'Ultrassonografia', 'Raio-X', 'Outro'];
const gravidades = ['Leve', 'Moderada', 'Grave'];
const mesesCurtos = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

// ---------------- datas ----------------
DateTime hoje([DateTime? agora]) {
  final a = agora ?? DateTime.now();
  return DateTime(a.year, a.month, a.day);
}

DateTime? data(String? iso) {
  if (iso == null || iso.length < 10) return null;
  final p = iso.substring(0, 10).split('-');
  if (p.length != 3) return null;
  final y = int.tryParse(p[0]), m = int.tryParse(p[1]), d = int.tryParse(p[2]);
  if (y == null || m == null || d == null) return null;
  return DateTime(y, m, d);
}

String _dd(int n) => n.toString().padLeft(2, '0');
String iso(DateTime d) => '${d.year}-${_dd(d.month)}-${_dd(d.day)}';
String br(String? s) {
  final d = data(s);
  return d == null ? '-' : '${_dd(d.day)}/${_dd(d.month)}/${d.year}';
}

String brCurta(String? s) {
  final d = data(s);
  return d == null ? '-' : '${_dd(d.day)} ${mesesCurtos[d.month - 1]}';
}

int dias(DateTime a, DateTime b) => DateTime.utc(b.year, b.month, b.day).difference(DateTime.utc(a.year, a.month, a.day)).inDays;

String relativo(String? due, [DateTime? agora]) {
  final d = data(due);
  if (d == null) return '';
  final n = dias(hoje(agora), d);
  if (n == 0) return 'hoje';
  if (n == 1) return 'amanhã';
  if (n == -1) return 'ontem';
  return n > 0 ? 'em $n dias' : 'há ${-n} dias';
}

String idadeTxt(String? nasc, [DateTime? agora]) {
  final d = data(nasc);
  if (d == null) return '';
  final h = hoje(agora);
  var meses = (h.year - d.year) * 12 + h.month - d.month;
  if (h.day < d.day) meses--;
  if (meses < 0) return '';
  if (meses < 12) return meses == 1 ? '1 mês' : '$meses meses';
  final anos = meses ~/ 12;
  return anos == 1 ? '1 ano' : '$anos anos';
}

/// Situação da tarefa recalculada no aparelho: a lista vem da última sincronização,
/// mas o dia de hoje muda mesmo sem internet.
String statusTarefa(Map t, [DateTime? agora]) {
  if (t['doc'] == true) return 'pendente';
  final d = data(t['due'] as String?);
  if (d == null) return 'futuro';
  final n = dias(hoje(agora), d);
  if (n < 0) return 'atrasado';
  if (n == 0) return 'hoje';
  if (n <= 7) return 'semana';
  return 'futuro';
}

// ---------------- tarefas e registros locais ----------------
/// Um registro feito no aparelho (ainda não refletido na última sincronização) atende a tarefa?
bool registroAtende(Map tarefa, Map registro) {
  if (registro['animalId'] != tarefa['animalId']) return false;
  if (tarefa['parto'] == true) return registro['tipo'] == 'reprodutivo' && (registro['evento'] == 'Parto' || registro['evento'] == 'Aborto');
  final pid = tarefa['protocoloId'];
  final prots = (registro['protocolos'] as List?) ?? const [];
  if (pid != null) return prots.contains(pid);
  return registro['tipo'] == tarefa['cat'];
}

/// Tarefas de campo (sem as documentais) que ainda faltam, com a situação de hoje.
List<Map<String, dynamic>> tarefasPendentes(List tarefas, List locais, [DateTime? agora]) {
  final out = <Map<String, dynamic>>[];
  for (final t in tarefas) {
    final m = Map<String, dynamic>.from(t as Map);
    if (m['doc'] == true) continue;
    if (locais.any((r) => registroAtende(m, r as Map))) continue;
    m['status'] = statusTarefa(m, agora);
    out.add(m);
  }
  out.sort((a, b) => (a['due'] as String? ?? '').compareTo(b['due'] as String? ?? ''));
  return out;
}

/// Pré-preenchimento do formulário a partir de uma tarefa (mesma regra do Portal Campo).
Map<String, dynamic> preDeTarefa(Map t) {
  if (t['parto'] == true) return {'animalId': t['animalId'], 'tipo': 'reprodutivo', 'evento': 'Parto', 'titulo': 'Registrar parto'};
  final pid = t['protocoloId'];
  return {
    'animalId': t['animalId'],
    'tipo': t['cat'],
    'protocolos': pid == null ? <String>[] : <String>[pid as String],
    'dose': t['dose'],
    'titulo': 'Registrar ${(t['titulo'] as String? ?? '').toLowerCase()}',
    if (t['cat'] == 'odontologia' && pid == 'aparelho') 'procedimento': 'Retorno de aparelho',
    if (t['cat'] == 'exame' && pid == 'aie') 'exame': 'Anemia Infecciosa (AIE)',
    if (t['cat'] == 'exame' && pid == 'mormo') 'exame': 'Mormo',
  };
}

String doseTxt(dynamic d) {
  if (d == 'reforco') return 'Reforço';
  if (d == null || d == 'unica' || d == '') return '';
  return '$dª dose';
}

String tituloRegistro(Map r, List protocolos) {
  final tipo = r['tipo'] as String? ?? '';
  if (tipo == 'vacina') {
    final nomes = ((r['protocolos'] as List?) ?? const []).map((pid) {
      final p = protocolos.cast<Map?>().firstWhere((x) => x?['id'] == pid, orElse: () => null);
      return p?['nome'] ?? pid;
    }).join(' + ');
    return 'Vacina $nomes';
  }
  if (tipo == 'ocorrencia') return (r['titulo'] as String?)?.isNotEmpty == true ? r['titulo'] as String : 'Ocorrência';
  if (tipo == 'reprodutivo' && r['evento'] != null) return r['evento'] as String;
  if (tipo == 'exame' && r['exame'] != null) return r['exame'] as String;
  if (tipo == 'odontologia' && r['procedimento'] != null) return 'Odontologia · ${r['procedimento']}';
  return cats[tipo] ?? 'Registro';
}

// ---------------- formulário de registro ----------------
class ErroValidacao implements Exception {
  final String mensagem;
  ErroValidacao(this.mensagem);
  @override
  String toString() => mensagem;
}

/// Monta o corpo enviado a POST /api/registros, com as mesmas validações do servidor e do Portal Campo.
Map<String, dynamic> montarRegistro({
  required String id,
  required String? animalId,
  required String? sexoAnimal,
  required String dataIso,
  required String tipo,
  List<String> protocolos = const [],
  String dose = 'reforco',
  String obs = '',
  Map<String, String> campos = const {},
  DateTime? agora,
}) {
  if (animalId == null || animalId.isEmpty) throw ErroValidacao('Escolha o animal.');
  final d = data(dataIso);
  if (d == null) throw ErroValidacao('Informe a data do registro.');
  if (d.isAfter(hoje(agora))) throw ErroValidacao('A data não pode ser futura. O sistema calcula a próxima etapa sozinho.');
  if (!cats.containsKey(tipo) || tipo == 'documental') throw ErroValidacao('Escolha o tipo de registro.');
  String c(String k) => (campos[k] ?? '').trim();
  final r = <String, dynamic>{'id': id, 'animalId': animalId, 'data': iso(d), 'tipo': tipo, 'protocolos': <String>[], 'dose': 'unica', 'obs': obs.trim()};
  switch (tipo) {
    case 'vacina':
      if (protocolos.isEmpty) throw ErroValidacao('Marque ao menos uma doença coberta pela vacina.');
      r['protocolos'] = List<String>.from(protocolos);
      r['dose'] = dose;
      r['produto'] = c('produto');
      r['lote'] = c('lote');
    case 'vermifugacao':
      r['protocolos'] = ['vermi'];
      r['produto'] = c('produto');
    case 'odontologia':
      final p = c('procedimento').isEmpty ? 'Avaliação' : c('procedimento');
      r['procedimento'] = p;
      r['protocolos'] = [p.toLowerCase().contains('aparelho') ? 'aparelho' : 'odonto'];
    case 'ferrageamento':
      r['protocolos'] = ['ferrag'];
      r['ferrador'] = c('ferrador');
    case 'exame':
      final e = c('exame').isEmpty ? exames.first : c('exame');
      r['exame'] = e;
      r['resultado'] = c('resultado');
      if (e.contains('AIE')) r['protocolos'] = ['aie'];
      if (e.contains('Mormo')) r['protocolos'] = ['mormo'];
    case 'reprodutivo':
      final ev = c('evento').isEmpty ? 'Cobertura' : c('evento');
      if (sexoAnimal != 'F' && ev != 'Cobertura') throw ErroValidacao('Eventos de gestação só se aplicam a fêmeas.');
      r['evento'] = ev;
      r['garanhao'] = c('garanhao').toUpperCase();
      if (ev == 'Diagnóstico positivo') {
        final cob = data(c('dataCobertura'));
        if (cob == null) throw ErroValidacao('Informe a data da cobertura para calcular a previsão de parto.');
        if (cob.isAfter(d)) throw ErroValidacao('A cobertura deve ser anterior ao diagnóstico.');
        r['dataCobertura'] = iso(cob);
      }
    case 'ocorrencia':
      if (c('titulo').isEmpty) throw ErroValidacao('Descreva a ocorrência em poucas palavras.');
      r['titulo'] = c('titulo');
      r['gravidade'] = c('gravidade').isEmpty ? 'Leve' : c('gravidade');
  }
  r.removeWhere((k, v) => v is String && v.isEmpty && k != 'obs');
  return r;
}

// ---------------- vínculo por QR Code ----------------
class DadosVinculo {
  final String servidor;
  final String codigo;
  DadosVinculo(this.servidor, this.codigo);
}

/// Normaliza o endereço digitado: "10.0.0.5:8090" vira "http://10.0.0.5:8090".
String normalizarServidor(String s) {
  var v = s.trim();
  while (v.endsWith('/')) {
    v = v.substring(0, v.length - 1);
  }
  if (v.isEmpty) return v;
  if (!v.startsWith('http://') && !v.startsWith('https://')) v = 'http://$v';
  return v;
}

/// Lê o conteúdo do QR Code gerado em Equipe › Vincular celular.
DadosVinculo? lerQrVinculo(String? texto) {
  if (texto == null) return null;
  final u = Uri.tryParse(texto.trim());
  if (u == null || u.scheme != 'haras360' || u.host != 'vincular') return null;
  final s = u.queryParameters['s'] ?? '';
  final c = u.queryParameters['c'] ?? '';
  final su = Uri.tryParse(s);
  if (c.length < 16 || su == null || !(su.scheme == 'http' || su.scheme == 'https') || su.host.isEmpty) return null;
  return DadosVinculo(normalizarServidor(s), c);
}

/// Há versão mais nova do APK no servidor?
bool haAtualizacao(Map? app, int codigoAtual) {
  if (app == null) return false;
  final c = app['codigo'];
  return c is int && c > codigoAtual;
}
