"""Certificado de registro da ABCCMM (v1.6.0): prévia, gravação (novo, atualizar ou anexar) e download do PDF."""
import json
import re
import unicodedata
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select

from . import certificado as C
from . import regras as R
from .config import COMPARTILHADO
from .db import Animal, Usuario
from .rotas_haras import _ativos, _limite, nid
from .seguranca import auditar, erro, gestor, get_db

r = APIRouter()
CERT_DIR = COMPARTILHADO / "certificados"
MAX_ARQUIVOS = 30
MAX_MB = 3
BASE = ("nome", "registro", "livro", "sexo", "nascimento", "dna", "chip", "pelagem")
ROTULOS = {"nome": "Nome", "registro": "Registro", "livro": "Livro", "sexo": "Sexo", "nascimento": "Nascimento", "dna": "DNA",
           "chip": "Microchip", "pelagem": "Pelagem", "pai": "Pai", "mae": "Mãe"}


def _norm(s):
    s = unicodedata.normalize("NFD", (s or "").upper())
    return re.sub(r"\s+", " ", "".join(c for c in s if unicodedata.category(c) != "Mn")).strip()


def _extras(d):
    return {k: d[k] for k in ("volume", "pagina", "classificacao", "dataResenha", "dataRegistro", "criador", "proprietario", "mensuracoes", "serie")}


def _valor(a: Animal, k):
    if k == "nascimento":
        return R.iso(a.nascimento) if a.nascimento else ""
    if k in ("pai", "mae"):
        return (a.genealogia or {}).get(k, "")
    return getattr(a, k) or ""


def _diferencas(a: Animal, d):
    out = []
    for k in BASE + ("pai", "mae"):
        novo = d["genealogia"][k] if k in ("pai", "mae") else d[k]
        antes = _valor(a, k)
        if novo and str(novo) != str(antes):
            out.append({"campo": ROTULOS[k], "antes": antes, "depois": novo})
    if not (a.genealogia or {}).get("arvore"):
        out.append({"campo": "Genealogia", "antes": "até avós", "depois": f"{len(d['genealogia']['arvore'])} ancestrais (4 gerações)"})
    if not a.certificado:
        out.append({"campo": "Certificado", "antes": "", "depois": "PDF, mensurações, criador e proprietário"})
    return out


def _achar(animais, d):
    """Animal do haras que corresponde ao certificado: registro, chip ou nome."""
    reg, chip, nome = d["registro"], d["chip"], _norm(d["nome"])
    return (next((a for a in animais if reg and a.registro == reg), None) or next((a for a in animais if chip and a.chip == chip), None)
            or next((a for a in animais if _norm(a.nome) == nome), None))


async def _ler_arquivos(arquivos):
    if not arquivos:
        erro(400, "Envie ao menos um certificado em PDF.")
    if len(arquivos) > MAX_ARQUIVOS:
        erro(400, f"Envie até {MAX_ARQUIVOS} certificados por vez.")
    out = []
    for f in arquivos:
        dados = await f.read(MAX_MB * 1024 * 1024 + 1)
        if len(dados) > MAX_MB * 1024 * 1024:
            out.append((f.filename, None, None, f"O arquivo passa de {MAX_MB} MB."))
            continue
        try:
            out.append((f.filename, dados, C.ler(dados), None))
        except C.CertificadoInvalido as e:
            out.append((f.filename, None, None, str(e)))
    return out


@r.post("/api/certificados/previa")
async def previa(arquivos: List[UploadFile] = File(...), animalId: str = Form(""), u: Usuario = Depends(gestor), db=Depends(get_db)):
    animais = list(db.scalars(select(Animal).where(Animal.haras_id == u.haras_id)))
    alvo = next((a for a in animais if a.id == animalId), None) if animalId else None
    if animalId and not alvo:
        erro(404, "Animal não encontrado.")
    res = []
    for nome, _bytes, d, falha in await _ler_arquivos(arquivos):
        if falha:
            res.append({"arquivo": nome, "ok": False, "erro": falha})
            continue
        avisos = []
        a = alvo or _achar(animais, d)
        if alvo:
            dono = next((x for x in animais if d["registro"] and x.registro == d["registro"] and x.id != alvo.id), None)
            if dono:
                avisos.append(f"O registro {d['registro']} já pertence a {dono.nome}.")
            if _norm(d["nome"]) != _norm(alvo.nome):
                avisos.append(f"O nome no certificado ({d['nome']}) é diferente do cadastro ({alvo.nome}).")
        if not d["nascimento"]:
            avisos.append("O certificado não traz a data de nascimento.")
        dif = _diferencas(a, d) if a else []
        situacao = "novo" if not a else ("igual" if not dif else "atualizar")
        res.append({"arquivo": nome, "ok": True, "dados": d, "situacao": situacao, "animalId": a.id if a else None,
                    "animal": a.nome if a else None, "externo": bool(a.externo) if a else False, "diferencas": dif, "avisos": avisos})
    return {"certificados": res}


def _aplicar(a: Animal, d, base: bool):
    if base:
        a.nome, a.registro, a.livro, a.sexo = d["nome"], d["registro"], d["livro"] or a.livro, d["sexo"] or a.sexo
        if d["nascimento"]:
            a.nascimento = R.d(d["nascimento"])
        a.dna, a.chip = d["dna"] or a.dna, d["chip"] or a.chip
    if d["pelagem"]:
        a.pelagem = d["pelagem"]
    a.genealogia = {**(a.genealogia or {}), **d["genealogia"]}
    a.certificado = {**_extras(d), "pdf": True, "enviadoEm": R.iso(R.hoje())}


@r.post("/api/certificados/gravar")
async def gravar(request: Request, arquivos: List[UploadFile] = File(...), acoes: str = Form(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    """acoes: JSON com uma ação por arquivo, na mesma ordem: {"acao": criar|atualizar|anexar|ignorar, "animalId", "externo"}."""
    try:
        lst = json.loads(acoes)
        assert isinstance(lst, list) and len(lst) == len(arquivos)
    except (ValueError, AssertionError):
        erro(400, "Ações inválidas para os certificados enviados.")
    lidos = await _ler_arquivos(arquivos)
    feitos, falhas, ids = [], [], []
    limite = _limite(db, u.haras_id)
    for (nome, dados, d, falha), ac in zip(lidos, lst):
        acao = (ac or {}).get("acao", "ignorar")
        if acao == "ignorar":
            ids.append(None)
            continue
        if falha:
            falhas.append(f"{nome}: {falha}")
            ids.append(None)
            continue
        alvo_id = str(ac.get("animalId") or "") if acao != "criar" else ""
        if d["registro"]:
            dono = db.scalar(select(Animal).where(Animal.haras_id == u.haras_id, Animal.registro == d["registro"], Animal.id != alvo_id))
            if dono:
                falhas.append(f"{nome}: o registro {d['registro']} já pertence a {dono.nome}.")
                ids.append(None)
                continue
        if acao == "criar":
            externo = bool(ac.get("externo"))
            if not d["sexo"] or (not d["nascimento"] and not externo):
                falhas.append(f"{nome}: faltam sexo ou nascimento no certificado.")
                ids.append(None)
                continue
            if not externo and len(_ativos(db, u.haras_id)) >= limite:
                falhas.append(f"{nome}: o plano deste haras atende até {limite} animais ativos.")
                ids.append(None)
                continue
            a = Animal(id="a" + nid(), haras_id=u.haras_id, origem="Externo" if externo else "Certificado ABCCMM", externo=externo,
                       vivo=not externo, bloqueado=False, contato={} if externo else None)
            db.add(a)
            base = True
        elif acao in ("atualizar", "anexar"):
            a = db.get(Animal, str(ac.get("animalId") or ""))
            if not a or a.haras_id != u.haras_id:
                falhas.append(f"{nome}: animal não encontrado.")
                ids.append(None)
                continue
            base = acao == "atualizar"
        else:
            erro(400, "Ação inválida.")
        _aplicar(a, d, base)
        db.flush()
        pasta = CERT_DIR / str(u.haras_id)
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / f"{a.id}.pdf").write_bytes(dados)
        auditar(db, "certificado_importado", usuario=u, alvo=a.nome, detalhe={"acao": acao, "registro": d["registro"], "arquivo": nome}, request=request)
        feitos.append(a.nome)
        ids.append(a.id)
    db.commit()
    resumo = f"{len(feitos)} certificado(s) gravado(s)." + (f" Não gravados: {'; '.join(falhas)}" if falhas else "")
    return {"resumo": resumo, "gravados": feitos, "falhas": falhas, "ids": ids}


@r.get("/api/animais/{aid}/certificado.pdf")
def baixar(aid: str, u: Usuario = Depends(gestor), db=Depends(get_db)):
    a = db.get(Animal, aid)
    if not a or a.haras_id != u.haras_id:
        erro(404, "Animal não encontrado.")
    f = CERT_DIR / str(u.haras_id) / f"{a.id}.pdf"
    if not f.exists():
        erro(404, "Este animal não tem certificado guardado.")
    nome = re.sub(r"[^A-Za-z0-9]+", "-", _norm(a.nome)).strip("-").lower()
    return FileResponse(f, media_type="application/pdf", filename=f"certificado-{nome}.pdf", headers={"Cache-Control": "no-store"})
