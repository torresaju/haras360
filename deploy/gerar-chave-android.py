"""Cria a chave Android que assina o APK do Haras360 (rode uma única vez, no seu computador).

    pip install cryptography        (já instalado se você usa o Journey)
    python gerar-chave-android.py

Grava em %USERPROFILE%\\journey-chaves\\haras360\\:
    haras360-android.p12    a chave (guarde para sempre: sem ela o app instalado não aceita atualizações)
    segredos-github.txt     os 4 valores para cadastrar no GitHub (Settings > Secrets and variables > Actions)

A chave não sai do seu computador. O GitHub recebe apenas a cópia que você cadastrar como segredo.
"""
import base64
import datetime
import hashlib
import secrets
import sys
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID
except ImportError:
    sys.exit("Instale a biblioteca antes: pip install cryptography")

PASTA = Path.home() / "journey-chaves" / "haras360"
ALIAS = "haras360"


def main():
    p12 = PASTA / "haras360-android.p12"
    txt = PASTA / "segredos-github.txt"
    if p12.exists():
        sys.exit(f"Já existe uma chave em {p12}. Não vou sobrescrever: o app instalado depende dela.")
    PASTA.mkdir(parents=True, exist_ok=True)
    senha = secrets.token_urlsafe(24)
    chave = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Haras360"), x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Haras360"),
                      x509.NameAttribute(NameOID.COUNTRY_NAME, "BR")])
    agora = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(nome).issuer_name(nome).public_key(chave.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(agora - datetime.timedelta(days=1))
            .not_valid_after(agora + datetime.timedelta(days=365 * 30)).sign(chave, hashes.SHA256()))
    cifra = (serialization.PrivateFormat.PKCS12.encryption_builder().kdf_rounds(100000)
             .key_cert_algorithm(pkcs12.PBES.PBESv2SHA256AndAES256CBC).hmac_hash(hashes.SHA256()).build(senha.encode()))
    dados = pkcs12.serialize_key_and_certificates(ALIAS.encode(), chave, cert, None, cifra)
    p12.write_bytes(dados)
    impressao = hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest().upper()
    impressao = ":".join(impressao[i:i + 2] for i in range(0, 64, 2))
    txt.write_text(
        "Cadastre estes 4 segredos no GitHub: repositório torresaju/haras360 > Settings > Secrets and variables > Actions > New repository secret\n"
        "Depois de cadastrar, guarde a senha num cofre de senhas e apague este arquivo.\n\n"
        f"ANDROID_KEYSTORE_BASE64\n{base64.b64encode(dados).decode()}\n\n"
        f"ANDROID_KEYSTORE_SENHA\n{senha}\n\n"
        f"ANDROID_CHAVE_ALIAS\n{ALIAS}\n\n"
        f"ANDROID_CHAVE_SENHA\n{senha}\n\n"
        f"Impressão digital SHA-256 do certificado (confere com a mostrada no build):\n{impressao}\n",
        encoding="utf-8")
    print(f"Chave Android criada: {p12}")
    print(f"Segredos para o GitHub: {txt}")
    print(f"Impressão digital SHA-256: {impressao}")
    print("\nGuarde haras360-android.p12 e a senha para sempre (a pasta journey-chaves-backup é um bom lugar).")


if __name__ == "__main__":
    main()
