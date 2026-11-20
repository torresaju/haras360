"""Login em duas etapas (senha e 2FA), cadastro do 2FA, sessões e senha."""
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Request, Response
from sqlalchemy import select

from . import parametros as P
from .db import Haras, Sessao, Usuario
from .seguranca import (COOKIE, auditar, checar_limite, confere_senha, confere_totp, criar_sessao, erro, exige_2fa, gerar_codigos_recuperacao,
                        get_db, gravar_cookie, limpar_falhas, novo_segredo, qr_svg, registrar_falha, revogar_sessoes, sessao_da_requisicao,
                        uri_2fa, usar_codigo_recuperacao, usuario_atual, validar_senha_nova, ip_de, hash_senha)

r = APIRouter(prefix="/api")


def _destino(u: Usuario):
    return {"admin": "/admin", "gestor": "/gestor"}.get(u.perfil, "/campo")


@r.post("/login")
def login(request: Request, resp: Response, body: dict = Body(...), db=Depends(get_db)):
    email = str(body.get("email") or "").strip().lower()[:160]
    senha = str(body.get("senha") or "")
    tipo = "app" if body.get("app") else "web"
    chave = ip_de(request) + "|" + email
    checar_limite(db, chave)
    u = db.scalar(select(Usuario).where(Usuario.email == email))
    if not u or not u.ativo or not confere_senha(senha, u.senha_hash):
        registrar_falha(chave)
        auditar(db, "login_falha", usuario=u, alvo=email, resultado="falha", request=request, nome=email)
        db.commit()
        erro(401, "E-mail ou senha incorretos.")
    if u.haras_id:
        h = db.get(Haras, u.haras_id)
        if not h or not h.ativo:
            erro(403, "Este haras está desativado. Fale com o administrador.")
        if u.perfil == "operador" and not P.modulo_liberado(db, h, "caseiro"):
            erro(403, "O acesso do caseiro não está incluído no plano deste haras.")
    if tipo == "app" and u.perfil != "operador":
        erro(403, "O aplicativo é de uso do caseiro. Gestores usam o portal web.")
    limpar_falhas(chave)
    if exige_2fa(u):
        etapa = "2fa" if u.totp_ativo else "cadastro2fa"
        token, _s = criar_sessao(db, u, request, etapa=etapa)
        db.commit()
        gravar_cookie(resp, token, 1)
        return {"etapa": etapa, "perfil": u.perfil, "nome": u.nome}
    token, s = criar_sessao(db, u, request, tipo=tipo)
    auditar(db, "login", usuario=u, alvo=tipo, request=request)
    db.commit()
    out = {"etapa": "ok", "perfil": u.perfil, "nome": u.nome, "destino": _destino(u)}
    if tipo == "app":
        out["token"] = token  # o app guarda o token no armazenamento seguro do aparelho
        out["sessao"] = s.publico
    else:
        gravar_cookie(resp, token, int(P.ler(db, "sessao_dias")))
    return out


def _concluir_2fa(db, request, resp, s: Sessao, u: Usuario):
    s.revogada = True
    token, _ = criar_sessao(db, u, request)
    gravar_cookie(resp, token, int(P.ler(db, "sessao_dias")))


@r.get("/2fa/cadastro")
def cadastro_2fa(request: Request, db=Depends(get_db)):
    s, u = sessao_da_requisicao(db, request, etapas=("cadastro2fa",))
    if not u.totp_segredo or u.totp_ativo:
        u.totp_segredo = novo_segredo()
        db.commit()
    uri = uri_2fa(u, u.totp_segredo)
    return {"segredo": u.totp_segredo, "uri": uri, "qr": qr_svg(uri), "email": u.email}


@r.post("/2fa/confirmar")
def confirmar_2fa(request: Request, resp: Response, body: dict = Body(...), db=Depends(get_db)):
    s, u = sessao_da_requisicao(db, request, etapas=("cadastro2fa",))
    chave = "2fa|" + str(u.id)
    checar_limite(db, chave)
    if not u.totp_segredo or not confere_totp(u.totp_segredo, body.get("codigo")):
        registrar_falha(chave)
        auditar(db, "2fa_falha", usuario=u, alvo="cadastro", resultado="falha", request=request)
        db.commit()
        erro(400, "Código incorreto. Confira a hora do celular e digite o código atual do aplicativo.")
    codigos, hashes = gerar_codigos_recuperacao()
    u.totp_ativo = True
    u.recuperacao = hashes
    _concluir_2fa(db, request, resp, s, u)
    auditar(db, "2fa_cadastro", usuario=u, request=request)
    auditar(db, "login", usuario=u, alvo="web", request=request)
    db.commit()
    limpar_falhas(chave)
    return {"codigos": codigos, "destino": _destino(u)}


@r.post("/2fa/verificar")
def verificar_2fa(request: Request, resp: Response, body: dict = Body(...), db=Depends(get_db)):
    s, u = sessao_da_requisicao(db, request, etapas=("2fa",))
    chave = "2fa|" + str(u.id)
    checar_limite(db, chave)
    codigo = str(body.get("codigo") or "")
    por_recuperacao = False
    if confere_totp(u.totp_segredo, codigo):
        pass
    elif usar_codigo_recuperacao(u, codigo):
        por_recuperacao = True
    else:
        registrar_falha(chave)
        auditar(db, "2fa_falha", usuario=u, resultado="falha", request=request)
        db.commit()
        erro(400, "Código incorreto.")
    _concluir_2fa(db, request, resp, s, u)
    auditar(db, "login", usuario=u, alvo="web" + (" (código de recuperação)" if por_recuperacao else ""), request=request)
    db.commit()
    limpar_falhas(chave)
    return {"destino": _destino(u), "restantes": len(u.recuperacao or []) if por_recuperacao else None}


@r.post("/logout")
def logout(request: Request, resp: Response, db=Depends(get_db)):
    try:
        s, u = sessao_da_requisicao(db, request, etapas=("ok", "2fa", "cadastro2fa"))
        s.revogada = True
        auditar(db, "logout", usuario=u, request=request)
        db.commit()
    except Exception:
        pass
    resp.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@r.get("/me")
def me(u: Usuario = Depends(usuario_atual)):
    return {"id": u.id, "nome": u.nome, "email": u.email, "perfil": u.perfil, "destino": _destino(u)}


@r.post("/me/senha")
def trocar_senha(request: Request, body: dict = Body(...), u: Usuario = Depends(usuario_atual), db=Depends(get_db)):
    u = db.get(Usuario, u.id)
    if not confere_senha(str(body.get("atual") or ""), u.senha_hash):
        erro(400, "A senha atual está incorreta.")
    nova = str(body.get("nova") or "")
    validar_senha_nova(nova)
    u.senha_hash = hash_senha(nova)
    revogar_sessoes(db, u.id, exceto=request.state.sessao.token_hash)
    auditar(db, "senha_troca", usuario=u, request=request)
    db.commit()
    return {"resumo": "Senha alterada. As outras sessões abertas foram encerradas."}


@r.post("/me/codigos-recuperacao")
def novos_codigos(request: Request, body: dict = Body(...), u: Usuario = Depends(usuario_atual), db=Depends(get_db)):
    u = db.get(Usuario, u.id)
    if not exige_2fa(u):
        erro(400, "Seu perfil não usa 2FA.")
    if not confere_senha(str(body.get("senha") or ""), u.senha_hash):
        erro(400, "Senha incorreta.")
    codigos, hashes = gerar_codigos_recuperacao()
    u.recuperacao = hashes
    auditar(db, "2fa_codigos_novos", usuario=u, request=request)
    db.commit()
    return {"codigos": codigos}


# ---------------- sessões ----------------
def sessao_out(s: Sessao, u: Usuario, atual_hash):
    return {"id": s.publico, "usuario": u.nome, "usuarioId": u.id, "perfil": u.perfil, "tipo": s.tipo, "ip": s.ip, "agente": s.agente,
            "criada": s.criada_em.isoformat(timespec="minutes"), "ultimoUso": s.ultimo_uso.isoformat(timespec="minutes"),
            "atual": s.token_hash == atual_hash}


@r.get("/sessoes")
def listar_sessoes(request: Request, u: Usuario = Depends(usuario_atual), db=Depends(get_db)):
    q = select(Sessao, Usuario).join(Usuario, Usuario.id == Sessao.usuario_id).where(
        Sessao.revogada.is_(False), Sessao.etapa == "ok", Sessao.expira_em > datetime.now())
    if u.perfil == "gestor":
        q = q.where(Usuario.haras_id == u.haras_id)
    elif u.perfil != "admin":
        q = q.where(Usuario.id == u.id)
    atual = request.state.sessao.token_hash
    return [sessao_out(s, x, atual) for s, x in db.execute(q.order_by(Sessao.ultimo_uso.desc()))]


@r.delete("/sessoes/{pub}")
def encerrar_sessao(pub: str, request: Request, u: Usuario = Depends(usuario_atual), db=Depends(get_db)):
    s = db.scalar(select(Sessao).where(Sessao.publico == pub))
    if not s:
        erro(404, "Sessão não encontrada.")
    dono = db.get(Usuario, s.usuario_id)
    pode = u.perfil == "admin" or dono.id == u.id or (u.perfil == "gestor" and dono.haras_id == u.haras_id)
    if not pode:
        erro(404, "Sessão não encontrada.")
    s.revogada = True
    auditar(db, "sessao_encerrada", usuario=u, alvo=f"{dono.nome} ({s.tipo}, {s.ip})", request=request)
    db.commit()
    return {"resumo": f"Sessão de {dono.nome} encerrada."}
