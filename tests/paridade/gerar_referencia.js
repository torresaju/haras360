// Gera, com o motor do protótipo validado em 01/10/2026, o estado de demonstração
// e as tarefas e notificações esperadas para a data de hoje. Saída: JSON no stdout.
global.window = global;
global.localStorage = { getItem() { return null; }, setItem() { }, removeItem() { } };
const H = require('./core_prototipo.js');
const st = H.seed();
process.stdout.write(JSON.stringify({
  hoje: H.iso(H.hoje()),
  estado: st,
  tarefas: H.tarefas(st),
  notificacoes: H.notificacoes(st),
  gestacoes: Object.fromEntries(st.animais.map(a => [a.id, H.gestacao(st, a)]))
}));
