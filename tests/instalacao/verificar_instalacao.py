"""Teste de ponta a ponta da instalação em uma máquina Ubuntu limpa (roda no GitHub Actions).

Pré-requisito: deploy/instalar-servidor.sh já executado com o administrador
admin@teste.local / senha-de-teste-123 e a chave pública de teste instalada.

Verifica: acesso pelo Caddy, cabeçalhos de segurança, 2FA do administrador, criação de haras,
atualização assinada, volta automática quando a nova versão não inicia, recusa de pacote
adulterado, volta manual de versão e backup.

Uso: python tests/instalacao/verificar_instalacao.py <pasta-com-chave-privada> <senha-da-chave>
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pyotp

BASE = "http://127.0.0.1:8090"
H = {"X-Haras360": "1"}
RAIZ = Path(__file__).resolve().parents[2]
DIST = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "dist-teste"
ENV_ASS = dict(os.environ, HARAS360_CHAVE_PRIVADA=sys.argv[1], HARAS360_SENHA_CHAVE=sys.argv[2])


def passo(msg):
    print(f"\n=== {msg}", flush=True)


def sh(*cmd, env=None, cwd=RAIZ):
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout, r.stderr)
        raise SystemExit(f"comando falhou: {' '.join(cmd)}")
    return r.stdout


def pacote(versao, quebrar=False):
    """Cria um commit temporário com a versão pedida e gera o pacote assinado."""
    (RAIZ / "VERSION").write_text(versao + "\n")
    alvo = RAIZ / "backend/app/main.py"
    original = alvo.read_text()
    if quebrar:
        alvo.write_text(original + "\nraise RuntimeError('versão quebrada de propósito para testar a volta automática')\n")
    sh("git", "add", "-A")
    sh("git", "-c", "user.name=teste", "-c", "user.email=teste@local", "commit", "-q", "-m", f"teste {versao}")
    sh("bash", "deploy/gerar-pacote.sh", "HEAD", str(DIST))
    alvo.write_text(original)
    arq = DIST / f"haras360-{versao}.tar.gz"
    sh(sys.executable, "deploy/assinar-pacote.py", str(arq), env=ENV_ASS)
    return arq


def enviar(c, arq, sig=None):
    sig = sig or Path(str(arq) + ".sig")
    with open(arq, "rb") as fp, open(sig, "rb") as fs:
        r = c.post(f"{BASE}/api/admin/atualizacao", files={"pacote": (arq.name, fp), "assinatura": (sig.name, fs)}, headers=H, timeout=120)
    assert r.status_code == 200, r.text
    return r.json()


def inicio_atual(c):
    try:
        return c.get(f"{BASE}/api/admin/tarefa", timeout=10).json()["atualizacao"].get("inicio")
    except (httpx.HTTPError, ValueError, KeyError):
        return None


def esperar(c, acao, antes, limite=600):
    """Espera a tarefa pedida terminar (status com início diferente do anterior ao pedido)."""
    t0 = time.time()
    while time.time() - t0 < limite:
        try:
            t = c.get(f"{BASE}/api/admin/tarefa", timeout=10).json()
            st = t["atualizacao"]
            if (not st.get("pendente") and st.get("inicio") != antes and st.get("acao") == acao
                    and st.get("estado") in ("concluido", "falhou")):
                return t
        except (httpx.HTTPError, ValueError, KeyError):
            pass  # a aplicação reinicia durante a atualização
        time.sleep(3)
    raise SystemExit(f"tempo esgotado esperando {acao}")


def entrar_admin():
    c = httpx.Client()
    r = c.post(f"{BASE}/api/login", json={"email": "admin@teste.local", "senha": "senha-de-teste-123"}, headers=H)
    assert r.status_code == 200, r.text
    if r.json()["etapa"] == "cadastro2fa":
        seg = c.get(f"{BASE}/api/2fa/cadastro").json()["segredo"]
        entrar_admin.segredo = seg
        r = c.post(f"{BASE}/api/2fa/confirmar", json={"codigo": pyotp.TOTP(seg).now()}, headers=H)
    else:
        r = c.post(f"{BASE}/api/2fa/verificar", json={"codigo": pyotp.TOTP(entrar_admin.segredo).now()}, headers=H)
    assert r.status_code == 200, r.text
    return c


def versao_servidor():
    return httpx.get(f"{BASE}/api/saude", timeout=10).json()["versao"]


def main():
    inicial = (RAIZ / "VERSION").read_text().strip()
    maj, men, pat = map(int, inicial.split("."))
    v1, v2, v3 = (f"{maj}.{men}.{pat + i}" for i in (1, 2, 3))

    passo("Acesso pelo Caddy e cabeçalhos de segurança")
    r = httpx.get(f"{BASE}/entrar")
    assert r.status_code == 200 and "frame-ancestors 'none'" in r.headers["content-security-policy"], r.headers
    assert "server" not in {k.lower() for k in r.headers}, "o servidor não deve se identificar"
    assert versao_servidor() == inicial

    passo("Login do administrador com cadastro do 2FA")
    c = entrar_admin()
    p = c.get(f"{BASE}/api/admin/painel").json()
    assert p["versao"] == inicial and p["versoes"]["emUso"] == inicial, p["versoes"]

    passo("Criação de haras e login do gestor")
    r = c.post(f"{BASE}/api/admin/haras", json={"nome": "Haras CI", "gestorNome": "Gestor CI", "gestorEmail": "gestor@ci.local", "gestorSenha": "senha-gestor-123"}, headers=H)
    assert r.status_code == 200, r.text
    g = httpx.Client()
    assert g.post(f"{BASE}/api/login", json={"email": "gestor@ci.local", "senha": "senha-gestor-123"}, headers=H).json()["etapa"] == "cadastro2fa"

    passo(f"Atualização assinada para {v1}")
    arq1 = pacote(v1)
    antes = inicio_atual(c)
    enviar(c, arq1)
    t = esperar(c, "atualizar", antes)
    assert t["atualizacao"]["estado"] == "concluido", t
    assert versao_servidor() == v1
    c = entrar_admin()

    passo(f"Versão {v2} que não inicia: volta automática para {v1}")
    arq2 = pacote(v2, quebrar=True)
    antes = inicio_atual(c)
    enviar(c, arq2)
    t = esperar(c, "atualizar", antes)
    assert t["atualizacao"]["estado"] == "falhou" and "voltou" in t["atualizacao"]["mensagem"], t
    assert versao_servidor() == v1
    c = entrar_admin()

    passo("Pacote adulterado é recusado")
    arq = pacote(v3)
    dados = bytearray(arq.read_bytes())
    dados[-100] ^= 0xFF
    adult = DIST / "adulterado" / arq.name
    adult.parent.mkdir(exist_ok=True)
    adult.write_bytes(dados)
    antes = inicio_atual(c)
    enviar(c, adult, Path(str(arq) + ".sig"))
    t = esperar(c, "atualizar", antes)
    assert t["atualizacao"]["estado"] == "falhou" and "recusado" in t["atualizacao"]["mensagem"], t
    assert versao_servidor() == v1

    passo(f"Volta manual para {inicial}")
    antes = inicio_atual(c)
    r = c.post(f"{BASE}/api/admin/rollback", json={"versao": inicial}, headers=H)
    assert r.status_code == 200, r.text
    t = esperar(c, "rollback", antes)
    assert t["atualizacao"]["estado"] == "concluido", t
    assert versao_servidor() == inicial
    c = entrar_admin()

    passo("Backup pela tela de administração")
    antes = inicio_atual(c)
    assert c.post(f"{BASE}/api/admin/backup", headers=H).status_code == 200
    t = esperar(c, "backup", antes)
    assert t["atualizacao"]["estado"] == "concluido" and t["backup"] and t["backup"]["arquivo"].startswith("haras360-backup-"), t

    passo("Auditoria registrou o ciclo")
    acoes = {x["acao"] for x in c.get(f"{BASE}/api/admin/auditoria?limite=500").json()}
    faltando = {"atualizacao_concluida", "atualizacao_falhou", "rollback_concluido", "backup_concluido", "haras_criado", "2fa_cadastro"} - acoes
    assert not faltando, f"faltam na auditoria: {faltando}"
    print("\nInstalação, atualização, volta automática, recusa de pacote adulterado, volta manual e backup: tudo certo.")


if __name__ == "__main__":
    main()
