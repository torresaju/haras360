"""Financeiro da plataforma (v1.7.0): clientes (contratantes dos haras), mensalidades, recebimentos,
avisos de vencimento e bloqueio por atraso. Valores em centavos.

Perfis: "admin" (tudo) e "financeiro" (só esta área). O gestor de cada haras vê a própria assinatura
em GET /api/assinatura.
"""
import re
import uuid
from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import Response
from sqlalchemy import func, select

from . import imagens as IMG
from . import parametros as P
from . import regras as R
from .config import VERSAO
from .db import Animal, Cliente, Cobranca, Haras, Usuario
from .seguranca import auditar, erro, gestor, get_db, qr_svg, usuario_atual
from .vendas import MEIOS, brl, centavos, cifrar, decifrar, documento_valido, formatar, mascara

r = APIRouter()
SITUACOES = ("Teste", "Ativo", "Suspenso", "Cancelado")
UFS = set("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())


def financeiro(u: Usuario = Depends(usuario_atual)) -> Usuario:
    if u.perfil not in ("admin", "financeiro"):
        erro(403, "Apenas o financeiro ou o administrador da plataforma pode fazer isto.")
    return u


def nid():
    return "f" + uuid.uuid4().hex[:20]


def _txt(v, n):
    return re.sub(r"[\x00-\x1f]", "", str(v or "")).strip()[:n]


def _data(v, rot, opcional=False):
    if opcional and v in (None, ""):
        return None
    try:
        return R.d(str(v))
    except (TypeError, ValueError):
        erro(400, f"Informe {rot} no formato AAAA-MM-DD.")


def params(db):
    return {**P.PADRAO_GLOBAL["financeiro"], **(P.ler(db, "financeiro") or {})}


# ---------------- clientes ----------------
def garantir_clientes(db, hoje=None):
    """Todo haras tem um cliente. Haras sem cliente (novos, de antes da v1.7.0 ou criados pela linha de comando) entram em Teste."""
    hoje = hoje or R.hoje()
    pf = params(db)
    tem = set(db.scalars(select(Cliente.haras_id)))
    for h in db.scalars(select(Haras)):
        if h.id not in tem:
            db.add(Cliente(haras_id=h.id, situacao="Teste", inicio=hoje, teste_ate=hoje + timedelta(days=int(pf["testeDias"])),
                           dia_vencimento=int(pf["diaPadrao"]), nome=h.proprietario or h.nome, endereco={}))
    db.flush()


def ativos_por_haras(db):
    return dict(db.execute(select(Animal.haras_id, func.count()).where(Animal.vivo.is_(True)).group_by(Animal.haras_id)).all())


def calcular(db, c: Cliente, n_animais, venc: date):
    """Mensalidade de um cliente: faixas de preço pelos animais ativos, com o ajuste combinado (se vigente no vencimento)."""
    faixas = P.ler(db, "faixas")
    base = P.mensalidade(faixas, n_animais)
    detalhe = []
    for f in faixas:
        q = max(0, min(n_animais, f["ate"]) - f["de"] + 1)
        if q:
            detalhe.append({"de": f["de"], "ate": f["ate"], "qtd": q, "valor": f.get("valor")})
    calc = {"animais": n_animais, "faixas": detalhe, "base": None if base is None else round(base * 100), "ajuste": None}
    vigente = c.ajuste_tipo in ("desconto", "fixo") and (not c.ajuste_ate or venc <= c.ajuste_ate)
    if base is None and not (vigente and c.ajuste_tipo == "fixo"):
        calc["valor"] = None  # faixa de preço sem valor definido
        return calc
    valor = round((base or 0) * 100)
    if vigente and c.ajuste_tipo == "desconto":
        valor = round(valor * (100 - c.ajuste_valor) / 100)
        calc["ajuste"] = f"Desconto de {c.ajuste_valor}%"
    elif vigente and c.ajuste_tipo == "fixo":
        valor = c.ajuste_valor
        calc["ajuste"] = f"Valor fixo combinado de {brl(c.ajuste_valor)}"
    calc["valor"] = max(0, valor)
    return calc


def _vencimento(ano, mes, dia):
    return date(ano, mes, min(dia, 28))


def gerar(db, hoje=None, request=None, u=None):
    """Gera as mensalidades que entram no prazo de antecedência. Idempotente: uma por haras e mês."""
    hoje = hoje or R.hoje()
    garantir_clientes(db, hoje)
    pf = params(db)
    ant = int(pf["antecedenciaDias"])
    ativos = ativos_por_haras(db)
    feitas = []
    for c, h in db.execute(select(Cliente, Haras).join(Haras, Haras.id == Cliente.haras_id)):
        if c.situacao == "Teste" and c.teste_ate and c.teste_ate < hoje:
            c.situacao = "Ativo"  # fim do teste
            auditar(db, "cliente_teste_encerrado", usuario=u, haras_id=h.id, alvo=h.nome, request=request)
        if c.situacao != "Ativo" or not h.ativo:
            continue
        desde = max(d for d in (c.inicio, (c.teste_ate + timedelta(days=1)) if c.teste_ate else None, date(2000, 1, 1)) if d)
        for k in (0, 1):
            m = hoje.month - 1 + k
            venc = _vencimento(hoje.year + m // 12, m % 12 + 1, c.dia_vencimento)
            comp = venc.strftime("%Y-%m")
            if venc < desde or hoje < venc - timedelta(days=ant):
                continue
            if db.scalar(select(Cobranca.id).where(Cobranca.haras_id == h.id, Cobranca.competencia == comp)):
                continue
            calc = calcular(db, c, ativos.get(h.id, 0), venc)
            if not calc["valor"]:  # faixa gratuita ou preço a definir: nada a cobrar
                continue
            cb = Cobranca(id=nid(), haras_id=h.id, competencia=comp, descricao=f"Mensalidade {comp[5:]}/{comp[:4]}", vencimento=venc,
                          valor=calc["valor"], calculo=calc)
            db.add(cb)
            db.flush()
            feitas.append(cb)
            auditar(db, "mensalidade_gerada", usuario=u, haras_id=h.id, alvo=h.nome, detalhe={"competencia": comp, "valor": calc["valor"]}, request=request)
    db.commit()
    return feitas


def situacao(cb: Cobranca, hoje=None):
    if cb.cancelada_em:
        return "cancelada"
    if cb.pago_em:
        return "paga"
    h = hoje or R.hoje()
    if cb.vencimento < h:
        return "atrasada"
    return "vence" if (cb.vencimento - h).days <= 7 else "aberta"


def cobranca_out(cb: Cobranca, nome_haras=""):
    s = situacao(cb)
    return {"id": cb.id, "harasId": cb.haras_id, "haras": nome_haras, "competencia": cb.competencia, "descricao": cb.descricao,
            "vencimento": R.iso(cb.vencimento), "valor": cb.valor, "calculo": cb.calculo, "situacao": s,
            "diasAtraso": (R.hoje() - cb.vencimento).days if s == "atrasada" else 0,
            "pagoEm": R.iso(cb.pago_em) if cb.pago_em else None, "valorPago": cb.valor_pago, "meio": cb.meio_pago or "", "obs": cb.obs or "",
            "canceladaEm": R.iso(cb.cancelada_em) if cb.cancelada_em else None, "motivoCancelamento": cb.motivo_cancelamento or ""}


def bloqueio(db, haras_id, hoje=None):
    """Mensalidade com atraso de N dias (parametrizável) deixa o gestor só para consulta, salvo liberação com prazo."""
    hoje = hoje or R.hoje()
    c = db.get(Cliente, haras_id)
    if c and c.liberado_ate and c.liberado_ate >= hoje:
        return None
    dias = int(params(db)["bloqueioDias"])
    cb = db.scalar(select(Cobranca).where(Cobranca.haras_id == haras_id, Cobranca.pago_em.is_(None), Cobranca.cancelada_em.is_(None),
                                          Cobranca.vencimento <= hoje - timedelta(days=dias)).order_by(Cobranca.vencimento))
    if not cb:
        return None
    return {"cobrancaId": cb.id, "descricao": cb.descricao, "vencimento": R.iso(cb.vencimento), "valor": cb.valor, "diasAtraso": (hoje - cb.vencimento).days}


def notificacoes_assinatura(db, haras_id):
    """Avisos ao gestor: mensalidade a vencer em 7 dias, vencendo hoje, atrasada e portal bloqueado."""
    n = []
    hoje = R.hoje()
    for cb in db.scalars(select(Cobranca).where(Cobranca.haras_id == haras_id, Cobranca.pago_em.is_(None), Cobranca.cancelada_em.is_(None))):
        s, txt = situacao(cb), f"{cb.descricao} do Haras360, {brl(cb.valor)}"
        if s == "atrasada":
            n.append({"id": f"n:mensalidade:{cb.id}:atrasada", "tipo": "mensalidade", "sev": "critico", "titulo": "Mensalidade do Haras360 em atraso",
                      "texto": f"{txt}, venceu em {R.br(cb.vencimento)}. Veja como pagar em Minha assinatura.", "cobrancaId": cb.id})
        elif cb.vencimento == hoje:
            n.append({"id": f"n:mensalidade:{cb.id}:hoje", "tipo": "mensalidade", "sev": "alerta", "titulo": "Mensalidade do Haras360 vence hoje",
                      "texto": f"{txt}. Veja como pagar em Minha assinatura.", "cobrancaId": cb.id})
        elif s == "vence":
            n.append({"id": f"n:mensalidade:{cb.id}:vence", "tipo": "mensalidade", "sev": "info", "titulo": "Mensalidade do Haras360 a vencer",
                      "texto": f"{txt}, vence em {R.br(cb.vencimento)} ({R.relativo(cb.vencimento)}).", "cobrancaId": cb.id})
    return n


# ---------------- Pix copia e cola (BR Code estático) ----------------
def _campo(i, v):
    return f"{i}{len(v):02d}{v}"


def _crc16(s):
    crc = 0xFFFF
    for b in s.encode("utf-8"):
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def _ascii(s, n):
    import unicodedata
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9 .\-]", "", s).upper().strip()[:n]


def pix_copia_e_cola(chave, nome, cidade, valor_centavos, txid):
    """Payload EMV do Pix (Manual do BR Code do Banco Central), estático, com valor e identificador."""
    conta = _campo("00", "br.gov.bcb.pix") + _campo("01", chave.strip())
    txid = re.sub(r"[^A-Za-z0-9]", "", txid)[:25] or "***"
    p = (_campo("00", "01") + _campo("26", conta) + _campo("52", "0000") + _campo("53", "986") + _campo("54", f"{valor_centavos / 100:.2f}")
         + _campo("58", "BR") + _campo("59", _ascii(nome, 25) or "HARAS360") + _campo("60", _ascii(cidade, 15) or "BRASIL")
         + _campo("62", _campo("05", txid)) + "6304")
    return p + _crc16(p)


def como_pagar(db, cb: Cobranca = None):
    pf = params(db)
    out = {"pixChave": pf["pixChave"], "pixNome": pf["pixNome"], "dadosBancarios": pf["dadosBancarios"]}
    if cb and pf["pixChave"] and not cb.pago_em and not cb.cancelada_em:
        txid = "H360" + re.sub(r"[^A-Za-z0-9]", "", cb.id)[-16:]
        out["pix"] = pix_copia_e_cola(pf["pixChave"], pf["pixNome"], pf["pixCidade"], cb.valor, txid)
        out["qr"] = qr_svg(out["pix"])
    return out


# ---------------- saídas ----------------
def cliente_out(c: Cliente, h: Haras, n_animais, cobs, bloq):
    abertas = [x for x in cobs if not x.pago_em and not x.cancelada_em]
    return {"harasId": h.id, "haras": h.nome, "harasAtivo": bool(h.ativo), "plano": h.plano, "animais": n_animais, "situacao": c.situacao,
            "inicio": R.iso(c.inicio) if c.inicio else None, "testeAte": R.iso(c.teste_ate) if c.teste_ate else None,
            "diaVencimento": c.dia_vencimento, "nome": c.nome, "documento": c.documento_mascara or "", "contatoNome": c.contato_nome,
            "contatoEmail": c.contato_email, "contatoTelefone": c.contato_telefone, "endereco": c.endereco or {},
            "ajusteTipo": c.ajuste_tipo, "ajusteValor": c.ajuste_valor, "ajusteAte": R.iso(c.ajuste_ate) if c.ajuste_ate else None,
            "liberadoAte": R.iso(c.liberado_ate) if c.liberado_ate else None, "liberadoMotivo": c.liberado_motivo or "",
            "canceladoEm": R.iso(c.cancelado_em) if c.cancelado_em else None, "obs": c.obs or "",
            "aReceber": sum(x.valor for x in abertas), "emAtraso": sum(x.valor for x in abertas if x.vencimento < R.hoje()),
            "bloqueado": bloq}


def _mes(d):
    return d.strftime("%Y-%m")


def painel_dados(db):
    hoje = R.hoje()
    ativos = ativos_por_haras(db)
    cobs = list(db.scalars(select(Cobranca).order_by(Cobranca.vencimento.desc())))
    por_haras = {}
    for cb in cobs:
        por_haras.setdefault(cb.haras_id, []).append(cb)
    clientes, nomes = [], {}
    for c, h in db.execute(select(Cliente, Haras).join(Haras, Haras.id == Cliente.haras_id).order_by(Haras.nome)):
        nomes[h.id] = h.nome
        b = bloqueio(db, h.id, hoje)
        out = cliente_out(c, h, ativos.get(h.id, 0), por_haras.get(h.id, []), b)
        m = hoje.month
        venc = _vencimento(hoje.year, m, c.dia_vencimento)
        out["proxima"] = calcular(db, c, ativos.get(h.id, 0), venc if venc >= hoje else _vencimento(hoje.year + m // 12, m % 12 + 1, c.dia_vencimento))
        clientes.append(out)
    mes = _mes(hoje)
    validas = [x for x in cobs if not x.cancelada_em]
    abertas = [x for x in validas if not x.pago_em]
    atrasadas = [x for x in abertas if x.vencimento < hoje]
    faixas = Counter()
    for x in atrasadas:
        d = (hoje - x.vencimento).days
        faixas["1 a 15 dias" if d <= 15 else "16 a 30 dias" if d <= 30 else "Mais de 30 dias"] += x.valor
    meses = []
    for k in range(11, -1, -1):
        m = hoje.month - 1 - k
        meses.append(f"{hoje.year + m // 12:04d}-{m % 12 + 1:02d}")
    fat_v, rec_v = Counter(), Counter()
    for x in validas:
        fat_v[_mes(x.vencimento)] += x.valor
        if x.pago_em:
            rec_v[_mes(x.pago_em)] += x.valor_pago or 0
    sit = Counter(c["situacao"] for c in clientes)
    mrr = sum((c["proxima"]["valor"] or 0) for c in clientes if c["situacao"] == "Ativo" and c["harasAtivo"])
    indicadores = {
        "clientes": {s: sit.get(s, 0) for s in SITUACOES}, "total": len(clientes),
        "novosMes": sum(1 for c in clientes if c["inicio"] and c["inicio"][:7] == mes),
        "canceladosMes": sum(1 for c in clientes if c["canceladoEm"] and c["canceladoEm"][:7] == mes),
        "animais": sum(c["animais"] for c in clientes), "bloqueados": sum(1 for c in clientes if c["bloqueado"]),
        "mrr": mrr, "faturadoMes": fat_v.get(mes, 0), "recebidoMes": rec_v.get(mes, 0),
        "aReceber": sum(x.valor for x in abertas), "emAtraso": sum(x.valor for x in atrasadas),
        "clientesEmAtraso": len({x.haras_id for x in atrasadas}),
        "inadimplencia": [{"faixa": k, "valor": faixas.get(k, 0)} for k in ("1 a 15 dias", "16 a 30 dias", "Mais de 30 dias")],
        "meses": [{"mes": k, "faturado": fat_v.get(k, 0), "recebido": rec_v.get(k, 0)} for k in meses],
    }
    return {"indicadores": indicadores, "clientes": clientes, "cobrancas": [cobranca_out(x, nomes.get(x.haras_id, "")) for x in cobs],
            "parametros": params(db), "meios": list(MEIOS), "situacoes": list(SITUACOES)}


# ---------------- rotas do financeiro ----------------
@r.get("/api/financeiro/painel")
def painel(request: Request, u: Usuario = Depends(financeiro), db=Depends(get_db)):
    gerar(db, request=request, u=u)
    out = painel_dados(db)
    out.update({"usuario": {"id": u.id, "nome": u.nome, "email": u.email, "perfil": u.perfil}, "versao": VERSAO, "marca": IMG.descrever(db)})
    return out


def _cliente(db, hid):
    c = db.get(Cliente, hid)
    h = db.get(Haras, hid)
    if not c or not h:
        erro(404, "Cliente não encontrado.")
    return c, h


@r.put("/api/financeiro/clientes/{hid}")
def editar_cliente(hid: int, request: Request, body: dict = Body(...), u: Usuario = Depends(financeiro), db=Depends(get_db)):
    c, h = _cliente(db, hid)
    antes = c.situacao
    sit = body.get("situacao", c.situacao)
    if sit not in SITUACOES:
        erro(400, "Situação inválida.")
    c.situacao = sit
    if sit == "Cancelado" and antes != "Cancelado":
        c.cancelado_em = R.hoje()
    elif sit != "Cancelado":
        c.cancelado_em = None
    c.inicio = _data(body.get("inicio"), "o início do contrato", opcional=True) or c.inicio
    c.teste_ate = _data(body.get("testeAte"), "o fim do teste", opcional=True)
    if sit == "Teste" and not c.teste_ate:
        erro(400, "Informe até quando vai o teste.")
    try:
        dia = int(body.get("diaVencimento", c.dia_vencimento))
    except (TypeError, ValueError):
        dia = 0
    if not 1 <= dia <= 28:
        erro(400, "O dia de vencimento deve ficar entre 1 e 28.")
    c.dia_vencimento = dia
    c.nome = _txt(body.get("nome"), 160)
    if not c.nome:
        erro(400, "Informe o nome ou a razão social do contratante.")
    doc = _txt(body.get("documento"), 30)
    if doc and "*" not in doc:
        if not documento_valido(doc)[0]:
            erro(400, "CPF ou CNPJ inválido. Confira os números.")
        c.documento, c.documento_mascara = cifrar(doc), mascara(doc)
    elif not doc:
        c.documento, c.documento_mascara = None, ""
    c.contato_nome = _txt(body.get("contatoNome"), 120)
    email = _txt(body.get("contatoEmail"), 160)
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        erro(400, "E-mail do contato financeiro inválido.")
    c.contato_email = email
    c.contato_telefone = _txt(body.get("contatoTelefone"), 40)
    e = body.get("endereco") or {}
    uf = _txt(e.get("uf"), 2).upper()
    if uf and uf not in UFS:
        erro(400, "UF inválida.")
    cep = re.sub(r"\D", "", str(e.get("cep") or ""))
    if cep and len(cep) != 8:
        erro(400, "CEP inválido.")
    c.endereco = {"logradouro": _txt(e.get("logradouro"), 160), "numero": _txt(e.get("numero"), 20), "complemento": _txt(e.get("complemento"), 80),
                  "bairro": _txt(e.get("bairro"), 80), "cidade": _txt(e.get("cidade"), 80), "uf": uf, "cep": f"{cep[:5]}-{cep[5:]}" if cep else ""}
    tipo = body.get("ajusteTipo", "nenhum")
    if tipo not in ("nenhum", "desconto", "fixo"):
        erro(400, "Ajuste inválido.")
    c.ajuste_tipo = tipo
    if tipo == "desconto":
        try:
            pct = int(body.get("ajusteValor") or 0)
        except (TypeError, ValueError):
            pct = -1
        if not 1 <= pct <= 100:
            erro(400, "O desconto deve ficar entre 1% e 100%.")
        c.ajuste_valor = pct
    elif tipo == "fixo":
        c.ajuste_valor = centavos(body.get("ajusteValor"))
    else:
        c.ajuste_valor = 0
    c.ajuste_ate = _data(body.get("ajusteAte"), "a validade do ajuste", opcional=True) if tipo != "nenhum" else None
    c.obs = _txt(body.get("obs"), 2000)
    auditar(db, "cliente_editado", usuario=u, haras_id=h.id, alvo=h.nome, detalhe={"situacao": f"{antes} > {sit}" if antes != sit else sit}, request=request)
    db.commit()
    return {"resumo": f"Dados de {h.nome} salvos."}


@r.post("/api/financeiro/clientes/{hid}/documento")
def ver_documento(hid: int, request: Request, u: Usuario = Depends(financeiro), db=Depends(get_db)):
    c, h = _cliente(db, hid)
    if not c.documento:
        erro(404, "Este cliente não tem CPF ou CNPJ cadastrado.")
    auditar(db, "documento_visto", usuario=u, haras_id=h.id, alvo=f"Contratante de {h.nome}", request=request)
    db.commit()
    return {"documento": formatar(decifrar(c.documento))}


@r.post("/api/financeiro/clientes/{hid}/liberar")
def liberar(hid: int, request: Request, body: dict = Body(...), u: Usuario = Depends(financeiro), db=Depends(get_db)):
    c, h = _cliente(db, hid)
    ate = _data(body.get("ate"), "até quando fica liberado", opcional=True)
    motivo = _txt(body.get("motivo"), 300)
    if ate:
        if ate < R.hoje() or ate > R.hoje() + timedelta(days=60):
            erro(400, "Libere por no máximo 60 dias a partir de hoje.")
        if not motivo:
            erro(400, "Informe o motivo da liberação.")
    c.liberado_ate, c.liberado_motivo = ate, motivo if ate else ""
    auditar(db, "cliente_liberado" if ate else "cliente_liberacao_removida", usuario=u, haras_id=h.id, alvo=h.nome,
            detalhe={"ate": R.iso(ate) if ate else None, "motivo": motivo}, request=request)
    db.commit()
    return {"resumo": f"{h.nome} liberado até {R.br(ate)}." if ate else f"Liberação de {h.nome} removida."}


@r.post("/api/financeiro/clientes/{hid}/avulsa")
def avulsa(hid: int, request: Request, body: dict = Body(...), u: Usuario = Depends(financeiro), db=Depends(get_db)):
    _c, h = _cliente(db, hid)
    desc = _txt(body.get("descricao"), 160)
    if not desc:
        erro(400, "Descreva a cobrança.")
    valor = centavos(body.get("valor"))
    if valor <= 0:
        erro(400, "Informe o valor da cobrança.")
    venc = _data(body.get("vencimento"), "o vencimento")
    cb = Cobranca(id=nid(), haras_id=h.id, competencia=None, descricao=desc, vencimento=venc, valor=valor, calculo={"avulsa": True})
    db.add(cb)
    auditar(db, "cobranca_avulsa", usuario=u, haras_id=h.id, alvo=h.nome, detalhe={"descricao": desc, "valor": valor}, request=request)
    db.commit()
    return {"resumo": f"Cobrança de {brl(valor)} criada para {h.nome}."}


def _cobranca(db, cid):
    cb = db.get(Cobranca, cid)
    if not cb:
        erro(404, "Cobrança não encontrada.")
    return cb, db.get(Haras, cb.haras_id)


@r.post("/api/financeiro/cobrancas/{cid}/pagar")
def pagar(cid: str, request: Request, body: dict = Body(...), u: Usuario = Depends(financeiro), db=Depends(get_db)):
    cb, h = _cobranca(db, cid)
    if cb.cancelada_em:
        erro(400, "Esta cobrança está cancelada.")
    if cb.pago_em:
        erro(400, "Esta cobrança já está paga.")
    data = _data(body.get("data"), "a data do pagamento")
    if data > R.hoje():
        erro(400, "A data do pagamento não pode ser futura.")
    valor = centavos(body.get("valor")) if body.get("valor") not in (None, "") else cb.valor
    if valor <= 0:
        erro(400, "Informe o valor recebido.")
    meio = _txt(body.get("meio"), 20)
    if meio and meio not in MEIOS:
        erro(400, "Meio de pagamento inválido.")
    cb.pago_em, cb.valor_pago, cb.meio_pago, cb.obs = data, valor, meio, _txt(body.get("obs"), 300)
    auditar(db, "mensalidade_paga", usuario=u, haras_id=h.id, alvo=f"{h.nome} · {cb.descricao}", detalhe={"valor": valor, "data": R.iso(data)}, request=request)
    db.commit()
    return {"resumo": f"Pagamento de {brl(valor)} registrado para {h.nome}."}


@r.post("/api/financeiro/cobrancas/{cid}/estornar")
def estornar(cid: str, request: Request, u: Usuario = Depends(financeiro), db=Depends(get_db)):
    cb, h = _cobranca(db, cid)
    if not cb.pago_em:
        erro(400, "Esta cobrança não está paga.")
    det = {"valor": cb.valor_pago, "data": R.iso(cb.pago_em)}
    cb.pago_em = cb.valor_pago = None
    cb.meio_pago, cb.obs = "", ""
    auditar(db, "mensalidade_estornada", usuario=u, haras_id=h.id, alvo=f"{h.nome} · {cb.descricao}", detalhe=det, request=request)
    db.commit()
    return {"resumo": "Pagamento estornado. A cobrança voltou a ficar em aberto."}


@r.post("/api/financeiro/cobrancas/{cid}/cancelar")
def cancelar(cid: str, request: Request, body: dict = Body(...), u: Usuario = Depends(financeiro), db=Depends(get_db)):
    cb, h = _cobranca(db, cid)
    if cb.pago_em:
        erro(400, "Estorne o pagamento antes de cancelar.")
    if cb.cancelada_em:
        erro(400, "Esta cobrança já está cancelada.")
    motivo = _txt(body.get("motivo"), 300)
    if not motivo:
        erro(400, "Informe o motivo do cancelamento.")
    cb.cancelada_em, cb.motivo_cancelamento = R.hoje(), motivo
    auditar(db, "cobranca_cancelada", usuario=u, haras_id=h.id, alvo=f"{h.nome} · {cb.descricao}", detalhe={"motivo": motivo}, request=request)
    db.commit()
    return {"resumo": "Cobrança cancelada."}


@r.post("/api/financeiro/cobrancas/{cid}/recalcular")
def recalcular(cid: str, request: Request, u: Usuario = Depends(financeiro), db=Depends(get_db)):
    cb, h = _cobranca(db, cid)
    if not cb.competencia:
        erro(400, "Cobrança avulsa não é recalculada.")
    if cb.pago_em or cb.cancelada_em or cb.vencimento < R.hoje():
        erro(400, "Só dá para recalcular uma mensalidade em aberto, antes do vencimento.")
    c = db.get(Cliente, h.id)
    calc = calcular(db, c, ativos_por_haras(db).get(h.id, 0), cb.vencimento)
    if calc["valor"] is None:
        erro(400, "Há faixa de preço sem valor definido para este número de animais.")
    antes = cb.valor
    cb.valor, cb.calculo = calc["valor"], calc
    auditar(db, "mensalidade_recalculada", usuario=u, haras_id=h.id, alvo=f"{h.nome} · {cb.descricao}", detalhe={"antes": antes, "depois": cb.valor}, request=request)
    db.commit()
    return {"resumo": f"Mensalidade recalculada: {brl(antes)} para {brl(cb.valor)}."}


@r.put("/api/financeiro/parametros")
def salvar_parametros(request: Request, body: dict = Body(...), u: Usuario = Depends(usuario_atual), db=Depends(get_db)):
    if u.perfil != "admin":
        erro(403, "Apenas o administrador altera as configurações do financeiro.")
    pf = params(db)
    for k, (lo, hi) in {"testeDias": (0, 180), "antecedenciaDias": (1, 25), "bloqueioDias": (1, 120), "diaPadrao": (1, 28)}.items():
        if k in body:
            try:
                v = int(body[k])
            except (TypeError, ValueError):
                v = lo - 1
            if not lo <= v <= hi:
                erro(400, f"{k} deve ficar entre {lo} e {hi}.")
            pf[k] = v
    for k, n in (("pixChave", 77), ("pixNome", 25), ("pixCidade", 15), ("dadosBancarios", 600)):
        if k in body:
            pf[k] = str(body[k] or "").strip()[:n]
    P.gravar(db, "financeiro", pf)
    auditar(db, "parametros_financeiro", usuario=u, detalhe={k: v for k, v in pf.items() if k != "dadosBancarios"}, request=request)
    db.commit()
    return {"resumo": "Configurações do financeiro salvas."}


def _relatorio(db, tipo):
    d = painel_dados(db)
    ind = d["indicadores"]
    kpis = [{"rotulo": "Clientes ativos", "valor": ind["clientes"]["Ativo"]}, {"rotulo": "Receita recorrente mensal", "valor": brl(ind["mrr"])},
            {"rotulo": "A receber", "valor": brl(ind["aReceber"])}, {"rotulo": "Em atraso", "valor": brl(ind["emAtraso"])}]
    reais = lambda c: round((c or 0) / 100, 2)  # noqa: E731
    if tipo == "clientes":
        tab = {"nome": "Clientes", "colunas": ["Haras", "Situação", "Contratante", "CPF ou CNPJ", "Contato", "E-mail", "Telefone", "Cidade/UF", "Início",
                                                "Vencimento (dia)", "Animais", "Próxima mensalidade (R$)", "A receber (R$)", "Em atraso (R$)"],
               "linhas": [[c["haras"], c["situacao"], c["nome"], c["documento"] or "-", c["contatoNome"], c["contatoEmail"], c["contatoTelefone"],
                           "/".join(x for x in (c["endereco"].get("cidade"), c["endereco"].get("uf")) if x) or "-", R.br(c["inicio"]) if c["inicio"] else "-",
                           c["diaVencimento"], c["animais"], reais(c["proxima"]["valor"]) if c["proxima"]["valor"] is not None else "A definir",
                           reais(c["aReceber"]), reais(c["emAtraso"])] for c in d["clientes"]]}
    elif tipo == "cobrancas":
        tab = {"nome": "Cobranças", "colunas": ["Vencimento", "Haras", "Descrição", "Animais", "Valor (R$)", "Situação", "Pago em", "Valor pago (R$)", "Meio"],
               "linhas": [[R.br(x["vencimento"]), x["haras"], x["descricao"], (x["calculo"] or {}).get("animais", "-"), reais(x["valor"]), x["situacao"],
                           R.br(x["pagoEm"]) if x["pagoEm"] else "-", reais(x["valorPago"]) if x["valorPago"] else "-", x["meio"] or "-"] for x in d["cobrancas"]]}
    elif tipo == "recebimentos":
        pagas = sorted([x for x in d["cobrancas"] if x["pagoEm"]], key=lambda x: x["pagoEm"], reverse=True)
        tab = {"nome": "Recebimentos", "colunas": ["Pago em", "Haras", "Descrição", "Valor pago (R$)", "Meio", "Observação"],
               "linhas": [[R.br(x["pagoEm"]), x["haras"], x["descricao"], reais(x["valorPago"]), x["meio"] or "-", x["obs"]] for x in pagas]}
    else:
        erro(404, "Relatório não encontrado.")
    hoje = R.iso(R.hoje())
    return {"tipo": tipo, "titulo": f"Financeiro · {tab['nome']}", "haras": "Haras360", "periodo": {"de": hoje, "ate": hoje}, "filtros": {},
            "geradoEm": hoje, "indicadores": kpis, "graficos": [], "tabelas": [dict(tab, links=[None] * len(tab["linhas"]))]}


@r.get("/api/financeiro/exportar")
def exportar(request: Request, tipo: str = "cobrancas", formato: str = "xlsx", u: Usuario = Depends(financeiro), db=Depends(get_db)):
    from .relatorios import para_csv, para_xlsx
    rel = _relatorio(db, tipo)
    auditar(db, "financeiro_exportado", usuario=u, detalhe={"tipo": tipo, "formato": formato}, request=request)
    db.commit()
    nome = f"haras360-financeiro-{tipo}-{rel['geradoEm']}"
    if formato == "csv":
        return Response(para_csv(rel), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{nome}.csv"'})
    if formato != "xlsx":
        erro(400, "Formato inválido.")
    return Response(para_xlsx(rel), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{nome}.xlsx"'})


# ---------------- assinatura do haras (gestor) ----------------
@r.get("/api/assinatura")
def assinatura(u: Usuario = Depends(gestor), db=Depends(get_db)):
    garantir_clientes(db)
    db.commit()
    h = db.get(Haras, u.haras_id)
    c = db.get(Cliente, h.id)
    n = ativos_por_haras(db).get(h.id, 0)
    hoje = R.hoje()
    venc = _vencimento(hoje.year, hoje.month, c.dia_vencimento)
    if venc < hoje:
        venc = _vencimento(hoje.year + hoje.month // 12, hoje.month % 12 + 1, c.dia_vencimento)
    cobs = list(db.scalars(select(Cobranca).where(Cobranca.haras_id == h.id).order_by(Cobranca.vencimento.desc())))
    abertas = [x for x in cobs if not x.pago_em and not x.cancelada_em]
    return {"haras": h.nome, "plano": P.plano_do_haras(db, h)["nome"], "situacao": c.situacao, "testeAte": R.iso(c.teste_ate) if c.teste_ate else None,
            "diaVencimento": c.dia_vencimento, "animais": n, "proxima": dict(calcular(db, c, n, venc), vencimento=R.iso(venc)),
            "cobrancas": [dict(cobranca_out(x), pagamento=como_pagar(db, x) if x in abertas else None) for x in cobs],
            "comoPagar": como_pagar(db), "bloqueio": bloqueio(db, h.id), "contato": P.ler(db, "email_contato")}
