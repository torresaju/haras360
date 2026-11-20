"""Aplicação web do Haras360: API, páginas e cabeçalhos de segurança."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy import select

from .config import FOTOS_DIR, VERSAO
from .migracoes import migrar
from .rotas_admin import r as rotas_admin
from .rotas_auth import r as rotas_auth
from .rotas_haras import r as rotas_haras
from .seguranca import confere_senha, get_db, hash_senha  # noqa: F401 (reexportados para o CLI e testes)

STATIC = Path(__file__).parent / "static"

CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
       "img-src 'self' data: blob:; worker-src 'self' blob: https://cdnjs.cloudflare.com; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


@asynccontextmanager
async def ciclo(_app):
    migrar(silencioso=True)
    Path(FOTOS_DIR).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Haras360", version=VERSAO, docs_url=None, redoc_url=None, openapi_url=None, lifespan=ciclo)


@app.middleware("http")
async def protecao(request: Request, call_next):
    # Toda alteração pela API exige o cabeçalho X-Haras360, que formulários de outros sites não conseguem enviar.
    if request.url.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if request.headers.get("x-haras360") != "1":
            return JSONResponse({"detail": "Requisição recusada."}, status_code=403)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if resp.headers.get("content-type", "").startswith("text/html"):
        resp.headers["Content-Security-Policy"] = CSP
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


app.include_router(rotas_auth)
app.include_router(rotas_haras)
app.include_router(rotas_admin)


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


@app.get("/admin")
def pg_admin():
    return _pagina("admin.html")


@app.get("/ajuda")
def pg_ajuda():
    return _pagina("ajuda.html")


@app.get("/ajuda/img/{nome}")
def img_ajuda(nome: str):
    p = (STATIC / "ajuda" / nome).resolve()
    if p.parent != (STATIC / "ajuda").resolve() or not p.is_file() or p.suffix not in (".png", ".webp", ".jpg"):
        return JSONResponse({"detail": "Não encontrado."}, status_code=404)
    return FileResponse(p, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/saude")
def saude(db=Depends(get_db)):
    db.execute(select(1))
    return {"ok": True, "versao": VERSAO}
