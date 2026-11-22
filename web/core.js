/* Haras360 · núcleo do navegador: utilidades, catálogos, leitura de PDF ABCCMM e assistente. O motor de regras roda na API. */
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
  const EVENTOS_REPRO = ['Cio', 'Cobertura', 'Inseminação', 'Diagnóstico positivo', 'Diagnóstico negativo', 'Parto', 'Aborto'];
  const GESTACAO_DIAS = 340;

  const FAIXAS = [
    { de: 1, ate: 3, valor: 0, nome: 'Gratuito' },
    { de: 4, ate: 10, valor: 12.9, nome: 'Faixa 1' },
    { de: 11, ate: 20, valor: 10.9, nome: 'Faixa 2' },
    { de: 21, ate: 30, valor: 8.9, nome: 'Faixa 3' }
  ];
  let LIMITE_ANIMAIS = 30;
  function mensalidade(n) {
    let t = 0;
    for (const f of FAIXAS) { const q = Math.max(0, Math.min(n, f.ate) - f.de + 1); t += q * f.valor; }
    return Math.round(t * 100) / 100;
  }

  /* ---------- leitura do estado calculado pela API (motor de regras no servidor) ---------- */
  function protocolo(st, id) { return st.protocolos.find(p => p.id === id); }
  function animal(st, id) { return st.animais.find(a => a.id === id); }
  function gestacao(st, a) { return a && st.gestacoes ? (st.gestacoes[a.id] || null) : null; }
  function tarefas(st, opts) { opts = opts || {}; return (st.tarefas || []).filter(t => !opts.animalId || t.animalId === opts.animalId); }
  function notificacoes(st) { return st.notificacoes || []; }
  const STATUS_TXT = { atrasado: 'Atrasado', hoje: 'Hoje', semana: 'Próximos 7 dias', mes: 'Próximos 30 dias', futuro: 'Programado', pendente: 'Pendência' };
  const TIPOS_NOTIF = {
    atrasado: 'Procedimento atrasado',
    semana: 'Procedimento nos próximos 7 dias',
    parto: 'Previsão de parto',
    ocorrencia: 'Ocorrência grave do caseiro',
    documental: 'Pendência documental ABCCMM',
    campo: 'Registro feito pelo operador de campo',
    financeiro: 'Parcelas de vendas a receber'
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

  /* ---------- auditoria e glossário ---------- */
  const ACOES_AUDIT = {
    login: 'Login', login_falha: 'Login recusado', logout: 'Saída', '2fa_cadastro': '2FA cadastrado', '2fa_falha': 'Código 2FA recusado',
    '2fa_redefinido': '2FA redefinido', '2fa_codigos_novos': 'Novos códigos de recuperação', senha_troca: 'Troca de senha', senha_redefinida: 'Senha redefinida',
    sessao_encerrada: 'Sessão encerrada', usuario_criado: 'Usuário criado', usuario_ativado: 'Usuário reativado', usuario_desativado: 'Usuário desativado',
    animal_criado: 'Animal cadastrado', animal_editado: 'Animal editado', importacao: 'Importação ABCCMM', registro_excluido: 'Registro excluído',
    protocolos_alterados: 'Protocolos alterados', protocolos_restaurados: 'Protocolos restaurados', parametro_alterado: 'Parametrização alterada',
    haras_criado: 'Haras criado', logo_alterado: 'Logotipo alterado', haras_alterado: 'Haras alterado', atualizacao_solicitada: 'Atualização solicitada', atualizacao_concluida: 'Atualização concluída',
    atualizacao_falhou: 'Atualização falhou', rollback_solicitado: 'Volta de versão solicitada', rollback_concluido: 'Volta de versão concluída',
    app_vinculo_gerado: 'QR Code do app gerado', app_vinculado: 'Celular vinculado', app_gestor_entrou: 'Gestor entrou pelo app', app_saiu: 'Saiu do app', app_vinculo_falha: 'Vínculo do app recusado',
    backup_solicitado: 'Backup solicitado', backup_concluido: 'Backup concluído', backup_falhou: 'Backup falhou',
    imagem_alterada: 'Imagem alterada', imagem_removida: 'Imagem removida', animal_baixa: 'Baixa de animal', animal_baixa_desfeita: 'Baixa desfeita',
    relatorio_exportado: 'Relatório exportado'
  };
  const GLOSSARIO = [
    ['ABCCMM', 'Associação Brasileira dos Criadores do Cavalo Mangalarga Marchador, responsável pelo registro genealógico da raça.'],
    ['Relatório de Plantel', 'PDF emitido pelo Sistema de Gestão ABCCMM com os animais de um associado. É a fonte da importação no Haras360.'],
    ['Livro', 'Categoria em que o animal está inscrito no registro genealógico, por exemplo "MM6 - Definitivo Fechado Fêmea".'],
    ['DNA VP', 'Exame de DNA com verificação de parentesco realizado. "Sem exame" gera pendência documental.'],
    ['Bloqueado', 'Situação do animal na ABCCMM que impede alguns serviços até ser regularizada.'],
    ['AIE', 'Anemia Infecciosa Equina. Exame com resultado negativo e dentro da validade é exigido para o trânsito (GTA).'],
    ['Mormo', 'Doença bacteriana dos equídeos. O exame negativo é exigido para trânsito e eventos.'],
    ['GTA', 'Guia de Trânsito Animal, documento obrigatório para transportar equídeos.'],
    ['Primovacinação', 'Série inicial de doses de uma vacina. Se o reforço vencer além da tolerância, a série recomeça.'],
    ['Reforço', 'Dose aplicada depois da série inicial, em geral anual ou semestral.'],
    ['Desmama', 'Separação do potro da mãe, por volta dos 6 meses. Marca a 1ª dose de rinopneumonite.'],
    ['Cobertura', 'Monta ou inseminação. Com o diagnóstico positivo, o sistema calcula a previsão de parto.'],
    ['Cio', 'Período em que a égua aceita o garanhão, a cada 21 dias em média. O Haras360 prevê o próximo cio até o diagnóstico positivo.'],
    ['Cio do potro', 'Primeiro cio depois do parto, em geral entre o 7º e o 12º dia.'],
    ['Taxa de prenhez', 'Diagnósticos positivos divididos pelo total de diagnósticos do período.'],
    ['Baixa', 'Saída do animal do plantel por venda, morte, doação ou transferência. O prontuário continua guardado.'],
    ['Vacina multivalente', 'Vacina que protege contra várias doenças em uma aplicação. No registro, marque todas as doenças cobertas.'],
    ['2FA', 'Verificação em duas etapas: além da senha, um código de 6 dígitos do aplicativo autenticador do celular.']
  ];

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
    if (has('plano', 'preco', 'mensal', 'cobran', 'pagar', 'gratis', 'gratuito')) { const n = st.animais.filter(a => a.vivo).length; return { t: 'O plano é gratuito até 3 animais. A partir do 4º, cobra-se por animal em faixas decrescentes. Com ' + n + ' animais ativos, a mensalidade simulada é ' + moeda(mensalidade(n)) + '. Os valores atuais são ilustrativos.', f: 'Plano Haras360' }; }
    if (has('vermif', 'verme')) return { t: 'O padrão configurado é vermifugação a cada 90 dias a partir dos 2 meses de idade. Esse intervalo é um padrão de mercado e deve ser ajustado pelo veterinário, de preferência com base em exame de OPG (contagem de ovos nas fezes).', f: 'Padrão de mercado' };
    if (has('dente', 'odonto', 'aparelho')) return { t: 'A avaliação odontológica está programada a cada 12 meses a partir dos 2 anos. Quando um aparelho dentário é registrado, o sistema agenda o retorno em 24 meses.', f: 'Padrão de mercado' };
    if (has('ferra', 'casco')) return { t: 'O ferrageamento é agendado a cada 45 dias a partir do primeiro registro de ferrageamento do animal. Ajuste o intervalo em Protocolos conforme o ferrador.', f: 'Padrão de mercado' };
    return { t: 'Ainda não tenho essa resposta na base atual. Na próxima versão, o assistente será treinado com o Estatuto e o Regulamento do Registro Genealógico da ABCCMM e responderá citando o artigo correspondente. Experimente perguntar sobre vacinas, gestação, transporte, DNA ou plano.', f: 'Demonstração' };
  }

  return {
    hoje, dt, iso, addDias, addMeses, dias, br, brCurta, brParaIso, idadeMeses, idadeTxt, relativo, uid, esc, norm, moeda, mascaraCPF,
    CATS, EVENTOS_REPRO, GESTACAO_DIAS, FAIXAS, LIMITE_ANIMAIS, STATUS_TXT, TIPOS_NOTIF,
    mensalidade,
    protocolo, animal, gestacao, tarefas, notificacoes, tituloRegistro, doseTxt,
    ACOES_AUDIT, GLOSSARIO,
    linhasPDF, lerPlantel, compararImportacao, lerGenealogia, responder
  };
})();
