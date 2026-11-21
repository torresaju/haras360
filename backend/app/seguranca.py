"""Senhas, sessões, 2FA, limite de tentativas e auditoria."""
import hashlib
import secrets
import time
from datetime import datetime, timedelta

import bcrypt
import pyotp
import segno
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select

from . import parametros as P
from .config import COOKIE_SECURE
from .db import Auditoria, Haras, SessionLocal, Sessao, Usuario

COOKIE = "h360"
EMISSOR_2FA = "Haras360"


def erro(status, msg):
    raise HTTPException(status_code=status, detail=msg)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- senhas ----------------
def hash_senha(s):
    return bcrypt.hashpw(s.encode(), bcrypt.gensalt()).decode()


def confere_senha(s, h):
    try:
        return bcrypt.checkpw((s or "").encode(), (h or "").encode())
    except ValueError:
        return False


def validar_senha_nova(s):
    if len(s or "") < 8:
        erro(400, "A senha precisa ter pelo menos 8 caracteres.")
    if len(s) > 128:
        erro(400, "A senha pode ter no máximo 128 caracteres.")


# ---------------- origem da requisição ----------------
def ip_de(request: Request):
    ip = request.client.host if request.client else ""
    # O Caddy roda na mesma máquina; só nele confiamos para o IP real.
    if ip in ("127.0.0.1", "::1"):
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            ip = fwd.split(",")[0].strip()
    return ip[:64]


# ---------------- auditoria ----------------
def auditar(db, acao, *, usuario=None, haras_id=None, alvo="", resultado="ok", detalhe=None, request=None, nome=None):
    db.add(Auditoria(
        acao=acao[:40], alvo=str(alvo or "")[:200], resultado=resultado, detalhe=detalhe or None,
        usuario_id=usuario.id if usuario else None,
        usuario=(nome or (f"{usuario.nome} <{usuario.email}>" if usuario else ""))[:160],
        haras_id=haras_id if haras_id is not None else (usuario.haras_id if usuario else None),
        ip=ip_de(request) if request else "",
    ))


# ---------------- limite de tentativas ----------------
_tentativas: dict = {}


def checar_limite(db, chave):
    n = int(P.ler(db, "login_tentativas"))
    janela = int(P.ler(db, "login_janela_min")) * 60
    t = time.time()
    lst = [x for x in _tentativas.get(chave, []) if t - x < janela]
    _tentativas[chave] = lst
    if len(lst) >= n:
        erro(429, f"Muitas tentativas. Aguarde {janela // 60} minutos e tente de novo.")


def registrar_falha(chave):
    _tentativas.setdefault(chave, []).append(time.time())


def limpar_falhas(chave):
    _tentativas.pop(chave, None)


# ---------------- sessões ----------------
def _hash_token(t):
    return hashlib.sha256(t.encode()).hexdigest()


def criar_sessao(db, u: Usuario, request: Request, etapa="ok", tipo="web"):
    token = secrets.token_urlsafe(32)
    if etapa != "ok":
        validade = timedelta(minutes=10)
    else:
        validade = timedelta(days=int(P.ler(db, "sessao_app_dias" if tipo == "app" else "sessao_dias")))
    s = Sessao(token_hash=_hash_token(token), publico=secrets.token_hex(6), usuario_id=u.id, etapa=etapa, tipo=tipo,
               ip=ip_de(request), agente=(request.headers.get("user-agent") or "")[:200], expira_em=datetime.now() + validade)
    db.add(s)
    return token, s


def gravar_cookie(resp: Response, token, dias=7):
    resp.set_cookie(COOKIE, token, max_age=dias * 86400, httponly=True, samesite="lax", secure=COOKIE_SECURE, path="/")


def token_da_requisicao(request: Request):
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(COOKIE)


def sessao_da_requisicao(db, request: Request, etapas=("ok",), token=None):
    tok = token or token_da_requisicao(request)
    if not tok:
        erro(401, "Faça login para continuar.")
    s = db.get(Sessao, _hash_token(tok))
    if not s or s.revogada or s.expira_em < datetime.now() or s.etapa not in etapas:
        erro(401, "Sessão expirada. Faça login novamente.")
    u = db.get(Usuario, s.usuario_id)
    if not u or not u.ativo:
        erro(401, "Acesso desativado. Fale com o gestor do haras.")
    if u.haras_id:
        h = db.get(Haras, u.haras_id)
        if not h or not h.ativo:
            erro(401, "Este haras está desativado. Fale com o administrador.")
    if (datetime.now() - s.ultimo_uso).total_seconds() > 300:
        s.ultimo_uso = datetime.now()
        db.commit()
    return s, u


def revogar_sessoes(db, usuario_id, exceto=None):
    for s in db.scalars(select(Sessao).where(Sessao.usuario_id == usuario_id, Sessao.revogada.is_(False))):
        if exceto is None or s.token_hash != exceto:
            s.revogada = True


def usuario_atual(request: Request, db=Depends(get_db)) -> Usuario:
    s, u = sessao_da_requisicao(db, request)
    request.state.sessao = s
    return u


def do_haras(u: Usuario = Depends(usuario_atual)) -> Usuario:
    if not u.haras_id:
        erro(403, "Esta área é dos usuários de um haras.")
    return u


def gestor(u: Usuario = Depends(do_haras)) -> Usuario:
    if u.perfil != "gestor":
        erro(403, "Apenas o gestor pode fazer esta alteração.")
    return u


def admin(u: Usuario = Depends(usuario_atual)) -> Usuario:
    if u.perfil != "admin":
        erro(403, "Apenas o administrador da plataforma pode fazer isto.")
    return u


# ---------------- 2FA ----------------
def exige_2fa(u: Usuario):
    return u.perfil in ("admin", "gestor")


def qr_svg(uri):
    # viewBox (omitsize) deixa o QR Code escalar com o CSS sem cortar as bordas.
    return segno.make(uri, error="m").svg_inline(scale=5, dark="#1b231e", light="#ffffff", border=4, omitsize=True)


def novo_segredo():
    return pyotp.random_base32()


def uri_2fa(u: Usuario, segredo):
    return pyotp.TOTP(segredo).provisioning_uri(name=u.email, issuer_name=EMISSOR_2FA)


def confere_totp(segredo, codigo):
    codigo = "".join(ch for ch in str(codigo or "") if ch.isdigit())
    return len(codigo) == 6 and pyotp.TOTP(segredo).verify(codigo, valid_window=1)


def gerar_codigos_recuperacao(n=8):
    codigos = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(n)]
    return codigos, [_hash_token(c) for c in codigos]


def usar_codigo_recuperacao(u: Usuario, codigo):
    c = str(codigo or "").strip().lower()
    h = _hash_token(c)
    lst = list(u.recuperacao or [])
    if h in lst:
        lst.remove(h)
        u.recuperacao = lst
        return True
    return False
