"""API e servidor web do Haras360."""
import base64
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import bcrypt
from fastapi import Body, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select

from . import regras as R
from .db import (COOKIE_SECURE, FOTOS_DIR, LIMITE_ANIMAIS, SECRET_KEY, Animal, Foto, Haras, Importacao, NotifLida, Protocolo, Registro,
                 SessionLocal, Usuario, iniciar_banco)

VERSAO = "1.0.0"
STATIC = Path(__file__).parent / "static"
COOKIE = "h360"
SESSAO_DIAS = 7
ser = URLSafeTimedSerializer(SECRET_KEY, salt="haras360-sessao")


@asynccontextmanager
async def ciclo(_app):
    iniciar_banco()
    Path(FOTOS_DIR).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Haras360", version=VERSAO, docs_url=None, redoc_url=None, openapi_url=None, lifespan=ciclo)


# ---------------- utilidades ----------------
def nid():
    return uuid.uuid4().hex[:10]


def hash_senha(s):
    return bcrypt.hashpw(s.encode(), bcrypt.gensalt()).decode()


def confere_senha(s, h):
    try:
        return bcrypt.checkpw(s.encode(), h.encode())
    except ValueError:
        return False


def erro(status, msg):
    raise HTTPException(status_code=status, detail=msg)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _iso(v):
    return v.isoformat() if v else ""


def _data(v, campo, obrigatorio=True):
    if not v:
        if obrigatorio:
            erro(400, f"Informe {campo}.")
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        erro(400, f"Data inválida em {campo}.")


def _txt(v, n=200):
    return str(v or "").strip()[:n]


# ---------------- proteção de formulários e sessão ----------------
@app.middleware("http")
async def protecao(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if request.headers.get("x-haras360") != "1":
            return JSONResponse({"detail": "Requisição recusada."}, status_code=403)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


def criar_sessao(resp: Response, u: Usuario):
    token = ser.dumps({"u": u.id, "v": u.senha_hash[-10:]})
    resp.set_cookie(COOKIE, token, max_age=SESSAO_DIAS * 86400, httponly=True, samesite="lax", secure=COOKIE_SECURE, path="/")


def usuario_atual(request: Request, db=Depends(get_db)) -> Usuario:
    tok = request.cookies.get(COOKIE)
    if not tok:
        erro(401, "Faça login para continuar.")
    try:
        dados = ser.loads(tok, max_age=SESSAO_DIAS * 86400)
    except (BadSignature, SignatureExpired):
        erro(401, "Sessão expirada. Faça login novamente.")
    u = db.get(Usuario, dados.get("u"))
    if not u or not u.ativo or u.senha_hash[-10:] != dados.get("v"):
        erro(401, "Sessão encerrada. Faça login novamente.")
    return u


def gestor(u: Usuario = Depends(usuario_atual)) -> Usuario:
    if u.perfil != "gestor":
        erro(403, "Apenas o gestor pode fazer esta alteração.")
    return u


def origem_de(request: Request):
    return {"gestor": "Portal Gestor", "campo": "Portal Cliente", "app": "App"}.get(request.headers.get("x-portal", ""), "Portal Cliente")


# ---------------- login ----------------
_tentativas: dict = {}


def _limite_login(chave):
    t = time.time()
    lst = [x for x in _tentativas.get(chave, []) if t - x < 900]
    _tentativas[chave] = lst
    if len(lst) >= 8:
        erro(429, "Muitas tentativas. Aguarde 15 minutos e tente de novo.")


@app.post("/api/login")
def login(request: Request, resp: Response, body: dict = Body(...), db=Depends(get_db)):
    email = _txt(body.get("email"), 160).lower()
    senha = str(body.get("senha") or "")
    chave = (request.client.host if request.client else "?") + "|" + email
    _limite_login(chave)
    u = db.scalar(select(Usuario).where(Usuario.email == email))
    if not u or not u.ativo or not confere_senha(senha, u.senha_hash):
        _tentativas.setdefault(chave, []).append(time.time())
        erro(401, "E-mail ou senha incorretos.")
    _tentativas.pop(chave, None)
    criar_sessao(resp, u)
    return {"perfil": u.perfil, "nome": u.nome}


@app.post("/api/logout")
def logout(resp: Response):
    resp.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@app.get("/api/me")
def me(u: Usuario = Depends(usuario_atual)):
    return {"id": u.id, "nome": u.nome, "email": u.email, "perfil": u.perfil}


@app.post("/api/me/senha")
def trocar_senha(resp: Response, body: dict = Body(...), u: Usuario = Depends(usuario_atual), db=Depends(get_db)):
    if not confere_senha(str(body.get("atual") or ""), u.senha_hash):
        erro(400, "A senha atual está incorreta.")
    nova = str(body.get("nova") or "")
    if len(nova) < 8:
        erro(400, "A nova senha precisa ter pelo menos 8 caracteres.")
    u = db.get(Usuario, u.id)
    u.senha_hash = hash_senha(nova)
    db.commit()
    criar_sessao(resp, u)
    return {"ok": True}


# ---------------- leitura do estado ----------------
def animal_out(a: Animal):
    return {"id": a.id, "nome": a.nome, "livro": a.livro or "", "registro": a.registro or "", "sexo": a.sexo, "bloqueado": bool(a.bloqueado), "vivo": bool(a.vivo),
            "dna": a.dna or "", "nascimento": _iso(a.nascimento), "chip": a.chip or "", "pelagem": a.pelagem or "", "genealogia": a.genealogia or {},
            "origem": a.origem or "", "importadoEm": _iso(a.importado_em)}


def _dose_out(v):
    return int(v) if v and str(v).isdigit() else (v or "unica")


def registro_out(r: Registro, fotos):
    o = {"id": r.id, "animalId": r.animal_id, "data": _iso(r.data), "tipo": r.tipo, "protocolos": r.protocolos or [], "dose": _dose_out(r.dose), "obs": r.obs or "",
         "autor": r.autor, "origem": r.origem, "fotos": [f"/fotos/{f}" for f in fotos.get(r.id, [])]}
    o.update(r.dados or {})
    return o


def protocolos_haras(db, haras_id):
    ps = [p.dados for p in db.scalars(select(Protocolo).where(Protocolo.haras_id == haras_id))]
    if not ps:
        for p in R.protocolos_padrao():
            db.add(Protocolo(haras_id=haras_id, pid=p["id"], dados=p))
        db.commit()
        ps = R.protocolos_padrao()
    return sorted(ps, key=lambda p: p.get("ordem", 99))


def haras_out(h: Haras):
    return {"id": h.id, "nome": h.nome, "proprietario": h.proprietario or "", "municipio": h.municipio or "", "raivaSemestral": bool(h.raiva_semestral), "associadoABCCMM": h.associado_abccmm or ""}


def carregar_base(db, haras_id):
    h = db.get(Haras, haras_id)
    animais = [animal_out(a) for a in db.scalars(select(Animal).where(Animal.haras_id == haras_id).order_by(Animal.nome))]
    fmap = {}
    for f in db.scalars(select(Foto).where(Foto.haras_id == haras_id).order_by(Foto.ordem)):
        fmap.setdefault(f.registro_id, []).append(f.id)
    regs = [registro_out(r, fmap) for r in db.scalars(select(Registro).where(Registro.haras_id == haras_id).order_by(Registro.data, Registro.criado_em))]
    return h, animais, regs, protocolos_haras(db, haras_id)


@app.get("/api/estado")
def estado(u: Usuario = Depends(usuario_atual), db=Depends(get_db)):
    h, animais, regs, prots = carregar_base(db, u.haras_id)
    hd = haras_out(h)
    ts = R.tarefas(hd, animais, regs, prots)
    usuarios = []
    if u.perfil == "gestor":
        usuarios = [{"id": x.id, "nome": x.nome, "email": x.email, "perfil": x.perfil, "ativo": bool(x.ativo)} for x in db.scalars(select(Usuario).where(Usuario.haras_id == u.haras_id).order_by(Usuario.id))]
    lidas = list(db.scalars(select(NotifLida.nid).where(NotifLida.usuario_id == u.id)))
    return {
        "versao": VERSAO, "hoje": R.iso(R.hoje()), "limiteAnimais": LIMITE_ANIMAIS,
        "haras": hd, "usuario": {"id": u.id, "nome": u.nome, "email": u.email, "perfil": u.perfil},
        "usuarios": usuarios, "animais": animais, "registros": regs, "protocolos": prots,
        "notifPrefs": h.notif_prefs or R.notif_prefs_padrao(), "lidas": lidas,
        "tarefas": ts, "gestacoes": {a["id"]: R.gestacao(a, regs) for a in animais},
        "notificacoes": R.notificacoes(hd, animais, regs, prots, ts),
    }


# ---------------- animais ----------------
def _ativos(db, haras_id, excluir=None):
    q = select(Animal).where(Animal.haras_id == haras_id, Animal.vivo.is_(True))
    return [a for a in db.scalars(q) if a.id != excluir]


def _aplicar_animal(a: Animal, b: dict, db, haras_id):
    nome = _txt(b.get("nome"), 160).upper()
    if not nome:
        erro(400, "Informe o nome do animal.")
    sexo = _txt(b.get("sexo"), 1).upper()
    if sexo not in ("M", "F"):
        erro(400, "Sexo deve ser M ou F.")
    nasc = _data(b.get("nascimento"), "a data de nascimento")
    if nasc > R.hoje():
        erro(400, "A data de nascimento não pode ser futura.")
    registro = _txt(b.get("registro"), 20)
    if registro:
        dup = db.scalar(select(Animal).where(Animal.haras_id == haras_id, Animal.registro == registro, Animal.id != (a.id or "")))
        if dup:
            erro(409, f"O registro {registro} já pertence a {dup.nome}.")
    vivo = bool(b.get("vivo", True))
    if vivo and (a.vivo is not True) and len(_ativos(db, haras_id, a.id)) >= LIMITE_ANIMAIS:
        erro(400, f"O plano atende até {LIMITE_ANIMAIS} animais ativos por haras.")
    a.nome, a.sexo, a.nascimento, a.registro, a.vivo = nome, sexo, nasc, registro, vivo
    a.livro = _txt(b.get("livro"), 120)
    a.bloqueado = bool(b.get("bloqueado", False))
    a.dna = _txt(b.get("dna"), 40)
    a.chip = _txt(b.get("chip"), 30)
    a.pelagem = _txt(b.get("pelagem"), 60)
    g = b.get("genealogia") or {}
    a.genealogia = {k: _txt(g.get(k), 160).upper() for k in ("pai", "mae", "avoPaterno", "avoPaterna", "avoMaterno", "avoMaterna")}


@app.post("/api/animais")
def criar_animal(body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    a = Animal(id="a" + nid(), haras_id=u.haras_id, origem="Cadastro manual", vivo=None)
    _aplicar_animal(a, body, db, u.haras_id)
    db.add(a)
    db.commit()
    return {"id": a.id, "resumo": f"{a.nome} cadastrado. A agenda sanitária foi gerada."}


@app.put("/api/animais/{aid}")
def editar_animal(aid: str, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    a = db.get(Animal, aid)
    if not a or a.haras_id != u.haras_id:
        erro(404, "Animal não encontrado.")
    _aplicar_animal(a, body, db, u.haras_id)
    db.commit()
    return {"id": a.id, "resumo": f"Dados de {a.nome} salvos."}


@app.post("/api/importacao")
def importar(body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    lst = body.get("animais") or []
    if not isinstance(lst, list) or not lst:
        erro(400, "Nenhum animal selecionado para importar.")
    if len(lst) > 200:
        erro(400, "Arquivo com animais demais para um haras.")
    impresso = _data(body.get("impresso"), "a data do relatório", obrigatorio=False) or R.hoje()
    existentes = list(db.scalars(select(Animal).where(Animal.haras_id == u.haras_id)))
    norm = lambda s: re.sub(r"\s+", " ", (s or "").strip().upper())
    ativos = len([a for a in existentes if a.vivo])
    novos = atual = 0
    for n in lst:
        reg, chip, nome = _txt(n.get("registro"), 20), _txt(n.get("chip"), 30), norm(n.get("nome"))
        ex = next((a for a in existentes if (reg and a.registro == reg) or (chip and a.chip == chip) or norm(a.nome) == nome), None)
        if ex is None:
            if bool(n.get("vivo", True)) and ativos >= LIMITE_ANIMAIS:
                erro(400, f"A importação ultrapassa o limite de {LIMITE_ANIMAIS} animais ativos. Desmarque alguns animais.")
            a = Animal(id="a" + nid(), haras_id=u.haras_id, origem="Importação ABCCMM", importado_em=impresso, vivo=None, genealogia={})
            _aplicar_animal(a, dict(n, genealogia={}), db, u.haras_id)
            db.add(a)
            db.flush()
            existentes.append(a)
            ativos += 1 if a.vivo else 0
            novos += 1
        else:
            gen = ex.genealogia or {}
            pel = ex.pelagem
            _aplicar_animal(ex, dict(n, genealogia=gen, pelagem=pel), db, u.haras_id)
            ex.importado_em = impresso
            atual += 1
    h = db.get(Haras, u.haras_id)
    if body.get("associado"):
        h.associado_abccmm = _txt(body.get("associado"), 160)
    db.add(Importacao(haras_id=u.haras_id, usuario_id=u.id, arquivo=_txt(body.get("arquivo"), 200), associado=_txt(body.get("associado"), 160), impresso=impresso, novos=novos, atualizados=atual))
    db.commit()
    return {"novos": novos, "atualizados": atual, "resumo": f"{novos} animal(is) importado(s) e {atual} atualizado(s). A agenda sanitária foi recalculada."}


# ---------------- registros e fotos ----------------
CAMPOS_DADOS = {"produto": 160, "lote": 40, "ferrador": 120, "resultado": 120, "exame": 80, "procedimento": 80, "evento": 40, "garanhao": 160, "dataCobertura": 10, "titulo": 160, "gravidade": 20}
ASSINATURAS = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp"}


def _salvar_foto(data_url, haras_id):
    m = re.match(r"^data:image/(jpeg|png|webp);base64,(.+)$", data_url or "", re.S)
    if not m:
        erro(400, "Formato de foto não suportado. Use JPG, PNG ou WebP.")
    raw = base64.b64decode(m.group(2), validate=False)
    if len(raw) > 4 * 1024 * 1024:
        erro(400, "Cada foto pode ter no máximo 4 MB.")
    ext = next((e for sig, e in ASSINATURAS.items() if raw.startswith(sig)), None)
    if not ext:
        erro(400, "O arquivo enviado não é uma imagem válida.")
    pasta = Path(FOTOS_DIR) / str(haras_id)
    pasta.mkdir(parents=True, exist_ok=True)
    fid = uuid.uuid4().hex
    arq = f"{fid}.{ext}"
    (pasta / arq).write_bytes(raw)
    return fid, arq


@app.post("/api/registros")
def criar_registro(request: Request, body: dict = Body(...), u: Usuario = Depends(usuario_atual), db=Depends(get_db)):
    a = db.get(Animal, _txt(body.get("animalId"), 16))
    if not a or a.haras_id != u.haras_id:
        erro(404, "Animal não encontrado.")
    tipo = _txt(body.get("tipo"), 20)
    if tipo not in R.CATS or tipo == "documental":
        erro(400, "Tipo de registro inválido.")
    data = _data(body.get("data"), "a data do registro")
    if data > R.hoje():
        erro(400, "A data não pode ser futura.")
    prots = {p["id"] for p in protocolos_haras(db, u.haras_id)}
    pl = [p for p in (body.get("protocolos") or []) if p in prots]
    if tipo == "vacina" and not pl:
        erro(400, "Marque ao menos uma doença coberta pela vacina.")
    dose = str(body.get("dose") or "unica")
    if dose not in ("1", "2", "3", "reforco", "unica"):
        erro(400, "Dose inválida.")
    dados = {k: _txt(body.get(k), n) for k, n in CAMPOS_DADOS.items() if body.get(k)}
    if tipo == "reprodutivo":
        if dados.get("evento") not in R.EVENTOS_REPRO:
            erro(400, "Evento reprodutivo inválido.")
        if a.sexo != "F" and dados["evento"] != "Cobertura":
            erro(400, "Eventos de gestação só se aplicam a fêmeas.")
        if dados["evento"] == "Diagnóstico positivo":
            cob = _data(dados.get("dataCobertura"), "a data da cobertura")
            if cob > data:
                erro(400, "A cobertura deve ser anterior ao diagnóstico.")
        dados["garanhao"] = dados.get("garanhao", "").upper()
    if tipo == "ocorrencia" and not dados.get("titulo"):
        erro(400, "Descreva a ocorrência em poucas palavras.")
    fotos = body.get("fotos") or []
    if len(fotos) > 4:
        erro(400, "Envie no máximo 4 fotos por registro.")
    r = Registro(id="r" + nid(), haras_id=u.haras_id, animal_id=a.id, data=data, tipo=tipo, protocolos=pl, dose=dose, obs=_txt(body.get("obs"), 4000),
                 dados=dados, autor=u.nome, autor_id=u.id, origem=origem_de(request))
    db.add(r)
    db.flush()
    salvos = []
    try:
        for i, f in enumerate(fotos):
            fid, arq = _salvar_foto(f, u.haras_id)
            salvos.append(arq)
            db.add(Foto(id=fid, registro_id=r.id, haras_id=u.haras_id, arquivo=arq, ordem=i))
        db.commit()
    except Exception:
        db.rollback()
        for arq in salvos:
            (Path(FOTOS_DIR) / str(u.haras_id) / arq).unlink(missing_ok=True)
        raise
    h, animais, regs, prs = carregar_base(db, u.haras_id)
    ro = next(x for x in regs if x["id"] == r.id)
    return {"id": r.id, "resumo": R.resumo_registro(haras_out(h), animais, regs, prs, ro)}


@app.delete("/api/registros/{rid}")
def excluir_registro(rid: str, u: Usuario = Depends(gestor), db=Depends(get_db)):
    r = db.get(Registro, rid)
    if not r or r.haras_id != u.haras_id:
        erro(404, "Registro não encontrado.")
    for f in db.scalars(select(Foto).where(Foto.registro_id == rid)):
        (Path(FOTOS_DIR) / str(f.haras_id) / f.arquivo).unlink(missing_ok=True)
        db.delete(f)
    db.delete(r)
    db.commit()
    return {"resumo": "Registro excluído. A agenda foi recalculada."}


@app.get("/fotos/{fid}")
def foto(fid: str, u: Usuario = Depends(usuario_atual), db=Depends(get_db)):
    f = db.get(Foto, fid)
    if not f or f.haras_id != u.haras_id:
        erro(404, "Foto não encontrada.")
    p = Path(FOTOS_DIR) / str(f.haras_id) / f.arquivo
    if not p.exists():
        erro(404, "Arquivo da foto não encontrado.")
    return FileResponse(p, headers={"Cache-Control": "private, max-age=86400"})


# ---------------- configurações ----------------
@app.put("/api/protocolos")
def salvar_protocolos(body: list = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    protocolos_haras(db, u.haras_id)
    atuais = {p.pid: p for p in db.scalars(select(Protocolo).where(Protocolo.haras_id == u.haras_id))}
    for item in body:
        p = atuais.get(item.get("id"))
        if not p:
            continue
        dd = dict(p.dados)
        dd["ativo"] = bool(item.get("ativo", dd.get("ativo")))
        if "idadeMeses" in item:
            v = int(item["idadeMeses"])
            if not 0 <= v <= 120:
                erro(400, f"Idade inválida em {dd['nome']}.")
            dd["idadeMeses"] = v
        if "serie" in item:
            s = [int(x) for x in item["serie"]]
            if any(x < 1 or x > 400 for x in s) or len(s) > 5:
                erro(400, f"Série inválida em {dd['nome']}.")
            dd["serie"] = s
        if "reforcoDias" in item:
            v = int(item["reforcoDias"])
            if not 1 <= v <= 1500:
                erro(400, f"Intervalo inválido em {dd['nome']}.")
            dd["reforcoDias"] = v
        p.dados = dd
    db.commit()
    return {"resumo": "Protocolos salvos. A agenda de todos os animais foi recalculada."}


@app.post("/api/protocolos/restaurar")
def restaurar_protocolos(u: Usuario = Depends(gestor), db=Depends(get_db)):
    for p in db.scalars(select(Protocolo).where(Protocolo.haras_id == u.haras_id)):
        db.delete(p)
    db.commit()
    protocolos_haras(db, u.haras_id)
    return {"resumo": "Protocolos restaurados para o padrão."}


@app.put("/api/haras")
def editar_haras(body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    h = db.get(Haras, u.haras_id)
    if "raivaSemestral" in body:
        h.raiva_semestral = bool(body["raivaSemestral"])
    for k, col in (("nome", "nome"), ("proprietario", "proprietario"), ("municipio", "municipio")):
        if k in body and _txt(body[k], 120):
            setattr(h, col, _txt(body[k], 120))
    db.commit()
    return {"ok": True}


@app.put("/api/notif-prefs")
def prefs(body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    h = db.get(Haras, u.haras_id)
    base = R.notif_prefs_padrao()
    for t in base:
        for c in base[t]:
            v = (body.get(t) or {}).get(c)
            if v is not None:
                base[t][c] = bool(v)
    h.notif_prefs = base
    db.commit()
    return {"ok": True}


@app.post("/api/notificacoes/lidas")
def marcar_lidas(body: dict = Body(...), u: Usuario = Depends(usuario_atual), db=Depends(get_db)):
    ja = set(db.scalars(select(NotifLida.nid).where(NotifLida.usuario_id == u.id)))
    for n in (body.get("ids") or [])[:500]:
        n = _txt(n, 190)
        if n and n not in ja:
            db.add(NotifLida(usuario_id=u.id, nid=n))
            ja.add(n)
    db.commit()
    return {"ok": True}


# ---------------- usuários ----------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.post("/api/usuarios")
def criar_usuario(body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    nome, email, perfil, senha = _txt(body.get("nome"), 120), _txt(body.get("email"), 160).lower(), body.get("perfil"), str(body.get("senha") or "")
    if not nome:
        erro(400, "Informe o nome.")
    if not EMAIL_RE.match(email):
        erro(400, "Informe um e-mail válido.")
    if perfil not in ("gestor", "operador"):
        erro(400, "Perfil inválido.")
    if len(senha) < 8:
        erro(400, "A senha inicial precisa ter pelo menos 8 caracteres.")
    if db.scalar(select(Usuario).where(Usuario.email == email)):
        erro(409, "Já existe um usuário com esse e-mail.")
    db.add(Usuario(haras_id=u.haras_id, nome=nome, email=email, perfil=perfil, senha_hash=hash_senha(senha), ativo=True))
    db.commit()
    return {"resumo": f"{nome} adicionado. Envie o endereço e a senha inicial para o primeiro acesso."}


def _usuario_do_haras(db, uid, u):
    x = db.get(Usuario, uid)
    if not x or x.haras_id != u.haras_id:
        erro(404, "Usuário não encontrado.")
    return x


@app.patch("/api/usuarios/{uid}")
def editar_usuario(uid: int, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    x = _usuario_do_haras(db, uid, u)
    if x.id == u.id:
        erro(400, "Você não pode desativar o próprio acesso.")
    if "ativo" in body:
        x.ativo = bool(body["ativo"])
    db.commit()
    return {"ok": True}


@app.post("/api/usuarios/{uid}/senha")
def redefinir_senha(uid: int, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    x = _usuario_do_haras(db, uid, u)
    senha = str(body.get("senha") or "")
    if len(senha) < 8:
        erro(400, "A senha precisa ter pelo menos 8 caracteres.")
    x.senha_hash = hash_senha(senha)
    db.commit()
    return {"resumo": f"Senha de {x.nome} redefinida. As sessões abertas dele foram encerradas."}


# ---------------- páginas ----------------
def _pagina(nome):
    return FileResponse(STATIC / nome, headers={"Cache-Control": "no-cache"}, media_type="text/html")


@app.get("/")
def raiz():
    return RedirectResponse("/entrar")


@app.get("/entrar")
def pg_entrar():
    return _pagina("entrar.html")


@app.get("/gestor")
def pg_gestor():
    return _pagina("gestor.html")


@app.get("/campo")
def pg_campo():
    return _pagina("campo.html")


@app.get("/api/saude")
def saude(db=Depends(get_db)):
    db.execute(select(1))
    return {"ok": True, "versao": VERSAO}
