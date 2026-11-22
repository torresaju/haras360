"""Venda com comprador e parcelas (v1.6.0)."""
from datetime import timedelta

import pytest

from app import regras as R
from app import vendas as V
from test_api import H, HC, entrar


def d(n):
    return R.iso(R.hoje() + timedelta(days=n))


@pytest.fixture(scope="module")
def g(base):
    return entrar("gestor@teste.com", "senha1234")


def _animal(g, nome):
    r = g.post("/api/animais", json={"nome": nome, "sexo": "M", "nascimento": "2020-01-01"}, headers=H)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_documento_e_parcelas():
    assert V.documento_valido("529.982.247-25") == (True, "cpf")
    assert V.documento_valido("11.222.333/0001-81") == (True, "cnpj")
    assert not V.documento_valido("111.111.111-11")[0] and not V.documento_valido("529.982.247-24")[0]
    assert V.mascara("52998224725") == "***.982.247-**"
    assert V.decifrar(V.cifrar("529.982.247-25")) == "52998224725"
    ps = V.gerar_parcelas(1000000, 100000, 3, R.d("2026-01-31"))
    assert [p[2] for p in ps] == [100000, 300000, 300000, 300000]
    assert [R.iso(p[1]) for p in ps[1:]] == ["2026-01-31", "2026-02-28", "2026-03-31"]
    assert sum(p[2] for p in V.gerar_parcelas(100000, 0, 3, R.d("2026-01-10"))) == 100000  # centavos na última


def test_comprador_cifrado_e_auditado(g, base):
    r = g.post("/api/compradores", json={"nome": "José Comprador", "documento": "529.982.247-25", "telefone": "(79) 98888-0000",
                                         "email": "jose@exemplo.com", "cidade": "Aracaju", "uf": "se", "cadastroAbccmm": "12345"}, headers=H)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    lst = g.get("/api/compradores").json()
    c = next(x for x in lst if x["id"] == cid)
    assert c["documento"] == "***.982.247-**" and c["uf"] == "SE" and c["nome"] == "JOSÉ COMPRADOR"
    assert g.post("/api/compradores", json={"nome": "X", "documento": "123.456.789-00"}, headers=H).status_code == 400
    # a máscara não apaga o documento ao editar
    assert g.put(f"/api/compradores/{cid}", json=dict(c, documento=c["documento"], telefone="(79) 97777-0000"), headers=H).status_code == 200
    assert g.post(f"/api/compradores/{cid}/documento", headers=H).json()["documento"] == "529.982.247-25"
    from app.db import Auditoria, Comprador, SessionLocal
    with SessionLocal() as db:
        assert "52998224725" not in (db.get(Comprador, cid).documento or "")
        assert db.query(Auditoria).filter(Auditoria.acao == "documento_visto").count() >= 1
    c2 = entrar("caseiro@teste.com", "campo1234", HC)
    assert c2.get("/api/compradores").status_code == 403
    assert c2.get("/api/estado").json()["vendas"] == []


def test_venda_parcelada_pagamentos_e_avisos(g):
    aid = _animal(g, "Vendido Parcelado")
    r = g.post("/api/vendas", json={"animalId": aid, "data": d(-40), "comprador": {"nome": "Maria Compradora", "documento": "11.222.333/0001-81"},
                                    "valor": "30.000,00", "forma": "parcelado", "meio": "Pix", "entrada": "6000", "nParcelas": 3,
                                    "primeiroVencimento": d(-10)}, headers=H)
    assert r.status_code == 200, r.text
    vid = r.json()["id"]
    est = g.get("/api/estado").json()
    a = next(x for x in est["animais"] if x["id"] == aid)
    assert a["baixa"]["motivo"] == "Venda" and a["baixa"]["destino"] == "MARIA COMPRADORA" and not a["vivo"]
    v = next(x for x in est["vendas"] if x["id"] == vid)
    assert v["total"] == 3000000 and v["recebido"] == 600000 and len(v["parcelas"]) == 4
    assert [p["situacao"] for p in v["parcelas"]] == ["paga", "atrasada", "aberta", "aberta"]
    ns = [n for n in est["notificacoes"] if n.get("vendaId") == vid]
    assert any(n["tipo"] == "financeiro" and n["sev"] == "critico" for n in ns)
    assert any("transferência" in n["titulo"].lower() for n in ns)
    # paga a parcela vencida, estorna e paga de novo
    p1 = v["parcelas"][1]["id"]
    assert g.post(f"/api/parcelas/{p1}/pagar", json={"data": d(0), "meio": "Pix"}, headers=H).status_code == 200
    assert g.post(f"/api/parcelas/{p1}/pagar", json={"data": d(0)}, headers=H).status_code == 400
    assert g.post(f"/api/parcelas/{p1}/estornar", headers=H).status_code == 200
    assert g.post(f"/api/parcelas/{p1}/pagar", json={"data": d(0), "valor": "8000,00"}, headers=H).status_code == 200
    # transferência comunicada some dos avisos
    assert g.post(f"/api/vendas/{vid}/transferencia", json={"feita": True}, headers=H).status_code == 200
    est = g.get("/api/estado").json()
    ns = [n for n in est["notificacoes"] if n.get("vendaId") == vid]
    assert not any("transferência" in n["titulo"].lower() for n in ns) and not any(n["sev"] == "critico" for n in ns)
    # com pagamento, a baixa não pode ser desfeita
    assert g.delete(f"/api/animais/{aid}/baixa", headers=H).status_code == 400
    rel = g.get("/api/relatorios/vendas").json()
    assert any(ln[2] == "MARIA COMPRADORA" for ln in rel["tabelas"][0]["linhas"])
    assert g.get("/api/relatorios/vendas/exportar?formato=xlsx").status_code == 200


def test_venda_a_vista_e_desfazer(g):
    aid = _animal(g, "Vendido à Vista")
    cid = g.post("/api/compradores", json={"nome": "Pedro Sem Documento"}, headers=H).json()["id"]
    assert g.post("/api/vendas", json={"animalId": aid, "data": d(1), "compradorId": cid, "valor": 1000, "forma": "avista"}, headers=H).status_code == 400
    assert g.post("/api/vendas", json={"animalId": aid, "data": d(0), "compradorId": cid, "valor": 0, "forma": "avista"}, headers=H).status_code == 400
    r = g.post("/api/vendas", json={"animalId": aid, "data": d(0), "compradorId": cid, "valor": 15000, "forma": "avista", "pago": False}, headers=H)
    assert r.status_code == 200, r.text
    assert g.post("/api/vendas", json={"animalId": aid, "data": d(0), "compradorId": cid, "valor": 1, "forma": "avista"}, headers=H).status_code == 400
    assert g.delete(f"/api/compradores/{cid}", headers=H).status_code == 400  # tem venda
    # sem pagamento: desfazer a baixa apaga a venda
    assert g.delete(f"/api/animais/{aid}/baixa", headers=H).status_code == 200, "desfazer"
    est = g.get("/api/estado").json()
    assert not any(v["animalId"] == aid for v in est["vendas"])
    assert g.delete(f"/api/compradores/{cid}", headers=H).status_code == 200


def test_parcelas_editadas_precisam_somar(g):
    aid = _animal(g, "Vendido Editado")
    base = {"animalId": aid, "data": d(0), "comprador": {"nome": "Ana"}, "valor": "1000", "forma": "parcelado"}
    ruim = dict(base, parcelas=[{"numero": 1, "vencimento": d(30), "valor": "400"}, {"numero": 2, "vencimento": d(60), "valor": "500"}])
    assert g.post("/api/vendas", json=ruim, headers=H).status_code == 400
    ok = dict(base, parcelas=[{"numero": 1, "vencimento": d(30), "valor": "400"}, {"numero": 2, "vencimento": d(60), "valor": "600"}])
    assert g.post("/api/vendas", json=ok, headers=H).status_code == 200
