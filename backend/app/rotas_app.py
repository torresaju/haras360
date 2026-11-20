"""Rotas do app Android do caseiro (v1.1.0): vínculo por QR Code, sincronização, fotos e versão do APK."""
import hashlib
import json
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from . import parametros as P
from .config import APP_DIR, FOTOS_DIR
from .db import Foto, Haras, Registro, Sessao, Usuario, VinculoApp
from .rotas_haras import ASSINATURAS, estado
from .seguranca import (auditar, checar_limite, criar_sessao, do_haras, erro, gestor, get_db, ip_de, limpar_falhas, qr_svg, registrar_falha)

r = APIRouter()

VALIDADE_VINCULO_MIN = 10
FOTO_ID = re.compile(r"^[a-f0-9]{32}$")
MAX_FOTO = 4 * 1024 * 1024
MAX_FOTOS_REGISTRO = 4


def _hash(c):
    return hashlib.sha256(c.encode()).hexdigest()


def _base_url(request: Request):
    # O Caddy repassa o Host original; o endereço é o mesmo que o gestor usa no navegador.
    return str(request.base_url).rstrip("/")


def info_apk():
    """Versão do APK incluído no pacote do servidor, ou None se não houver."""
    apk = APP_DIR / "haras360.apk"
    meta = APP_DIR / "versao.json"
    if not apk.is_file() or not meta.is_file():
        return None
    try:
        m = json.loads(meta.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return {"versao": str(m.get("versao", "")), "codigo": int(m.get("codigo", 0)), "sha256": str(m.get("sha256", "")),
            "tamanho": apk.stat().st_size, "url": "/app/haras360.apk"}


# ---------------- vínculo do aparelho ----------------
@r.post("/api/usuarios/{uid}/vinculo")
def gerar_vinculo(uid: int, request: Request, u: Usuario = Depends(gestor), db=Depends(get_db)):
    alvo = db.get(Usuario, uid)
    if not alvo or alvo.haras_id != u.haras_id:
        erro(404, "Usuário não encontrado.")
    if alvo.perfil != "operador":
        erro(400, "O app Android é de uso do caseiro.")
    if not alvo.ativo:
        erro(400, "Reative o acesso deste caseiro antes de vincular um celular.")
    if not P.modulo_liberado(db, db.get(Haras, u.haras_id), "caseiro"):
        erro(403, "O acesso do caseiro não está incluído no plano deste haras.")
    # Um código pendente por caseiro: gerar outro invalida o anterior.
    for v in db.scalars(select(VinculoApp).where(VinculoApp.usuario_id == uid, VinculoApp.usado_em.is_(None))):
        db.delete(v)
    codigo = secrets.token_urlsafe(18)
    expira = datetime.now() + timedelta(minutes=VALIDADE_VINCULO_MIN)
    db.add(VinculoApp(codigo_hash=_hash(codigo), usuario_id=uid, haras_id=u.haras_id, criado_por=u.id, expira_em=expira))
    auditar(db, "app_vinculo_gerado", usuario=u, alvo=alvo.nome, request=request)
    db.commit()
    servidor = _base_url(request)
    link = f"haras360://vincular?s={quote(servidor, safe='')}&c={codigo}"
    return {"qr": qr_svg(link), "link": link, "servidor": servidor, "codigo": codigo, "minutos": VALIDADE_VINCULO_MIN,
            "expira": expira.isoformat(timespec="minutes"), "caseiro": alvo.nome}


@r.post("/api/app/vincular")
def vincular(request: Request, body: dict = Body(...), db=Depends(get_db)):
    chave = "vinculo|" + ip_de(request)
    checar_limite(db, chave)
    codigo = str(body.get("codigo") or "").strip()[:64]
    aparelho = re.sub(r"[\x00-\x1f]", "", str(body.get("aparelho") or "Celular Android"))[:120]
    v = db.get(VinculoApp, _hash(codigo)) if codigo else None
    if not v or v.usado_em or v.expira_em < datetime.now():
        registrar_falha(chave)
        auditar(db, "app_vinculo_falha", alvo=aparelho, resultado="falha", request=request, nome="(código de vínculo)")
        db.commit()
        erro(401, "Código inválido ou vencido. Peça ao gestor um novo QR Code.")
    u = db.get(Usuario, v.usuario_id)
    h = db.get(Haras, v.haras_id)
    if not u or not u.ativo or u.perfil != "operador" or not h or not h.ativo:
        erro(403, "Acesso desativado. Fale com o gestor do haras.")
    if not P.modulo_liberado(db, h, "caseiro"):
        erro(403, "O acesso do caseiro não está incluído no plano deste haras.")
    v.usado_em = datetime.now()
    limpar_falhas(chave)
    token, s = criar_sessao(db, u, request, tipo="app")
    s.agente = f"App Android · {aparelho}"[:200]
    auditar(db, "app_vinculado", usuario=u, alvo=aparelho, request=request)
    db.commit()
    return {"token": token, "sessao": s.publico, "nome": u.nome, "email": u.email, "haras": h.nome}


# ---------------- sincronização ----------------
@r.get("/api/app/sincronizar")
def sincronizar(request: Request, u: Usuario = Depends(do_haras), db=Depends(get_db)):
    if u.perfil != "operador":
        erro(403, "A sincronização é do app do caseiro.")
    s: Sessao = db.get(Sessao, request.state.sessao.token_hash)
    if s.tipo == "app":
        # Cada sincronização renova a validade do aparelho.
        s.expira_em = datetime.now() + timedelta(days=int(P.ler(db, "sessao_app_dias")))
        s.ultimo_uso = datetime.now()
        db.commit()
    e = estado(u, db)
    for k in ("usuarios", "plano", "notifPrefs"):
        e.pop(k, None)
    e["app"] = info_apk()
    e["sincronizadoEm"] = datetime.now().isoformat(timespec="seconds")
    return e


@r.post("/api/app/fotos")
async def enviar_foto(request: Request, registroId: str = Form(...), fotoId: str = Form(...), ordem: int = Form(0),
                      arquivo: UploadFile = File(...), u: Usuario = Depends(do_haras), db=Depends(get_db)):
    fid = fotoId.strip().lower()
    if not FOTO_ID.match(fid):
        erro(400, "Identificador de foto inválido.")
    ja = db.get(Foto, fid)
    if ja:
        if ja.haras_id != u.haras_id:
            erro(409, "Identificador de foto em uso.")
        return {"id": fid, "duplicado": True}
    rg = db.get(Registro, registroId.strip()[:40])
    if not rg or rg.haras_id != u.haras_id:
        erro(404, "Registro não encontrado. Envie o registro antes das fotos.")
    if u.perfil == "operador" and rg.autor_id != u.id:
        erro(403, "Só é possível anexar fotos aos próprios registros.")
    n = db.scalar(select(func.count()).select_from(Foto).where(Foto.registro_id == rg.id)) or 0
    if n >= MAX_FOTOS_REGISTRO:
        erro(400, f"Cada registro aceita no máximo {MAX_FOTOS_REGISTRO} fotos.")
    raw = await arquivo.read(MAX_FOTO + 1)
    if len(raw) > MAX_FOTO:
        erro(400, "Cada foto pode ter no máximo 4 MB.")
    ext = next((e for sig, e in ASSINATURAS.items() if raw.startswith(sig)), None)
    if not ext:
        erro(400, "O arquivo enviado não é uma imagem válida.")
    pasta = Path(FOTOS_DIR) / str(u.haras_id)
    pasta.mkdir(parents=True, exist_ok=True)
    arq = f"{fid}.{ext}"
    (pasta / arq).write_bytes(raw)
    try:
        db.add(Foto(id=fid, registro_id=rg.id, haras_id=u.haras_id, arquivo=arq, ordem=max(0, min(int(ordem), 9))))
        db.commit()
    except Exception:
        db.rollback()
        (pasta / arq).unlink(missing_ok=True)
        raise
    return {"id": fid}


# ---------------- APK ----------------
@r.get("/api/app/versao")
def versao_app():
    i = info_apk()
    if not i:
        return {"disponivel": False}
    return dict(i, disponivel=True)


@r.get("/api/app/instalar")
def instalar_app(request: Request, u: Usuario = Depends(do_haras)):
    i = info_apk()
    if not i:
        return {"disponivel": False}
    url = _base_url(request) + i["url"]
    return dict(i, disponivel=True, link=url, qr=qr_svg(url))


@r.get("/app/haras360.apk")
def baixar_apk():
    # Público: o APK não contém dados nem segredos, e o Android só aceita atualizações assinadas pela mesma chave.
    p = APP_DIR / "haras360.apk"
    if not p.is_file():
        erro(404, "O app Android ainda não foi incluído nesta versão do servidor.")
    return FileResponse(p, media_type="application/vnd.android.package-archive", filename="haras360.apk",
                        headers={"Cache-Control": "no-cache"})
