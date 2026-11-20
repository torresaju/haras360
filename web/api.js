/* Haras360 · cliente da API */
const API = (function () {
  async function req(metodo, url, corpo, bruto) {
    let r;
    const headers = { 'X-Haras360': '1', 'X-Portal': window.H360_PORTAL || '' };
    if (!bruto) headers['Content-Type'] = 'application/json';
    try {
      r = await fetch(url, { method: metodo, credentials: 'same-origin', headers, body: corpo === undefined ? undefined : (bruto ? corpo : JSON.stringify(corpo)) });
    } catch (e) { throw new Error('Sem conexão com o servidor. Verifique a internet e tente de novo.'); }
    let dados = null;
    try { dados = await r.json(); } catch (e) { }
    if (r.status === 401 && !/\/api\/(login|me\/senha|me\/codigos)/.test(url)) {
      location.href = '/entrar?volta=' + encodeURIComponent(location.pathname);
      throw new Error('Sessão expirada. Faça login novamente.');
    }
    if (!r.ok) {
      const d = dados && dados.detail;
      throw new Error(typeof d === 'string' ? d : r.status === 413 ? 'Arquivo grande demais.' : 'Não foi possível concluir (erro ' + r.status + '). Confira os dados e tente de novo.');
    }
    return dados;
  }
  return {
    get: u => req('GET', u), post: (u, b) => req('POST', u, b || {}), put: (u, b) => req('PUT', u, b), patch: (u, b) => req('PATCH', u, b), del: u => req('DELETE', u),
    upload: (u, formData) => req('POST', u, formData, true)
  };
})();
