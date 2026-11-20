/* Haras360 · componentes de interface compartilhados pelos dois portais */
const UI = (function () {
  const { esc, br, brCurta, relativo } = H;
  const $ = s => document.querySelector(s);

  const I = (p, extra) => '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"' + (extra || '') + '>' + p + '</svg>';
  const ICON = {
    plus: I('<path d="M12 5v14M5 12h14"/>'),
    home: I('<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-5v-6h-4v6H5a1 1 0 0 1-1-1z"/>'),
    horse: I('<path d="M5 20l2-6c-1-2-1-4 1-6l3-3 1 2 3-1c2 0 4 2 4 4l1 3-2 1-2-2-2 2v6"/><path d="M14 20v-4"/>'),
    upload: I('<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>'),
    cal: I('<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>'),
    rules: I('<path d="M4 6h10M4 12h16M4 18h7"/><circle cx="17" cy="6" r="2"/><circle cx="14" cy="18" r="2"/>'),
    bell: I('<path d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/>'),
    team: I('<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 3-5 6-5s6 2 6 5"/><circle cx="17" cy="9" r="2.4"/><path d="M16 15c3 0 5 2 5 4"/>'),
    chat: I('<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9h8M8 12h5"/>'),
    card: I('<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h4"/>'),
    back: I('<path d="M15 5l-7 7 7 7"/>'),
    cam: I('<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>'),
    check: I('<path d="M5 12l5 5 9-10"/>'),
    file: I('<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>'),
    send: I('<path d="M4 12l16-8-6 16-3-6z"/>'),
    alert: I('<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17v.5"/>')
  };

  /* ---------- toast e modal ---------- */
  let tt;
  function toast(msg) {
    let t = $('#toast');
    t.textContent = msg; t.hidden = false;
    clearTimeout(tt); tt = setTimeout(() => { t.hidden = true; }, 4200);
  }
  let onClose = null;
  function abrir({ titulo, corpo, rodape, largo }) {
    const m = $('#modal');
    m.innerHTML = '<div class="sheet' + (largo ? ' wide' : '') + '" role="dialog" aria-modal="true" aria-labelledby="mt"><header><h2 id="mt">' + titulo + '</h2><button class="x" data-act="fechar" aria-label="Fechar">×</button></header><div class="sbody">' + corpo + '</div>' + (rodape ? '<footer>' + rodape + '</footer>' : '') + '</div>';
    m.hidden = false;
    document.body.style.overflow = 'hidden';
    const f = m.querySelector('input:not([type=hidden]):not([type=checkbox]),select,textarea');
    if (f) setTimeout(() => f.focus(), 30);
    return m;
  }
  function fechar() { const m = $('#modal'); m.hidden = true; m.innerHTML = ''; document.body.style.overflow = ''; if (onClose) { const f = onClose; onClose = null; f(); } }
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('#modal').hidden) fechar(); });
  document.addEventListener('click', e => { if (e.target.id === 'modal') fechar(); });

  /* ---------- tons ---------- */
  const TOM = { atrasado: 'c-late', hoje: 'c-soon', semana: 'c-soon', mes: 'c-ok', futuro: 'c-muted', pendente: 'c-info' };
  const TOMCAT = t => 'c-' + ((H.CATS[t] || {}).tom || 'muted');
  function chipStatus(s) { return '<span class="chip ' + TOM[s] + '">' + H.STATUS_TXT[s] + '</span>'; }
  function chipCat(c) { return '<span class="chip nodot ' + TOMCAT(c) + '">' + esc((H.CATS[c] || { nome: c }).nome) + '</span>'; }

  /* ---------- linha de tarefa ---------- */
  function linhaTarefa(t, o) {
    o = o || {};
    const quando = t.doc ? '<b>Pend.</b>doc.' : '<b>' + brCurta(t.due) + '</b>' + relativo(t.due);
    const animal = o.semAnimal ? '' : '<a href="#" data-act="ver-animal" data-id="' + t.animalId + '">' + esc(t.animal) + '</a> · ';
    const acao = t.doc ? '' : t.parto ? '<button class="btn sm" data-act="registrar-tarefa" data-id="' + esc(t.id) + '">Registrar parto</button>' : '<button class="btn sm" data-act="registrar-tarefa" data-id="' + esc(t.id) + '">' + ICON.check + 'Registrar</button>';
    return '<div class="task ' + t.status + '"><span class="bar"></span><div class="when">' + quando + '</div><div class="what"><div class="row" style="gap:8px"><strong>' + esc(t.titulo) + '</strong><span class="chip nodot c-muted">' + esc(t.etapa) + '</span>' + (t.status === 'atrasado' ? '<span class="chip c-late">Atrasado</span>' : '') + '</div><div class="sub">' + animal + esc(t.nota || '') + '</div></div><div class="act">' + acao + '</div></div>';
  }

  /* ---------- prontuário ---------- */
  function linhaTempo(st, regs, o) {
    o = o || {};
    if (!regs.length) return '<div class="empty">Nenhum registro nesta categoria.</div>';
    return '<div class="timeline">' + regs.map(r => {
      const meta = [];
      const dose = H.doseTxt(r.dose); if (r.tipo === 'vacina' && dose) meta.push(dose);
      if (r.produto) meta.push('Produto: ' + esc(r.produto));
      if (r.lote) meta.push('Lote <span class="mono">' + esc(r.lote) + '</span>');
      if (r.ferrador) meta.push('Ferrador: ' + esc(r.ferrador));
      if (r.resultado) meta.push('Resultado: ' + esc(r.resultado));
      if (r.garanhao) meta.push('Garanhão: ' + esc(r.garanhao));
      if (r.dataCobertura && r.evento === 'Diagnóstico positivo') meta.push('Cobertura em ' + br(r.dataCobertura));
      if (r.gravidade) meta.push('Gravidade: ' + esc(r.gravidade));
      const fotos = (r.fotos || []).length ? '<div class="thumbs">' + r.fotos.map((f, i) => '<button data-act="ver-foto" data-r="' + r.id + '" data-i="' + i + '" aria-label="Ampliar foto ' + (i + 1) + '"><img src="' + f + '" alt=""></button>').join('') + '</div>' : '';
      const nome = o.comAnimal ? (() => { const a = H.animal(st, r.animalId); return a ? '<a href="#" data-act="ver-animal" data-id="' + a.id + '">' + esc(a.nome) + '</a> · ' : ''; })() : '';
      const del = o.excluir ? '<button class="btn ghost sm danger" data-act="excluir-reg" data-id="' + r.id + '">Excluir</button>' : '';
      return '<div class="ev"><div class="d">' + br(r.data) + '</div><div class="body"><div class="spread"><div class="row" style="gap:8px">' + chipCat(r.tipo) + '<strong>' + esc(H.tituloRegistro(st, r)) + '</strong></div>' + del + '</div>' + (meta.length ? '<div class="meta">' + meta.map(m => '<span>' + m + '</span>').join('') + '</div>' : '') + (r.obs ? '<p class="obs">' + esc(r.obs) + '</p>' : '') + fotos + '<div class="meta">' + nome + '<span>' + esc(r.autor) + ' · ' + esc(r.origem) + '</span></div></div></div>';
    }).join('') + '</div>';
  }

  function verFoto(st, rid, i) {
    const r = st.registros.find(x => x.id === rid); if (!r) return;
    abrir({ titulo: esc(H.tituloRegistro(st, r)), corpo: '<img src="' + r.fotos[i] + '" alt="Foto do registro" style="border-radius:8px;width:100%"><p class="muted small">' + br(r.data) + ' · ' + esc(r.autor) + '</p>', largo: true });
  }

  /* ---------- fotos ---------- */
  function comprimir(file, max, q) {
    max = max || 1600; q = q || 0.8;
    return new Promise((res, rej) => {
      const fr = new FileReader();
      fr.onload = () => {
        const img = new Image();
        img.onload = () => {
          const k = Math.min(1, max / Math.max(img.width, img.height));
          const c = document.createElement('canvas'); c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
          c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
          res(c.toDataURL('image/jpeg', q));
        };
        img.onerror = () => rej(new Error('Arquivo de imagem inválido'));
        img.src = fr.result;
      };
      fr.onerror = () => rej(new Error('Não foi possível ler o arquivo'));
      fr.readAsDataURL(file);
    });
  }

  /* ---------- formulário de registro ---------- */
  let fotosPend = [];
  const OPC = (arr, sel) => arr.map(v => { const [val, lab] = Array.isArray(v) ? v : [v, v]; return '<option value="' + esc(val) + '"' + (String(val) === String(sel) ? ' selected' : '') + '>' + esc(lab) + '</option>'; }).join('');

  function extras(st, tipo, p) {
    p = p || {};
    if (tipo === 'vacina') {
      const vs = st.protocolos.filter(x => x.cat === 'vacina');
      return '<div class="field full"><span class="lbl">Doenças cobertas (marque todas em vacinas multivalentes)</span><div class="checks">' + vs.map(v => '<label class="check"><input type="checkbox" name="prot" value="' + v.id + '"' + ((p.protocolos || []).includes(v.id) ? ' checked' : '') + '>' + esc(v.nome) + '</label>').join('') + '</div></div>' +
        '<div class="field"><label for="f-dose">Dose</label><select id="f-dose" class="inp">' + OPC([[1, '1ª dose'], [2, '2ª dose'], [3, '3ª dose'], ['reforco', 'Reforço']], p.dose || 'reforco') + '</select></div>' +
        '<div class="field"><label for="f-lote">Lote</label><input id="f-lote" class="inp" value="' + esc(p.lote || '') + '" placeholder="Ex.: RB2291"></div>' +
        '<div class="field full"><label for="f-produto">Produto / marca</label><input id="f-produto" class="inp" value="' + esc(p.produto || '') + '" placeholder="Ex.: Trivalente tétano + encefalomielite + influenza"></div>';
    }
    if (tipo === 'vermifugacao') return '<div class="field full"><label for="f-produto">Vermífugo (princípio ativo)</label><input id="f-produto" class="inp" value="' + esc(p.produto || '') + '" placeholder="Ex.: Ivermectina + praziquantel"></div>';
    if (tipo === 'odontologia') return '<div class="field full"><label for="f-proc">Procedimento</label><select id="f-proc" class="inp">' + OPC(['Avaliação', 'Avaliação e correção', 'Aparelho dentário instalado', 'Retorno de aparelho', 'Extração', 'Outro'], p.procedimento || ((p.protocolos || []).includes('aparelho') ? 'Retorno de aparelho' : 'Avaliação')) + '</select></div>';
    if (tipo === 'ferrageamento') return '<div class="field full"><label for="f-ferrador">Ferrador</label><input id="f-ferrador" class="inp" value="' + esc(p.ferrador || '') + '"></div>';
    if (tipo === 'exame') {
      const sel = (p.protocolos || []).includes('aie') ? 'Anemia Infecciosa (AIE)' : (p.protocolos || []).includes('mormo') ? 'Mormo' : (p.exame || 'Anemia Infecciosa (AIE)');
      return '<div class="field"><label for="f-exame">Exame</label><select id="f-exame" class="inp">' + OPC(['Anemia Infecciosa (AIE)', 'Mormo', 'Hemograma', 'Ultrassonografia', 'Raio-X', 'Outro'], sel) + '</select></div><div class="field"><label for="f-res">Resultado</label><input id="f-res" class="inp" value="' + esc(p.resultado || '') + '" placeholder="Ex.: Negativo"></div>';
    }
    if (tipo === 'reprodutivo') {
      const machos = st.animais.filter(a => a.sexo === 'M').map(a => '<option value="' + esc(a.nome) + '">');
      return '<div class="field"><label for="f-evento">Evento</label><select id="f-evento" class="inp">' + OPC(H.EVENTOS_REPRO, p.evento || 'Cobertura') + '</select></div><div class="field"><label for="f-garanhao">Garanhão</label><input id="f-garanhao" class="inp" list="dl-machos" value="' + esc(p.garanhao || '') + '"><datalist id="dl-machos">' + machos.join('') + '</datalist></div><div class="field"><label for="f-cob">Data da cobertura (diagnóstico positivo)</label><input id="f-cob" type="date" class="inp" value="' + esc(p.dataCobertura || '') + '"></div>';
    }
    if (tipo === 'ocorrencia') return '<div class="field"><label for="f-titulo">O que aconteceu</label><input id="f-titulo" class="inp" value="' + esc(p.titulo || '') + '" placeholder="Ex.: Mancando da pata traseira"></div><div class="field"><label for="f-grav">Gravidade</label><select id="f-grav" class="inp">' + OPC(['Leve', 'Moderada', 'Grave'], p.gravidade || 'Leve') + '</select></div>';
    return '';
  }

  function formRegistro(st, pre, ctx) {
    pre = pre || {}; fotosPend = [];
    const tipos = Object.keys(H.CATS).filter(k => k !== 'documental');
    const animais = st.animais.filter(a => a.vivo);
    const tipo = pre.tipo || 'vacina';
    const corpo = '<form id="fr" class="stack" novalidate><div class="fgrid">' +
      '<div class="field"><label for="f-animal">Animal</label><select id="f-animal" class="inp">' + OPC(animais.map(a => [a.id, a.nome]), pre.animalId) + '</select></div>' +
      '<div class="field"><label for="f-data">Data</label><input id="f-data" type="date" class="inp" value="' + (pre.data || H.iso(H.hoje())) + '" max="' + H.iso(H.hoje()) + '"></div>' +
      '<div class="field full"><label for="f-tipo">Tipo de registro</label><select id="f-tipo" class="inp">' + OPC(tipos.map(k => [k, H.CATS[k].nome]), tipo) + '</select></div>' +
      '</div><div id="f-extra" class="fgrid">' + extras(st, tipo, pre) + '</div>' +
      '<div class="field"><label for="f-obs">Observações</label><textarea id="f-obs" class="inp" placeholder="Descreva o que foi feito ou observado">' + esc(pre.obs || '') + '</textarea></div>' +
      '<div class="field"><span class="lbl">Fotos (até 4)</span><div class="row"><label class="btn" for="f-fotos">' + ICON.cam + 'Adicionar fotos</label><input id="f-fotos" type="file" accept="image/*" multiple hidden><span class="small muted" id="f-fstat">Nenhuma foto</span></div><div class="thumbs" id="f-thumbs"></div></div>' +
      '<p class="note" id="f-erro" hidden></p></form>';
    abrir({ titulo: pre.tituloModal || 'Novo registro no prontuário', corpo, rodape: '<button class="btn" data-act="fechar">Cancelar</button><button class="btn pri" data-act="salvar-registro">' + ICON.check + 'Salvar registro</button>' });
    $('#f-tipo').addEventListener('change', e => { $('#f-extra').innerHTML = extras(st, e.target.value, {}); });
    $('#f-fotos').addEventListener('change', async e => {
      const files = [...e.target.files].slice(0, 4 - fotosPend.length);
      for (const f of files) { try { fotosPend.push(await comprimir(f)); } catch (err) { toast(err.message); } }
      e.target.value = '';
      desenharFotos();
    });
    formRegistro.ctx = ctx;
  }
  function desenharFotos() {
    $('#f-thumbs').innerHTML = fotosPend.map((f, i) => '<button type="button" data-act="rem-foto" data-i="' + i + '" title="Remover foto" style="cursor:pointer"><img src="' + f + '" alt="Foto ' + (i + 1) + '"></button>').join('');
    $('#f-fstat').textContent = fotosPend.length ? fotosPend.length + ' de 4 · toque para remover' : 'Nenhuma foto';
  }
  function remFoto(i) { fotosPend.splice(i, 1); desenharFotos(); }

  function lerRegistro(st) {
    const v = id => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };
    const tipo = v('f-tipo');
    const r = { id: H.uid(), animalId: v('f-animal'), data: v('f-data'), tipo, protocolos: [], dose: 'unica', obs: v('f-obs'), fotos: fotosPend.slice() };
    const erro = m => { const e = $('#f-erro'); e.textContent = m; e.className = 'note bad'; e.hidden = false; return null; };
    if (!r.animalId) return erro('Escolha o animal.');
    if (!r.data) return erro('Informe a data do registro.');
    if (r.data > H.iso(H.hoje())) return erro('A data não pode ser futura. Para agendar, o sistema calcula a próxima etapa automaticamente.');
    if (tipo === 'vacina') {
      r.protocolos = [...document.querySelectorAll('input[name=prot]:checked')].map(i => i.value);
      if (!r.protocolos.length) return erro('Marque ao menos uma doença coberta pela vacina.');
      const d = v('f-dose'); r.dose = d === 'reforco' ? 'reforco' : Number(d);
      r.produto = v('f-produto'); r.lote = v('f-lote');
    } else if (tipo === 'vermifugacao') { r.protocolos = ['vermi']; r.produto = v('f-produto'); }
    else if (tipo === 'odontologia') { r.procedimento = v('f-proc'); r.protocolos = /aparelho/i.test(r.procedimento) ? ['aparelho'] : ['odonto']; }
    else if (tipo === 'ferrageamento') { r.protocolos = ['ferrag']; r.ferrador = v('f-ferrador'); }
    else if (tipo === 'exame') { r.exame = v('f-exame'); r.resultado = v('f-res'); if (/AIE/.test(r.exame)) r.protocolos = ['aie']; if (/Mormo/.test(r.exame)) r.protocolos = ['mormo']; }
    else if (tipo === 'reprodutivo') {
      r.evento = v('f-evento'); r.garanhao = v('f-garanhao').toUpperCase(); r.dataCobertura = v('f-cob');
      const a = H.animal(st, r.animalId);
      if (a && a.sexo !== 'F' && r.evento !== 'Cobertura') return erro('Eventos de gestação só se aplicam a fêmeas.');
      if (r.evento === 'Diagnóstico positivo' && !r.dataCobertura) return erro('Informe a data da cobertura para calcular a previsão de parto.');
    } else if (tipo === 'ocorrencia') { r.titulo = v('f-titulo'); r.gravidade = v('f-grav'); if (!r.titulo) return erro('Descreva a ocorrência em poucas palavras.'); }
    return r;
  }

  /* pré-preenche o formulário a partir de uma tarefa do motor de regras */
  function preDeTarefa(t) {
    if (t.parto) return { animalId: t.animalId, tipo: 'reprodutivo', evento: 'Parto', tituloModal: 'Registrar parto' };
    return { animalId: t.animalId, tipo: t.cat, protocolos: t.protocoloId ? [t.protocoloId] : [], dose: t.dose, tituloModal: 'Registrar ' + t.titulo.toLowerCase() };
  }

  /* ---------- assistente ---------- */
  const SUGS = ['Quais procedimentos estão atrasados?', 'Quando é o parto da Diva?', 'O que muda na vacina de raiva em região endêmica?', 'Quais exames preciso para transportar um cavalo?', 'Como vacinar uma égua gestante?', 'Perdi o prazo do reforço, o que fazer?'];
  function chatHTML(hist, titulo, sub) {
    return '<div class="card flush chat"><div style="padding:16px 18px;border-bottom:1px solid var(--line)"><h2>' + titulo + '</h2><p class="small muted">' + sub + '</p></div><div class="msgs" id="msgs">' +
      hist.map(m => '<div class="msg ' + m.de + '">' + esc(m.t) + (m.f ? '<span class="src">Base: ' + esc(m.f) + '</span>' : '') + '</div>').join('') +
      '</div>' + (hist.length <= 1 ? '<div class="sugs">' + SUGS.map(s => '<button type="button" data-act="sug" data-q="' + esc(s) + '">' + esc(s) + '</button>').join('') + '</div>' : '') +
      '<form id="chat-f"><input id="chat-q" class="inp" placeholder="Pergunte sobre vacinas, normas, gestação ou o plantel" autocomplete="off"><button class="btn pri" aria-label="Enviar">' + ICON.send + '</button></form></div>';
  }

  return { ICON, toast, abrir, fechar, chipStatus, chipCat, linhaTarefa, linhaTempo, verFoto, formRegistro, lerRegistro, remFoto, preDeTarefa, chatHTML, comprimir, TOM, set onClose(f) { onClose = f; } };
})();
