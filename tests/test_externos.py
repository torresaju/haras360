"""Animais externos e tipo de sêmen (v1.6.0)."""
from datetime import timedelta

import pytest

from app import regras as R
from test_api import H, HC, entrar


def d(n):
    return R.iso(R.hoje() + timedelta(days=n))


@pytest.fixture(scope="module")
def g(base):
    return entrar("gestor@teste.com", "senha1234")


def test_garanhao_e_egua_externos(g):
    est0 = g.get("/api/estado").json()
    ativos0 = sum(1 for a in est0["animais"] if a["vivo"])
    gar = g.post("/api/animais", json={"nome": "Trovão de Fora", "sexo": "M", "registro": "0555001", "externo": True,
                                       "contato": {"proprietario": "Haras Vizinho", "telefone": "(79) 99999-0000", "email": "x@exemplo.com"}}, headers=H)
    assert gar.status_code == 200, gar.text
    egua = g.post("/api/animais", json={"nome": "Lua de Fora", "sexo": "F", "nascimento": "2015-01-01", "externo": True}, headers=H).json()["id"]
    est = g.get("/api/estado").json()
    ext = {a["id"]: a for a in est["animais"] if a["externo"]}
    assert ext[gar.json()["id"]]["contato"]["proprietario"] == "Haras Vizinho" and ext[gar.json()["id"]]["vivo"] is False
    assert sum(1 for a in est["animais"] if a["vivo"]) == ativos0  # fora do plantel e do limite
    assert not [t for t in est["tarefas"] if t["animalId"] in ext]  # sem agenda sanitária
    # égua externa recebe cobertura (com o garanhão do haras ou externo) e inseminação com tipo de sêmen
    assert g.post("/api/registros", json={"animalId": egua, "data": d(-3), "tipo": "reprodutivo", "evento": "Inseminação",
                                          "garanhao": "Trovão de Fora", "semen": "Congelado", "central": "Central Teste"}, headers=H).status_code == 200
    rg = [x for x in g.get("/api/estado").json()["registros"] if x["animalId"] == egua][0]
    assert (rg["semen"], rg["central"], rg["garanhao"]) == ("Congelado", "Central Teste", "TROVÃO DE FORA")
    assert g.post("/api/registros", json={"animalId": egua, "data": d(-3), "tipo": "reprodutivo", "evento": "Inseminação", "semen": "Gelado"}, headers=H).status_code == 400
    assert g.post("/api/registros", json={"animalId": egua, "data": d(-3), "tipo": "vermifugacao"}, headers=H).status_code == 400
    assert g.post(f"/api/animais/{egua}/baixa", json={"data": d(-1), "motivo": "Venda"}, headers=H).status_code == 400
    rep = g.get(f"/api/relatorios/reprodutivo?animal={egua}").json()
    assert any(ln[2] == "Inseminação" for ln in next(t for t in rep["tabelas"] if t["nome"] == "Eventos reprodutivos")["linhas"])
    # o caseiro não vê externos
    c = entrar("caseiro@teste.com", "campo1234", HC)
    ec = c.get("/api/estado").json()
    assert not any(a["id"] == egua for a in ec["animais"]) and not any(x["animalId"] == egua for x in ec["registros"])
    assert c.post("/api/registros", json={"animalId": egua, "data": d(-1), "tipo": "reprodutivo", "evento": "Cio"}, headers=HC).status_code == 404
