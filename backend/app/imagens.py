"""Personalização por imagens (v1.3.0): marca da plataforma e imagens de cada haras.

* Plataforma (administrador): logo, entrada, cabecalho, banner e app. São públicas, porque a
  tela de entrada aparece antes do login, e servem de padrão para os haras.
* Haras (gestor): cabecalho, banner e app. Só usuários do haras recebem. O logotipo do haras
  continua em logos.py.
O navegador já reduz e converte para WebP; o servidor confere o tipo real do arquivo.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select

from .config import IMAGENS_DIR
from .db import ImagemMarca, Usuario
from .seguranca import admin, auditar, do_haras, erro, gestor, get_db

r = APIRouter()

TIPOS_PLATAFORMA = {"logo": "Logotipo da plataforma", "entrada": "Fundo da tela de entrada", "cabecalho": "Imagem do cabeçalho",
                    "banner": "Banner do Dashboard", "app": "Fundo do app"}
TIPOS_HARAS = {k: v for k, v in TIPOS_PLATAFORMA.items() if k in ("cabecalho", "banner", "app")}
FOCOS = ("centro", "topo", "base")
ASSINATURAS = {b"\x89PNG": "png", b"\xff\xd8\xff": "jpg", b"RIFF": "webp"}
MAX_BYTES = 3 * 1024 * 1024


def _tipo_real(raw: bytes):
    ext = next((e for sig, e in ASSINATURAS.items() if raw.startswith(sig)), None)
    if ext == "webp" and raw[8:12] != b"WEBP":
        return None
    return ext


def _registro(db, haras_id, tipo):
    q = select(ImagemMarca).where(ImagemMarca.tipo == tipo)
    q = q.where(ImagemMarca.haras_id.is_(None)) if haras_id is None else q.where(ImagemMarca.haras_id == haras_id)
    return db.scalar(q)


def _versao(img):
    return int(img.atualizado_em.timestamp()) if img.atualizado_em else 0


def descrever(db, haras_id=None):
    """Imagens em vigor: as do haras e, na falta, as da plataforma. None = usar a ilustração padrão."""
    plat = {i.tipo: i for i in db.scalars(select(ImagemMarca).where(ImagemMarca.haras_id.is_(None)))}
    prop = {i.tipo: i for i in db.scalars(select(ImagemMarca).where(ImagemMarca.haras_id == haras_id))} if haras_id else {}
    out = {}
    for tipo in TIPOS_PLATAFORMA:
        if tipo in prop and tipo in TIPOS_HARAS:
            i = prop[tipo]
            out[tipo] = {"url": f"/imagens/{tipo}?v={_versao(i)}", "foco": i.foco, "origem": "haras", "versao": _versao(i)}
        elif tipo in plat:
            i = plat[tipo]
            out[tipo] = {"url": f"/marca/{tipo}?v={_versao(i)}", "foco": i.foco, "origem": "plataforma", "versao": _versao(i)}
        else:
            out[tipo] = None
    return out


async def _gravar(db, haras_id, tipo, arquivo: UploadFile, foco: str):
    if foco not in FOCOS:
        erro(400, "Ponto de foco inválido.")
    raw = await arquivo.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        erro(400, "A imagem pode ter no máximo 3 MB depois de reduzida.")
    ext = _tipo_real(raw)
    if not ext:
        erro(400, "Envie uma imagem PNG, JPG ou WebP.")
    pasta = IMAGENS_DIR / ("plataforma" if haras_id is None else str(haras_id))
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{tipo}-{uuid.uuid4().hex[:12]}.{ext}"
    (pasta / nome).write_bytes(raw)
    img = _registro(db, haras_id, tipo)
    if img:
        (pasta / img.arquivo).unlink(missing_ok=True)
        img.arquivo, img.foco = nome, foco
        img.atualizado_em = datetime.now()
    else:
        db.add(ImagemMarca(haras_id=haras_id, tipo=tipo, arquivo=nome, foco=foco))


def _remover(db, haras_id, tipo):
    img = _registro(db, haras_id, tipo)
    if not img:
        return False
    (IMAGENS_DIR / ("plataforma" if haras_id is None else str(haras_id)) / img.arquivo).unlink(missing_ok=True)
    db.delete(img)
    return True


def _foco(db, haras_id, tipo, foco):
    if foco not in FOCOS:
        erro(400, "Ponto de foco inválido.")
    img = _registro(db, haras_id, tipo)
    if not img:
        erro(404, "Nenhuma imagem própria para ajustar.")
    img.foco = foco
    img.atualizado_em = datetime.now()


def _servir(haras_id, img):
    if not img:
        erro(404, "Imagem não encontrada.")
    p = IMAGENS_DIR / ("plataforma" if haras_id is None else str(haras_id)) / img.arquivo
    if not p.is_file():
        erro(404, "Imagem não encontrada.")
    # A URL leva ?v=<versão>; uma troca gera outra URL, então o cache pode ser longo.
    return FileResponse(p, headers={"Cache-Control": ("public" if haras_id is None else "private") + ", max-age=2592000"})


# ---------------- leitura ----------------
@r.get("/api/marca")
def marca_publica(db=Depends(get_db)):
    d = descrever(db)
    return {"logo": d["logo"], "entrada": d["entrada"]}


@r.get("/marca/{tipo}")
def imagem_plataforma(tipo: str, db=Depends(get_db)):
    if tipo not in TIPOS_PLATAFORMA:
        erro(404, "Imagem não encontrada.")
    return _servir(None, _registro(db, None, tipo))


@r.get("/imagens/{tipo}")
def imagem_haras(tipo: str, u: Usuario = Depends(do_haras), db=Depends(get_db)):
    if tipo not in TIPOS_HARAS:
        erro(404, "Imagem não encontrada.")
    return _servir(u.haras_id, _registro(db, u.haras_id, tipo))


# ---------------- gestor do haras ----------------
@r.post("/api/haras/imagens/{tipo}")
async def enviar_haras(tipo: str, request: Request, arquivo: UploadFile = File(...), foco: str = Form("centro"),
                       u: Usuario = Depends(gestor), db=Depends(get_db)):
    if tipo not in TIPOS_HARAS:
        erro(404, "Tipo de imagem inválido.")
    await _gravar(db, u.haras_id, tipo, arquivo, foco)
    auditar(db, "imagem_alterada", usuario=u, alvo=TIPOS_HARAS[tipo], request=request)
    db.commit()
    return {"resumo": f"{TIPOS_HARAS[tipo]} atualizada.", "imagens": descrever(db, u.haras_id)}


@r.patch("/api/haras/imagens/{tipo}")
def foco_haras(tipo: str, request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    if tipo not in TIPOS_HARAS:
        erro(404, "Tipo de imagem inválido.")
    _foco(db, u.haras_id, tipo, str(body.get("foco") or ""))
    db.commit()
    return {"resumo": "Ponto de foco ajustado.", "imagens": descrever(db, u.haras_id)}


@r.delete("/api/haras/imagens/{tipo}")
def remover_haras(tipo: str, request: Request, u: Usuario = Depends(gestor), db=Depends(get_db)):
    if tipo not in TIPOS_HARAS:
        erro(404, "Tipo de imagem inválido.")
    if _remover(db, u.haras_id, tipo):
        auditar(db, "imagem_removida", usuario=u, alvo=TIPOS_HARAS[tipo], request=request)
    db.commit()
    return {"resumo": f"{TIPOS_HARAS[tipo]}: de volta ao padrão.", "imagens": descrever(db, u.haras_id)}


# ---------------- administrador da plataforma ----------------
@r.post("/api/admin/marca/{tipo}")
async def enviar_plataforma(tipo: str, request: Request, arquivo: UploadFile = File(...), foco: str = Form("centro"),
                            u: Usuario = Depends(admin), db=Depends(get_db)):
    if tipo not in TIPOS_PLATAFORMA:
        erro(404, "Tipo de imagem inválido.")
    await _gravar(db, None, tipo, arquivo, foco)
    auditar(db, "imagem_alterada", usuario=u, alvo=f"Plataforma: {TIPOS_PLATAFORMA[tipo]}", request=request)
    db.commit()
    return {"resumo": f"{TIPOS_PLATAFORMA[tipo]} atualizada.", "marca": descrever(db)}


@r.patch("/api/admin/marca/{tipo}")
def foco_plataforma(tipo: str, body: dict = Body(...), u: Usuario = Depends(admin), db=Depends(get_db)):
    if tipo not in TIPOS_PLATAFORMA:
        erro(404, "Tipo de imagem inválido.")
    _foco(db, None, tipo, str(body.get("foco") or ""))
    db.commit()
    return {"resumo": "Ponto de foco ajustado.", "marca": descrever(db)}


@r.delete("/api/admin/marca/{tipo}")
def remover_plataforma(tipo: str, request: Request, u: Usuario = Depends(admin), db=Depends(get_db)):
    if tipo not in TIPOS_PLATAFORMA:
        erro(404, "Tipo de imagem inválido.")
    if _remover(db, None, tipo):
        auditar(db, "imagem_removida", usuario=u, alvo=f"Plataforma: {TIPOS_PLATAFORMA[tipo]}", request=request)
    db.commit()
    return {"resumo": f"{TIPOS_PLATAFORMA[tipo]}: de volta ao padrão.", "marca": descrever(db)}


@r.get("/api/admin/marca")
def ver_marca(u: Usuario = Depends(admin), db=Depends(get_db)):
    return {"marca": descrever(db)}

