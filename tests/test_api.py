"""Testes da API: 2FA, sessões, perfis, planos, auditoria, parametrizações, importação, registros e administração."""
import base64
import json

import pyotp
from fastapi.testclient import TestClient

from app import regras as R
from app.config import FILA_DIR
from app.main import app

H = {"X-Haras360": "1", "X-Portal": "gestor"}
HC = {"X-Haras360": "1", "X-Portal": "campo"}
PNG = "data:image/png;base64," + base64.b64encode(bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201a1b6d5e20000000049454e44ae426082")).decode()
PLANTEL = [
    {"nome": "AURORA DO VALE", "livro": "MM6 - DEFINITIVO FECHADO FÊMEA", "registro": "0900101", "sexo": "F", "bloqueado": False, "vivo": True,
     "dna": "DNA - VP", "nascimento": "2017-01-13", "chip": "900000000000101"},
    {"nome": "DOURADO DA CAATINGA", "livro": "", "registro": "", "sexo": "M", "bloqueado": False, "vivo": True, "dna": "Sem exame",
     "nascimento": "2026-01-15", "chip": "900000000000104"},
]
SEGREDOS = {}


def entrar(email, senha, hdr=H):
    """Login completo, cadastrando o 2FA no primeiro acesso quando o perfil exige."""
    c = TestClient(app)
    r = c.post("/api/login", json={"email": email, "senha": senha}, headers=hdr)
    assert r.status_code == 200, r.text
    etapa = r.json()["etapa"]
    if etapa == "cadastro2fa":
        seg = c.get("/api/2fa/cadastro").json()["segredo"]
        SEGREDOS[email] = seg
        r = c.post("/api/2fa/confirmar", json={"codigo": pyotp.TOTP(seg).now()}, headers=H)
        assert r.status_code == 200, r.text
        assert len(r.json()["codigos"]) == 8
    elif etapa == "2fa":
        r = c.post("/api/2fa/verificar", json={"codigo": pyotp.TOTP(SEGREDOS[email]).now()}, headers=H)
        assert r.status_code == 200, r.text
    return c


# ---------------- login, 2FA e sessões ----------------
def test_login_errado_e_protecoes(base):
    c = TestClient(app)
    assert c.post("/api/login", json={"email": "gestor@teste.com", "senha": "x"}, headers=H).status_code == 401
    assert c.post("/api/login", json={}).status_code == 403
    assert c.get("/api/estado").status_code == 401


def test_gestor_cadastra_2fa_no_primeiro_acesso(base):
    c = TestClient(app)
    r = c.post("/api/login", json={"email": "gestor@teste.com", "senha": "senha1234"}, headers=H)
    assert r.json()["etapa"] == "cadastro2fa"
    assert c.get("/api/estado").status_code == 401  # sem 2FA, nada liberado
    cad = c.get("/api/2fa/cadastro").json()
    assert cad["qr"].startswith("<svg") and "otpauth://" in cad["uri"]
    assert c.post("/api/2fa/confirmar", json={"codigo": "000000"}, headers=H).status_code == 400
    r = c.post("/api/2fa/confirmar", json={"codigo": pyotp.TOTP(cad["segredo"]).now()}, headers=H)
    assert r.status_code == 200 and r.json()["destino"] == "/gestor"
    SEGREDOS["gestor@teste.com"] = cad["segredo"]
    assert c.get("/api/estado").status_code == 200


def test_segundo_login_pede_codigo_e_aceita_recuperacao(base):
    c = TestClient(app)
    assert c.post("/api/login", json={"email": "gestor@teste.com", "senha": "senha1234"}, headers=H).json()["etapa"] == "2fa"
    assert c.post("/api/2fa/verificar", json={"codigo": "123456"}, headers=H).status_code == 400
    assert c.post("/api/2fa/verificar", json={"codigo": pyotp.TOTP(SEGREDOS["gestor@teste.com"]).now()}, headers=H).status_code == 200
    # gera códigos de recuperação novos e usa um deles
    codigos = c.post("/api/me/codigos-recuperacao", json={"senha": "senha1234"}, headers=H).json()["codigos"]
    c2 = TestClient(app)
    c2.post("/api/login", json={"email": "gestor@teste.com", "senha": "senha1234"}, headers=H)
    r = c2.post("/api/2fa/verificar", json={"codigo": codigos[0]}, headers=H)
    assert r.status_code == 200 and r.json()["restantes"] == 7
    c3 = TestClient(app)
    c3.post("/api/login", json={"email": "gestor@teste.com", "senha": "senha1234"}, headers=H)
    assert c3.post("/api/2fa/verificar", json={"codigo": codigos[0]}, headers=H).status_code == 400  # código usado não vale de novo


def test_caseiro_entra_sem_2fa(base):
    c = TestClient(app)
    r = c.post("/api/login", json={"email": "caseiro@teste.com", "senha": "campo1234"}, headers=HC)
    assert r.json()["etapa"] == "ok" and r.json()["destino"] == "/campo"
    assert c.get("/api/estado").status_code == 200


def test_login_do_app_devolve_token(base):
    c = TestClient(app)
    r = c.post("/api/login", json={"email": "caseiro@teste.com", "senha": "campo1234", "app": True}, headers=HC)
    tok = r.json()["token"]
    assert "h360" not in r.cookies
    assert TestClient(app).get("/api/estado", headers={"Authorization": f"Bearer {tok}"}).status_code == 200
    assert c.post("/api/login", json={"email": "gestor@teste.com", "senha": "senha1234", "app": True}, headers=H).status_code == 403


def test_sessoes_listar_e_encerrar(base):
    g = entrar("gestor@teste.com", "senha1234")
    k = entrar("caseiro@teste.com", "campo1234", HC)
    sess = g.get("/api/sessoes").json()
    alvo = next(s for s in sess if s["usuario"] == "Caseiro Teste")
    assert g.delete(f"/api/sessoes/{alvo['id']}", headers=H).status_code == 200
    restantes = [s for s in g.get("/api/sessoes").json() if s["usuario"] == "Caseiro Teste"]
    assert len(restantes) < len([s for s in sess if s["usuario"] == "Caseiro Teste"])
    # o caseiro não vê nem encerra sessões do gestor
    k2 = entrar("caseiro@teste.com", "campo1234", HC)
    assert all(s["usuario"] == "Caseiro Teste" for s in k2.get("/api/sessoes").json())
    gid = next(s["id"] for s in sess if s["usuario"] == "Gestor Teste")
    assert k2.delete(f"/api/sessoes/{gid}", headers=H).status_code == 404
    del k


def test_troca_de_senha_encerra_outras_sessoes(base):
    antiga = entrar("caseiro@teste.com", "campo1234", HC)
    nova = entrar("caseiro@teste.com", "campo1234", HC)
    assert nova.post("/api/me/senha", json={"atual": "campo1234", "nova": "outra1234"}, headers=H).status_code == 200
    assert nova.get("/api/me").status_code == 200
    assert antiga.get("/api/me").status_code == 401
    assert nova.post("/api/me/senha", json={"atual": "outra1234", "nova": "campo1234"}, headers=H).status_code == 200


def test_limite_de_tentativas(base):
    c = TestClient(app)
    for _ in range(8):
        c.post("/api/login", json={"email": "ninguem@teste.com", "senha": "x"}, headers=H)
    assert c.post("/api/login", json={"email": "ninguem@teste.com", "senha": "x"}, headers=H).status_code == 429


# ---------------- plantel e registros ----------------
def test_importacao_e_reimportacao(base):
    c = entrar("gestor@teste.com", "senha1234")
    r = c.post("/api/importacao", json={"arquivo": "Plantel.pdf", "associado": "ASSOCIADO", "impresso": "2026-09-02", "animais": PLANTEL}, headers=H)
    assert r.json()["novos"] == 2
    r = c.post("/api/importacao", json={"animais": PLANTEL}, headers=H)
    assert r.json()["novos"] == 0 and r.json()["atualizados"] == 2
    e = c.get("/api/estado").json()
    assert len(e["animais"]) == 2
    assert {t["titulo"] for t in e["tarefas"] if t.get("doc")} == {"Registro ABCCMM pendente", "Exame de DNA pendente"}
    assert e["plano"]["nome"] == "Padrão" and all(e["plano"]["modulos"].values())


def test_caseiro_registra_com_foto_e_gestor_ve(base):
    g = entrar("gestor@teste.com", "senha1234")
    animal = g.get("/api/estado").json()["animais"][0]
    k = entrar("caseiro@teste.com", "campo1234", HC)
    r = k.post("/api/registros", json={"animalId": animal["id"], "data": R.iso(R.hoje()), "tipo": "ocorrencia", "titulo": "Mancando", "gravidade": "Leve",
                                       "fotos": [PNG]}, headers=HC)
    assert r.status_code == 200, r.text
    reg = next(x for x in g.get("/api/estado").json()["registros"] if x["id"] == r.json()["id"])
    assert reg["origem"] == "Portal Cliente" and reg["autor"] == "Caseiro Teste"
    assert g.get(reg["fotos"][0]).status_code == 200
    assert TestClient(app).get(reg["fotos"][0]).status_code == 401
    assert entrar("outro@teste.com", "senha1234").get(reg["fotos"][0]).status_code == 404  # outro haras não vê


def test_registro_com_id_do_aparelho_nao_duplica(base):
    k = entrar("caseiro@teste.com", "campo1234", HC)
    a = k.get("/api/estado").json()["animais"][0]
    corpo = {"id": "0b9d4c1e-1111-4a2b-9c3d-abcdefabcdef", "animalId": a["id"], "data": R.iso(R.hoje()), "tipo": "vermifugacao", "produto": "Ivermectina"}
    assert k.post("/api/registros", json=corpo, headers=HC).json().get("duplicado") is None
    assert k.post("/api/registros", json=corpo, headers=HC).json()["duplicado"] is True
    assert sum(1 for x in k.get("/api/estado").json()["registros"] if x["id"] == corpo["id"]) == 1


def test_perfil_caseiro_restrito(base):
    k = entrar("caseiro@teste.com", "campo1234", HC)
    assert k.post("/api/animais", json={"nome": "X"}, headers=H).status_code == 403
    assert k.put("/api/protocolos", json=[], headers=H).status_code == 403
    assert k.get("/api/auditoria").status_code == 403
    assert k.get("/api/admin/painel").status_code == 403
    assert k.get("/api/estado").json()["usuarios"] == []


def test_validacoes_de_registro(base):
    g = entrar("gestor@teste.com", "senha1234")
    a = g.get("/api/estado").json()["animais"][0]
    futuro = R.iso(R.add_dias(R.hoje(), 3))
    assert g.post("/api/registros", json={"animalId": a["id"], "data": futuro, "tipo": "vermifugacao"}, headers=H).status_code == 400
    assert g.post("/api/registros", json={"animalId": a["id"], "data": R.iso(R.hoje()), "tipo": "vacina"}, headers=H).status_code == 400
    assert g.post("/api/registros", json={"animalId": a["id"], "data": R.iso(R.hoje()), "tipo": "ocorrencia", "titulo": "x",
                                          "fotos": ["data:image/png;base64,AAAA"]}, headers=H).status_code == 400


def test_exclusao_fica_na_auditoria(base):
    g = entrar("gestor@teste.com", "senha1234")
    a = g.get("/api/estado").json()["animais"][0]
    rid = g.post("/api/registros", json={"animalId": a["id"], "data": R.iso(R.hoje()), "tipo": "ocorrencia", "titulo": "Para excluir"}, headers=H).json()["id"]
    assert g.delete(f"/api/registros/{rid}", headers=H).status_code == 200
    aud = g.get("/api/auditoria?acao=registro_excluido").json()
    assert aud and aud[0]["detalhe"]["dados"]["titulo"] == "Para excluir"


# ---------------- parametrizações e protocolos ----------------
def test_protocolos_e_raiva_auditados(base):
    g = entrar("gestor@teste.com", "senha1234")
    assert g.put("/api/protocolos", json=[{"id": "vermi", "reforcoDias": 60}], headers=H).status_code == 200
    assert next(p for p in g.get("/api/estado").json()["protocolos"] if p["id"] == "vermi")["reforcoDias"] == 60
    assert g.put("/api/protocolos", json=[{"id": "vermi", "reforcoDias": 0}], headers=H).status_code == 400
    assert g.put("/api/haras", json={"raivaSemestral": True}, headers=H).status_code == 200
    assert g.get("/api/estado").json()["haras"]["raivaSemestral"] is True
    acoes = {x["acao"] for x in g.get("/api/auditoria").json()}
    assert {"protocolos_alterados", "parametro_alterado", "importacao", "login"} <= acoes


def test_dias_de_gestacao_parametrizados(base):
    g = entrar("gestor@teste.com", "senha1234")
    e = g.get("/api/estado").json()
    egua = next(a for a in e["animais"] if a["sexo"] == "F")
    cob = R.iso(R.add_dias(R.hoje(), -100))
    g.post("/api/registros", json={"animalId": egua["id"], "data": R.iso(R.add_dias(R.hoje(), -80)), "tipo": "reprodutivo", "evento": "Diagnóstico positivo",
                                   "dataCobertura": cob}, headers=H)
    assert g.get("/api/estado").json()["gestacoes"][egua["id"]]["parto"] == R.iso(R.add_dias(cob, 340))
    assert g.put("/api/haras", json={"gestacaoDias": 330}, headers=H).status_code == 200
    assert g.get("/api/estado").json()["gestacoes"][egua["id"]]["parto"] == R.iso(R.add_dias(cob, 330))
    assert g.put("/api/haras", json={"gestacaoDias": 900}, headers=H).status_code == 400


def test_gestor_nao_ve_auditoria_de_outro_haras(base):
    o = entrar("outro@teste.com", "senha1234")
    assert all(x["harasId"] == base["outro"] for x in o.get("/api/auditoria").json())


# ---------------- planos e módulos ----------------
def test_plano_restringe_modulos_e_limite(base):
    adm = entrar("admin@teste.com", "admin1234")
    planos = {"Padrão": {"limite": 30, "modulos": {"importacao": True, "assistente": True, "caseiro": True}},
              "Básico": {"limite": 2, "modulos": {"importacao": False, "assistente": False, "caseiro": False}}}
    assert adm.put("/api/admin/parametros", json={"planos": planos}, headers=H).status_code == 200
    # haras com 2 animais cabe no Básico (limite 2)
    assert adm.patch(f"/api/admin/haras/{base['haras']}", json={"plano": "Básico"}, headers=H).status_code == 200
    g = entrar("gestor@teste.com", "senha1234")
    assert g.post("/api/importacao", json={"animais": PLANTEL}, headers=H).status_code == 403
    assert g.post("/api/animais", json={"nome": "NOVO", "sexo": "F", "nascimento": "2020-01-01"}, headers=H).status_code == 400  # limite
    assert g.post("/api/usuarios", json={"nome": "X", "email": "x@teste.com", "perfil": "operador", "senha": "12345678"}, headers=H).status_code == 403
    assert TestClient(app).post("/api/login", json={"email": "caseiro@teste.com", "senha": "campo1234"}, headers=HC).status_code == 403
    # não dá para remover um plano em uso
    assert adm.put("/api/admin/parametros", json={"planos": {"Padrão": planos["Padrão"]}}, headers=H).status_code == 400
    assert adm.patch(f"/api/admin/haras/{base['haras']}", json={"plano": "Padrão"}, headers=H).status_code == 200
    assert entrar("caseiro@teste.com", "campo1234", HC).get("/api/estado").status_code == 200


# ---------------- administração ----------------
def test_admin_painel_e_haras(base):
    adm = entrar("admin@teste.com", "admin1234")
    p = adm.get("/api/admin/painel").json()
    assert p["parametros"]["smtp"]["senha"] == "" and {h["nome"] for h in p["haras"]} >= {"Haras Teste", "Outro Haras"}
    r = adm.post("/api/admin/haras", json={"nome": "Haras Novo", "gestorNome": "G", "gestorEmail": "novo@teste.com", "gestorSenha": "senha1234"}, headers=H)
    assert r.status_code == 200
    assert adm.post("/api/admin/haras", json={"nome": "X", "gestorNome": "G", "gestorEmail": "novo@teste.com", "gestorSenha": "senha1234"},
                    headers=H).status_code == 409
    assert entrar("gestor@teste.com", "senha1234").get("/api/admin/painel").status_code == 403


def test_admin_parametros_validados(base):
    adm = entrar("admin@teste.com", "admin1234")
    ruim = [{"de": 1, "ate": 3, "valor": 0}, {"de": 5, "ate": 30, "valor": 10}]
    assert adm.put("/api/admin/parametros", json={"faixas": ruim}, headers=H).status_code == 400
    ok = [{"de": 1, "ate": 3, "valor": 0}, {"de": 4, "ate": 30, "valor": 9.9}]
    assert adm.put("/api/admin/parametros", json={"faixas": ok, "smtp": {"host": "smtp.exemplo.com", "senha": "segredo"}}, headers=H).status_code == 200
    p = adm.get("/api/admin/painel").json()["parametros"]
    assert p["smtp"]["senha"] == "" and p["smtp"]["senhaDefinida"] is True
    det = adm.get("/api/admin/auditoria?acao=parametro_alterado").json()[0]["detalhe"]
    assert "segredo" not in json.dumps(det)


def test_admin_fila_de_atualizacao(base):
    adm = entrar("admin@teste.com", "admin1234")
    arq = {"pacote": ("pacote.zip", b"x"), "assinatura": ("pacote.sig", b"y")}
    assert adm.post("/api/admin/atualizacao", files=arq, headers=H).status_code == 400  # nome fora do padrão
    arq = {"pacote": ("haras360-1.0.1.tar.gz", b"conteudo"), "assinatura": ("haras360-1.0.1.tar.gz.sig", b"assinatura")}
    assert adm.post("/api/admin/atualizacao", files=arq, data={"sha256": "0" * 64}, headers=H).status_code == 400  # SHA-256 não confere
    r = adm.post("/api/admin/atualizacao", files=arq, headers=H)
    assert r.status_code == 200
    pedido = json.loads((FILA_DIR / "pedido.json").read_text())
    assert pedido["acao"] == "atualizar" and pedido["versao"] == "1.0.1"
    assert (FILA_DIR / "entrada" / "pacote.tar.gz").read_bytes() == b"conteudo"
    assert adm.post("/api/admin/backup", headers=H).status_code == 409  # uma tarefa por vez
    (FILA_DIR / "pedido.json").unlink()
    assert adm.post("/api/admin/rollback", json={"versao": "9.9.9"}, headers=H).status_code == 400
    assert adm.post("/api/admin/backup", headers=H).status_code == 200
    (FILA_DIR / "pedido.json").unlink()


def test_gestor_redefine_2fa_de_outro_gestor(base):
    g = entrar("gestor@teste.com", "senha1234")
    assert g.post("/api/usuarios", json={"nome": "Sócio", "email": "socio@teste.com", "perfil": "gestor", "senha": "senha1234"}, headers=H).status_code == 200
    entrar("socio@teste.com", "senha1234")
    uid = next(u["id"] for u in g.get("/api/estado").json()["usuarios"] if u["email"] == "socio@teste.com")
    assert g.post(f"/api/usuarios/{uid}/2fa/redefinir", headers=H).status_code == 200
    c = TestClient(app)
    assert c.post("/api/login", json={"email": "socio@teste.com", "senha": "senha1234"}, headers=H).json()["etapa"] == "cadastro2fa"


def test_desativar_usuario_encerra_sessoes(base):
    g = entrar("gestor@teste.com", "senha1234")
    k = entrar("caseiro@teste.com", "campo1234", HC)
    uid = next(u["id"] for u in g.get("/api/estado").json()["usuarios"] if u["perfil"] == "operador")
    assert g.patch(f"/api/usuarios/{uid}", json={"ativo": False}, headers=H).status_code == 200
    assert k.get("/api/estado").status_code == 401
    assert g.patch(f"/api/usuarios/{uid}", json={"ativo": True}, headers=H).status_code == 200


def test_paginas_e_saude(base):
    c = TestClient(app)
    for p in ("/entrar", "/gestor", "/campo", "/admin", "/ajuda", "/api/saude"):
        r = c.get(p)
        assert r.status_code == 200, p
    assert "frame-ancestors 'none'" in c.get("/entrar").headers["content-security-policy"]


def test_logotipo_do_haras(base):
    g = entrar("gestor@teste.com", "senha1234")
    assert g.put("/api/haras/logo", json={"imagem": "data:image/png;base64,AAAA"}, headers=H).status_code == 400
    r = g.put("/api/haras/logo", json={"imagem": PNG}, headers=H)
    assert r.status_code == 200
    url = r.json()["logo"]
    assert g.get("/api/estado").json()["haras"]["logo"] == url
    assert g.get(url).status_code == 200
    assert TestClient(app).get(url).status_code == 401
    assert entrar("outro@teste.com", "senha1234").get(url).status_code == 404  # logotipo de outro haras
    assert entrar("admin@teste.com", "admin1234").get(url).status_code == 200
    assert g.delete("/api/haras/logo", headers=H).status_code == 200
    assert g.get(url).status_code == 404 and g.get("/api/estado").json()["haras"]["logo"] == ""
    adm = entrar("admin@teste.com", "admin1234")
    assert adm.patch(f"/api/admin/haras/{base['haras']}", json={"logo": PNG}, headers=H).status_code == 200
    assert next(h for h in adm.get("/api/admin/painel").json()["haras"] if h["id"] == base["haras"])["logo"].startswith("/logos/")
    assert "logo_alterado" in {x["acao"] for x in g.get("/api/auditoria").json()}
