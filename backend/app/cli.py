"""Comandos de administração do Haras360 (rodam na VPS como usuário haras360).

  haras360 migrar
  haras360 criar-admin
  haras360 criar-haras
  haras360 listar
  haras360 redefinir-senha --email x@y
  haras360 redefinir-2fa --email x@y
  haras360 demonstracao
  haras360 auditar --acao atualizacao_concluida --alvo "1.0.0 para 1.0.1"   (usado pelos scripts do servidor)
"""
import argparse
import getpass
import re
import sys

from sqlalchemy import select

from .db import Haras, SessionLocal, Usuario
from .migracoes import migrar
from .seguranca import auditar, hash_senha, revogar_sessoes

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def pedir(rotulo, valor=None, obrigatorio=True):
    if valor is not None:
        return valor
    while True:
        v = input(f"{rotulo}: ").strip()
        if v or not obrigatorio:
            return v
        print("  Campo obrigatório.")


def pedir_email(valor=None):
    e = pedir("E-mail de login", valor).lower()
    if not EMAIL.match(e):
        sys.exit("E-mail inválido.")
    return e


def pedir_senha(valor=None, rotulo="Senha"):
    if valor:
        if len(valor) < 8:
            sys.exit("A senha precisa ter pelo menos 8 caracteres.")
        return valor
    while True:
        s1 = getpass.getpass(f"{rotulo} (mín. 8 caracteres): ")
        if len(s1) < 8:
            print("  Senha curta demais.")
            continue
        if s1 != getpass.getpass("Repita a senha: "):
            print("  As senhas não conferem.")
            continue
        return s1


def c_migrar(_a):
    migrar()


def c_criar_admin(a):
    migrar(silencioso=True)
    with SessionLocal() as db:
        nome = pedir("Nome do administrador", a.nome)
        email = pedir_email(a.email)
        if db.scalar(select(Usuario).where(Usuario.email == email)):
            sys.exit("Já existe um usuário com esse e-mail.")
        u = Usuario(haras_id=None, nome=nome, email=email, senha_hash=hash_senha(pedir_senha(a.senha)), perfil="admin", ativo=True)
        db.add(u)
        db.flush()
        auditar(db, "usuario_criado", nome="linha de comando", alvo=f"{nome} <{email}> (admin)")
        db.commit()
        print(f"Administrador {email} criado. No primeiro login ele cadastra o 2FA.")


def c_criar_haras(a):
    from fastapi import HTTPException

    from .rotas_admin import criar_haras_com_gestor
    migrar(silencioso=True)
    with SessionLocal() as db:
        try:
            h, g = criar_haras_com_gestor(db, pedir("Nome do haras", a.haras), pedir("Município/UF", a.municipio, False), a.plano,
                                          pedir("Nome do gestor", a.nome), pedir_email(a.email), pedir_senha(a.senha, "Senha do gestor"))
        except HTTPException as e:
            sys.exit(e.detail)
        auditar(db, "haras_criado", nome="linha de comando", haras_id=h.id, alvo=f"{h.nome} · gestor {g.email}")
        db.commit()
        print(f"Haras '{h.nome}' criado (id {h.id}). Gestor: {g.email}")


def c_listar(_a):
    migrar(silencioso=True)
    with SessionLocal() as db:
        for u in db.scalars(select(Usuario).where(Usuario.haras_id.is_(None))):
            print(f"[plataforma] admin     {u.email}  {'ativo' if u.ativo else 'desativado'}  2FA {'sim' if u.totp_ativo else 'pendente'}")
        for h in db.scalars(select(Haras).order_by(Haras.id)):
            print(f"[{h.id}] {h.nome}  plano {h.plano}  {'ativo' if h.ativo else 'desativado'}")
            for u in db.scalars(select(Usuario).where(Usuario.haras_id == h.id)):
                f2 = "" if u.perfil == "operador" else f"  2FA {'sim' if u.totp_ativo else 'pendente'}"
                print(f"    {u.perfil:9} {u.email}  {'ativo' if u.ativo else 'desativado'}{f2}")


def _usuario(db, email):
    u = db.scalar(select(Usuario).where(Usuario.email == email.lower()))
    if not u:
        sys.exit("Usuário não encontrado.")
    return u


def c_redefinir_senha(a):
    with SessionLocal() as db:
        u = _usuario(db, pedir_email(a.email))
        u.senha_hash = hash_senha(pedir_senha(a.senha, "Nova senha"))
        u.ativo = True
        revogar_sessoes(db, u.id)
        auditar(db, "senha_redefinida", nome="linha de comando", haras_id=u.haras_id, alvo=f"{u.nome} <{u.email}>")
        db.commit()
        print(f"Senha de {u.nome} redefinida.")


def c_redefinir_2fa(a):
    with SessionLocal() as db:
        u = _usuario(db, pedir_email(a.email))
        u.totp_ativo, u.totp_segredo, u.recuperacao = False, None, None
        revogar_sessoes(db, u.id)
        auditar(db, "2fa_redefinido", nome="linha de comando", haras_id=u.haras_id, alvo=f"{u.nome} <{u.email}>")
        db.commit()
        print(f"2FA de {u.nome} redefinido. No próximo login ele cadastra o aplicativo de novo.")


def c_demonstracao(a):
    from . import demonstracao
    migrar(silencioso=True)
    with SessionLocal() as db:
        h = demonstracao.criar(db, a.gestor or "gestor@demonstracao.local", a.senha or "demonstracao123",
                               a.caseiro or "caseiro@demonstracao.local", a.senha or "demonstracao123")
        print(f"'{h.nome}' criado com plantel fictício.")


def c_vincular_celular(a):
    from .rotas_app import VALIDADE_VINCULO_MIN, link_vinculo, novo_vinculo
    with SessionLocal() as db:
        u = _usuario(db, pedir_email(a.email))
        if u.perfil != "operador" or not u.ativo:
            sys.exit("O app Android é de uso do caseiro, e o acesso precisa estar ativo.")
        codigo, _ = novo_vinculo(db, u)
        auditar(db, "app_vinculo_gerado", nome="linha de comando", haras_id=u.haras_id, alvo=u.nome)
        db.commit()
    print(f"Código para {u.nome} (vale {VALIDADE_VINCULO_MIN} minutos, uso único): {codigo}")
    if a.servidor:
        print(f"Link do QR Code: {link_vinculo(a.servidor.rstrip('/'), codigo)}")


def c_auditar(a):
    with SessionLocal() as db:
        auditar(db, a.acao, nome=a.quem or "servidor", alvo=a.alvo or "", resultado=a.resultado)
        db.commit()


def main():
    ap = argparse.ArgumentParser(prog="haras360", description="Administração do Haras360")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrar", help="aplica as migrações pendentes do banco")
    c = sub.add_parser("criar-admin", help="cria um administrador da plataforma")
    c.add_argument("--nome"); c.add_argument("--email"); c.add_argument("--senha")
    c = sub.add_parser("criar-haras", help="cria um haras e o gestor")
    c.add_argument("--haras"); c.add_argument("--municipio"); c.add_argument("--plano"); c.add_argument("--nome"); c.add_argument("--email"); c.add_argument("--senha")
    sub.add_parser("listar", help="lista haras e usuários")
    c = sub.add_parser("redefinir-senha"); c.add_argument("--email"); c.add_argument("--senha")
    c = sub.add_parser("redefinir-2fa"); c.add_argument("--email")
    c = sub.add_parser("demonstracao", help="cria o Haras Demonstração com plantel fictício")
    c.add_argument("--gestor"); c.add_argument("--caseiro"); c.add_argument("--senha")
    c = sub.add_parser("vincular-celular", help="gera o código de vínculo do app Android de um caseiro")
    c.add_argument("--email"); c.add_argument("--servidor", help="endereço do servidor, para montar o link do QR Code")
    c = sub.add_parser("auditar", help="registra um evento na auditoria (uso dos scripts)")
    c.add_argument("--acao", required=True); c.add_argument("--alvo"); c.add_argument("--quem"); c.add_argument("--resultado", default="ok")
    a = ap.parse_args()
    {"migrar": c_migrar, "criar-admin": c_criar_admin, "criar-haras": c_criar_haras, "listar": c_listar, "redefinir-senha": c_redefinir_senha,
     "redefinir-2fa": c_redefinir_2fa, "demonstracao": c_demonstracao, "vincular-celular": c_vincular_celular, "auditar": c_auditar}[a.cmd](a)


if __name__ == "__main__":
    main()
