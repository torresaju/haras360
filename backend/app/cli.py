"""Comandos de administração do Haras360.

Uso (dentro do container):
  python -m app.cli criar-haras
  python -m app.cli redefinir-senha --email gestor@exemplo.com
  python -m app.cli listar
"""
import argparse
import getpass
import re
import sys

from sqlalchemy import select

from . import regras as R
from .db import Haras, Protocolo, SessionLocal, Usuario, iniciar_banco
from .main import hash_senha


def pedir(rotulo, valor=None, obrigatorio=True):
    if valor:
        return valor
    while True:
        v = input(f"{rotulo}: ").strip()
        if v or not obrigatorio:
            return v
        print("  Campo obrigatório.")


def pedir_senha(valor=None):
    if valor:
        if len(valor) < 8:
            sys.exit("A senha precisa ter pelo menos 8 caracteres.")
        return valor
    while True:
        s1 = getpass.getpass("Senha do gestor (mín. 8 caracteres): ")
        if len(s1) < 8:
            print("  Senha curta demais.")
            continue
        if s1 != getpass.getpass("Repita a senha: "):
            print("  As senhas não conferem.")
            continue
        return s1


def criar_haras(a):
    iniciar_banco()
    db = SessionLocal()
    nome = pedir("Nome do haras", a.haras)
    gestor = pedir("Nome do gestor", a.nome)
    email = pedir("E-mail de login do gestor", a.email).lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        sys.exit("E-mail inválido.")
    if db.scalar(select(Usuario).where(Usuario.email == email)):
        sys.exit("Já existe um usuário com esse e-mail.")
    senha = pedir_senha(a.senha)
    municipio = a.municipio if a.municipio is not None else pedir("Município/UF (opcional)", obrigatorio=False)
    h = Haras(nome=nome, proprietario=gestor, municipio=municipio, notif_prefs=R.notif_prefs_padrao())
    db.add(h)
    db.flush()
    for p in R.protocolos_padrao():
        db.add(Protocolo(haras_id=h.id, pid=p["id"], dados=p))
    db.add(Usuario(haras_id=h.id, nome=gestor, email=email, senha_hash=hash_senha(senha), perfil="gestor", ativo=True))
    db.commit()
    print(f"\nHaras '{nome}' criado (id {h.id}). Gestor: {email}")


def redefinir(a):
    iniciar_banco()
    db = SessionLocal()
    email = pedir("E-mail do usuário", a.email).lower()
    u = db.scalar(select(Usuario).where(Usuario.email == email))
    if not u:
        sys.exit("Usuário não encontrado.")
    u.senha_hash = hash_senha(pedir_senha(a.senha))
    u.ativo = True
    db.commit()
    print(f"Senha de {u.nome} redefinida.")


def listar(_a):
    iniciar_banco()
    db = SessionLocal()
    for h in db.scalars(select(Haras)):
        print(f"[{h.id}] {h.nome}")
        for u in db.scalars(select(Usuario).where(Usuario.haras_id == h.id)):
            print(f"    {u.perfil:9} {u.email}  {'ativo' if u.ativo else 'desativado'}")


def main():
    ap = argparse.ArgumentParser(prog="haras360")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("criar-haras")
    c.add_argument("--haras"); c.add_argument("--nome"); c.add_argument("--email"); c.add_argument("--senha"); c.add_argument("--municipio")
    r = sub.add_parser("redefinir-senha")
    r.add_argument("--email"); r.add_argument("--senha")
    sub.add_parser("listar")
    a = ap.parse_args()
    {"criar-haras": criar_haras, "redefinir-senha": redefinir, "listar": listar}[a.cmd](a)


if __name__ == "__main__":
    main()
