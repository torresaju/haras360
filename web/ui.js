/* Haras360 · componentes de interface compartilhados pelos dois portais */
const UI = (function () {
  const { esc, br, brCurta, relativo } = H;
  const $ = s => document.querySelector(s);

  const I = (p, extra) => '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"' + (extra || '') + '>' + p + '</svg>';
  const ICON = {
    plus: I('<path d="M12 5v14M5 12h14"/>'),
    // módulos (v1.3.0): traço linear único
    dash: I('<rect x="3.5" y="3.5" width="7" height="8" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="5" rx="1.5"/><rect x="13.5" y="11.5" width="7" height="9" rx="1.5"/><rect x="3.5" y="14.5" width="7" height="6" rx="1.5"/>'),
    cavalo: I('<path d="M6 21c-.6-3.6.2-6.8 2.6-9.6L12 8l.6-3.5 1.6 2 1.4-1.6.2 2.6c1.7 1.3 3 3.2 3.8 5.3.3.8-.3 1.6-1.1 1.4l-2.4-.6c-1 .9-1.4 2.6-1.2 7.4"/><circle cx="15.2" cy="9.6" r=".7" fill="currentColor"/>'),
    escudo: I('<path d="M12 3l7 3v5.5c0 4.4-3 7.8-7 9.5-4-1.7-7-5.1-7-9.5V6z"/><path d="M12 8.5v6M9 11.5h6"/>'),
    repro: I('<circle cx="9" cy="9" r="4.5"/><path d="M9 13.5V21M6 18h6"/><path d="M13.5 6.5l5-4M14.5 2.5h4v4"/>'),
    agenda: I('<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/><path d="M8 14h2M14 14h2M8 17h2"/>'),
    graf: I('<path d="M4 20h16"/><rect x="5.5" y="12" width="3" height="6" rx=".8"/><rect x="10.5" y="8" width="3" height="10" rx=".8"/><rect x="15.5" y="4.5" width="3" height="13.5" rx=".8"/>'),
    engr: I('<circle cx="12" cy="12" r="3"/><path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.5 5.5l1.7 1.7M16.8 16.8l1.7 1.7M5.5 18.5l1.7-1.7M16.8 7.2l1.7-1.7"/>'),
    ajuda: I('<circle cx="12" cy="12" r="9"/><path d="M9.6 9.4a2.5 2.5 0 0 1 4.8.9c0 1.7-2.4 2.1-2.4 3.6"/><circle cx="12" cy="17" r=".6" fill="currentColor"/>'),
    vacina: I('<path d="M17 3l4 4M19 5l-9.5 9.5M14 6l4 4M8 13l3 3M4 20l3.5-3.5M6.5 13.5l4 4-2 2-4-4z"/>'),
    sino: I('<path d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15z"/><path d="M10 20a2 2 0 0 0 4 0"/>'),
    imagem: I('<rect x="3" y="4.5" width="18" height="15" rx="2"/><circle cx="8.5" cy="9.5" r="1.8"/><path d="M21 16l-5-5-8 8"/>'),
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
    mic: I('<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>'),
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
    const acao = t.doc ? '' : t.parto ? '<button class="btn sm" data-act="registrar-tarefa" data-id="' + esc(t.id) + '">Registrar parto</button>' : t.cio ? '<button class="btn sm" data-act="registrar-tarefa" data-id="' + esc(t.id) + '">Registrar cio</button>' : '<button class="btn sm" data-act="registrar-tarefa" data-id="' + esc(t.id) + '">' + ICON.check + 'Registrar</button>';
    return '<div class="task ' + t.status + '"><span class="bar"></span><div class="when">' + quando + '</div><div class="what"><div class="row" style="gap:8px"><strong>' + esc(t.titulo) + '</strong><span class="chip nodot c-muted">' + esc(t.etapa) + '</span>' + (t.status === 'atrasado' ? '<span class="chip c-late">Atrasado</span>' : '') + '</div><div class="sub">' + animal + esc(t.nota || '') + '</div></div><div class="act">' + acao + '</div></div>';
  }

  /* ---------- prontuário ---------- */
  const ORIGEM = { 'Portal Cliente': 'Portal Campo', 'Portal Gestor': 'Portal do Gestor', App: 'App do caseiro', 'App do gestor': 'App do gestor' };
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
      if (r.semen) meta.push('Sêmen ' + esc(r.semen.toLowerCase()) + (r.central ? ' · ' + esc(r.central) : ''));
      if (r.dataCobertura && r.evento === 'Diagnóstico positivo') meta.push('Cobertura em ' + br(r.dataCobertura));
      if (r.gravidade) meta.push('Gravidade: ' + esc(r.gravidade));
      if (r.sinais) meta.push('Sinais: ' + esc(r.sinais));
      if (r.ovario) meta.push('Ovário ' + esc(r.ovario.toLowerCase()));
      if (r.foliculo) meta.push('Folículo ' + esc(r.foliculo) + ' mm');
      if (r.edema) meta.push('Edema ' + esc(r.edema));
      const fotos = (r.fotos || []).length ? '<div class="thumbs">' + r.fotos.map((f, i) => '<button data-act="ver-foto" data-r="' + r.id + '" data-i="' + i + '" aria-label="Ampliar foto ' + (i + 1) + '"><img src="' + f + '" alt=""></button>').join('') + '</div>' : '';
      const dur = r.audio ? Math.floor(r.audio.duracao / 60) + ':' + String(r.audio.duracao % 60).padStart(2, '0') : '';
      const audio = r.audio ? '<div class="audio-reg"><span class="small muted">' + ICON.mic + 'Áudio do campo · ' + dur + '</span><audio controls preload="none" src="' + esc(r.audio.url) + '"></audio></div>' : '';
      const nome = o.comAnimal ? (() => { const a = H.animal(st, r.animalId); return a ? '<a href="#" data-act="ver-animal" data-id="' + a.id + '">' + esc(a.nome) + '</a> · ' : ''; })() : '';
      const del = o.excluir ? '<button class="btn ghost sm danger" data-act="excluir-reg" data-id="' + r.id + '">Excluir</button>' : '';
      return '<div class="ev"><div class="d">' + br(r.data) + '</div><div class="body"><div class="spread"><div class="row" style="gap:8px">' + chipCat(r.tipo) + '<strong>' + esc(H.tituloRegistro(st, r)) + '</strong></div>' + del + '</div>' + (meta.length ? '<div class="meta">' + meta.map(m => '<span>' + m + '</span>').join('') + '</div>' : '') + (r.obs ? '<p class="obs">' + esc(r.obs) + '</p>' : '') + fotos + audio + '<div class="meta">' + nome + '<span>' + esc(r.autor) + ' · ' + esc(ORIGEM[r.origem] || r.origem) + '</span></div></div></div>';
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

  /* ---------- logotipo do haras: reduz para 512 px mantendo a transparência ---------- */
  function prepararLogo(file) {
    return new Promise((res, rej) => {
      if (!/^image\/(png|jpeg|webp)$/.test(file.type)) { rej(new Error('Use uma imagem PNG, JPG ou WebP.')); return; }
      const fr = new FileReader();
      fr.onload = () => {
        const img = new Image();
        img.onload = () => {
          // recorta as margens vazias (brancas ou transparentes) para o logotipo ocupar bem o espaço
          const o = document.createElement('canvas'); o.width = img.width; o.height = img.height;
          const ox = o.getContext('2d'); ox.drawImage(img, 0, 0);
          const px = ox.getImageData(0, 0, o.width, o.height).data;
          let x0 = o.width, y0 = o.height, x1 = -1, y1 = -1;
          for (let y = 0; y < o.height; y += 2) for (let x = 0; x < o.width; x += 2) {
            const i = (y * o.width + x) * 4;
            if (px[i + 3] > 24 && (px[i] < 235 || px[i + 1] < 235 || px[i + 2] < 235)) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
          }
          let sx = 0, sy = 0, sw = o.width, sh = o.height;
          if (x1 > x0 && y1 > y0) { const m = Math.round(Math.max(x1 - x0, y1 - y0) * 0.04); sx = Math.max(0, x0 - m); sy = Math.max(0, y0 - m); sw = Math.min(o.width, x1 + m + 2) - sx; sh = Math.min(o.height, y1 + m + 2) - sy; }
          const k = Math.min(1, 512 / Math.max(sw, sh));
          const c = document.createElement('canvas'); c.width = Math.round(sw * k); c.height = Math.round(sh * k);
          c.getContext('2d').drawImage(o, sx, sy, sw, sh, 0, 0, c.width, c.height);
          let url = c.toDataURL('image/png');
          if (url.length > 1300000) url = c.toDataURL('image/webp', 0.9);
          if (url.length > 1300000) { rej(new Error('O logotipo ficou grande demais. Use uma imagem mais simples.')); return; }
          res(url);
        };
        img.onerror = () => rej(new Error('Não foi possível abrir a imagem.'));
        img.src = fr.result;
      };
      fr.onerror = () => rej(new Error('Não foi possível ler o arquivo.'));
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
      // v1.6.0: garanhões do haras e de fora (externos), marcados
      const machos = st.animais.filter(a => a.sexo === 'M' && !(a.baixa && a.baixa.motivo === 'Morte')).map(a => '<option value="' + esc(a.nome) + '"' + (a.externo ? ' label="' + esc(a.nome) + ' (externo)"' : '') + '>');
      const ev = p.evento || 'Cobertura', cio = ev === 'Cio', ins = ev === 'Inseminação';
      // v1.4.0: o evento Cio mostra sinais e dados do exame; os demais, garanhão e cobertura
      return '<div class="field"><label for="f-evento">Evento</label><select id="f-evento" class="inp">' + OPC(H.EVENTOS_REPRO, ev) + '</select></div>' +
        '<div class="field" data-ev="outro"' + (cio ? ' hidden' : '') + '><label for="f-garanhao">Garanhão</label><input id="f-garanhao" class="inp" list="dl-machos" value="' + esc(p.garanhao || '') + '"><datalist id="dl-machos">' + machos.join('') + '</datalist></div>' +
        '<div class="field" data-ev="outro"' + (cio ? ' hidden' : '') + '><label for="f-cob">Data da cobertura (diagnóstico positivo)</label><input id="f-cob" type="date" class="inp" value="' + esc(p.dataCobertura || '') + '"></div>' +
        '<div class="field" data-ev="ins"' + (ins ? '' : ' hidden') + '><label for="f-semen">Tipo de sêmen</label><select id="f-semen" class="inp">' + OPC([['', 'Não informado'], 'Fresco', 'Refrigerado', 'Congelado'], p.semen || '') + '</select></div>' +
        '<div class="field" data-ev="ins"' + (ins ? '' : ' hidden') + '><label for="f-central">Central ou origem do sêmen</label><input id="f-central" class="inp" value="' + esc(p.central || '') + '" placeholder="Ex.: Central Reprodutiva X"></div>' +
        '<div class="field" data-ev="cio"' + (cio ? '' : ' hidden') + '><label for="f-sinais">Sinais observados</label><input id="f-sinais" class="inp" value="' + esc(p.sinais || '') + '" placeholder="Ex.: aceita o rufião, urina com frequência"></div>' +
        '<div class="field" data-ev="cio"' + (cio ? '' : ' hidden') + '><label for="f-ovario">Ovário (exame)</label><select id="f-ovario" class="inp">' + OPC([['', 'Não examinado'], 'Esquerdo', 'Direito'], p.ovario || '') + '</select></div>' +
        '<div class="field" data-ev="cio"' + (cio ? '' : ' hidden') + '><label for="f-foliculo">Folículo (mm)</label><input id="f-foliculo" type="number" min="5" max="80" class="inp" value="' + esc(p.foliculo || '') + '" placeholder="Ex.: 35"></div>' +
        '<div class="field" data-ev="cio"' + (cio ? '' : ' hidden') + '><label for="f-edema">Edema uterino</label><select id="f-edema" class="inp">' + OPC([['', 'Não avaliado'], ['0', '0 (ausente)'], ['1', '1 (leve)'], ['2', '2 (moderado)'], ['3', '3 (intenso)']], p.edema || '') + '</select></div>';
    }
    if (tipo === 'ocorrencia') return '<div class="field"><label for="f-titulo">O que aconteceu</label><input id="f-titulo" class="inp" value="' + esc(p.titulo || '') + '" placeholder="Ex.: Mancando da pata traseira"></div><div class="field"><label for="f-grav">Gravidade</label><select id="f-grav" class="inp">' + OPC(['Leve', 'Moderada', 'Grave'], p.gravidade || 'Leve') + '</select></div>';
    return '';
  }

  function formRegistro(st, pre, ctx) {
    pre = pre || {}; fotosPend = [];
    const tipos = Object.keys(H.CATS).filter(k => k !== 'documental');
    // v1.6.0: animais externos (só gestor) entram no fim da lista, para eventos reprodutivos
    const animais = st.animais.filter(a => a.vivo && !a.baixa).concat(st.animais.filter(a => a.externo));
    const tipo = pre.tipo || ((H.animal(st, pre.animalId) || {}).externo ? 'reprodutivo' : 'vacina');
    const corpo = '<form id="fr" class="stack" novalidate><div class="fgrid">' +
      '<div class="field"><label for="f-animal">Animal</label><select id="f-animal" class="inp">' + OPC(animais.map(a => [a.id, a.nome + (a.externo ? ' (externo)' : '')]), pre.animalId) + '</select></div>' +
      '<div class="field"><label for="f-data">Data</label><input id="f-data" type="date" class="inp" value="' + (pre.data || H.iso(H.hoje())) + '" max="' + H.iso(H.hoje()) + '"></div>' +
      '<div class="field full"><label for="f-tipo">Tipo de registro</label><select id="f-tipo" class="inp">' + OPC(tipos.map(k => [k, H.CATS[k].nome]), tipo) + '</select></div>' +
      '</div><div id="f-extra" class="fgrid">' + extras(st, tipo, pre) + '</div>' +
      '<div class="field"><label for="f-obs">Observações</label><textarea id="f-obs" class="inp" placeholder="Descreva o que foi feito ou observado">' + esc(pre.obs || '') + '</textarea></div>' +
      '<div class="field"><span class="lbl">Fotos (até 4)</span><div class="row"><label class="btn" for="f-fotos">' + ICON.cam + 'Adicionar fotos</label><input id="f-fotos" type="file" accept="image/*" multiple hidden><span class="small muted" id="f-fstat">Nenhuma foto</span></div><div class="thumbs" id="f-thumbs"></div></div>' +
      '<p class="note" id="f-erro" hidden></p></form>';
    abrir({ titulo: pre.tituloModal || 'Novo registro no prontuário', corpo, rodape: '<button class="btn" data-act="fechar">Cancelar</button><button class="btn pri" data-act="salvar-registro">' + ICON.check + 'Salvar registro</button>' });
    $('#f-tipo').addEventListener('change', e => { $('#f-extra').innerHTML = extras(st, e.target.value, {}); });
    $('#f-extra').addEventListener('change', e => {
      if (e.target.id !== 'f-evento') return;
      const ev = e.target.value, cio = ev === 'Cio';
      document.querySelectorAll('#f-extra [data-ev]').forEach(el => { el.hidden = el.dataset.ev === 'ins' ? ev !== 'Inseminação' : (el.dataset.ev === 'cio') !== cio; });
    });
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
    if ((H.animal(st, r.animalId) || {}).externo && tipo !== 'reprodutivo') return erro('Para animais externos, registre apenas eventos reprodutivos.');
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
      r.evento = v('f-evento');
      if (r.evento === 'Cio') {
        r.sinais = v('f-sinais'); r.ovario = v('f-ovario'); r.foliculo = v('f-foliculo'); r.edema = v('f-edema');
        if (r.foliculo && !(+r.foliculo >= 5 && +r.foliculo <= 80)) return erro('O folículo deve ficar entre 5 e 80 mm.');
      } else { r.garanhao = v('f-garanhao').toUpperCase(); r.dataCobertura = v('f-cob'); }
      if (r.evento === 'Inseminação') { r.semen = v('f-semen'); r.central = v('f-central'); }
      const a = H.animal(st, r.animalId);
      if (a && a.sexo !== 'F' && r.evento !== 'Cobertura') return erro(r.evento === 'Cio' ? 'O cio só se aplica a fêmeas.' : 'Eventos de gestação só se aplicam a fêmeas.');
      if (r.evento === 'Diagnóstico positivo' && !r.dataCobertura) return erro('Informe a data da cobertura para calcular a previsão de parto.');
    } else if (tipo === 'ocorrencia') { r.titulo = v('f-titulo'); r.gravidade = v('f-grav'); if (!r.titulo) return erro('Descreva a ocorrência em poucas palavras.'); }
    return r;
  }

  /* pré-preenche o formulário a partir de uma tarefa do motor de regras */
  function preDeTarefa(t) {
    if (t.parto) return { animalId: t.animalId, tipo: 'reprodutivo', evento: 'Parto', tituloModal: 'Registrar parto' };
    if (t.cio) return { animalId: t.animalId, tipo: 'reprodutivo', evento: 'Cio', tituloModal: 'Registrar cio' };
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

  /* ---------- barra superior com menus agrupados ---------- */
  /* ---------- marca (v1.3.0): perfil de cavalo em traço contínuo com o arco dourado do "360" ---------- */
  const LOGO_PATH = 'M34 106 C31 84 34 64 43 49 C48 39 53 31 58 26 L60 16 L65 23 L69 15 L71 25 C78 30 84 38 89 48 C93 56 98 63 100 69 C101 74 97 78 92 77 C87 76 83 73 79 71 C74 69 70 70 68 74 C66 82 67 94 71 106';
  function logo(escuro, cls) {
    const tinta = escuro ? '#F3F1E9' : '#193D30';
    return '<svg class="' + (cls || 'logo-sim') + '" viewBox="0 0 120 120" aria-hidden="true" focusable="false"><path d="M18 94 A50 50 0 0 1 94 20" fill="none" stroke="#D5A064" stroke-width="6" stroke-linecap="round"/>' +
      '<path d="' + LOGO_PATH + '" fill="none" stroke="' + tinta + '" stroke-width="5.5" stroke-linejoin="round" stroke-linecap="round"/><path d="M57 32 C50 44 46 58 46 76" fill="none" stroke="' + tinta + '" stroke-width="3.2" stroke-linecap="round"/><circle cx="76" cy="41" r="2.8" fill="' + tinta + '"/></svg>';
  }
  /* Marca completa: o logotipo enviado pelo administrador ou o símbolo padrão com o nome. */
  function marca(marcaImg, escuro) {
    if (marcaImg && marcaImg.url) return '<span class="marca-img"><img src="' + esc(marcaImg.url) + '" alt="Haras360"></span>';
    return logo(escuro) + '<span class="marca-txt"><b>Haras<i>360</i></b><small>Gestão de haras</small></span>';
  }
  /* Ilustração padrão (vetor próprio): campo ao entardecer, cerca, árvore, égua e potro. */
  const CAVALO = 'M60 58 C64 48 76 45 92 47 C106 49 118 48 128 44 C134 41 140 34 146 26 C150 20 154 16 158 14 L158 7 L162 12 L165 7 L166 15 C170 19 176 28 181 38 C184 44 186 48 183 51 C180 53 175 51 171 47 C167 43 162 40 158 41 C154 46 151 54 148 62 C146 70 144 74 138 77 C128 80 104 80 84 80 C72 80 64 76 61 70 C59 66 59 62 60 58 Z M61 58 C52 60 46 70 45 82 C44 92 46 100 50 104 C49 94 52 84 58 76 C61 70 62 64 61 58 Z M60 64 C64 76 72 80 78 78 C76 88 70 94 68 100 L68 122 L63 122 L63 100 C62 92 59 80 60 64 Z M80 76 L92 78 C90 88 86 96 85 104 L85 122 L80 122 L80 104 C80 94 80 86 80 76 Z M128 76 L138 76 C137 86 134 92 134 100 L134 122 L129 122 L129 100 C129 92 128 84 128 76 Z M138 72 L148 64 C148 76 146 86 146 96 L148 122 L143 122 L141 98 C140 88 139 80 138 72 Z';
  let nIlu = 0;
  // recortes da mesma cena: faixa do horizonte para o cabeçalho, cena inteira para banner e fundos
  const RECORTE = { 'cab-img': '0 110 1200 220', 'side-ilu': '330 120 700 290' };
  function ilustracao(cls) {
    const k = 'i' + (++nIlu);
    const vb = RECORTE[cls] || '0 0 1200 400';
    let cerca = '';
    for (let x = 0; x <= 1200; x += 70) cerca += '<rect x="' + x + '" y="292" width="7" height="58" rx="2"/>';
    return '<svg class="' + (cls || 'ilustra') + '" viewBox="' + vb + '" preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false">' +
      '<defs><linearGradient id="ceu-' + k + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2B5A47"/><stop offset=".45" stop-color="#C98F52"/><stop offset=".8" stop-color="#F0D3A0"/></linearGradient>' +
      '<radialGradient id="sol-' + k + '" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#FFF4D8"/><stop offset=".55" stop-color="#F7DCA6" stop-opacity=".9"/><stop offset="1" stop-color="#F7DCA6" stop-opacity="0"/></radialGradient></defs>' +
      '<rect width="1200" height="400" fill="url(#ceu-' + k + ')"/><circle cx="760" cy="262" r="150" fill="url(#sol-' + k + ')"/>' +
      '<path d="M0 262 C160 226 300 240 430 252 C560 264 700 226 860 230 C1000 234 1100 250 1200 240 V400 H0 Z" fill="#82978A" opacity=".55"/>' +
      '<path d="M0 300 C200 276 380 290 560 296 C760 302 960 276 1200 286 V400 H0 Z" fill="#244D3C"/>' +
      '<g fill="#193D30" opacity=".9"><rect x="0" y="306" width="1200" height="6"/><rect x="0" y="328" width="1200" height="6"/>' + cerca + '</g>' +
      '<g fill="#193D30"><path d="M128 312 L136 230 L144 312 Z"/><circle cx="118" cy="214" r="34"/><circle cx="150" cy="196" r="40"/><circle cx="176" cy="222" r="30"/><circle cx="136" cy="182" r="30"/></g>' +
      '<g fill="#14322A"><path transform="translate(500 196) scale(1.12)" d="' + CAVALO + '"/><path transform="translate(905 252) scale(-.62 .62)" d="' + CAVALO + '"/></g>' +
      '<path d="M0 340 C300 330 600 344 900 336 C1020 333 1120 338 1200 336 V400 H0 Z" fill="#193D30"/></svg>';
  }
  /* Fundo personalizado: a imagem do haras ou da plataforma, ou a ilustração padrão. */
  const FOCO = { centro: 'center', topo: 'top', base: 'bottom' };
  function fundo(img, cls) {
    if (img && img.url) return '<img class="' + (cls || 'fundo') + '" src="' + esc(img.url) + '" alt="" style="object-position:center ' + (FOCO[img.foco] || 'center') + '">';
    return ilustracao(cls || 'fundo');
  }
  /* Reduz e converte para WebP no navegador antes de enviar (v1.3.0). */
  async function prepararImagem(file, maxL, maxA) {
    if (!/^image\/(png|jpeg|webp)$/.test(file.type)) throw new Error('Envie uma imagem PNG, JPG ou WebP.');
    if (file.size > 8 * 1024 * 1024) throw new Error('A imagem pode ter no máximo 8 MB.');
    const bmp = await createImageBitmap(file);
    const k = Math.min(1, maxL / bmp.width, maxA / bmp.height);
    const c = document.createElement('canvas'); c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
    c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
    const blob = await new Promise(res => c.toBlob(res, 'image/webp', 0.82));
    if (!blob) throw new Error('Não foi possível converter a imagem neste navegador.');
    return blob;
  }

  /* Editor de imagens de personalização (v1.3.0), usado pelo gestor (haras) e pelo administrador (plataforma).
     slots: [{ tipo, rotulo, onde, proporcao, maxL, maxA }]; imagens: retorno de descrever(); escopo: 'haras' | 'plataforma' */
  const SLOTS = {
    logo: { rotulo: 'Logotipo da plataforma', onde: 'Menu lateral, tela de entrada e manual', proporcao: '3/1', maxL: 900, maxA: 300, contem: true },
    entrada: { rotulo: 'Fundo da tela de entrada', onde: 'Lado esquerdo da tela de login', proporcao: '4/5', maxL: 1400, maxA: 1750 },
    cabecalho: { rotulo: 'Imagem do cabeçalho', onde: 'Topo do portal do gestor e do Portal Campo', proporcao: '3/1', maxL: 2400, maxA: 800 },
    banner: { rotulo: 'Banner do Dashboard', onde: 'Faixa "Desempenho do haras"', proporcao: '4/1', maxL: 2400, maxA: 600 },
    app: { rotulo: 'Fundo do app', onde: 'Abertura e topo do app Android', proporcao: '9/16', maxL: 1080, maxA: 1920 }
  };
  function editorImagens(tipos, imagens, escopo) {
    return '<div class="img-grid">' + tipos.map(t => {
      const sl = SLOTS[t], im = imagens[t];
      const propria = im && im.origem === escopo;
      const prev = sl.contem ? (im ? '<img src="' + esc(im.url) + '" alt="" style="object-fit:contain;padding:12px">' : '<div class="img-marca">' + marca(null, true) + '</div>') : fundo(im, 'img-prev-f');
      return '<div class="img-slot"><div class="img-prev' + (sl.contem ? ' escuro' : '') + '" style="aspect-ratio:' + sl.proporcao + '">' + prev + '</div>' +
        '<div class="img-info"><b>' + sl.rotulo + '</b><span class="small muted">' + sl.onde + ' · ' + (propria ? 'imagem própria' : im ? 'padrão da plataforma' : 'ilustração padrão') + '</span>' +
        '<div class="row" style="gap:6px;margin-top:6px"><label class="btn sm" for="img-' + t + '">' + ICON.imagem + 'Escolher imagem</label><input id="img-' + t + '" type="file" accept="image/png,image/jpeg,image/webp" data-img-tipo="' + t + '" hidden>' +
        (propria && !sl.contem ? '<select class="inp sm" data-img-foco="' + t + '" aria-label="Ponto de foco"><option value="centro"' + (im.foco === 'centro' ? ' selected' : '') + '>Foco no centro</option><option value="topo"' + (im.foco === 'topo' ? ' selected' : '') + '>Foco no topo</option><option value="base"' + (im.foco === 'base' ? ' selected' : '') + '>Foco na base</option></select>' : '') +
        (propria ? '<button class="btn ghost sm" data-act="img-padrao" data-tipo="' + t + '">Voltar ao padrão</button>' : '') + '</div></div></div>';
    }).join('') + '</div><p class="small muted">PNG, JPG ou WebP de até 8 MB. O navegador reduz e converte para WebP antes de enviar.</p>';
  }
  /* liga os campos do editor: base é '/api/haras/imagens' ou '/api/admin/marca'; depois(resposta) atualiza a tela */
  function ligarEditorImagens(base, depois) {
    document.querySelectorAll('[data-img-tipo]').forEach(inp => inp.onchange = async () => {
      const f = inp.files[0]; if (!f) return;
      const sl = SLOTS[inp.dataset.imgTipo];
      try {
        toast('Preparando a imagem...');
        const blob = await prepararImagem(f, sl.maxL, sl.maxA);
        const fd = new FormData(); fd.append('arquivo', blob, inp.dataset.imgTipo + '.webp'); fd.append('foco', 'centro');
        const r = await API.upload(base + '/' + inp.dataset.imgTipo, fd);
        toast(r.resumo); depois(r);
      } catch (e) { toast(e.message); }
    });
    document.querySelectorAll('[data-img-foco]').forEach(sel => sel.onchange = async () => {
      try { const r = await API.patch(base + '/' + sel.dataset.imgFoco, { foco: sel.value }); toast(r.resumo); depois(r); } catch (e) { toast(e.message); }
    });
  }

  const CARET = '<svg class="caret" viewBox="0 0 10 10" aria-hidden="true"><path d="M2 3.5l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';
  const MARCA = '<svg viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" aria-hidden="true"><path d="M11 34V20a9 9 0 0 1 18 0v14"/><path d="M7 34h8M25 34h8"/><circle cx="14" cy="22" r="1.2" fill="currentColor"/><circle cx="26" cy="22" r="1.2" fill="currentColor"/><circle cx="16" cy="14.5" r="1.2" fill="currentColor"/><circle cx="24" cy="14.5" r="1.2" fill="currentColor"/></svg>';
  function itemMenu(it, atual, cls) {
    const sel = atual === it.id || (it.tambem || []).includes(atual);
    if (it.href) return '<a class="' + cls + '" href="' + it.href + '" target="_blank" rel="noopener">' + esc(it.rotulo) + (it.desc ? '<small>' + esc(it.desc) + '</small>' : '') + '</a>';
    if (it.off) return '<button class="' + cls + ' off" data-act="fora-plano" data-m="' + esc(it.rotulo) + '" title="Disponível em outro plano">' + esc(it.rotulo) + '<span class="tag">Plano</span></button>';
    return '<button class="' + cls + '" data-act="nav" data-v="' + it.id + '"' + (sel ? ' aria-current="page"' : '') + '>' + (cls === 'di' && it.desc ? '<span>' + esc(it.rotulo) + '<small>' + esc(it.desc) + '</small></span>' : esc(it.rotulo)) + '</button>';
  }
  /* Estrutura v1.3.0: menu lateral (marca + módulos) e cabeçalho com o haras, avisos e usuário. */
  function itemLado(it, atual) {
    const sel = atual === it.id || (it.tambem || []).includes(atual);
    const ic = it.ic ? ICON[it.ic] || '' : '';
    if (it.href) return '<a class="si" href="' + it.href + '" target="_blank" rel="noopener">' + ic + '<span>' + esc(it.rotulo) + '</span></a>';
    if (it.off) return '<button class="si off" data-act="fora-plano" data-m="' + esc(it.rotulo) + '" title="Disponível em outro plano">' + ic + '<span>' + esc(it.rotulo) + '</span><span class="tag">Plano</span></button>';
    if (it.breve) return '<button class="si off" data-act="em-breve" data-m="' + esc(it.rotulo) + '">' + ic + '<span>' + esc(it.rotulo) + '</span><span class="tag">Em breve</span></button>';
    return '<button class="si" data-act="nav" data-v="' + it.id + '"' + (sel ? ' aria-current="page"' : '') + '>' + ic + '<span>' + esc(it.rotulo) + '</span></button>';
  }
  function topbar(o) {
    const lado = o.menu.map((m, i) => {
      if (!m.itens) return itemLado(m, o.atual);
      const sel = m.itens.some(it => it.id === o.atual || (it.tambem || []).includes(o.atual));
      const aberto = sel || (topbar.abertos || {})[m.grupo];
      return '<div class="sg"><button class="si' + (m.itens.every(it => it.off) ? ' off' : '') + '" data-grp="' + esc(m.grupo) + '" aria-expanded="' + !!aberto + '"' + (sel ? ' data-sel="1"' : '') + '>' + (ICON[m.ic] || '') + '<span>' + esc(m.grupo) + '</span>' + CARET + '</button>' +
        '<div class="sub"' + (aberto ? '' : ' hidden') + '>' + m.itens.map(it => itemLado(Object.assign({}, it, { ic: null }), o.atual)).join('') + '</div></div>';
    }).join('');
    const ini = (o.usuario.nome || '?').split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase();
    const userMenu = '<div class="drop-m" id="dd-user" hidden><div style="padding:8px 10px"><b>' + esc(o.usuario.nome) + '</b><small class="muted" style="display:block">' + esc(o.usuario.email) + '</small></div><div class="dsep"></div>' +
      o.usuarioItens.map(it => '<button class="di" data-act="' + it.act + '">' + esc(it.rotulo) + '</button>').join('') + '<div class="dsep"></div><button class="di" data-act="sair">Sair</button></div>';
    const h = o.haras;
    const ident = h ? (h.logo ? '<span class="logo-h"><img src="' + esc(h.logo) + '" alt="Logotipo de ' + esc(h.nome) + '"></span>' : '') +
        '<div class="cab-nome"><b>' + esc(h.nome) + '</b>' + (h.municipio ? '<small>' + esc(h.municipio) + (h.uf ? ' – ' + esc(h.uf) : '') + '</small>' : '') + '</div>'
      : '<div class="cab-nome"><b>' + esc(o.sub) + '</b></div>';
    return '<aside class="side" id="menu-principal" aria-label="Menu principal"><a class="side-marca" href="' + o.home + '">' + marca(o.marca, true) + '</a>' +
      '<nav class="side-nav">' + lado + '</nav><div class="side-pe">' + ilustracao('side-ilu') + '</div></aside>' +
      '<div class="cab">' + (o.cabecalho !== false ? '<div class="cab-fundo">' + fundo(o.cabecalho, 'cab-img') + '</div>' : '') +
      '<div class="cab-in"><button class="tb-ic hamb" data-act="hamb" aria-label="Abrir menu" aria-controls="menu-principal" aria-expanded="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>' +
      '<div class="cab-id">' + ident + '</div><div class="tb-acts">' +
      (o.sino ? '<button class="tb-ic" data-act="nav" data-v="' + o.sino.view + '" aria-label="Notificações">' + ICON.sino + (o.sino.n ? '<span class="badge">' + o.sino.n + '</span>' : '') + '</button>' : '') +
      '<div style="position:relative"><button class="userbtn" data-dd="user" aria-expanded="false" aria-haspopup="true"><span class="avatar">' + esc(ini) + '</span><span class="n">' + esc(o.usuario.nome.split(' ')[0]) + '<small>' + esc(o.perfilTxt) + '</small></span>' + CARET + '</button>' + userMenu + '</div>' +
      '</div></div></div><div class="side-veu" data-act="hamb" hidden></div>';
  }
  document.addEventListener('click', e => {
    const g = e.target.closest('[data-grp]');
    if (!g) return;
    const ab = g.getAttribute('aria-expanded') !== 'true';
    g.setAttribute('aria-expanded', String(ab)); g.nextElementSibling.hidden = !ab;
    topbar.abertos = Object.assign(topbar.abertos || {}, { [g.dataset.grp]: ab });
  });
  function fecharMenus(exceto) {
    document.querySelectorAll('[data-dd][aria-expanded="true"]').forEach(b => { if (b !== exceto) { b.setAttribute('aria-expanded', 'false'); const d = document.getElementById('dd-' + b.dataset.dd); if (d) d.hidden = true; } });
  }
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-dd]');
    if (b) { const ab = b.getAttribute('aria-expanded') === 'true'; fecharMenus(b); b.setAttribute('aria-expanded', String(!ab)); const d = document.getElementById('dd-' + b.dataset.dd); if (d) d.hidden = ab; return; }
    if (e.target.closest('[data-act="hamb"]')) { const m = document.getElementById('menu-principal'); const ab = m.classList.toggle('aberto'); document.querySelectorAll('[data-act="hamb"].tb-ic').forEach(b => b.setAttribute('aria-expanded', String(ab))); const v = document.querySelector('.side-veu'); if (v) v.hidden = !ab; return; }
    if (!e.target.closest('.drop-m') || e.target.closest('[data-act]')) { fecharMenus(); const m = document.getElementById('menu-principal'); if (m && e.target.closest('[data-act="nav"]')) { m.classList.remove('aberto'); const v = document.querySelector('.side-veu'); if (v) v.hidden = true; } }
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharMenus(); });

  /* confirmação na própria página: o primeiro clique arma, o segundo executa */
  function confirmar(el, txt, fn) {
    if (el.dataset.armed) { delete el.dataset.armed; fn(); return; }
    el.dataset.armed = '1'; const old = el.innerHTML; el.innerHTML = txt; el.classList.add('danger');
    setTimeout(() => { if (el.isConnected && el.dataset.armed) { delete el.dataset.armed; el.innerHTML = old; el.classList.remove('danger'); } }, 4000);
  }

  /* códigos de recuperação do 2FA: mostrados uma única vez */
  function mostrarCodigos(codigos, titulo) {
    abrir({ titulo: titulo || 'Códigos de recuperação', corpo: '<p>Guarde estes códigos em local seguro, fora do celular. Cada um permite entrar uma única vez se você perder o aplicativo autenticador.</p><div class="codigos mono" style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;font-size:1rem;background:var(--surface-2);padding:14px;border-radius:8px">' + codigos.map(c => '<span>' + esc(c) + '</span>').join('') + '</div><p class="note warn">Estes códigos não serão mostrados de novo.</p>', rodape: '<button class="btn" data-act="copiar-codigos">Copiar</button><button class="btn pri" data-act="fechar">Já guardei</button>' });
    mostrarCodigos.atual = codigos;
  }
  document.addEventListener('click', async e => {
    if (!e.target.closest('[data-act="copiar-codigos"]')) return;
    try { await navigator.clipboard.writeText((mostrarCodigos.atual || []).join('\n')); toast('Códigos copiados.'); } catch (err) { toast('Selecione os códigos e copie manualmente.'); }
  });

  return { ICON, logo, marca, ilustracao, fundo, prepararImagem, editorImagens, ligarEditorImagens, toast, topbar, prepararLogo, fecharMenus, confirmar, mostrarCodigos, abrir, fechar, chipStatus, chipCat, linhaTarefa, linhaTempo, verFoto, formRegistro, lerRegistro, remFoto, preDeTarefa, chatHTML, comprimir, TOM, set onClose(f) { onClose = f; } };
})();
