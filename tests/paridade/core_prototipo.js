/* Haras360 · núcleo compartilhado: modelo de dados, motor de regras, notificações, planos e leitura de PDF ABCCMM */
const H = (function () {
  const DAY = 86400000;
  const pad = n => String(n).padStart(2, '0');

  /* ---------- datas ---------- */
  function hoje() { const d = new Date(); d.setHours(0, 0, 0, 0); return d; }
  function dt(s) {
    if (s instanceof Date) { const x = new Date(s); x.setHours(0, 0, 0, 0); return x; }
    const [y, m, d] = String(s).slice(0, 10).split('-').map(Number);
    return new Date(y, m - 1, d);
  }
  function iso(d) { d = dt(d); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function addDias(d, n) { const x = dt(d); x.setDate(x.getDate() + n); return x; }
  function addMeses(d, n) {
    const x = dt(d); const day = x.getDate(); x.setDate(1); x.setMonth(x.getMonth() + n);
    const last = new Date(x.getFullYear(), x.getMonth() + 1, 0).getDate(); x.setDate(Math.min(day, last)); return x;
  }
  function dias(a, b) { return Math.round((dt(b) - dt(a)) / DAY); }
  function br(s) { if (!s) return '-'; const d = dt(s); return pad(d.getDate()) + '/' + pad(d.getMonth() + 1) + '/' + d.getFullYear(); }
  function brCurta(s) { const d = dt(s); const m = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']; return pad(d.getDate()) + ' ' + m[d.getMonth()]; }
  function brParaIso(s) { const [d, m, y] = s.split('/'); return y + '-' + m + '-' + d; }
  function idadeMeses(nasc) {
    const n = dt(nasc), t = hoje();
    let m = (t.getFullYear() - n.getFullYear()) * 12 + (t.getMonth() - n.getMonth());
    if (t.getDate() < n.getDate()) m--; return Math.max(0, m);
  }
  function idadeTxt(nasc) {
    if (!nasc) return '-';
    const m = idadeMeses(nasc);
    if (m < 24) return m + (m === 1 ? ' mês' : ' meses');
    const a = Math.floor(m / 12), r = m % 12;
    return a + ' anos' + (r ? ' e ' + r + (r === 1 ? ' mês' : ' meses') : '');
  }
  function relativo(due) {
    const d = dias(hoje(), due);
    if (d === 0) return 'hoje';
    if (d === 1) return 'amanhã';
    if (d === -1) return 'ontem';
    if (d < 0) return 'há ' + (-d) + ' dias';
    return 'em ' + d + ' dias';
  }
  function uid() { return Math.random().toString(36).slice(2, 10); }
  function esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
  function norm(s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  function moeda(v) { return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }); }
  function mascaraCPF(c) { const d = String(c || '').replace(/\D/g, ''); if (d.length !== 11) return c || '-'; return d.slice(0, 3) + '.***.***-' + d.slice(9); }

  /* ---------- catálogos ---------- */
  const CATS = {
    vacina: { nome: 'Vacinação', tom: 'info' },
    vermifugacao: { nome: 'Vermifugação', tom: 'ok' },
    odontologia: { nome: 'Odontologia', tom: 'accent' },
    ferrageamento: { nome: 'Ferrageamento', tom: 'muted' },
    exame: { nome: 'Exame clínico', tom: 'info' },
    reprodutivo: { nome: 'Reprodução', tom: 'accent' },
    ocorrencia: { nome: 'Ocorrência', tom: 'soon' },
    documental: { nome: 'Documentação', tom: 'late' }
  };
  const EVENTOS_REPRO = ['Cobertura', 'Inseminação', 'Diagnóstico positivo', 'Diagnóstico negativo', 'Parto', 'Aborto'];
  const GESTACAO_DIAS = 340;

  function protocolosPadrao() {
    const vet = 'VetJr. UFMG';
    const mer = 'Padrão de mercado';
    return [
      { id: 'raiva', nome: 'Raiva', cat: 'vacina', obrig: 'Obrigatória', gatilho: 'idade', idadeMeses: 4, serie: [30], reforcoDias: 365, via: 'SC ou IM (ver bula)', fonte: vet, ativo: true, nota: 'Reforço semestral em regiões endêmicas (configurável por haras)' },
      { id: 'tetano', nome: 'Tétano', cat: 'vacina', obrig: 'Recomendada', gatilho: 'idade', idadeMeses: 3, serie: [30, 30], reforcoDias: 365, via: 'IM', fonte: vet, ativo: true },
      { id: 'encefalo', nome: 'Encefalomielite', cat: 'vacina', obrig: 'Obrigatória para transporte', gatilho: 'idade', idadeMeses: 3, serie: [30, 30], reforcoDias: 365, via: 'IM', fonte: vet, ativo: true },
      { id: 'influenza', nome: 'Influenza', cat: 'vacina', obrig: 'Recomendada', gatilho: 'idade', idadeMeses: 3, serie: [30, 30], reforcoDias: 365, via: 'IM', fonte: vet, ativo: true, nota: 'Semestral ou anual, a critério do veterinário' },
      { id: 'rino', nome: 'Rinopneumonite', cat: 'vacina', obrig: 'Exigida por alguns estabelecimentos', gatilho: 'idade', idadeMeses: 6, serie: [25, 180], reforcoDias: 365, via: 'IM', fonte: vet, ativo: true, gestacao: [5, 7, 9], nota: '1ª dose na desmama (6 meses). Gestantes no 5º, 7º e 9º mês' },
      { id: 'lepto', nome: 'Leptospirose', cat: 'vacina', obrig: 'Recomendada', gatilho: 'idade', idadeMeses: 4, serie: [30], reforcoDias: 180, via: 'IM', fonte: vet, ativo: true },
      { id: 'garrotilho', nome: 'Garrotilho (adenite)', cat: 'vacina', obrig: 'Conforme risco', gatilho: 'idade', idadeMeses: 4, serie: [], reforcoDias: 180, via: 'IM ou SC (ver bula)', fonte: vet, ativo: false, nota: 'Ative quando houver risco no plantel' },
      { id: 'vermi', nome: 'Vermifugação', cat: 'vermifugacao', gatilho: 'idade', idadeMeses: 2, serie: [], reforcoDias: 90, fonte: mer, ativo: true },
      { id: 'odonto', nome: 'Avaliação odontológica', cat: 'odontologia', gatilho: 'idade', idadeMeses: 24, serie: [], reforcoDias: 365, fonte: mer, ativo: true },
      { id: 'aparelho', nome: 'Retorno de aparelho dentário', cat: 'odontologia', gatilho: 'registro', serie: [], reforcoDias: 730, fonte: mer, ativo: true, nota: 'Começa a contar quando um aparelho é registrado' },
      { id: 'ferrag', nome: 'Ferrageamento', cat: 'ferrageamento', gatilho: 'registro', serie: [], reforcoDias: 45, fonte: mer, ativo: true, nota: 'Começa a contar no primeiro ferrageamento registrado' },
      { id: 'aie', nome: 'Exame de Anemia Infecciosa (AIE)', cat: 'exame', gatilho: 'registro', serie: [], reforcoDias: 60, fonte: mer, ativo: true, nota: 'Validade usual para GTA. Confirme a regra do seu estado' },
      { id: 'mormo', nome: 'Exame de Mormo', cat: 'exame', gatilho: 'registro', serie: [], reforcoDias: 60, fonte: mer, ativo: true, nota: 'Validade usual para GTA. Confirme a regra do seu estado' }
    ];
  }

  const FAIXAS = [
    { de: 1, ate: 3, valor: 0, nome: 'Gratuito' },
    { de: 4, ate: 10, valor: 12.9, nome: 'Faixa 1' },
    { de: 11, ate: 20, valor: 10.9, nome: 'Faixa 2' },
    { de: 21, ate: 30, valor: 8.9, nome: 'Faixa 3' }
  ];
  const LIMITE_ANIMAIS = 30;
  function mensalidade(n) {
    let t = 0;
    for (const f of FAIXAS) { const q = Math.max(0, Math.min(n, f.ate) - f.de + 1); t += q * f.valor; }
    return Math.round(t * 100) / 100;
  }

  /* ---------- dados de demonstração (associado anonimizado) ---------- */
  function seed() {
    const T = hoje();
    const a = n => iso(addDias(T, -n));
    const regs = [];
    const r = (animalId, data, tipo, extra) => regs.push(Object.assign({ id: uid(), animalId, data, tipo, protocolos: [], dose: 'unica', obs: '', fotos: [], autor: 'Carlos Andrade', origem: 'Portal Gestor' }, extra || {}));
    const tri = ['tetano', 'encefalo', 'influenza'];
    const campo = { autor: 'José Ribeiro', origem: 'Portal Cliente' };

    // Beribela
    r('a1', a(250), 'vacina', { protocolos: ['raiva'], dose: 'reforco', produto: 'Vacina antirrábica', lote: 'RB2291' });
    r('a1', a(200), 'vacina', { protocolos: ['tetano', 'encefalo'], dose: 'reforco', produto: 'Bivalente tétano + encefalomielite', lote: 'TE0412' });
    r('a1', a(395), 'vacina', { protocolos: ['influenza'], dose: 'reforco', produto: 'Influenza equina', lote: 'IF1180' });
    r('a1', a(300), 'vacina', { protocolos: ['rino'], dose: 'reforco', produto: 'Herpesvírus equino', lote: 'HV7710' });
    r('a1', a(150), 'vacina', { protocolos: ['lepto'], dose: 'reforco', produto: 'Leptospirose equina', lote: 'LP3304' });
    r('a1', a(95), 'vermifugacao', { protocolos: ['vermi'], produto: 'Ivermectina + praziquantel', obs: 'Dose conforme peso estimado de 420 kg' });
    r('a1', a(340), 'odontologia', { protocolos: ['odonto'], procedimento: 'Avaliação e correção', obs: 'Desgaste de pontas no 2º pré-molar' });
    r('a1', a(40), 'ferrageamento', Object.assign({ protocolos: ['ferrag'], ferrador: 'Seu Antônio', obs: 'Ferrageamento completo, quatro patas' }, campo));
    r('a1', a(50), 'exame', { protocolos: ['aie'], exame: 'Anemia Infecciosa (AIE)', resultado: 'Negativo' });

    // Diva (gestante)
    r('a2', a(215), 'reprodutivo', { evento: 'Cobertura', garanhao: 'SAMBA JFS', obs: 'Monta controlada' });
    r('a2', a(190), 'reprodutivo', { evento: 'Diagnóstico positivo', dataCobertura: a(215), garanhao: 'SAMBA JFS', obs: 'Ultrassonografia aos 25 dias' });
    r('a2', a(60), 'vacina', { protocolos: ['rino'], dose: 'reforco', produto: 'Herpesvírus equino', lote: 'HV7710', obs: 'Dose do 5º mês de gestação' });
    r('a2', a(100), 'vacina', { protocolos: ['raiva'], dose: 'reforco', produto: 'Vacina antirrábica', lote: 'RB2291' });
    r('a2', a(100), 'vacina', { protocolos: tri.slice(), dose: 'reforco', produto: 'Trivalente tétano + encefalomielite + influenza', lote: 'TR5520' });
    r('a2', a(170), 'vacina', { protocolos: ['lepto'], dose: 'reforco', produto: 'Leptospirose equina', lote: 'LP3304' });
    r('a2', a(30), 'vermifugacao', Object.assign({ protocolos: ['vermi'], produto: 'Pamoato de pirantel', obs: 'Princípio ativo seguro para gestantes, conforme veterinário' }, campo));
    r('a2', a(200), 'odontologia', { protocolos: ['odonto'], procedimento: 'Avaliação', obs: 'Sem alterações' });
    r('a2', a(30), 'exame', { exame: 'Ultrassonografia', resultado: 'Gestação evoluindo bem', obs: 'Feto ativo, batimentos normais' });

    // Fiorela
    r('a3', a(370), 'vacina', { protocolos: ['raiva'], dose: 'reforco', produto: 'Vacina antirrábica', lote: 'RB1876' });
    r('a3', a(120), 'vacina', { protocolos: tri.slice(), dose: 'reforco', produto: 'Trivalente tétano + encefalomielite + influenza', lote: 'TR5520' });
    r('a3', a(120), 'vacina', { protocolos: ['rino'], dose: 'reforco', produto: 'Herpesvírus equino', lote: 'HV7710' });
    r('a3', a(90), 'vacina', { protocolos: ['lepto'], dose: 'reforco', produto: 'Leptospirose equina', lote: 'LP3304' });
    r('a3', a(88), 'vermifugacao', Object.assign({ protocolos: ['vermi'], produto: 'Ivermectina' }, campo));
    r('a3', a(100), 'odontologia', { protocolos: ['odonto'], procedimento: 'Avaliação', obs: 'Acompanhar aparelho' });
    r('a3', a(700), 'odontologia', { protocolos: ['aparelho'], procedimento: 'Aparelho dentário instalado', obs: 'Correção de oclusão. Retorno previsto em 24 meses' });

    // Samba
    r('a5', a(20), 'vacina', { protocolos: ['raiva'], dose: 'reforco', produto: 'Vacina antirrábica', lote: 'RB2291' });
    r('a5', a(20), 'vacina', { protocolos: tri.slice(), dose: 'reforco', produto: 'Trivalente tétano + encefalomielite + influenza', lote: 'TR5520' });
    r('a5', a(20), 'vacina', { protocolos: ['rino'], dose: 'reforco', produto: 'Herpesvírus equino', lote: 'HV7710' });
    r('a5', a(20), 'vacina', { protocolos: ['lepto'], dose: 'reforco', produto: 'Leptospirose equina', lote: 'LP3304' });
    r('a5', a(20), 'vermifugacao', Object.assign({ protocolos: ['vermi'], produto: 'Ivermectina + praziquantel' }, campo));
    r('a5', a(30), 'odontologia', { protocolos: ['odonto'], procedimento: 'Avaliação e correção' });
    r('a5', a(44), 'ferrageamento', Object.assign({ protocolos: ['ferrag'], ferrador: 'Seu Antônio' }, campo));
    r('a5', a(58), 'exame', { protocolos: ['aie'], exame: 'Anemia Infecciosa (AIE)', resultado: 'Negativo', obs: 'Para GTA do evento regional' });
    r('a5', a(58), 'exame', { protocolos: ['mormo'], exame: 'Mormo', resultado: 'Negativo' });
    r('a5', a(3), 'ocorrencia', Object.assign({ titulo: 'Corte superficial no boleto anterior esquerdo', gravidade: 'Leve', obs: 'Limpeza com soro e spray cicatrizante. Observar por 3 dias.' }, campo));

    // Neto (potro, nasc. 15/01/2026)
    r('a4', '2026-05-15', 'vacina', { protocolos: ['raiva'], dose: 1, produto: 'Vacina antirrábica', lote: 'RB2291' });
    r('a4', '2026-06-14', 'vacina', { protocolos: ['raiva'], dose: 2, produto: 'Vacina antirrábica', lote: 'RB2291' });
    r('a4', '2026-04-20', 'vacina', { protocolos: tri.slice(), dose: 1, produto: 'Trivalente tétano + encefalomielite + influenza', lote: 'TR4410' });
    r('a4', '2026-05-20', 'vacina', { protocolos: tri.slice(), dose: 2, produto: 'Trivalente tétano + encefalomielite + influenza', lote: 'TR4410' });
    r('a4', '2026-06-19', 'vacina', { protocolos: tri.slice(), dose: 3, produto: 'Trivalente tétano + encefalomielite + influenza', lote: 'TR4410' });
    r('a4', '2026-07-20', 'vacina', { protocolos: ['rino'], dose: 1, produto: 'Herpesvírus equino', lote: 'HV7710', obs: 'Aplicada na desmama' });
    r('a4', '2026-08-15', 'vacina', { protocolos: ['rino'], dose: 2, produto: 'Herpesvírus equino', lote: 'HV7710' });
    r('a4', a(60), 'vermifugacao', Object.assign({ protocolos: ['vermi'], produto: 'Fembendazol', obs: 'Potro, dose ajustada ao peso' }, campo));
    r('a4', a(1), 'ocorrencia', Object.assign({ titulo: 'Potro com leve secreção nasal', gravidade: 'Moderada', obs: 'Comendo normalmente. Temperatura não aferida.' }, campo));

    return {
      versao: 1,
      haras: { nome: 'Haras Recanto do Marchador', proprietario: 'Carlos Andrade', cpf: '00011122233', municipio: 'Sergipe', raivaSemestral: false, associadoABCCMM: 'Carlos Andrade' },
      usuarios: [
        { id: 'u1', nome: 'Carlos Andrade', email: 'carlos@exemplo.com.br', perfil: 'gestor', ativo: true },
        { id: 'u2', nome: 'José Ribeiro', email: 'jose@exemplo.com.br', perfil: 'operador', ativo: true }
      ],
      animais: [
        { id: 'a1', nome: 'BERIBELA DA TERRARUNA', livro: 'MM6 - DEFINITIVO FECHADO FÊMEA', registro: '0185916', sexo: 'F', bloqueado: false, vivo: true, dna: 'DNA - VP', nascimento: '2017-01-13', chip: '982000409602729', pelagem: '', genealogia: {}, origem: 'Importação ABCCMM', importadoEm: '2026-09-02' },
        { id: 'a2', nome: 'DIVA ELO', livro: 'MM6 - DEFINITIVO FECHADO FÊMEA', registro: '0228465', sexo: 'F', bloqueado: false, vivo: true, dna: 'DNA - VP', nascimento: '2020-12-14', chip: '978101083340998', pelagem: '', genealogia: {}, origem: 'Importação ABCCMM', importadoEm: '2026-09-02' },
        { id: 'a3', nome: 'FIORELA RANCHO DA MIRA', livro: 'MM6 - DEFINITIVO FECHADO FÊMEA', registro: '0234790', sexo: 'F', bloqueado: false, vivo: true, dna: 'DNA - VP', nascimento: '2022-03-22', chip: '978101083372202', pelagem: '', genealogia: {}, origem: 'Importação ABCCMM', importadoEm: '2026-09-02' },
        { id: 'a4', nome: 'NETO VÓ PQNA', livro: '', registro: '', sexo: 'M', bloqueado: false, vivo: true, dna: 'Sem exame', nascimento: '2026-01-15', chip: '963003101075189', pelagem: '', genealogia: {}, origem: 'Importação ABCCMM', importadoEm: '2026-09-02' },
        { id: 'a5', nome: 'SAMBA JFS', livro: 'MM5 - DEFINITIVO FECHADO MACHO', registro: '072356', sexo: 'M', bloqueado: false, vivo: true, dna: 'DNA - VP', nascimento: '2021-12-25', chip: '978101083465878', pelagem: '', genealogia: {}, origem: 'Importação ABCCMM', importadoEm: '2026-09-02' }
      ],
      registros: regs,
      protocolos: protocolosPadrao(),
      notifPrefs: {
        atrasado: { push: true, email: true, web: true },
        semana: { push: true, email: false, web: true },
        parto: { push: true, email: true, web: true },
        documental: { push: false, email: true, web: true },
        campo: { push: false, email: false, web: true }
      },
      lidas: []
    };
  }

  /* ---------- persistência local ---------- */
  function carregar(chave) {
    try { const s = localStorage.getItem(chave); if (s) { const o = JSON.parse(s); if (o && o.versao === 1) return o; } } catch (e) { }
    return seed();
  }
  function salvar(chave, st) { try { localStorage.setItem(chave, JSON.stringify(st)); return true; } catch (e) { return false; } }
  function limpar(chave) { try { localStorage.removeItem(chave); } catch (e) { } }

  /* ---------- motor de regras ---------- */
  const porData = (x, y) => (x.data < y.data ? -1 : x.data > y.data ? 1 : 0);
  function protocolo(st, id) { return st.protocolos.find(p => p.id === id); }
  function reforcoDias(st, p) { return p.id === 'raiva' ? (st.haras.raivaSemestral ? 180 : 365) : p.reforcoDias; }
  function animal(st, id) { return st.animais.find(a => a.id === id); }

  function gestacao(st, a) {
    if (!a || a.sexo !== 'F') return null;
    const ev = st.registros.filter(r => r.animalId === a.id && r.tipo === 'reprodutivo' && r.evento).sort(porData);
    let g = null;
    for (const r of ev) {
      if (r.evento === 'Diagnóstico positivo') g = { cobertura: r.dataCobertura || r.data, diagnostico: r.data, garanhao: r.garanhao || '' };
      else if (['Parto', 'Aborto', 'Diagnóstico negativo'].includes(r.evento)) g = null;
    }
    if (!g) return null;
    g.dias = dias(g.cobertura, hoje());
    g.mes = Math.floor(g.dias / 30.44) + 1;
    g.parto = iso(addDias(g.cobertura, GESTACAO_DIAS));
    g.faltam = dias(hoje(), g.parto);
    g.pct = Math.max(0, Math.min(100, Math.round(g.dias / GESTACAO_DIAS * 100)));
    return g;
  }

  function statusDe(due) {
    const d = dias(hoje(), due);
    if (d < 0) return 'atrasado';
    if (d === 0) return 'hoje';
    if (d <= 7) return 'semana';
    if (d <= 30) return 'mes';
    return 'futuro';
  }
  const STATUS_TXT = { atrasado: 'Atrasado', hoje: 'Hoje', semana: 'Próximos 7 dias', mes: 'Próximos 30 dias', futuro: 'Programado', pendente: 'Pendência' };

  function proximaEtapa(st, a, p) {
    const regs = st.registros.filter(r => r.animalId === a.id && (r.protocolos || []).includes(p.id)).sort(porData);
    const serieN = 1 + (p.serie || []).length;
    let due = null, etapa = '', nota = '', dose = 'unica';
    if (!regs.length) {
      if (p.gatilho !== 'idade' || !a.nascimento) return null;
      due = addMeses(a.nascimento, p.idadeMeses);
      if (p.cat === 'vacina') { etapa = serieN > 1 ? '1ª dose (primovacinação)' : '1ª dose'; dose = 1; }
      else etapa = p.cat === 'odontologia' ? 'Primeira avaliação' : 'Primeira aplicação';
      nota = 'Indicada a partir de ' + p.idadeMeses + ' meses de idade';
    } else {
      const last = regs[regs.length - 1];
      const pos = (last.dose === 'reforco' || last.dose === 'unica' || !last.dose) ? serieN : Math.min(Number(last.dose) || serieN, serieN);
      if (pos < serieN) {
        due = addDias(last.data, p.serie[pos - 1]); etapa = (pos + 1) + 'ª dose'; dose = pos + 1;
        nota = 'Intervalo de ' + p.serie[pos - 1] + ' dias após a ' + pos + 'ª dose';
      } else {
        due = addDias(last.data, reforcoDias(st, p));
        dose = p.cat === 'vacina' ? 'reforco' : 'unica';
        etapa = p.cat === 'vacina' ? 'Reforço' : p.cat === 'exame' ? 'Renovação do exame' : p.id === 'aparelho' ? 'Retorno' : 'Próxima aplicação';
        const rd = reforcoDias(st, p);
        nota = (p.cat === 'vacina' ? 'Reforço ' : 'Intervalo ') + (rd >= 365 ? 'anual' : rd === 180 ? 'semestral' : 'de ' + rd + ' dias');
        if (p.cat === 'vacina' && a.nascimento && last.dose !== 'reforco') {
          const m12 = addMeses(a.nascimento, 12);
          if (m12 > dt(last.data) && m12 < due) { due = m12; nota = 'Primeiro reforço aos 12 meses de idade, após a primovacinação'; }
        }
        if (p.cat === 'vacina' && dias(due, hoje()) > 15) {
          nota = 'Reforço vencido há ' + dias(due, hoje()) + ' dias. O protocolo indica reiniciar a primovacinação';
          etapa = 'Reiniciar primovacinação'; dose = 1;
        }
      }
    }
    return { due: iso(due), etapa, nota, dose };
  }

  function tarefas(st, opts) {
    opts = opts || {};
    const out = [];
    for (const a of st.animais) {
      if (!a.vivo) continue;
      if (opts.animalId && a.id !== opts.animalId) continue;
      const g = gestacao(st, a);
      for (const p of st.protocolos) {
        if (!p.ativo) continue;
        const e = proximaEtapa(st, a, p);
        if (!e) continue;
        if (g && p.id === 'rino' && e.etapa !== '2ª dose' && e.etapa !== '3ª dose') continue; // gestante segue o protocolo próprio
        out.push({ id: a.id + ':' + p.id, animalId: a.id, animal: a.nome, protocoloId: p.id, cat: p.cat, titulo: p.nome, etapa: e.etapa, nota: e.nota, dose: e.dose, due: e.due });
      }
      if (g) {
        const rino = protocolo(st, 'rino');
        if (rino && rino.ativo) {
          const regs = st.registros.filter(r => r.animalId === a.id && (r.protocolos || []).includes('rino'));
          for (const m of (rino.gestacao || [5, 7, 9])) {
            const d = addMeses(g.cobertura, m);
            if (regs.some(r => Math.abs(dias(r.data, d)) <= 20)) continue;
            out.push({ id: a.id + ':rino-g' + m, animalId: a.id, animal: a.nome, protocoloId: 'rino', cat: 'vacina', titulo: 'Rinopneumonite', etapa: 'Gestante, ' + m + 'º mês', nota: 'Protocolo de éguas gestantes (5º, 7º e 9º mês)', dose: 'reforco', due: iso(d) });
          }
        }
        out.push({ id: a.id + ':parto', animalId: a.id, animal: a.nome, protocoloId: null, cat: 'reprodutivo', titulo: 'Previsão de parto', etapa: g.mes + 'º mês de gestação', nota: 'Cobertura em ' + br(g.cobertura) + (g.garanhao ? ' com ' + g.garanhao : '') + '. Estimativa de ' + GESTACAO_DIAS + ' dias', dose: null, due: g.parto, parto: true });
      }
      const T = iso(hoje());
      if (!a.registro) out.push({ id: a.id + ':reg', animalId: a.id, animal: a.nome, cat: 'documental', titulo: 'Registro ABCCMM pendente', etapa: 'Documentação', nota: 'Animal sem número de registro no relatório de plantel', due: T, doc: true });
      if (/sem exame/i.test(a.dna || '') || !a.dna) out.push({ id: a.id + ':dna', animalId: a.id, animal: a.nome, cat: 'documental', titulo: 'Exame de DNA pendente', etapa: 'Documentação', nota: 'Necessário para o registro genealógico', due: T, doc: true });
      if (a.bloqueado) out.push({ id: a.id + ':bloq', animalId: a.id, animal: a.nome, cat: 'documental', titulo: 'Animal bloqueado na ABCCMM', etapa: 'Documentação', nota: 'Verifique a situação junto à associação', due: T, doc: true, critico: true });
    }
    out.forEach(t => { t.status = t.doc ? 'pendente' : statusDe(t.due); });
    out.sort((x, y) => (x.due < y.due ? -1 : x.due > y.due ? 1 : 0));
    return out;
  }

  /* ---------- notificações ---------- */
  function notificacoes(st) {
    const ts = tarefas(st);
    const n = [];
    for (const t of ts) {
      if (t.status === 'atrasado') n.push({ id: 'n:' + t.id + ':' + t.due, tipo: 'atrasado', sev: 'critico', titulo: t.titulo + ' · ' + t.animal, texto: t.etapa + ' prevista para ' + br(t.due) + ' (' + relativo(t.due) + ').', animalId: t.animalId, tarefa: t });
      else if (t.parto && dias(hoje(), t.due) <= 45) n.push({ id: 'n:' + t.id, tipo: 'parto', sev: 'alerta', titulo: 'Parto previsto · ' + t.animal, texto: 'Previsão para ' + br(t.due) + ' (' + relativo(t.due) + '). Prepare a baia de maternidade.', animalId: t.animalId });
      else if (t.status === 'hoje' || t.status === 'semana') n.push({ id: 'n:' + t.id + ':' + t.due, tipo: 'semana', sev: 'alerta', titulo: t.titulo + ' · ' + t.animal, texto: t.etapa + ' ' + relativo(t.due) + ', em ' + br(t.due) + '.', animalId: t.animalId, tarefa: t });
      else if (t.doc) n.push({ id: 'n:' + t.id, tipo: 'documental', sev: t.critico ? 'critico' : 'info', titulo: t.titulo + ' · ' + t.animal, texto: t.nota + '.', animalId: t.animalId });
    }
    const limite = iso(addDias(hoje(), -7));
    st.registros.filter(r => r.origem === 'Portal Cliente' && r.data >= limite).sort(porData).reverse().forEach(r => {
      const a = animal(st, r.animalId);
      n.push({ id: 'n:campo:' + r.id, tipo: 'campo', sev: r.tipo === 'ocorrencia' && r.gravidade !== 'Leve' ? 'alerta' : 'info', titulo: 'Registro do campo · ' + (a ? a.nome : ''), texto: r.autor + ' registrou ' + tituloRegistro(st, r).toLowerCase() + ' em ' + br(r.data) + '.', animalId: r.animalId });
    });
    const ordem = { critico: 0, alerta: 1, info: 2 };
    n.sort((x, y) => ordem[x.sev] - ordem[y.sev]);
    return n;
  }
  const TIPOS_NOTIF = {
    atrasado: 'Procedimento atrasado',
    semana: 'Procedimento nos próximos 7 dias',
    parto: 'Previsão de parto',
    documental: 'Pendência documental ABCCMM',
    campo: 'Registro feito pelo operador de campo'
  };

  function tituloRegistro(st, r) {
    if (r.tipo === 'vacina') return 'Vacina ' + (r.protocolos || []).map(id => (protocolo(st, id) || { nome: id }).nome).join(' + ');
    if (r.tipo === 'reprodutivo') return r.evento || 'Evento reprodutivo';
    if (r.tipo === 'ocorrencia') return r.titulo || 'Ocorrência';
    if (r.tipo === 'exame') return 'Exame: ' + (r.exame || 'clínico');
    if (r.tipo === 'odontologia') return r.procedimento || 'Odontologia';
    if (r.tipo === 'ferrageamento') return 'Ferrageamento';
    if (r.tipo === 'vermifugacao') return 'Vermifugação';
    return CATS[r.tipo] ? CATS[r.tipo].nome : 'Registro';
  }
  function doseTxt(d) { if (d === 'reforco') return 'Reforço'; if (d === 'unica' || !d) return ''; return d + 'ª dose'; }

  /* ---------- leitura de PDF (Relatório de Plantel ABCCMM) ---------- */
  async function linhasPDF(file) {
    if (!window.pdfjsLib) throw new Error('O leitor de PDF não carregou. Verifique a conexão e recarregue a página.');
    try { pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'; } catch (e) { }
    const data = new Uint8Array(await file.arrayBuffer());
    const pdf = await pdfjsLib.getDocument({ data, isEvalSupported: false }).promise;
    const linhas = [];
    for (let i = 1; i <= pdf.numPages; i++) {
      const pg = await pdf.getPage(i);
      const tc = await pg.getTextContent();
      const its = tc.items.filter(it => it.str && it.str.trim()).map(it => ({ s: it.str, x: it.transform[4], y: it.transform[5], w: it.width || 0, h: Math.abs(it.transform[3]) || 8 }));
      its.sort((p, q) => q.y - p.y || p.x - q.x);
      const rows = [];
      for (const it of its) {
        const row = rows.find(r => Math.abs(r.y - it.y) <= Math.max(2, it.h * 0.4));
        if (row) row.items.push(it); else rows.push({ y: it.y, items: [it] });
      }
      rows.sort((p, q) => q.y - p.y);
      for (const row of rows) {
        row.items.sort((p, q) => p.x - q.x);
        let s = '', fim = null;
        for (const it of row.items) { if (fim !== null && it.x - fim > 0.8) s += ' '; s += it.s; fim = it.x + it.w; }
        s = s.replace(/\s+/g, ' ').trim();
        if (s) linhas.push(s);
      }
    }
    return linhas;
  }

  const RE_ANIMAL = /^(.+?)\s+(?:(MM\s?\d+\s*-\s*.+?)\s+)?(?:(\d{4,8})\s+)?([MF])\s+(\S+)\s+(Viv[oa]|Mort[oa])\s+(.+?)\s+(\d{2}\/\d{2}\/\d{4})(?:\s+(\d{6,20}))?$/i;
  function lerPlantel(linhas) {
    const texto = linhas.join('\n');
    const plano = linhas.join(' ');
    const res = { valido: /RELAT[ÓO]RIO DE PLANTEL/i.test(texto) || /ABCCMM|Mangalarga/i.test(texto), associado: '', cpf: '', impresso: '', totalInformado: null, machos: null, femeas: null, animais: [], ignoradas: [] };
    let m = plano.match(/Associado\(a\):\s*(.+?)\s*-\s*CPF:\s*([\d.\-]+)/i);
    if (m) { res.associado = m[1].trim(); res.cpf = m[2].replace(/\D/g, ''); }
    m = plano.match(/Impresso em\s*(\d{2}\/\d{2}\/\d{4})/i); if (m) res.impresso = brParaIso(m[1]);
    m = plano.match(/Total de animais:\s*(\d+)/i); if (m) res.totalInformado = Number(m[1]);
    for (const l of linhas) {
      if (!/\d{2}\/\d{2}\/\d{4}/.test(l) || /Impresso em|Associado\(a\)/i.test(l)) continue;
      const x = l.match(RE_ANIMAL);
      if (!x) { res.ignoradas.push(l); continue; }
      res.animais.push({
        nome: x[1].trim().toUpperCase(),
        livro: (x[2] || '').trim(),
        registro: x[3] || '',
        sexo: x[4].toUpperCase(),
        bloqueado: !/^(-|n[aã]o|n)$/i.test(x[5]),
        vivo: /viv/i.test(x[6]),
        dna: x[7].trim(),
        nascimento: brParaIso(x[8]),
        chip: x[9] || ''
      });
    }
    res.machos = res.animais.filter(a => a.sexo === 'M').length;
    res.femeas = res.animais.filter(a => a.sexo === 'F').length;
    return res;
  }

  function compararImportacao(st, lidos) {
    return lidos.map(n => {
      const ex = st.animais.find(a => (n.registro && a.registro === n.registro) || (n.chip && a.chip === n.chip) || norm(a.nome) === norm(n.nome));
      if (!ex) return { novo: n, situacao: 'novo', diffs: [] };
      const campos = ['nome', 'livro', 'registro', 'sexo', 'bloqueado', 'vivo', 'dna', 'nascimento', 'chip'];
      const diffs = campos.filter(c => String(ex[c] ?? '') !== String(n[c] ?? ''));
      return { novo: n, existente: ex, situacao: diffs.length ? 'atualizar' : 'igual', diffs };
    });
  }

  /* certificado ou outro PDF com genealogia: busca rótulos usuais */
  function lerGenealogia(linhas) {
    const g = {};
    const regras = [
      ['avoPaterno', /av[ôo]\s*paterno\s*[:\-]?\s*(.+)/i],
      ['avoPaterna', /av[óo]\s*paterna\s*[:\-]?\s*(.+)/i],
      ['avoMaterno', /av[ôo]\s*materno\s*[:\-]?\s*(.+)/i],
      ['avoMaterna', /av[óo]\s*materna\s*[:\-]?\s*(.+)/i],
      ['pai', /^(?:.*\s)?pai\s*[:\-]\s*(.+)/i],
      ['mae', /^(?:.*\s)?m[ãa]e\s*[:\-]\s*(.+)/i]
    ];
    for (const l of linhas) {
      for (const [k, re] of regras) {
        if (g[k]) continue;
        const m = l.match(re);
        if (m) { const v = m[1].replace(/\s+(registro|reg\.?|n[ºo])\s*.*$/i, '').trim(); if (v && v.length < 80) { g[k] = v.toUpperCase(); break; } }
      }
    }
    return g;
  }

  /* ---------- assistente (base de demonstração) ---------- */
  function responder(st, pergunta) {
    const q = norm(pergunta);
    const has = (...k) => k.some(w => q.includes(w));
    const alvo = st.animais.find(a => q.includes(norm(a.nome).split(' ')[0]));
    const ts = tarefas(st);
    const vac = id => protocolo(st, id);
    const lista = arr => arr.map(t => '• ' + t.animal + ': ' + t.titulo + ' (' + t.etapa + ', ' + br(t.due) + ')').join('\n');

    if (alvo && has('parto', 'gestac', 'prenhe', 'parir')) {
      const g = gestacao(st, alvo);
      if (!g) return { t: alvo.nome + ' não tem gestação ativa registrada no prontuário.' };
      return { t: alvo.nome + ' está com ' + g.dias + ' dias de gestação (' + g.mes + 'º mês). A cobertura foi em ' + br(g.cobertura) + (g.garanhao ? ' com ' + g.garanhao : '') + ', e o parto está previsto para ' + br(g.parto) + ', ' + relativo(g.parto) + '. A estimativa usa ' + GESTACAO_DIAS + ' dias; o veterinário deve confirmar por ultrassonografia.', f: 'Dados do prontuário' };
    }
    if (alvo && has('vacina', 'pendente', 'atras', 'proxim', 'agenda')) {
      const t = ts.filter(x => x.animalId === alvo.id && x.status !== 'futuro');
      if (!t.length) return { t: alvo.nome + ' não tem procedimentos atrasados nem previstos para os próximos 30 dias.', f: 'Motor de regras' };
      return { t: 'Pendências e próximos 30 dias de ' + alvo.nome + ':\n' + lista(t), f: 'Motor de regras' };
    }
    if (has('atrasad', 'pendenc', 'vencid')) {
      const t = ts.filter(x => x.status === 'atrasado');
      if (!t.length) return { t: 'Nenhum procedimento atrasado no plantel.', f: 'Motor de regras' };
      return { t: 'Há ' + t.length + ' procedimento(s) atrasado(s):\n' + lista(t), f: 'Motor de regras' };
    }
    if (has('raiva')) {
      const r = vac('raiva');
      return { t: 'Raiva é obrigatória. 1ª dose aos 4 meses, 2ª dose 30 dias depois e reforço anual. Em estados endêmicos o reforço passa a ser semestral. Neste haras o reforço está configurado como ' + (st.haras.raivaSemestral ? 'semestral' : 'anual') + '. Via ' + (r ? r.via : 'SC ou IM') + ', conforme a bula.', f: 'Protocolo VetJr. UFMG' };
    }
    if (has('gestante', 'prenha', 'gestacao', 'rinopneu', 'herpes')) return { t: 'Para rinopneumonite: 1ª dose na desmama, 2ª dose 3 a 4 semanas depois e 3ª dose 6 meses após a segunda. Éguas gestantes recebem doses no 5º, 7º e 9º mês de gestação. O Haras360 agenda essas doses automaticamente quando um diagnóstico positivo é registrado.', f: 'Protocolo VetJr. UFMG' };
    if (has('reinici', 'perdeu', 'perdi', 'esqueci', 'nunca vacin')) return { t: 'Animais que nunca foram vacinados ou que perderam o prazo do reforço devem refazer a primovacinação daquela vacina, ou seja, reiniciar o esquema desde a 1ª dose. O sistema sinaliza "Reiniciar primovacinação" quando o reforço passa de 15 dias do vencimento.', f: 'Protocolo VetJr. UFMG' };
    if (has('potro', 'potra', 'filhote', '12 meses')) return { t: 'Potros iniciam a vacinação entre 3 e 4 meses (tétano, encefalomielite e influenza a partir de 3; raiva e leptospirose a partir de 4; rinopneumonite na desmama). Concluído o esquema inicial, o primeiro reforço é feito a partir dos 12 meses de idade, e o sistema já programa nessa data.', f: 'Protocolo VetJr. UFMG' };
    if (has('multival', 'trivalen', 'bivalen', 'combinad')) return { t: 'Vacinas multivalentes protegem contra mais de uma doença na mesma aplicação, geralmente com custo menor. No Haras360 basta marcar todas as doenças cobertas em um único registro, e cada protocolo é atualizado.', f: 'Protocolo VetJr. UFMG' };
    if (has('transport', 'gta', 'viagem', 'evento', 'exposic', 'leilao')) return { t: 'Para transporte, a vacina de encefalomielite é obrigatória, e o trânsito de equídeos costuma exigir exames negativos de Anemia Infecciosa (AIE) e Mormo dentro da validade. O sistema usa 60 dias como validade padrão, editável em Protocolos. Confirme a exigência do órgão de defesa agropecuária do seu estado e do evento.', f: 'Protocolo VetJr. UFMG e padrão de mercado' };
    if (has('obrigator')) return { t: 'Pelo protocolo de referência: raiva é obrigatória; encefalomielite é obrigatória para transporte e em alguns estabelecimentos; rinopneumonite é exigida por alguns estabelecimentos. Tétano, influenza e leptospirose são fortemente recomendadas, e garrotilho depende do risco do plantel.', f: 'Protocolo VetJr. UFMG' };
    if (has('dna')) return { t: 'O Relatório de Plantel informa a situação do exame de DNA de cada animal. Quando aparece "Sem exame", o Haras360 abre uma pendência documental, porque o exame é necessário para o registro genealógico.', f: 'Relatório de Plantel ABCCMM' };
    if (has('livro', 'mm5', 'mm6', 'definitivo', 'registro')) return { t: 'O campo "Livro" do relatório indica a categoria em que o animal está inscrito no registro genealógico, por exemplo "MM6 - Definitivo Fechado Fêmea". Animais sem livro e sem número de registro geram a pendência "Registro ABCCMM pendente". Na versão final, o assistente explicará cada categoria citando o artigo do Regulamento do Registro Genealógico.', f: 'Relatório de Plantel ABCCMM' };
    if (has('plano', 'preco', 'mensal', 'cobran', 'pagar', 'gratis', 'gratuito')) { const n = st.animais.filter(a => a.vivo).length; return { t: 'O plano é gratuito até 3 animais. A partir do 4º, cobra-se por animal em faixas decrescentes. Com ' + n + ' animais ativos, a mensalidade simulada é ' + moeda(mensalidade(n)) + '. Os valores desta demonstração são ilustrativos.', f: 'Plano Haras360' }; }
    if (has('vermif', 'verme')) return { t: 'O padrão configurado é vermifugação a cada 90 dias a partir dos 2 meses de idade. Esse intervalo é um padrão de mercado e deve ser ajustado pelo veterinário, de preferência com base em exame de OPG (contagem de ovos nas fezes).', f: 'Padrão de mercado' };
    if (has('dente', 'odonto', 'aparelho')) return { t: 'A avaliação odontológica está programada a cada 12 meses a partir dos 2 anos. Quando um aparelho dentário é registrado, o sistema agenda o retorno em 24 meses.', f: 'Padrão de mercado' };
    if (has('ferra', 'casco')) return { t: 'O ferrageamento é agendado a cada 45 dias a partir do primeiro registro de ferrageamento do animal. Ajuste o intervalo em Protocolos conforme o ferrador.', f: 'Padrão de mercado' };
    return { t: 'Ainda não tenho essa resposta na base desta demonstração. Na versão final, o assistente será treinado com o Estatuto e o Regulamento do Registro Genealógico da ABCCMM e responderá citando o artigo correspondente. Experimente perguntar sobre vacinas, gestação, transporte, DNA ou plano.', f: 'Demonstração' };
  }

  return {
    hoje, dt, iso, addDias, addMeses, dias, br, brCurta, brParaIso, idadeMeses, idadeTxt, relativo, uid, esc, norm, moeda, mascaraCPF,
    CATS, EVENTOS_REPRO, GESTACAO_DIAS, FAIXAS, LIMITE_ANIMAIS, STATUS_TXT, TIPOS_NOTIF,
    protocolosPadrao, mensalidade, seed, carregar, salvar, limpar,
    protocolo, animal, gestacao, proximaEtapa, tarefas, notificacoes, tituloRegistro, doseTxt, statusDe,
    linhasPDF, lerPlantel, compararImportacao, lerGenealogia, responder
  };
})();
if (typeof module !== "undefined") module.exports = H;
