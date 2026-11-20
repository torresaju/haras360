"""Assina pacotes de atualização do Haras360 (Windows, macOS ou Linux).

Preparação, uma única vez:
    pip install cryptography
    python assinar-pacote.py gerar-chaves
        Cria a chave privada, protegida por senha, em %USERPROFILE%\\.haras360\\chave-privada.pem
        e grava chave-publica.pem na pasta atual. A chave pública vai para o servidor;
        a privada nunca sai da sua máquina.

A cada versão:
    python assinar-pacote.py haras360-1.0.1.tar.gz
        Pede a senha da chave e grava haras360-1.0.1.tar.gz.sig ao lado do pacote.

    python assinar-pacote.py conferir haras360-1.0.1.tar.gz chave-publica.pem
        Confere uma assinatura (o servidor faz a mesma conferência antes de atualizar).

Para automação (testes), a senha pode vir da variável HARAS360_SENHA_CHAVE e o local
da chave de HARAS360_CHAVE_PRIVADA.
"""
import base64
import getpass
import hashlib
import json
import os
import re
import sys
from pathlib import Path

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
except ImportError:
    sys.exit("Instale a biblioteca antes: pip install cryptography")

NOME = re.compile(r"^haras360-\d+\.\d+\.\d+\.tar\.gz$")
CHAVE = Path(os.environ.get("HARAS360_CHAVE_PRIVADA", Path.home() / ".haras360" / "chave-privada.pem"))


def senha(confirmar=False):
    s = os.environ.get("HARAS360_SENHA_CHAVE")
    if s:
        return s.encode()
    while True:
        s1 = getpass.getpass("Senha da chave de assinatura: ")
        if not confirmar:
            return s1.encode()
        if len(s1) < 12:
            print("  Use pelo menos 12 caracteres.")
            continue
        if s1 != getpass.getpass("Repita a senha: "):
            print("  As senhas não conferem.")
            continue
        return s1.encode()


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def gerar_chaves():
    if CHAVE.exists():
        sys.exit(f"Já existe uma chave em {CHAVE}. Apague-a manualmente se quiser criar outra (e troque a chave pública no servidor).")
    s = senha(confirmar=True)
    priv = Ed25519PrivateKey.generate()
    CHAVE.parent.mkdir(parents=True, exist_ok=True)
    CHAVE.write_bytes(priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(s)))
    try:
        os.chmod(CHAVE, 0o600)
    except OSError:
        pass
    pub = priv.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    Path("chave-publica.pem").write_bytes(pub)
    print(f"Chave privada: {CHAVE}  (guarde uma cópia em local seguro e não perca a senha)")
    print("Chave pública: chave-publica.pem  (envie para o servidor ou para o repositório em deploy/chave-publica.pem)\n")
    print(pub.decode())


def assinar(pacote):
    p = Path(pacote)
    if not p.is_file():
        sys.exit(f"Arquivo não encontrado: {pacote}")
    if not NOME.match(p.name):
        sys.exit("O pacote precisa se chamar haras360-X.Y.Z.tar.gz, como baixado da Release.")
    if not CHAVE.exists():
        sys.exit(f"Chave não encontrada em {CHAVE}. Rode primeiro: python assinar-pacote.py gerar-chaves")
    try:
        priv = serialization.load_pem_private_key(CHAVE.read_bytes(), password=senha())
    except (ValueError, TypeError):
        sys.exit("Senha da chave incorreta.")
    h = sha256(p)
    sig = priv.sign(f"haras360-pacote|{p.name}|{h}".encode())
    saida = p.with_name(p.name + ".sig")
    saida.write_text(json.dumps({"arquivo": p.name, "sha256": h, "assinatura": base64.b64encode(sig).decode()}, indent=1), encoding="utf-8")
    print(f"Assinatura gravada em {saida}")
    print(f"SHA-256 do pacote: {h}")


def conferir(pacote, chave_publica):
    p = Path(pacote)
    sig = json.loads(p.with_name(p.name + ".sig").read_text(encoding="utf-8"))
    h = sha256(p)
    if sig.get("arquivo") != p.name or sig.get("sha256") != h:
        sys.exit("A assinatura não corresponde a este arquivo.")
    pub = serialization.load_pem_public_key(Path(chave_publica).read_bytes())
    try:
        pub.verify(base64.b64decode(sig["assinatura"]), f"haras360-pacote|{p.name}|{h}".encode())
    except InvalidSignature:
        sys.exit("Assinatura inválida para esta chave pública.")
    print("Assinatura válida.")


def main():
    a = sys.argv[1:]
    if a == ["gerar-chaves"]:
        gerar_chaves()
    elif len(a) == 3 and a[0] == "conferir":
        conferir(a[1], a[2])
    elif len(a) == 1 and not a[0].startswith("-"):
        assinar(a[0])
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
