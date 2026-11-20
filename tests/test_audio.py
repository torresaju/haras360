"""Áudio nos registros do caseiro (v1.2.0)."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app import regras as R
from app.main import app
from test_api import H, entrar
from test_app import HA, _vincular

M4A = b"\x00\x00\x00\x1cftypM4A \x00\x00\x02\x00M4A isommp42" + b"\x00" * 2000


@pytest.fixture(scope="module", autouse=True)
def animal(base):
    g = entrar("gestor@teste.com", "senha1234")
    if not g.get("/api/estado").json()["animais"]:
        assert g.post("/api/animais", json={"nome": "Estrela do Audio", "sexo": "F", "nascimento": "2018-03-10"}, headers=H).status_code == 200


def _app():
    g = entrar("gestor@teste.com", "senha1234")
    _q, v = _vincular(g)
    return g, TestClient(app, headers={"Authorization": f"Bearer {v['token']}"})


def _registro(a):
    est = a.get("/api/app/sincronizar").json()
    rid = str(uuid.uuid4())
    assert a.post("/api/registros", json={"id": rid, "animalId": est["animais"][0]["id"], "data": R.iso(R.hoje()), "tipo": "ocorrencia",
                                          "titulo": "Tosse", "gravidade": "Leve"}, headers=HA).status_code == 200
    return rid


def _enviar(a, rid, aid=None, dados=M4A, duracao=42, cab=HA):
    return a.post("/api/app/audios", data={"registroId": rid, "audioId": aid or uuid.uuid4().hex, "duracao": str(duracao)},
                  files={"arquivo": ("a.m4a", dados, "audio/mp4")}, headers=cab)


def test_sincronizar_informa_audio(base):
    _g, a = _app()
    e = a.get("/api/app/sincronizar").json()
    assert e["audio"] == {"liberado": True, "maxSeg": 120}


def test_envio_idempotente_e_player_no_prontuario(base):
    g, a = _app()
    rid = _registro(a)
    aid = uuid.uuid4().hex
    assert _enviar(a, rid, aid).status_code == 200
    assert _enviar(a, rid, aid).json()["duplicado"] is True  # reenvio depois de queda do Wi-Fi
    assert _enviar(a, rid).status_code == 409  # um áudio por registro
    reg = next(x for x in g.get("/api/estado").json()["registros"] if x["id"] == rid)
    assert reg["audio"] == {"url": f"/audios/{aid}", "duracao": 42}
    r = g.get(reg["audio"]["url"])
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mp4" and r.content == M4A
    assert TestClient(app).get(reg["audio"]["url"]).status_code == 401
    assert entrar("outro@teste.com", "senha1234").get(reg["audio"]["url"]).status_code == 404


def test_tipo_tamanho_e_duracao(base):
    _g, a = _app()
    rid = _registro(a)
    assert _enviar(a, rid, dados=b"RIFF....WAVEfmt " + b"\x00" * 100).status_code == 400  # outro formato
    assert _enviar(a, rid, dados=b"\x89PNG\r\n\x1a\n" + b"\x00" * 100).status_code == 400
    assert _enviar(a, rid, duracao=600).status_code == 400
    assert _enviar(a, rid, dados=M4A + b"\x00" * (1024 * 1024)).status_code == 400
    assert _enviar(a, rid, aid="../../etc/passwd").status_code == 400
    assert _enviar(a, str(uuid.uuid4())).status_code == 404  # registro ainda não enviado


def test_exclusao_do_registro_leva_o_audio(base):
    g, a = _app()
    rid = _registro(a)
    aid = uuid.uuid4().hex
    assert _enviar(a, rid, aid).status_code == 200
    assert g.delete(f"/api/registros/{rid}", headers=H).status_code == 200
    assert g.get(f"/audios/{aid}").status_code == 404


def test_modulo_desligado_no_plano(base):
    _g, a = _app()
    rid = _registro(a)
    adm = entrar("admin@teste.com", "admin1234")
    p = adm.get("/api/admin/painel").json()["parametros"]
    planos = p["planos"]
    for pl in planos.values():
        pl["modulos"]["audio"] = False
    assert adm.put("/api/admin/parametros", json={"planos": planos}, headers=H).status_code == 200
    try:
        assert a.get("/api/app/sincronizar").json()["audio"]["liberado"] is False
        assert _enviar(a, rid).status_code == 403
    finally:
        for pl in planos.values():
            pl["modulos"]["audio"] = True
        adm.put("/api/admin/parametros", json={"planos": planos}, headers=H)


def test_duracao_maxima_parametrizada(base):
    adm = entrar("admin@teste.com", "admin1234")
    assert adm.put("/api/admin/parametros", json={"audio_max_seg": 5}, headers=H).status_code == 400  # abaixo do mínimo
    assert adm.put("/api/admin/parametros", json={"audio_max_seg": 60}, headers=H).status_code == 200
    try:
        _g, a = _app()
        assert a.get("/api/app/sincronizar").json()["audio"]["maxSeg"] == 60
        assert _enviar(a, _registro(a), duracao=90).status_code == 400
    finally:
        adm.put("/api/admin/parametros", json={"audio_max_seg": 120}, headers=H)
