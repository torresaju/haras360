"""Rotas do app Android: caseiro por QR Code (v1.1.0) e gestor por e-mail, senha e 2FA (v1.5.0);
sincronização, fotos, áudios e versão do APK."""
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
from .db import Audio, Foto, Haras, Registro, Sessao, Usuario, VinculoApp
from .rotas_haras import ASSINATURAS, estado
from .seguranca import (auditar, checar_limite, confere_senha, confere_totp, criar_sessao, do_haras, erro, exige_2fa, gestor, get_db, ip_de,
                        limpar_falhas, qr_svg, registrar_falha, sessao_da_requisicao, usar_codigo_recuperacao)

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
def novo_vinculo(db, alvo: Usuario, criado_por=None):
    """Gera o código de uso único do caseiro. Um código pendente por caseiro: gerar outro invalida o anterior."""
    for v in db.scalars(select(VinculoApp).where(VinculoApp.usuario_id == alvo.id, VinculoApp.usado_em.is_(None))):
        db.delete(v)
    codigo = secrets.token_urlsafe(18)
    expira = datetime.now() + timedelta(minutes=VALIDADE_VINCULO_MIN)
    db.add(VinculoApp(codigo_hash=_hash(codigo), usuario_id=alvo.id, haras_id=alvo.haras_id, criado_por=criado_por, expira_em=expira))
    return codigo, expira


def link_vinculo(servidor, codigo):
    return f"haras360://vincular?s={quote(servidor, safe='')}&c={codigo}"


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
    codigo, expira = novo_vinculo(db, alvo, u.id)
    auditar(db, "app_vinculo_gerado", usuario=u, alvo=alvo.nome, request=request)
    db.commit()
    servidor = _base_url(request)
    link = link_vinculo(servidor, codigo)
    apk = info_apk()
    instalar = {"link": servidor + apk["url"], "qr": qr_svg(servidor + apk["url"]), "versao": apk["versao"]} if apk else None
    return {"qr": qr_svg(link), "link": link, "servidor": servidor, "codigo": codigo, "minutos": VALIDADE_VINCULO_MIN,
            "expira": expira.isoformat(timespec="minutes"), "caseiro": alvo.nome, "instalar": instalar}


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


# ---------------- login do gestor no app (v1.5.0) ----------------
def https(request: Request):
    return request.url.scheme == "https"


def _exigir_https(db, request):
    if not https(request) and not P.ler(db, "app_gestor_sem_https"):
        erro(403, "O app do gestor só funciona com o servidor em HTTPS. Use o portal no navegador até o administrador ativar o HTTPS.")


def _aparelho(body):
    return re.sub(r"[\x00-\x1f]", "", str(body.get("aparelho") or "Celular Android"))[:120]


@r.post("/api/app/entrar")
def entrar_gestor(request: Request, body: dict = Body(...), db=Depends(get_db)):
    _exigir_https(db, request)
    email = str(body.get("email") or "").strip().lower()[:160]
    chave = ip_de(request) + "|" + email
    checar_limite(db, chave)
    u = db.scalar(select(Usuario).where(Usuario.email == email))
    if not u or not u.ativo or not confere_senha(str(body.get("senha") or ""), u.senha_hash):
        registrar_falha(chave)
        auditar(db, "login_falha", usuario=u, alvo=f"app · {email}", resultado="falha", request=request, nome=email)
        db.commit()
        erro(401, "E-mail ou senha incorretos.")
    if u.perfil == "operador":
        erro(403, "O caseiro entra no app pelo QR Code que o gestor gera em Equipe.")
    if u.perfil != "gestor":
        erro(403, "O app é para gestores e caseiros dos haras. Administradores usam o portal.")
    h = db.get(Haras, u.haras_id)
    if not h or not h.ativo:
        erro(403, "Este haras está desativado. Fale com o administrador.")
    if exige_2fa(u) and not u.totp_ativo:
        erro(403, "Ative a verificação em duas etapas (2FA) no portal antes de usar o app.")
    limpar_falhas(chave)
    token, _s = criar_sessao(db, u, request, etapa="2fa", tipo="app")
    _s.agente = f"App Android · {_aparelho(body)}"[:200]
    db.commit()
    return {"etapa": "2fa", "desafio": token, "nome": u.nome}


@r.post("/api/app/entrar/2fa")
def entrar_gestor_2fa(request: Request, body: dict = Body(...), db=Depends(get_db)):
    _exigir_https(db, request)
    tok = str(body.get("desafio") or "")
    if not tok:
        erro(401, "Sessão expirada. Faça login novamente.")
    s, u = sessao_da_requisicao(db, request, etapas=("2fa",), token=tok)
    chave = "2fa|" + str(u.id)
    checar_limite(db, chave)
    codigo = str(body.get("codigo") or "")
    recuperacao = False
    if confere_totp(u.totp_segredo, codigo):
        pass
    elif usar_codigo_recuperacao(u, codigo):
        recuperacao = True
    else:
        registrar_falha(chave)
        auditar(db, "2fa_falha", usuario=u, alvo="app", resultado="falha", request=request)
        db.commit()
        erro(400, "Código incorreto. Confira a hora do celular e digite o código atual do autenticador.")
    s.revogada = True
    token, novo = criar_sessao(db, u, request, tipo="app")
    novo.agente = s.agente
    novo.expira_em = datetime.now() + timedelta(days=int(P.ler(db, "sessao_app_gestor_dias")))
    h = db.get(Haras, u.haras_id)
    auditar(db, "app_gestor_entrou", usuario=u, alvo=s.agente.replace("App Android · ", "") + (" (código de recuperação)" if recuperacao else ""), request=request)
    db.commit()
    limpar_falhas(chave)
    return {"token": token, "sessao": novo.publico, "nome": u.nome, "email": u.email, "haras": h.nome, "perfil": "gestor",
            "restantes": len(u.recuperacao or []) if recuperacao else None}


@r.post("/api/app/sair")
def sair_app(request: Request, u: Usuario = Depends(do_haras), db=Depends(get_db)):
    s: Sessao = db.get(Sessao, request.state.sessao.token_hash)
    s.revogada = True
    auditar(db, "app_saiu", usuario=u, alvo=s.agente.replace("App Android · ", ""), request=request)
    db.commit()
    return {"ok": True}


# ---------------- sincronização ----------------
@r.get("/api/app/sincronizar")
def sincronizar(request: Request, u: Usuario = Depends(do_haras), db=Depends(get_db)):
    s: Sessao = db.get(Sessao, request.state.sessao.token_hash)
    if u.perfil == "gestor":
        if s.tipo != "app":
            erro(403, "Entre pelo app com e-mail, senha e 2FA.")
        _exigir_https(db, request)
    if s.tipo == "app":
        # Cada sincronização renova a validade do aparelho (gestor: 30 dias sem uso, por padrão).
        dias = "sessao_app_gestor_dias" if u.perfil == "gestor" else "sessao_app_dias"
        s.expira_em = datetime.now() + timedelta(days=int(P.ler(db, dias)))
        s.ultimo_uso = datetime.now()
        db.commit()
    e = estado(u, db)
    for k in ("usuarios", "notifPrefs") + (("plano",) if u.perfil != "gestor" else ()):
        e.pop(k, None)
    h = db.get(Haras, u.haras_id)
    e["perfil"] = u.perfil
    e["relatorios"] = u.perfil == "gestor" and P.modulo_liberado(db, h, "relatorios")
    e["app"] = info_apk()
    e["audio"] = {"liberado": P.modulo_liberado(db, h, "audio"), "maxSeg": int(P.ler(db, "audio_max_seg"))}
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


def _e_m4a(raw: bytes):
    """Áudio AAC em contêiner MP4/M4A (o que o app grava): caixa 'ftyp' no início do arquivo."""
    return len(raw) > 12 and raw[4:8] == b"ftyp" and raw[8:12] in (b"M4A ", b"mp42", b"isom", b"mp41", b"3gp4", b"3gp5", b"iso2", b"dash")


@r.post("/api/app/audios")
async def enviar_audio(request: Request, registroId: str = Form(...), audioId: str = Form(...), duracao: int = Form(0),
                       arquivo: UploadFile = File(...), u: Usuario = Depends(do_haras), db=Depends(get_db)):
    aid = audioId.strip().lower()
    if not FOTO_ID.match(aid):
        erro(400, "Identificador de áudio inválido.")
    ja = db.get(Audio, aid)
    if ja:
        if ja.haras_id != u.haras_id:
            erro(409, "Identificador de áudio em uso.")
        return {"id": aid, "duplicado": True}
    h = db.get(Haras, u.haras_id)
    if not P.modulo_liberado(db, h, "audio"):
        erro(403, "O áudio nos registros não está incluído no plano deste haras.")
    rg = db.get(Registro, registroId.strip()[:40])
    if not rg or rg.haras_id != u.haras_id:
        erro(404, "Registro não encontrado. Envie o registro antes do áudio.")
    if u.perfil == "operador" and rg.autor_id != u.id:
        erro(403, "Só é possível anexar áudio aos próprios registros.")
    if db.scalar(select(Audio).where(Audio.registro_id == rg.id)):
        erro(409, "Este registro já tem um áudio.")
    max_seg = int(P.ler(db, "audio_max_seg"))
    if duracao < 0 or duracao > max_seg + 5:
        erro(400, f"O áudio pode ter no máximo {max_seg} segundos.")
    limite = max(1024 * 1024, max_seg * 6000)
    raw = await arquivo.read(limite + 1)
    if len(raw) > limite:
        erro(400, f"O áudio pode ter no máximo {limite // 1024} KB.")
    if not _e_m4a(raw):
        erro(400, "O arquivo enviado não é um áudio válido.")
    pasta = Path(FOTOS_DIR) / str(u.haras_id)
    pasta.mkdir(parents=True, exist_ok=True)
    arq = f"{aid}.m4a"
    (pasta / arq).write_bytes(raw)
    try:
        db.add(Audio(id=aid, registro_id=rg.id, haras_id=u.haras_id, arquivo=arq, duracao=max(0, int(duracao))))
        db.commit()
    except Exception:
        db.rollback()
        (pasta / arq).unlink(missing_ok=True)
        raise
    return {"id": aid}


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
