"""Testes da API do app Android (v1.1.0): vínculo por QR Code, sincronização, fotos e APK."""
import base64
import json
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app import regras as R
from app.config import APP_DIR
from app.db import SessionLocal, Usuario, VinculoApp
from app.main import app
from app.seguranca import hash_senha
from test_api import H, PNG, entrar

HA = {"X-Haras360": "1", "X-Portal": "app"}
PNG_BYTES = base64.b64decode(PNG.split(",", 1)[1])


def _caseiro_id(g):
    return next(x["id"] for x in g.get("/api/estado").json()["usuarios"] if x["email"] == "caseiro@teste.com")


def _vincular(g, aparelho="Moto G (teste)"):
    r = g.post(f"/api/usuarios/{_caseiro_id(g)}/vinculo", headers=H)
    assert r.status_code == 200, r.text
    q = r.json()
    assert q["link"].startswith("haras360://vincular?s=") and "<svg" in q["qr"] and q["minutos"] == 10
    r = TestClient(app).post("/api/app/vincular", json={"codigo": q["codigo"], "aparelho": aparelho}, headers=HA)
    assert r.status_code == 200, r.text
    return q, r.json()


def test_vinculo_por_qr_code_e_uso_unico(base):
    g = entrar("gestor@teste.com", "senha1234")
    q, v = _vincular(g)
    assert v["nome"] == "Caseiro Teste" and v["haras"] == "Haras Teste"
    app_c = TestClient(app, headers={"Authorization": f"Bearer {v['token']}"})
    assert app_c.get("/api/app/sincronizar").status_code == 200
    # o mesmo código não serve duas vezes
    assert TestClient(app).post("/api/app/vincular", json={"codigo": q["codigo"]}, headers=HA).status_code == 401
    # o aparelho aparece nas sessões do gestor, com o modelo, e pode ser encerrado
    s = next(x for x in g.get("/api/sessoes").json() if x["id"] == v["sessao"])
    assert s["tipo"] == "app" and "Moto G" in s["agente"]
    assert g.delete(f"/api/sessoes/{v['sessao']}", headers=H).status_code == 200
    assert app_c.get("/api/app/sincronizar").status_code == 401
    acoes = [a["acao"] for a in g.get("/api/auditoria").json()]
    assert "app_vinculo_gerado" in acoes and "app_vinculado" in acoes


def test_vinculo_vencido_ou_substituido(base):
    g = entrar("gestor@teste.com", "senha1234")
    uid = _caseiro_id(g)
    c1 = g.post(f"/api/usuarios/{uid}/vinculo", headers=H).json()["codigo"]
    c2 = g.post(f"/api/usuarios/{uid}/vinculo", headers=H).json()["codigo"]
    assert TestClient(app).post("/api/app/vincular", json={"codigo": c1}, headers=HA).status_code == 401  # substituído
    with SessionLocal() as db:
        for v in db.query(VinculoApp).filter(VinculoApp.usado_em.is_(None)):
            v.expira_em = datetime.now() - timedelta(minutes=1)
        db.commit()
    assert TestClient(app).post("/api/app/vincular", json={"codigo": c2}, headers=HA).status_code == 401  # vencido


def test_vinculo_so_para_caseiro_do_proprio_haras(base):
    g = entrar("gestor@teste.com", "senha1234")
    gid = next(x["id"] for x in g.get("/api/estado").json()["usuarios"] if x["perfil"] == "gestor")
    assert g.post(f"/api/usuarios/{gid}/vinculo", headers=H).status_code == 400
    outro = entrar("outro@teste.com", "senha1234")
    assert outro.post(f"/api/usuarios/{_caseiro_id(g)}/vinculo", headers=H).status_code == 404
    k = entrar("caseiro@teste.com", "campo1234", {"X-Haras360": "1", "X-Portal": "campo"})
    assert k.post(f"/api/usuarios/{_caseiro_id(g)}/vinculo", headers=H).status_code == 403
    assert TestClient(app).post("/api/app/vincular", json={"codigo": "x" * 24}).status_code == 403  # sem o cabeçalho X-Haras360


def test_registro_offline_e_fotos_separadas(base):
    g = entrar("gestor@teste.com", "senha1234")
    _q, v = _vincular(g)
    a = TestClient(app, headers={"Authorization": f"Bearer {v['token']}"})
    est = a.get("/api/app/sincronizar").json()
    assert "usuarios" not in est and est["tarefas"] is not None and est["animais"]
    rid = str(uuid.uuid4())
    corpo = {"id": rid, "animalId": est["animais"][0]["id"], "data": R.iso(R.hoje()), "tipo": "ocorrencia", "titulo": "Corte na pata", "gravidade": "Leve"}
    assert a.post("/api/registros", json=corpo, headers=HA).status_code == 200
    assert a.post("/api/registros", json=corpo, headers=HA).json()["duplicado"] is True  # reenvio após queda do Wi-Fi
    fid = uuid.uuid4().hex
    env = lambda f=fid, dados=PNG_BYTES: a.post("/api/app/fotos", data={"registroId": rid, "fotoId": f, "ordem": "0"},
                                                files={"arquivo": ("foto.jpg", dados, "image/jpeg")}, headers=HA)
    assert env().status_code == 200
    assert env().json()["duplicado"] is True
    assert env(uuid.uuid4().hex, b"isto nao e imagem").status_code == 400
    assert env("../../etc").status_code == 400
    reg = next(x for x in g.get("/api/estado").json()["registros"] if x["id"] == rid)
    assert reg["origem"] == "App" and len(reg["fotos"]) == 1
    assert g.get(reg["fotos"][0]).status_code == 200
    # limite de fotos por registro
    for _ in range(3):
        assert env(uuid.uuid4().hex).status_code == 200
    assert env(uuid.uuid4().hex).status_code == 400


def test_foto_em_registro_alheio_recusada(base):
    g = entrar("gestor@teste.com", "senha1234")
    a_id = g.get("/api/estado").json()["animais"][0]["id"]
    rid = g.post("/api/registros", json={"animalId": a_id, "data": R.iso(R.hoje()), "tipo": "ocorrencia", "titulo": "Do gestor"}, headers=H).json()["id"]
    _q, v = _vincular(g)
    a = TestClient(app, headers={"Authorization": f"Bearer {v['token']}"})
    r = a.post("/api/app/fotos", data={"registroId": rid, "fotoId": uuid.uuid4().hex}, files={"arquivo": ("f.png", PNG_BYTES, "image/png")}, headers=HA)
    assert r.status_code == 403
    o = entrar("outro@teste.com", "senha1234")
    r = o.post("/api/app/fotos", data={"registroId": rid, "fotoId": uuid.uuid4().hex}, files={"arquivo": ("f.png", PNG_BYTES, "image/png")}, headers=H)
    assert r.status_code == 404


def test_sincronizar_so_para_caseiro_e_renova_validade(base):
    g = entrar("gestor@teste.com", "senha1234")
    assert g.get("/api/app/sincronizar").status_code == 403
    _q, v = _vincular(g)
    from app.db import Sessao
    with SessionLocal() as db:
        s = db.query(Sessao).filter(Sessao.publico == v["sessao"]).one()
        s.expira_em = datetime.now() + timedelta(days=1)
        db.commit()
    TestClient(app, headers={"Authorization": f"Bearer {v['token']}"}).get("/api/app/sincronizar")
    with SessionLocal() as db:
        s = db.query(Sessao).filter(Sessao.publico == v["sessao"]).one()
        assert s.expira_em > datetime.now() + timedelta(days=80)


def test_apk_servido_pelo_servidor(base):
    c = TestClient(app)
    assert c.get("/api/app/versao").json() == {"disponivel": False}
    assert c.get("/app/haras360.apk").status_code == 404
    APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        (APP_DIR / "haras360.apk").write_bytes(b"PK\x03\x04apk-de-teste")
        (APP_DIR / "versao.json").write_text(json.dumps({"versao": "1.1.0", "codigo": 10100, "sha256": "ab" * 32}))
        v = c.get("/api/app/versao").json()
        assert v["disponivel"] and v["versao"] == "1.1.0" and v["codigo"] == 10100 and v["url"] == "/app/haras360.apk"
        r = c.get("/app/haras360.apk")
        assert r.status_code == 200 and r.headers["content-type"] == "application/vnd.android.package-archive"
        k = entrar("caseiro@teste.com", "campo1234", {"X-Haras360": "1", "X-Portal": "campo"})
        i = k.get("/api/app/instalar").json()
        assert i["link"].endswith("/app/haras360.apk") and "<svg" in i["qr"]
        assert c.get("/api/app/instalar").status_code == 401
    finally:
        (APP_DIR / "haras360.apk").unlink(missing_ok=True)
        (APP_DIR / "versao.json").unlink(missing_ok=True)


def test_caseiro_desativado_nao_vincula(base):
    g = entrar("gestor@teste.com", "senha1234")
    with SessionLocal() as db:
        db.add(Usuario(haras_id=base["haras"], nome="Caseiro Dois", email="caseiro2@teste.com", senha_hash=hash_senha("campo1234"), perfil="operador"))
        db.commit()
    uid = next(x["id"] for x in g.get("/api/estado").json()["usuarios"] if x["email"] == "caseiro2@teste.com")
    cod = g.post(f"/api/usuarios/{uid}/vinculo", headers=H).json()["codigo"]
    assert g.patch(f"/api/usuarios/{uid}", json={"ativo": False}, headers=H).status_code == 200
    assert TestClient(app).post("/api/app/vincular", json={"codigo": cod}, headers=HA).status_code == 403
    assert g.post(f"/api/usuarios/{uid}/vinculo", headers=H).status_code == 400
