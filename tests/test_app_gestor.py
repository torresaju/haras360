"""App do gestor (v1.5.0): login com senha e 2FA, exigência de HTTPS, sessão do aparelho e avisos."""
import pyotp
import pytest
from fastapi.testclient import TestClient

from app import regras as R
from app.main import app
from test_api import H, HC, SEGREDOS, entrar

HA = {"X-Haras360": "1", "X-Portal": "app"}


def _https():
    return TestClient(app, base_url="https://testserver")


def _login_app(email="gestor@teste.com", senha="senha1234"):
    c = _https()
    r = c.post("/api/app/entrar", json={"email": email, "senha": senha, "aparelho": "Moto G Teste"}, headers=HA)
    assert r.status_code == 200, r.text
    r2 = c.post("/api/app/entrar/2fa", json={"desafio": r.json()["desafio"], "codigo": pyotp.TOTP(SEGREDOS[email]).now()}, headers=HA)
    assert r2.status_code == 200, r2.text
    return c, r2.json()


@pytest.fixture(scope="module")
def portal(base):
    return entrar("gestor@teste.com", "senha1234")  # garante o 2FA cadastrado


def test_exige_https_e_chave_de_teste_do_admin(portal):
    c = TestClient(app)  # http
    r = c.post("/api/app/entrar", json={"email": "gestor@teste.com", "senha": "senha1234"}, headers=HA)
    assert r.status_code == 403 and "HTTPS" in r.json()["detail"]
    adm = entrar("admin@teste.com", "admin1234")
    assert adm.put("/api/admin/parametros", json={"app_gestor_sem_https": True}, headers=H).status_code == 200
    try:
        r = c.post("/api/app/entrar", json={"email": "gestor@teste.com", "senha": "senha1234"}, headers=HA)
        assert r.status_code == 200 and r.json()["etapa"] == "2fa"
    finally:
        adm.put("/api/admin/parametros", json={"app_gestor_sem_https": False}, headers=H)
    aud = adm.get("/api/admin/auditoria?acao=parametro_alterado").json()
    assert any("app_gestor_sem_https" in a["alvo"] for a in aud)


def test_login_com_2fa_e_uso_das_rotas_do_gestor(portal):
    c, j = _login_app()
    assert j["perfil"] == "gestor" and j["token"]
    T = {**HA, "Authorization": "Bearer " + j["token"]}
    s = c.get("/api/app/sincronizar", headers=T).json()
    assert s["perfil"] == "gestor" and s["relatorios"] is True and "plano" in s and "usuarios" not in s
    assert c.get("/api/relatorios/plantel", headers=T).status_code == 200
    assert c.get("/api/relatorios/campo/exportar?formato=csv", headers=T).status_code == 200
    aid = c.post("/api/animais", json={"nome": "Do App do Gestor", "sexo": "F", "nascimento": "2017-03-03"}, headers=T).json()["id"]
    rg = c.post("/api/registros", json={"animalId": aid, "data": R.iso(R.hoje()), "tipo": "reprodutivo", "evento": "Cio", "sinais": "Inquieta"}, headers=T)
    assert rg.status_code == 200, rg.text
    est = c.get("/api/app/sincronizar", headers=T).json()
    assert next(x for x in est["registros"] if x["id"] == rg.json()["id"])["origem"] == "App do gestor"
    assert not any(n.get("animalId") == aid and n["tipo"] == "campo" for n in est["notificacoes"])
    # a sessão aparece para o gestor no portal como celular
    sess = portal.get("/api/sessoes").json()
    assert any("Moto G Teste" in x.get("agente", "") for x in sess)
    assert c.post("/api/app/sair", headers=T).status_code == 200
    assert c.get("/api/app/sincronizar", headers=T).status_code == 401


def test_erros_de_login(portal):
    c = _https()
    assert c.post("/api/app/entrar", json={"email": "gestor@teste.com", "senha": "errada"}, headers=HA).status_code == 401
    r = c.post("/api/app/entrar", json={"email": "caseiro@teste.com", "senha": "campo1234"}, headers=HA)
    assert r.status_code == 403 and "QR Code" in r.json()["detail"]
    r = c.post("/api/app/entrar", json={"email": "admin@teste.com", "senha": "admin1234"}, headers=HA)
    assert r.status_code == 403
    d = c.post("/api/app/entrar", json={"email": "gestor@teste.com", "senha": "senha1234"}, headers=HA).json()["desafio"]
    assert c.post("/api/app/entrar/2fa", json={"desafio": d, "codigo": "000000"}, headers=HA).status_code == 400
    assert c.post("/api/app/entrar/2fa", json={"desafio": "inventado", "codigo": "000000"}, headers=HA).status_code == 401
    # o desafio não serve como sessão
    assert c.get("/api/app/sincronizar", headers={**HA, "Authorization": "Bearer " + d}).status_code == 401


def test_sessao_web_do_gestor_nao_sincroniza_como_app(portal):
    assert portal.get("/api/app/sincronizar").status_code == 403


def test_aviso_de_ocorrencia_grave_do_caseiro(portal):
    animal = portal.post("/api/animais", json={"nome": "Ferido do Teste", "sexo": "M", "nascimento": "2018-01-01"}, headers=H).json()["id"]
    k = entrar("caseiro@teste.com", "campo1234", HC)
    r = k.post("/api/registros", json={"animalId": animal, "data": R.iso(R.hoje()),
                                       "tipo": "ocorrencia", "titulo": "Corte profundo na pata", "gravidade": "Grave"}, headers=HC)
    assert r.status_code == 200, r.text
    ns = portal.get("/api/estado").json()["notificacoes"]
    n = next(x for x in ns if x["tipo"] == "ocorrencia")
    assert n["sev"] == "critico" and "corte profundo" in n["texto"]
    assert portal.get("/api/estado").json()["notifPrefs"]["ocorrencia"]["push"] is True


def test_troca_de_senha_encerra_o_app(portal):
    _c, j = _login_app()
    T = {**HA, "Authorization": "Bearer " + j["token"]}
    c = _https()
    assert c.get("/api/app/sincronizar", headers=T).status_code == 200
    assert portal.post("/api/me/senha", json={"atual": "senha1234", "nova": "senha1234novo"}, headers=H).status_code == 200
    try:
        assert c.get("/api/app/sincronizar", headers=T).status_code == 401
    finally:
        g = entrar("gestor@teste.com", "senha1234novo")
        g.post("/api/me/senha", json={"atual": "senha1234novo", "nova": "senha1234"}, headers=H)
