"""Rotas do administrador da plataforma."""
import hashlib
import re

from fastapi import APIRouter, Body, Depends, File, Form, Request, UploadFile
from sqlalchemy import func, select

from . import logos as L
from . import imagens as IMG
from . import parametros as P
from . import regras as R
from . import sistema as S
from .config import MAX_PACOTE_MB, VERSAO
from .db import Animal, Haras, Protocolo, Usuario
from .migracoes import versao_banco
from .rotas_haras import EMAIL_RE, consultar_auditoria
from .seguranca import admin, auditar, confere_senha, erro, get_db, hash_senha, revogar_sessoes, validar_senha_nova

r = APIRouter(prefix="/api/admin")
PACOTE_RE = re.compile(r"^haras360-(\d+\.\d+\.\d+)\.tar\.gz$")


def _txt(v, n=200):
    return str(v or "").strip()[:n]


def criar_haras_com_gestor(db, nome, municipio, plano, gestor_nome, gestor_email, gestor_senha):
    """Usado pela tela do administrador e pelo comando de linha `criar-haras`."""
    nome, gestor_nome, gestor_email = _txt(nome, 120), _txt(gestor_nome, 120), _txt(gestor_email, 160).lower()
    if not nome:
        erro(400, "Informe o nome do haras.")
    if not gestor_nome:
        erro(400, "Informe o nome do gestor.")
    if not EMAIL_RE.match(gestor_email):
        erro(400, "Informe um e-mail válido para o gestor.")
    validar_senha_nova(gestor_senha)
    if db.scalar(select(Usuario).where(Usuario.email == gestor_email)):
        erro(409, "Já existe um usuário com esse e-mail.")
    planos = P.ler(db, "planos")
    plano = plano if plano in planos else next(iter(planos))
    h = Haras(nome=nome, proprietario=gestor_nome, municipio=_txt(municipio, 120), plano=plano, notif_prefs=R.notif_prefs_padrao())
    db.add(h)
    db.flush()
    for p in R.protocolos_padrao():
        db.add(Protocolo(haras_id=h.id, pid=p["id"], dados=p))
    g = Usuario(haras_id=h.id, nome=gestor_nome, email=gestor_email, senha_hash=hash_senha(gestor_senha), perfil="gestor", ativo=True)
    db.add(g)
    db.flush()
    return h, g


@r.get("/painel")
def painel(u: Usuario = Depends(admin), db=Depends(get_db)):
    contagem = dict(db.execute(select(Animal.haras_id, func.count()).where(Animal.vivo.is_(True)).group_by(Animal.haras_id)).all())
    usuarios = {}
    for x in db.scalars(select(Usuario).where(Usuario.haras_id.is_not(None)).order_by(Usuario.id)):
        usuarios.setdefault(x.haras_id, []).append({"id": x.id, "nome": x.nome, "email": x.email, "perfil": x.perfil, "ativo": bool(x.ativo),
                                                    "doisFatores": bool(x.totp_ativo)})
    faixas = P.ler(db, "faixas")
    haras = []
    for h in db.scalars(select(Haras).order_by(Haras.nome)):
        n = contagem.get(h.id, 0)
        plano = P.plano_do_haras(db, h)
        haras.append({"id": h.id, "nome": h.nome, "municipio": h.municipio, "plano": plano["nome"], "logo": L.url(h), "limite": plano["limite"], "ativo": bool(h.ativo),
                      "animais": n, "mensalidade": P.mensalidade(faixas, n), "usuarios": usuarios.get(h.id, []),
                      "criado": h.criado_em.date().isoformat()})
    administradores = [{"id": x.id, "nome": x.nome, "email": x.email, "ativo": bool(x.ativo), "doisFatores": bool(x.totp_ativo), "eu": x.id == u.id}
                       for x in db.scalars(select(Usuario).where(Usuario.perfil == "admin").order_by(Usuario.nome))]
    return {
        "versao": VERSAO, "versaoBanco": versao_banco(), "usuario": {"id": u.id, "nome": u.nome, "email": u.email, "perfil": u.perfil},
        "haras": haras, "administradores": administradores, "marca": IMG.descrever(db), "parametros": P.publico_global(P.todos(db)), "modulos": P.MODULOS,
        "atualizacao": S.status_tarefa(), "versoes": S.versoes_guardadas(), "backup": S.ultimo_backup(),
        "limitePacoteMB": MAX_PACOTE_MB,
    }


@r.post("/haras")
def novo_haras(request: Request, body: dict = Body(...), u: Usuario = Depends(admin), db=Depends(get_db)):
    h, g = criar_haras_com_gestor(db, body.get("nome"), body.get("municipio"), body.get("plano"), body.get("gestorNome"), body.get("gestorEmail"),
                                  str(body.get("gestorSenha") or ""))
    if body.get("logo"):
        L.salvar(h, body["logo"])
    auditar(db, "haras_criado", usuario=u, haras_id=h.id, alvo=f"{h.nome} · gestor {g.email}", detalhe={"plano": h.plano}, request=request)
    db.commit()
    return {"id": h.id, "resumo": f"Haras {h.nome} criado. O gestor cadastra o 2FA no primeiro acesso."}


@r.patch("/haras/{hid}")
def editar_haras(hid: int, request: Request, body: dict = Body(...), u: Usuario = Depends(admin), db=Depends(get_db)):
    h = db.get(Haras, hid)
    if not h:
        erro(404, "Haras não encontrado.")
    mud = {}
    if "plano" in body:
        planos = P.ler(db, "planos")
        if body["plano"] not in planos:
            erro(400, "Plano inexistente.")
        ativos = db.scalar(select(func.count()).select_from(Animal).where(Animal.haras_id == h.id, Animal.vivo.is_(True)))
        if ativos > int(planos[body["plano"]]["limite"]):
            erro(400, f"O haras tem {ativos} animais ativos, acima do limite do plano {body['plano']}.")
        mud["plano"] = {"antes": h.plano, "depois": body["plano"]}
        h.plano = body["plano"]
    if "ativo" in body:
        mud["ativo"] = {"antes": h.ativo, "depois": bool(body["ativo"])}
        h.ativo = bool(body["ativo"])
        if not h.ativo:
            for x in db.scalars(select(Usuario).where(Usuario.haras_id == h.id)):
                revogar_sessoes(db, x.id)
    if "nome" in body and _txt(body["nome"], 120):
        h.nome = _txt(body["nome"], 120)
    if "logo" in body:
        if body["logo"]:
            L.salvar(h, body["logo"])
        else:
            L.remover_arquivo(h.logo)
            h.logo = None
        mud["logo"] = "alterado" if body["logo"] else "removido"
    if mud:
        auditar(db, "haras_alterado", usuario=u, haras_id=h.id, alvo=h.nome, detalhe=mud, request=request)
    db.commit()
    return {"resumo": f"Haras {h.nome} atualizado."}


def _usuario(db, uid):
    x = db.get(Usuario, uid)
    if not x or x.perfil == "admin":
        erro(404, "Usuário não encontrado.")
    return x


@r.post("/usuarios/{uid}/senha")
def senha_usuario(uid: int, request: Request, body: dict = Body(...), u: Usuario = Depends(admin), db=Depends(get_db)):
    x = _usuario(db, uid)
    s = str(body.get("senha") or "")
    validar_senha_nova(s)
    x.senha_hash = hash_senha(s)
    x.ativo = True
    revogar_sessoes(db, x.id)
    auditar(db, "senha_redefinida", usuario=u, haras_id=x.haras_id, alvo=f"{x.nome} <{x.email}>", request=request)
    db.commit()
    return {"resumo": f"Senha de {x.nome} redefinida."}


@r.post("/usuarios/{uid}/2fa/redefinir")
def dois_fatores_usuario(uid: int, request: Request, u: Usuario = Depends(admin), db=Depends(get_db)):
    x = _usuario(db, uid)
    x.totp_ativo, x.totp_segredo, x.recuperacao = False, None, None
    revogar_sessoes(db, x.id)
    auditar(db, "2fa_redefinido", usuario=u, haras_id=x.haras_id, alvo=f"{x.nome} <{x.email}>", request=request)
    db.commit()
    return {"resumo": f"2FA de {x.nome} redefinido."}


# ---------------- administradores (v1.1.1) ----------------
def _confirmar_minha_senha(u: Usuario, body: dict):
    """Ações sobre administradores pedem a senha de quem as faz."""
    if not confere_senha(str(body.get("minhaSenha") or ""), u.senha_hash):
        erro(403, "Sua senha não confere. Digite a sua senha atual para confirmar.")


def _outro_admin(db, uid, u: Usuario):
    x = db.get(Usuario, uid)
    if not x or x.perfil != "admin":
        erro(404, "Administrador não encontrado.")
    if x.id == u.id:
        erro(400, "Para a sua própria conta, use o menu com o seu nome (senha e códigos de recuperação).")
    return x


@r.post("/administradores")
def criar_administrador(request: Request, body: dict = Body(...), u: Usuario = Depends(admin), db=Depends(get_db)):
    _confirmar_minha_senha(u, body)
    nome = _txt(body.get("nome"), 120)
    email = str(body.get("email") or "").strip().lower()[:160]
    senha = str(body.get("senha") or "")
    if not nome:
        erro(400, "Informe o nome.")
    if not EMAIL_RE.match(email):
        erro(400, "E-mail inválido.")
    validar_senha_nova(senha)
    if db.scalar(select(Usuario).where(Usuario.email == email)):
        erro(409, "Já existe um usuário com este e-mail.")
    x = Usuario(haras_id=None, nome=nome, email=email, senha_hash=hash_senha(senha), perfil="admin", ativo=True)
    db.add(x)
    auditar(db, "usuario_criado", usuario=u, alvo=f"{nome} <{email}> (admin)", request=request)
    db.commit()
    return {"resumo": f"Administrador {nome} criado. No primeiro acesso ele cadastra o 2FA."}


@r.patch("/administradores/{uid}")
def alterar_administrador(uid: int, request: Request, body: dict = Body(...), u: Usuario = Depends(admin), db=Depends(get_db)):
    x = _outro_admin(db, uid, u)
    if "ativo" not in body:
        erro(400, "Nada para alterar.")
    _confirmar_minha_senha(u, body)
    ativo = bool(body["ativo"])
    if not ativo:
        outros = db.scalar(select(func.count()).select_from(Usuario).where(Usuario.perfil == "admin", Usuario.ativo.is_(True), Usuario.id != x.id)) or 0
        if outros == 0:
            erro(400, "A plataforma precisa de pelo menos um administrador ativo.")
        revogar_sessoes(db, x.id)
    x.ativo = ativo
    auditar(db, "usuario_ativado" if ativo else "usuario_desativado", usuario=u, alvo=f"{x.nome} <{x.email}> (admin)", request=request)
    db.commit()
    return {"resumo": f"Administrador {x.nome} {'reativado' if ativo else 'desativado'}."}


@r.post("/administradores/{uid}/senha")
def senha_administrador(uid: int, request: Request, body: dict = Body(...), u: Usuario = Depends(admin), db=Depends(get_db)):
    x = _outro_admin(db, uid, u)
    _confirmar_minha_senha(u, body)
    s = str(body.get("senha") or "")
    validar_senha_nova(s)
    x.senha_hash = hash_senha(s)
    revogar_sessoes(db, x.id)
    auditar(db, "senha_redefinida", usuario=u, alvo=f"{x.nome} <{x.email}> (admin)", request=request)
    db.commit()
    return {"resumo": f"Senha de {x.nome} redefinida. As sessões dele foram encerradas."}


@r.post("/administradores/{uid}/2fa/redefinir")
def dois_fatores_administrador(uid: int, request: Request, body: dict = Body(...), u: Usuario = Depends(admin), db=Depends(get_db)):
    x = _outro_admin(db, uid, u)
    _confirmar_minha_senha(u, body)
    x.totp_ativo, x.totp_segredo, x.recuperacao = False, None, None
    revogar_sessoes(db, x.id)
    auditar(db, "2fa_redefinido", usuario=u, alvo=f"{x.nome} <{x.email}> (admin)", request=request)
    db.commit()
    return {"resumo": f"2FA de {x.nome} redefinido. Ele cadastra de novo no próximo acesso."}


@r.put("/parametros")
def salvar_parametros(request: Request, body: dict = Body(...), u: Usuario = Depends(admin), db=Depends(get_db)):
    atual = P.todos(db)
    try:
        novo = P.validar_global(body, atual)
    except (ValueError, TypeError, KeyError) as e:
        erro(400, str(e) or "Valor inválido.")
    if "planos" in novo:
        usados = set(db.scalars(select(Haras.plano)))
        faltando = usados - set(novo["planos"])
        if faltando:
            erro(400, f"Há haras no plano {', '.join(sorted(faltando))}. Mude o plano desses haras antes de removê-lo.")
    dif = {}
    for k, v in novo.items():
        if atual.get(k) != v:
            antes, depois = atual.get(k), v
            if k == "smtp":
                antes, depois = dict(antes, senha="***" if antes.get("senha") else ""), dict(depois, senha="***" if depois.get("senha") else "")
            dif[k] = {"antes": antes, "depois": depois}
            P.gravar(db, k, v)
    if dif:
        auditar(db, "parametro_alterado", usuario=u, alvo="global: " + ", ".join(dif), detalhe=dif, request=request)
    db.commit()
    return {"resumo": "Parametrizações salvas." if dif else "Nada mudou."}


@r.get("/auditoria")
def auditoria(haras: int = None, acao: str = "", texto: str = "", de: str = "", ate: str = "", limite: int = 200, u: Usuario = Depends(admin),
              db=Depends(get_db)):
    return consultar_auditoria(db, haras, acao, texto, de, ate, limite)


# ---------------- atualização, rollback e backup ----------------
@r.post("/atualizacao")
async def enviar_pacote(request: Request, pacote: UploadFile = File(...), assinatura: UploadFile = File(...), sha256: str = Form(""),
                        u: Usuario = Depends(admin), db=Depends(get_db)):
    if S.ocupado():
        erro(409, "Já existe uma tarefa em andamento. Aguarde a conclusão.")
    m = PACOTE_RE.match(pacote.filename or "")
    if not m:
        erro(400, "O pacote deve se chamar haras360-X.Y.Z.tar.gz, como gerado na Release do GitHub.")
    versao = m.group(1)
    destino = S.caminho_entrada()
    h = hashlib.sha256()
    tam = 0
    with open(destino / "pacote.tar.gz", "wb") as f:
        while chunk := await pacote.read(1024 * 1024):
            tam += len(chunk)
            if tam > MAX_PACOTE_MB * 1024 * 1024:
                f.close()
                (destino / "pacote.tar.gz").unlink(missing_ok=True)
                erro(413, f"O pacote passa do limite de {MAX_PACOTE_MB} MB.")
            h.update(chunk)
            f.write(chunk)
    sig = await assinatura.read(4096)
    (destino / "pacote.sig").write_bytes(sig)
    calc = h.hexdigest()
    if sha256 and sha256.strip().lower() != calc:
        (destino / "pacote.tar.gz").unlink(missing_ok=True)
        (destino / "pacote.sig").unlink(missing_ok=True)
        erro(400, "O SHA-256 informado não confere com o arquivo enviado. Baixe o pacote de novo.")
    S.gravar_pedido("atualizar", u.email, versao=versao, sha256=calc)
    auditar(db, "atualizacao_solicitada", usuario=u, alvo=f"{versao} (de {VERSAO})", detalhe={"sha256": calc, "bytes": tam}, request=request)
    db.commit()
    return {"resumo": f"Pacote {versao} recebido. O servidor confere a assinatura e aplica a atualização; acompanhe nesta tela.", "sha256": calc}


@r.post("/rollback")
def rollback(request: Request, body: dict = Body(...), u: Usuario = Depends(admin), db=Depends(get_db)):
    if S.ocupado():
        erro(409, "Já existe uma tarefa em andamento. Aguarde a conclusão.")
    versao = _txt(body.get("versao"), 20)
    vs = S.versoes_guardadas()
    if not any(v["versao"] == versao and not v["atual"] for v in vs["versoes"]):
        erro(400, "Escolha uma das versões guardadas, diferente da atual.")
    S.gravar_pedido("rollback", u.email, versao=versao)
    auditar(db, "rollback_solicitado", usuario=u, alvo=f"{vs['emUso']} para {versao}", request=request)
    db.commit()
    return {"resumo": f"Volta para a versão {versao} solicitada."}


@r.post("/backup")
def backup_agora(request: Request, u: Usuario = Depends(admin), db=Depends(get_db)):
    if S.ocupado():
        erro(409, "Já existe uma tarefa em andamento. Aguarde a conclusão.")
    S.gravar_pedido("backup", u.email)
    auditar(db, "backup_solicitado", usuario=u, request=request)
    db.commit()
    return {"resumo": "Backup solicitado. Leva poucos minutos."}


@r.get("/tarefa")
def tarefa(u: Usuario = Depends(admin)):
    return {"atualizacao": S.status_tarefa(), "versoes": S.versoes_guardadas(), "backup": S.ultimo_backup(), "versao": VERSAO}
