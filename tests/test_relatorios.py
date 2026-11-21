"""Baixa de animais, registro de cio e relatórios com exportação (v1.4.0)."""
import io
from datetime import timedelta

import pytest

from app import regras as R
from test_api import H, HC, entrar


def d(n):
    return R.iso(R.hoje() + timedelta(days=n))


@pytest.fixture(scope="module")
def g(base):
    return entrar("gestor@teste.com", "senha1234")


@pytest.fixture(scope="module")
def egua(g):
    r = g.post("/api/animais", json={"nome": "Lua do Relatorio", "sexo": "F", "nascimento": "2016-05-02"}, headers=H)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_cio_com_dados_do_exame_e_validacoes(g, egua):
    ok = g.post("/api/registros", json={"animalId": egua, "data": d(-4), "tipo": "reprodutivo", "evento": "Cio", "sinais": "Aceita o rufião",
                                        "ovario": "Esquerdo", "foliculo": "35", "edema": "2"}, headers=H)
    assert ok.status_code == 200, ok.text
    est = g.get("/api/estado").json()
    rg = next(x for x in est["registros"] if x["id"] == ok.json()["id"])
    assert (rg["evento"], rg["ovario"], rg["foliculo"], rg["edema"]) == ("Cio", "Esquerdo", "35", "2")
    t = next(t for t in est["tarefas"] if t["animalId"] == egua and t.get("cio"))
    assert t["due"] == d(17)
    for extra, msg in (({"ovario": "Meio"}, "Ovário"), ({"foliculo": "200"}, "folículo"), ({"edema": "5"}, "Edema")):
        r = g.post("/api/registros", json=dict({"animalId": egua, "data": d(-4), "tipo": "reprodutivo", "evento": "Cio"}, **extra), headers=H)
        assert r.status_code == 400 and msg in r.json()["detail"]


def test_caseiro_registra_cio(base, egua):
    c = entrar("caseiro@teste.com", "campo1234", HC)
    r = c.post("/api/registros", json={"animalId": egua, "data": d(-1), "tipo": "reprodutivo", "evento": "Cio", "sinais": "Inquieta"}, headers=HC)
    assert r.status_code == 200, r.text


def test_parametros_de_reproducao(g):
    assert g.put("/api/haras", json={"cicloDias": 30}, headers=H).status_code == 400
    assert g.put("/api/haras", json={"cioPotroDe": 12, "cioPotroAte": 8}, headers=H).status_code == 400
    assert g.put("/api/haras", json={"cicloDias": 22, "previsaoCio": True}, headers=H).status_code == 200
    assert g.get("/api/estado").json()["haras"]["cicloDias"] == 22
    g.put("/api/haras", json={"cicloDias": 21}, headers=H)


def test_baixa_e_desfazer(g):
    aid = g.post("/api/animais", json={"nome": "Vendido do Teste", "sexo": "M", "nascimento": "2019-01-01"}, headers=H).json()["id"]
    assert g.post(f"/api/animais/{aid}/baixa", json={"data": d(1), "motivo": "Venda"}, headers=H).status_code == 400
    assert g.post(f"/api/animais/{aid}/baixa", json={"data": d(-2), "motivo": "Roubo"}, headers=H).status_code == 400
    r = g.post(f"/api/animais/{aid}/baixa", json={"data": d(-2), "motivo": "Venda", "destino": "Haras Vizinho"}, headers=H)
    assert r.status_code == 200, r.text
    est = g.get("/api/estado").json()
    a = next(x for x in est["animais"] if x["id"] == aid)
    assert a["baixa"]["motivo"] == "Venda" and a["vivo"] is False
    assert not [t for t in est["tarefas"] if t["animalId"] == aid]
    # editar não devolve ao plantel
    g.put(f"/api/animais/{aid}", json={"nome": "Vendido do Teste", "sexo": "M", "nascimento": "2019-01-01", "vivo": True}, headers=H)
    assert next(x for x in g.get("/api/estado").json()["animais"] if x["id"] == aid)["vivo"] is False
    rel = g.get("/api/relatorios/plantel").json()
    saidas = next(t for t in rel["tabelas"] if t["nome"] == "Saídas")
    assert ["VENDIDO DO TESTE", "Venda", "Haras Vizinho"] == saidas["linhas"][0][1:4]
    aud = g.get("/api/auditoria?acao=animal_baixa").json()
    assert aud and aud[0]["alvo"] == "VENDIDO DO TESTE"
    assert g.delete(f"/api/animais/{aid}/baixa", headers=H).status_code == 200
    assert next(x for x in g.get("/api/estado").json()["animais"] if x["id"] == aid)["baixa"] is None


def test_relatorios_formato_e_filtros(g, egua):
    for tipo in ("sanitario", "reprodutivo", "plantel", "campo"):
        r = g.get(f"/api/relatorios/{tipo}")
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["indicadores"] and j["graficos"] and j["tabelas"]
        for t in j["tabelas"]:
            assert all(len(ln) == len(t["colunas"]) for ln in t["linhas"])
    rep = g.get(f"/api/relatorios/reprodutivo?animal={egua}").json()
    assert next(i for i in rep["indicadores"] if i["rotulo"] == "Cios registrados")["valor"] == 2
    ev = next(t for t in rep["tabelas"] if t["nome"] == "Eventos reprodutivos")
    assert any("folículo 35 mm" in ln[4] for ln in ev["linhas"])
    campo = g.get("/api/relatorios/campo").json()
    assert any(ln[0] == "Caseiro Teste" for ln in campo["tabelas"][0]["linhas"])
    assert g.get("/api/relatorios/inexistente").status_code == 404
    assert g.get("/api/relatorios/plantel?de=2026-12-01&ate=2026-01-01").status_code == 400
    assert g.get("/api/relatorios/plantel?categoria=zebra").status_code == 400


def test_exportacao_xlsx_e_csv(g):
    from openpyxl import load_workbook
    r = g.get("/api/relatorios/reprodutivo/exportar?formato=xlsx")
    assert r.status_code == 200 and "spreadsheetml" in r.headers["content-type"]
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.sheetnames[:3] == ["Resumo", "Situação das éguas", "Eventos reprodutivos"]
    assert wb["Situação das éguas"]["A1"].value == "Égua"
    link = next(c.hyperlink.target for c in wb["Situação das éguas"]["G"] if c.hyperlink)
    assert "/gestor?animal=" in link
    c = g.get("/api/relatorios/campo/exportar?formato=csv")
    assert c.status_code == 200 and c.content.startswith(b"\xef\xbb\xbf")
    txt = c.content.decode("utf-8-sig")
    assert "Atividade do campo" in txt and "Registrado por;Origem" in txt
    assert g.get("/api/auditoria?acao=relatorio_exportado").json()


def test_so_gestor_e_modulo_do_plano(base):
    c = entrar("caseiro@teste.com", "campo1234", HC)
    assert c.get("/api/relatorios/plantel").status_code == 403
    adm = entrar("admin@teste.com", "admin1234")
    planos = adm.get("/api/admin/painel").json()["parametros"]["planos"]
    for pl in planos.values():
        pl["modulos"]["relatorios"] = False
    assert adm.put("/api/admin/parametros", json={"planos": planos}, headers=H).status_code == 200
    try:
        g = entrar("gestor@teste.com", "senha1234")
        assert g.get("/api/relatorios/plantel").status_code == 403
        assert g.get("/api/relatorios/plantel/exportar?formato=csv").status_code == 403
    finally:
        for pl in planos.values():
            pl["modulos"]["relatorios"] = True
        adm.put("/api/admin/parametros", json={"planos": planos}, headers=H)
