"""Correções da v1.5.2: vários animais sem registro na ABCCMM."""
import pytest

from test_api import H, entrar


@pytest.fixture(scope="module")
def g(base):
    return entrar("gestor@teste.com", "senha1234")


def test_varios_animais_sem_registro(g):
    ids = []
    for nome, reg in (("Sem Registro Um", "*sem registro na ABCCMM"), ("Sem Registro Dois", "*sem registro na ABCCMM"), ("Sem Registro Tres", "")):
        r = g.post("/api/animais", json={"nome": nome, "sexo": "F", "nascimento": "2024-02-02", "registro": reg, "chip": "*****"}, headers=H)
        assert r.status_code == 200, r.text
        ids.append(r.json()["id"])
    est = {a["id"]: a for a in g.get("/api/estado").json()["animais"]}
    assert all(est[i]["registro"] == "" and est[i]["chip"] == "" for i in ids)
    # registro de verdade continua único
    assert g.post("/api/animais", json={"nome": "Com Registro A", "sexo": "M", "nascimento": "2020-01-01", "registro": "0999001"}, headers=H).status_code == 200
    r = g.post("/api/animais", json={"nome": "Com Registro B", "sexo": "M", "nascimento": "2020-01-01", "registro": "0999001"}, headers=H)
    assert r.status_code == 409 and "COM REGISTRO A" in r.json()["detail"]
