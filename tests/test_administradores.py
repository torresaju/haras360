"""Tela de Administradores (v1.1.1): criar, desativar, redefinir senha e 2FA de outro administrador."""
from fastapi.testclient import TestClient

from app.db import SessionLocal, Usuario
from app.main import app
from test_api import H, entrar

URL = "/api/admin/administradores"


def _id(email):
    with SessionLocal() as db:
        return db.query(Usuario).filter(Usuario.email == email).one().id


def test_criar_administrador_pede_minha_senha(base):
    adm = entrar("admin@teste.com", "admin1234")
    novo = {"nome": "Segundo Admin", "email": "segundo@teste.com", "senha": "segunda1234"}
    assert adm.post(URL, json=novo, headers=H).status_code == 403
    assert adm.post(URL, json=dict(novo, minhaSenha="errada"), headers=H).status_code == 403
    r = adm.post(URL, json=dict(novo, minhaSenha="admin1234"), headers=H)
    assert r.status_code == 200, r.text
    assert adm.post(URL, json=dict(novo, minhaSenha="admin1234"), headers=H).status_code == 409  # e-mail repetido
    assert adm.post(URL, json=dict(novo, email="x@teste.com", senha="curta", minhaSenha="admin1234"), headers=H).status_code == 400
    lista = adm.get("/api/admin/painel").json()["administradores"]
    s = next(a for a in lista if a["email"] == "segundo@teste.com")
    assert s["ativo"] and not s["doisFatores"] and not s["eu"]
    assert next(a for a in lista if a["email"] == "admin@teste.com")["eu"]
    # o novo administrador entra e cadastra o 2FA
    entrar("segundo@teste.com", "segunda1234")
    acoes = [a["alvo"] for a in adm.get("/api/admin/auditoria").json() if a["acao"] == "usuario_criado"]
    assert any("segundo@teste.com" in (x or "") for x in acoes)


def test_so_administrador_mexe_em_administradores(base):
    k = entrar("caseiro@teste.com", "campo1234", {"X-Haras360": "1", "X-Portal": "campo"})
    assert k.post(URL, json={"nome": "X", "email": "x2@teste.com", "senha": "abcdefgh1", "minhaSenha": "campo1234"}, headers=H).status_code == 403
    assert TestClient(app).post(URL, json={}, headers=H).status_code == 401
    # as rotas de administradores não mexem em gestores, e as de usuários não mexem em administradores
    adm = entrar("admin@teste.com", "admin1234")
    gid = _id("gestor@teste.com")
    assert adm.post(f"{URL}/{gid}/senha", json={"senha": "outra12345", "minhaSenha": "admin1234"}, headers=H).status_code == 404
    assert adm.post(f"/api/admin/usuarios/{_id('admin@teste.com')}/senha", json={"senha": "outra12345"}, headers=H).status_code == 404


def test_redefinir_senha_e_2fa_de_outro_admin(base):
    adm = entrar("admin@teste.com", "admin1234")
    adm.post(URL, json={"nome": "Terceiro", "email": "terceiro@teste.com", "senha": "terceira123", "minhaSenha": "admin1234"}, headers=H)
    t = entrar("terceiro@teste.com", "terceira123")
    tid = _id("terceiro@teste.com")
    assert adm.post(f"{URL}/{tid}/senha", json={"senha": "nova-senha-123", "minhaSenha": "admin1234"}, headers=H).status_code == 200
    assert t.get("/api/admin/painel").status_code == 401  # sessão encerrada
    t = entrar("terceiro@teste.com", "nova-senha-123")
    assert adm.post(f"{URL}/{tid}/2fa/redefinir", json={"minhaSenha": "admin1234"}, headers=H).status_code == 200
    with SessionLocal() as db:
        x = db.get(Usuario, tid)
        assert not x.totp_ativo and x.totp_segredo is None and x.recuperacao is None
    assert t.get("/api/admin/painel").status_code == 401
    # a própria conta não passa por aqui
    me = _id("admin@teste.com")
    assert adm.post(f"{URL}/{me}/senha", json={"senha": "x" * 10, "minhaSenha": "admin1234"}, headers=H).status_code == 400
    assert adm.post(f"{URL}/{me}/2fa/redefinir", json={"minhaSenha": "admin1234"}, headers=H).status_code == 400


def test_nunca_sem_administrador_ativo(base):
    adm = entrar("admin@teste.com", "admin1234")
    adm.post(URL, json={"nome": "Quarto", "email": "quarto@teste.com", "senha": "quarta1234", "minhaSenha": "admin1234"}, headers=H)
    q = entrar("quarto@teste.com", "quarta1234")
    qid, me = _id("quarto@teste.com"), _id("admin@teste.com")
    assert adm.patch(f"{URL}/{me}", json={"ativo": False, "minhaSenha": "admin1234"}, headers=H).status_code == 400  # a si mesmo
    # desativa todos os outros, um por vez; o último ativo (você) continua
    with SessionLocal() as db:
        outros = [x.id for x in db.query(Usuario).filter(Usuario.perfil == "admin", Usuario.id != me, Usuario.ativo.is_(True))]
    for oid in outros:
        assert adm.patch(f"{URL}/{oid}", json={"ativo": False, "minhaSenha": "admin1234"}, headers=H).status_code == 200
    assert q.get("/api/admin/painel").status_code == 401
    r = TestClient(app).post("/api/login", json={"email": "quarto@teste.com", "senha": "quarta1234"}, headers=H)
    assert r.status_code in (401, 403)
    # reativado, o quarto desativa o administrador de teste (sobra ele); a si mesmo, nunca
    assert adm.patch(f"{URL}/{qid}", json={"ativo": True, "minhaSenha": "admin1234"}, headers=H).status_code == 200
    q = entrar("quarto@teste.com", "quarta1234")
    assert q.patch(f"{URL}/{me}", json={"ativo": False, "minhaSenha": "quarta1234"}, headers=H).status_code == 200
    assert adm.get("/api/admin/painel").status_code == 401
    assert q.patch(f"{URL}/{qid}", json={"ativo": False, "minhaSenha": "quarta1234"}, headers=H).status_code == 400
    # devolve o administrador de teste para os outros testes
    assert q.patch(f"{URL}/{me}", json={"ativo": True, "minhaSenha": "quarta1234"}, headers=H).status_code == 200
