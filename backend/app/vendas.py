"""Venda de animais (v1.6.0): compradores, venda à vista ou parcelada, recebimento das parcelas,
avisos de vencimento e a pendência de transferência na ABCCMM. Só o gestor vê valores.

Valores em centavos. CPF ou CNPJ do comprador ficam cifrados (Fernet, chave derivada da SECRET_KEY)
e são mostrados mascarados; ver o número completo fica registrado na auditoria.
"""
import base64
import hashlib
import re
from datetime import date

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy import select

from . import regras as R
from .config import SECRET_KEY
from .db import Animal, Comprador, Parcela, Usuario, Venda
from .seguranca import auditar, erro, gestor, get_db

r = APIRouter()
MEIOS = ("Pix", "Transferência", "Boleto", "Cheque", "Dinheiro", "Cartão")
_F = Fernet(base64.urlsafe_b64encode(hashlib.sha256(("haras360-documentos:" + SECRET_KEY).encode()).digest()))


def nid():
    import uuid
    return uuid.uuid4().hex[:20]


# ---------------- CPF e CNPJ ----------------
def _dv(nums, pesos):
    s = sum(int(n) * p for n, p in zip(nums, pesos)) % 11
    return "0" if s < 2 else str(11 - s)


def documento_valido(doc: str):
    d = re.sub(r"\D", "", doc or "")
    if len(d) == 11 and len(set(d)) > 1:
        return d[9] == _dv(d[:9], range(10, 1, -1)) and d[10] == _dv(d[:10], range(11, 1, -1)), "cpf"
    if len(d) == 14 and len(set(d)) > 1:
        p1, p2 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        return d[12] == _dv(d[:12], p1) and d[13] == _dv(d[:13], p2), "cnpj"
    return False, ""


def mascara(doc: str):
    d = re.sub(r"\D", "", doc or "")
    if len(d) == 11:
        return f"***.{d[3:6]}.{d[6:9]}-**"
    if len(d) == 14:
        return f"**.{d[2:5]}.{d[5:8]}/{d[8:12]}-**"
    return ""


def formatar(doc: str):
    d = re.sub(r"\D", "", doc or "")
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return d


def cifrar(doc):
    return _F.encrypt(re.sub(r"\D", "", doc).encode()).decode()


def decifrar(tok):
    try:
        return _F.decrypt(tok.encode()).decode()
    except (InvalidToken, AttributeError, ValueError):
        return ""


# ---------------- apoio ----------------
def _txt(v, n):
    return re.sub(r"[\x00-\x1f]", "", str(v or "")).strip()[:n]


def centavos(v):
    if v in (None, ""):
        return 0
    if isinstance(v, str):
        v = v.replace("R$", "").strip()
        if "," in v:
            v = v.replace(".", "").replace(",", ".")
    try:
        c = round(float(v) * 100)
    except ValueError:
        erro(400, "Valor inválido.")
    if c < 0:
        erro(400, "O valor não pode ser negativo.")
    return c


def _data(v, rot):
    try:
        return R.d(str(v))
    except (TypeError, ValueError):
        erro(400, f"Informe {rot} no formato AAAA-MM-DD.")


def add_meses(d0: date, n: int):
    m = d0.month - 1 + n
    y, m = d0.year + m // 12, m % 12 + 1
    dias = [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d0.day, dias))


def gerar_parcelas(total, entrada, n, primeiro: date):
    """Entrada (número 0) e n parcelas mensais iguais; os centavos que sobram vão para a última."""
    if entrada > total:
        erro(400, "A entrada não pode passar do valor total.")
    resto = total - entrada
    base = resto // n
    out = [(0, None, entrada)] if entrada else []
    for i in range(n):
        out.append((i + 1, add_meses(primeiro, i), base + (resto - base * n if i == n - 1 else 0)))
    return out


def comprador_out(c: Comprador, vendas=0):
    return {"id": c.id, "nome": c.nome, "documento": c.documento_mascara, "cadastroAbccmm": c.cadastro_abccmm, "telefone": c.telefone,
            "email": c.email, "cidade": c.cidade, "uf": c.uf, "vendas": vendas}


def situacao(p: Parcela, hoje=None):
    if p.pago_em:
        return "paga"
    h = hoje or R.hoje()
    if p.vencimento < h:
        return "atrasada"
    return "vence" if (p.vencimento - h).days <= 7 else "aberta"


def venda_out(v: Venda, a: Animal, c: Comprador, ps):
    pago = sum(p.valor_pago or 0 for p in ps if p.pago_em)
    return {"id": v.id, "data": R.iso(v.data), "animalId": v.animal_id, "animal": a.nome if a else "", "compradorId": v.comprador_id,
            "comprador": c.nome if c else "", "total": v.valor_total, "recebido": pago, "saldo": v.valor_total - pago, "forma": v.forma, "meio": v.meio,
            "transferenciaEm": R.iso(v.transferencia_em) if v.transferencia_em else None, "obs": v.obs or "",
            "parcelas": [{"id": p.id, "numero": p.numero, "vencimento": R.iso(p.vencimento), "valor": p.valor, "pagoEm": R.iso(p.pago_em) if p.pago_em else None,
                          "valorPago": p.valor_pago, "meio": p.meio_pago or "", "obs": p.obs or "", "situacao": situacao(p)} for p in ps]}


def vendas_do_haras(db, haras_id):
    vs = list(db.scalars(select(Venda).where(Venda.haras_id == haras_id).order_by(Venda.data.desc())))
    if not vs:
        return []
    ids = [v.id for v in vs]
    pmap = {}
    for p in db.scalars(select(Parcela).where(Parcela.venda_id.in_(ids)).order_by(Parcela.numero)):
        pmap.setdefault(p.venda_id, []).append(p)
    amap = {a.id: a for a in db.scalars(select(Animal).where(Animal.id.in_({v.animal_id for v in vs})))}
    cmap = {c.id: c for c in db.scalars(select(Comprador).where(Comprador.id.in_({v.comprador_id for v in vs})))}
    return [venda_out(v, amap.get(v.animal_id), cmap.get(v.comprador_id), pmap.get(v.id, [])) for v in vs]


def brl(c):
    s = f"{c / 100:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def notificacoes_vendas(vendas):
    """Avisos de parcelas (vencendo em 7 dias e vencidas) e da transferência na ABCCMM pendente."""
    n = []
    for v in vendas:
        for p in v["parcelas"]:
            nome = "Entrada" if p["numero"] == 0 else f"Parcela {p['numero']}/{sum(1 for x in v['parcelas'] if x['numero'] > 0)}"
            if p["situacao"] == "atrasada":
                n.append({"id": f"n:parcela:{p['id']}:atrasada", "tipo": "financeiro", "sev": "critico", "titulo": f"Parcela vencida · {v['animal']}",
                          "texto": f"{nome} de {v['comprador']}, {brl(p['valor'])}, venceu em {R.br(p['vencimento'])}.", "animalId": v["animalId"], "vendaId": v["id"]})
            elif p["situacao"] == "vence":
                n.append({"id": f"n:parcela:{p['id']}:vence", "tipo": "financeiro", "sev": "alerta", "titulo": f"Parcela a vencer · {v['animal']}",
                          "texto": f"{nome} de {v['comprador']}, {brl(p['valor'])}, vence em {R.br(p['vencimento'])} ({R.relativo(p['vencimento'])}).",
                          "animalId": v["animalId"], "vendaId": v["id"]})
        if not v["transferenciaEm"]:
            n.append({"id": f"n:transferencia:{v['id']}", "tipo": "documental", "sev": "alerta", "titulo": f"Comunicar a transferência na ABCCMM · {v['animal']}",
                      "texto": f"Venda para {v['comprador']} em {R.br(v['data'])}. Marque como feita em Vendas depois de comunicar a ABCCMM.",
                      "animalId": v["animalId"], "vendaId": v["id"]})
    return n


# ---------------- compradores ----------------
def _aplicar_comprador(c: Comprador, b: dict):
    c.nome = _txt(b.get("nome"), 160).upper()
    if not c.nome:
        erro(400, "Informe o nome do comprador.")
    doc = _txt(b.get("documento"), 30)
    if doc and "*" not in doc:  # "*" = máscara: o documento não mudou
        ok, _tipo = documento_valido(doc)
        if not ok:
            erro(400, "CPF ou CNPJ inválido. Confira os números.")
        c.documento, c.documento_mascara = cifrar(doc), mascara(doc)
    elif not doc:
        c.documento, c.documento_mascara = None, ""
    c.cadastro_abccmm = _txt(b.get("cadastroAbccmm"), 20)
    c.telefone = _txt(b.get("telefone"), 40)
    email = _txt(b.get("email"), 160)
    if email and "@" not in email:
        erro(400, "E-mail do comprador inválido.")
    c.email = email
    c.cidade = _txt(b.get("cidade"), 80)
    uf = _txt(b.get("uf"), 2).upper()
    if uf and not re.match(r"^[A-Z]{2}$", uf):
        erro(400, "UF inválida.")
    c.uf = uf


def _comprador(db, cid, u):
    c = db.get(Comprador, cid)
    if not c or c.haras_id != u.haras_id:
        erro(404, "Comprador não encontrado.")
    return c


@r.get("/api/compradores")
def listar_compradores(u: Usuario = Depends(gestor), db=Depends(get_db)):
    cont = {}
    for v in db.scalars(select(Venda).where(Venda.haras_id == u.haras_id)):
        cont[v.comprador_id] = cont.get(v.comprador_id, 0) + 1
    return [comprador_out(c, cont.get(c.id, 0)) for c in db.scalars(select(Comprador).where(Comprador.haras_id == u.haras_id).order_by(Comprador.nome))]


@r.post("/api/compradores")
def criar_comprador(request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    c = Comprador(id="c" + nid(), haras_id=u.haras_id)
    _aplicar_comprador(c, body)
    db.add(c)
    auditar(db, "comprador_criado", usuario=u, alvo=c.nome, request=request)
    db.commit()
    return {"id": c.id, "resumo": f"Comprador {c.nome} cadastrado."}


@r.put("/api/compradores/{cid}")
def editar_comprador(cid: str, request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    c = _comprador(db, cid, u)
    _aplicar_comprador(c, body)
    auditar(db, "comprador_editado", usuario=u, alvo=c.nome, request=request)
    db.commit()
    return {"id": c.id, "resumo": f"Dados de {c.nome} salvos."}


@r.delete("/api/compradores/{cid}")
def excluir_comprador(cid: str, request: Request, u: Usuario = Depends(gestor), db=Depends(get_db)):
    c = _comprador(db, cid, u)
    if db.scalar(select(Venda).where(Venda.comprador_id == c.id)):
        erro(400, "Este comprador tem vendas registradas e não pode ser excluído.")
    auditar(db, "comprador_excluido", usuario=u, alvo=c.nome, request=request)
    db.delete(c)
    db.commit()
    return {"resumo": f"Comprador {c.nome} excluído."}


@r.post("/api/compradores/{cid}/documento")
def ver_documento(cid: str, request: Request, u: Usuario = Depends(gestor), db=Depends(get_db)):
    c = _comprador(db, cid, u)
    if not c.documento:
        erro(404, "Este comprador não tem CPF ou CNPJ cadastrado.")
    auditar(db, "documento_visto", usuario=u, alvo=c.nome, request=request)
    db.commit()
    return {"documento": formatar(decifrar(c.documento))}


# ---------------- vendas ----------------
@r.get("/api/vendas")
def listar_vendas(u: Usuario = Depends(gestor), db=Depends(get_db)):
    return vendas_do_haras(db, u.haras_id)


@r.post("/api/vendas")
def criar_venda(request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    """Venda = baixa por venda + comprador + parcelas."""
    a = db.get(Animal, _txt(body.get("animalId"), 16))
    if not a or a.haras_id != u.haras_id or a.externo:
        erro(404, "Animal não encontrado.")
    if a.baixa_data:
        erro(400, f"{a.nome} já está baixado desde {R.br(a.baixa_data)}.")
    data = _data(body.get("data"), "a data da venda")
    if data > R.hoje():
        erro(400, "A data da venda não pode ser futura.")
    if body.get("compradorId"):
        c = _comprador(db, str(body["compradorId"]), u)
    else:
        c = Comprador(id="c" + nid(), haras_id=u.haras_id)
        _aplicar_comprador(c, body.get("comprador") or {})
        db.add(c)
    total = centavos(body.get("valor"))
    if total <= 0:
        erro(400, "Informe o valor da venda.")
    forma = body.get("forma")
    meio = _txt(body.get("meio"), 20)
    if meio and meio not in MEIOS:
        erro(400, "Meio de pagamento inválido.")
    if forma == "avista":
        pago = body.get("pago", True)
        ps = [(1, data, total)]
    elif forma == "parcelado":
        if body.get("parcelas"):  # parcelas editadas na tela
            ps = []
            for i, p in enumerate(body["parcelas"]):
                ps.append((int(p.get("numero", i + 1)), _data(p.get("vencimento"), "o vencimento da parcela"), centavos(p.get("valor"))))
            if sum(v for _, _, v in ps) != total:
                erro(400, f"A soma das parcelas ({brl(sum(v for _, _, v in ps))}) precisa ser igual ao valor total ({brl(total)}).")
            if any(v <= 0 for n, _, v in ps if n > 0):
                erro(400, "Toda parcela precisa ter valor.")
        else:
            n = int(body.get("nParcelas") or 0)
            if not 2 <= n <= 60:
                erro(400, "Parcelado: informe de 2 a 60 parcelas.")
            ps = gerar_parcelas(total, centavos(body.get("entrada")), n, _data(body.get("primeiroVencimento"), "o primeiro vencimento"))
            ps = [(nm, venc or data, v) for nm, venc, v in ps]
        pago = False
    else:
        erro(400, "Escolha à vista ou parcelado.")
    v = Venda(id="v" + nid(), haras_id=u.haras_id, animal_id=a.id, comprador_id=c.id, data=data, valor_total=total, forma=forma, meio=meio,
              obs=_txt(body.get("obs"), 1000))
    db.add(v)
    for numero, venc, valor in ps:
        p = Parcela(id="p" + nid(), venda_id=v.id, numero=numero, vencimento=venc, valor=valor)
        if forma == "avista" and pago:
            p.pago_em, p.valor_pago, p.meio_pago = data, valor, meio
        if forma == "parcelado" and numero == 0 and body.get("entradaPaga", True):  # entrada recebida no ato
            p.pago_em, p.valor_pago, p.meio_pago = data, valor, meio
        db.add(p)
    a.baixa_data, a.baixa_motivo, a.baixa_destino, a.baixa_obs = data, "Venda", c.nome, _txt(body.get("obs"), 2000)
    a.vivo = False
    auditar(db, "venda_registrada", usuario=u, alvo=a.nome, detalhe={"comprador": c.nome, "total": total, "forma": forma, "parcelas": len(ps)}, request=request)
    db.commit()
    return {"id": v.id, "resumo": f"Venda de {a.nome} para {c.nome} registrada ({brl(total)}, {'à vista' if forma == 'avista' else f'{len(ps)} pagamento(s)'})."}


def _parcela(db, pid, u):
    p = db.get(Parcela, pid)
    v = db.get(Venda, p.venda_id) if p else None
    if not p or not v or v.haras_id != u.haras_id:
        erro(404, "Parcela não encontrada.")
    return p, v


@r.post("/api/parcelas/{pid}/pagar")
def pagar(pid: str, request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    p, v = _parcela(db, pid, u)
    if p.pago_em:
        erro(400, "Esta parcela já está paga.")
    data = _data(body.get("data"), "a data do pagamento")
    if data > R.hoje():
        erro(400, "A data do pagamento não pode ser futura.")
    valor = centavos(body.get("valor")) if body.get("valor") not in (None, "") else p.valor
    if valor <= 0:
        erro(400, "Informe o valor recebido.")
    meio = _txt(body.get("meio"), 20)
    if meio and meio not in MEIOS:
        erro(400, "Meio de pagamento inválido.")
    p.pago_em, p.valor_pago, p.meio_pago, p.obs = data, valor, meio, _txt(body.get("obs"), 300)
    a = db.get(Animal, v.animal_id)
    auditar(db, "parcela_paga", usuario=u, alvo=f"{a.nome if a else ''} · parcela {p.numero}", detalhe={"valor": valor, "data": R.iso(data)}, request=request)
    db.commit()
    return {"resumo": f"Pagamento de {brl(valor)} registrado."}


@r.post("/api/parcelas/{pid}/estornar")
def estornar(pid: str, request: Request, u: Usuario = Depends(gestor), db=Depends(get_db)):
    p, v = _parcela(db, pid, u)
    if not p.pago_em:
        erro(400, "Esta parcela não está paga.")
    detalhe = {"valor": p.valor_pago, "data": R.iso(p.pago_em)}
    p.pago_em = p.valor_pago = None
    p.meio_pago, p.obs = "", ""
    a = db.get(Animal, v.animal_id)
    auditar(db, "parcela_estornada", usuario=u, alvo=f"{a.nome if a else ''} · parcela {p.numero}", detalhe=detalhe, request=request)
    db.commit()
    return {"resumo": "Pagamento estornado. A parcela voltou a ficar em aberto."}


@r.post("/api/vendas/{vid}/transferencia")
def transferencia(vid: str, request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    v = db.get(Venda, vid)
    if not v or v.haras_id != u.haras_id:
        erro(404, "Venda não encontrada.")
    if body.get("feita", True):
        data = _data(body.get("data") or R.iso(R.hoje()), "a data da comunicação")
        v.transferencia_em = data
        msg = f"Transferência marcada como comunicada em {R.br(data)}."
    else:
        v.transferencia_em = None
        msg = "Transferência voltou para pendente."
    a = db.get(Animal, v.animal_id)
    auditar(db, "transferencia_abccmm", usuario=u, alvo=a.nome if a else "", detalhe={"feita": bool(v.transferencia_em)}, request=request)
    db.commit()
    return {"resumo": msg}


def venda_do_animal(db, animal_id):
    return db.scalar(select(Venda).where(Venda.animal_id == animal_id))


def apagar_venda_sem_pagamento(db, animal_id):
    """Desfazer a baixa de um animal vendido: só sem parcela paga (a entrada à vista conta como paga)."""
    v = venda_do_animal(db, animal_id)
    if not v:
        return
    ps = list(db.scalars(select(Parcela).where(Parcela.venda_id == v.id)))
    if any(p.pago_em for p in ps):
        erro(400, "Esta venda tem pagamento registrado. Estorne os pagamentos em Vendas antes de desfazer a baixa.")
    for p in ps:
        db.delete(p)
    db.delete(v)
