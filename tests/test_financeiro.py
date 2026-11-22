"""Financeiro da plataforma (v1.7.0): clientes, mensalidades, pagamentos e bloqueio por atraso."""
from datetime import date, timedelta

import pytest

from app import financeiro as F
from app import regras as R
from app.db import Auditoria, Cliente, Cobranca, SessionLocal
from test_api import H, entrar


@pytest.fixture(scope="module")
def fin(base):
    adm = entrar("admin@teste.com", "admin1234")
    r = adm.post("/api/admin/administradores", json={"nome": "Financeiro Teste", "email": "fin@teste.com", "senha": "financeiro1", "perfil": "financeiro",
                                                     "minhaSenha": "admin1234"}, headers=H)
    assert r.status_code == 200, r.text
    lst = adm.get("/api/admin/painel").json()["administradores"]
    assert any(a["email"] == "fin@teste.com" and a["perfil"] == "financeiro" for a in lst)
    return entrar("fin@teste.com", "financeiro1")


def test_pix_copia_e_cola():
    # exemplo do Manual do BR Code (Banco Central): o CRC confere
    ex = "00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-4266554400005204000053039865802BR5913Fulano de Tal6008BRASILIA62070503***6304"
    assert F._crc16(ex) == "1D3D"
    p = F.pix_copia_e_cola("contato@haras360.com.br", "Haras360 Gestão Ltda", "Aracaju", 15000, "H360-abc_123")
    assert p.startswith("000201") and "br.gov.bcb.pix" in p and "5406150.00" in p and "5802BR" in p and "0510H360abc123" in p
    assert F._crc16(p[:-4]) == p[-4:]


def test_perfil_financeiro_so_ve_o_financeiro(fin, base):
    assert fin.get("/api/admin/painel").status_code == 403
    d = fin.get("/api/financeiro/painel").json()
    assert d["usuario"]["perfil"] == "financeiro"
    cl = {c["harasId"]: c for c in d["clientes"]}
    assert cl[base["outro"]]["situacao"] == "Teste" and cl[base["outro"]]["testeAte"]
    assert fin.get("/api/me").json()["destino"] == "/admin"
    g = entrar("gestor@teste.com", "senha1234")
    assert g.get("/api/financeiro/painel").status_code == 403
    assert g.put("/api/financeiro/parametros", json={"bloqueioDias": 20}, headers=H).status_code == 403
    assert fin.put("/api/financeiro/parametros", json={"bloqueioDias": 20}, headers=H).status_code == 403  # só o administrador


def test_calculo_com_ajuste():
    from app import parametros as P
    c = Cliente(haras_id=0, ajuste_tipo="nenhum", ajuste_valor=0)
    with SessionLocal() as db:
        faixas = P.ler(db, "faixas")
        P.gravar(db, "faixas", [{"de": 1, "ate": 3, "valor": 0}, {"de": 4, "ate": 10, "valor": None}])  # só nesta sessão (rollback no fim)
        assert F.calcular(db, c, 2, date(2026, 1, 10))["valor"] == 0  # faixa gratuita
        assert F.calcular(db, c, 5, date(2026, 1, 10))["valor"] is None  # faixa sem preço definido
        c.ajuste_tipo, c.ajuste_valor, c.ajuste_ate = "fixo", 15000, date(2026, 6, 30)
        assert F.calcular(db, c, 5, date(2026, 1, 10))["valor"] == 15000
        assert F.calcular(db, c, 5, date(2026, 7, 10))["valor"] is None  # ajuste vencido
        P.gravar(db, "faixas", [{"de": 1, "ate": 3, "valor": 0}, {"de": 4, "ate": 500, "valor": 20}])
        c.ajuste_tipo, c.ajuste_valor, c.ajuste_ate = "desconto", 10, None
        calc = F.calcular(db, c, 5, date(2026, 1, 10))
        assert (calc["base"], calc["valor"]) == (4000, 3600) and calc["ajuste"] == "Desconto de 10%"
        db.rollback()
        assert P.ler(db, "faixas") == faixas


def test_cliente_dados_validados_e_documento_auditado(fin, base):
    hid = base["outro"]
    corpo = {"situacao": "Ativo", "inicio": "2026-01-01", "diaVencimento": 10, "nome": "Outro Haras Agropecuária Ltda", "documento": "11.222.333/0001-81",
             "contatoNome": "Ana", "contatoEmail": "ana@exemplo.com", "contatoTelefone": "(79) 99999-1111",
             "endereco": {"logradouro": "Rua A", "numero": "10", "bairro": "Centro", "cidade": "Aracaju", "uf": "se", "cep": "49000000"},
             "ajusteTipo": "fixo", "ajusteValor": "150,00"}
    assert fin.put(f"/api/financeiro/clientes/{hid}", json=dict(corpo, diaVencimento=31), headers=H).status_code == 400
    assert fin.put(f"/api/financeiro/clientes/{hid}", json=dict(corpo, documento="11.222.333/0001-80"), headers=H).status_code == 400
    assert fin.put(f"/api/financeiro/clientes/{hid}", json=corpo, headers=H).status_code == 200
    c = next(x for x in fin.get("/api/financeiro/painel").json()["clientes"] if x["harasId"] == hid)
    assert c["documento"] == "**.222.333/0001-**" and c["endereco"]["uf"] == "SE" and c["endereco"]["cep"] == "49000-000" and c["ajusteValor"] == 15000
    assert fin.post(f"/api/financeiro/clientes/{hid}/documento", headers=H).json()["documento"] == "11.222.333/0001-81"
    with SessionLocal() as db:
        assert "11222333" not in (db.get(Cliente, hid).documento or "")
        assert db.query(Auditoria).filter(Auditoria.acao == "documento_visto").count() >= 1


def test_geracao_idempotente_e_bloqueio(fin, base):
    hid = base["outro"]
    with SessionLocal() as db:
        F.gerar(db, hoje=date(2026, 3, 1))
        F.gerar(db, hoje=date(2026, 3, 2))  # não duplica
        cobs = db.query(Cobranca).filter(Cobranca.haras_id == hid, Cobranca.competencia == "2026-03").all()  # o painel também gera o mês atual
        assert [(x.competencia, R.iso(x.vencimento), x.valor) for x in cobs] == [("2026-03", "2026-03-10", 15000)]
        assert cobs[0].calculo["ajuste"].startswith("Valor fixo")
        assert F.bloqueio(db, hid, hoje=date(2026, 3, 24)) is None  # 14 dias de atraso
        assert F.bloqueio(db, hid, hoje=date(2026, 3, 25))["diasAtraso"] == 15
        cid = cobs[0].id
    og = entrar("outro@teste.com", "senha1234")
    est = og.get("/api/estado").json()  # consulta continua
    assert est["bloqueio"]["cobrancaId"] == cid
    assert any(n["tipo"] == "mensalidade" and n["sev"] == "critico" for n in est["notificacoes"])
    novo = {"nome": "Potro Bloqueado", "sexo": "M", "nascimento": "2025-01-01"}
    r = og.post("/api/animais", json=novo, headers=H)
    assert r.status_code == 423 and "Minha assinatura" in r.json()["detail"]
    assert og.post("/api/notificacoes/lidas", json={"ids": ["x"]}, headers=H).status_code == 200  # livre
    # liberação com prazo e motivo
    assert fin.post(f"/api/financeiro/clientes/{hid}/liberar", json={"ate": R.iso(R.hoje() + timedelta(days=5))}, headers=H).status_code == 400
    assert fin.post(f"/api/financeiro/clientes/{hid}/liberar", json={"ate": R.iso(R.hoje() + timedelta(days=5)), "motivo": "Combinado por telefone"},
                    headers=H).status_code == 200
    assert og.post("/api/animais", json=novo, headers=H).status_code == 200
    assert fin.post(f"/api/financeiro/clientes/{hid}/liberar", json={}, headers=H).status_code == 200
    assert og.post("/api/animais", json=dict(novo, nome="Outro Potro"), headers=H).status_code == 423
    # Minha assinatura com Pix copia e cola
    adm = entrar("admin@teste.com", "admin1234")
    assert adm.put("/api/financeiro/parametros", json={"pixChave": "contato@haras360.com.br", "pixNome": "Haras360", "pixCidade": "Aracaju",
                                                       "dadosBancarios": "Banco X, ag. 1, cc 2"}, headers=H).status_code == 200
    a = og.get("/api/assinatura").json()
    cb = next(x for x in a["cobrancas"] if x["id"] == cid)
    assert cb["situacao"] == "atrasada" and cb["pagamento"]["pix"].startswith("000201") and "<svg" in cb["pagamento"]["qr"]
    assert a["bloqueio"] and a["comoPagar"]["dadosBancarios"] == "Banco X, ag. 1, cc 2"
    # pagamento libera; estorno bloqueia de novo; cancelar paga é recusado
    assert fin.post(f"/api/financeiro/cobrancas/{cid}/recalcular", headers=H).status_code == 400  # vencida
    assert fin.post(f"/api/financeiro/cobrancas/{cid}/pagar", json={"data": R.iso(R.hoje()), "meio": "Pix"}, headers=H).status_code == 200
    assert og.get("/api/estado").json()["bloqueio"] is None
    assert fin.post(f"/api/financeiro/cobrancas/{cid}/cancelar", json={"motivo": "x"}, headers=H).status_code == 400
    assert fin.post(f"/api/financeiro/cobrancas/{cid}/estornar", headers=H).status_code == 200
    assert og.get("/api/estado").json()["bloqueio"]
    assert fin.post(f"/api/financeiro/cobrancas/{cid}/cancelar", json={}, headers=H).status_code == 400
    assert fin.post(f"/api/financeiro/cobrancas/{cid}/cancelar", json={"motivo": "Cortesia do primeiro mês"}, headers=H).status_code == 200
    assert og.get("/api/estado").json()["bloqueio"] is None
    # avulsa e painel
    assert fin.post(f"/api/financeiro/clientes/{hid}/avulsa", json={"descricao": "Implantação", "valor": "300,00",
                                                                     "vencimento": R.iso(R.hoje() + timedelta(days=3))}, headers=H).status_code == 200
    d = fin.get("/api/financeiro/painel").json()
    assert d["indicadores"]["aReceber"] >= 30000 and any(x["descricao"] == "Implantação" and x["situacao"] == "vence" for x in d["cobrancas"])
    for tipo in ("clientes", "cobrancas", "recebimentos"):
        for fmt in ("xlsx", "csv"):
            r = fin.get(f"/api/financeiro/exportar?tipo={tipo}&formato={fmt}")
            assert r.status_code == 200 and len(r.content) > 200, (tipo, fmt)
    # deixa o Outro Haras em dia para os testes seguintes
    with SessionLocal() as db:
        for x in db.query(Cobranca).filter(Cobranca.haras_id == hid, Cobranca.pago_em.is_(None), Cobranca.cancelada_em.is_(None)):
            x.pago_em, x.valor_pago = R.hoje(), x.valor
        db.commit()


def test_teste_vira_ativo_e_novo_haras_comeca_em_teste(base):
    with SessionLocal() as db:
        c = db.get(Cliente, base["haras"])
        assert c.situacao == "Teste" and c.teste_ate
        situ, ate = c.situacao, c.teste_ate
        F.gerar(db, hoje=c.teste_ate + timedelta(days=1))
        assert db.get(Cliente, base["haras"]).situacao == "Ativo"
        # Haras Teste está na faixa gratuita ou sem preço definido: nada é cobrado
        assert not db.query(Cobranca).filter(Cobranca.haras_id == base["haras"]).count()
        c = db.get(Cliente, base["haras"])
        c.situacao, c.teste_ate = situ, ate
        db.commit()
