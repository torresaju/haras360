"""Testes unitários do motor de regras sanitárias."""
from datetime import timedelta

from app import regras as R

HARAS = {"raivaSemestral": False}


def prots(*ids):
    return [p for p in R.protocolos_padrao() if not ids or p["id"] in ids]


def animal(nasc, sexo="F", **kw):
    a = {"id": "a1", "nome": "TESTE", "sexo": sexo, "nascimento": nasc, "vivo": True, "registro": "123", "dna": "DNA - VP", "bloqueado": False}
    a.update(kw)
    return a


def reg(data, tipo, protocolos=(), dose="reforco", **kw):
    r = {"id": "r" + data + tipo, "animalId": "a1", "data": data, "tipo": tipo, "protocolos": list(protocolos), "dose": dose, "origem": "Portal Gestor", "autor": "Teste"}
    r.update(kw)
    return r


def d(n):
    return R.iso(R.hoje() + timedelta(days=n))


def test_add_meses_fim_de_mes():
    assert R.add_meses("2026-01-31", 1).isoformat() == "2026-02-28"
    assert R.add_meses("2024-01-31", 1).isoformat() == "2024-02-29"
    assert R.add_meses("2026-11-15", 3).isoformat() == "2027-02-15"


def test_primeira_dose_pela_idade():
    a = animal("2026-01-15")
    e = R.proxima_etapa(HARAS, a, prots("raiva")[0], [])
    assert e["due"] == "2026-05-15" and e["dose"] == 1 and e["etapa"] == "1ª dose (primovacinação)"


def test_serie_inicial_segunda_dose():
    a = animal("2026-01-15")
    p = prots("tetano")[0]
    e = R.proxima_etapa(HARAS, a, p, [reg("2026-04-20", "vacina", ["tetano"], dose=1)])
    assert e["due"] == "2026-05-20" and e["etapa"] == "2ª dose"


def test_primeiro_reforco_aos_12_meses():
    a = animal("2026-01-15")
    regs = [reg(x, "vacina", ["tetano"], dose=i) for i, x in enumerate(["2026-04-20", "2026-05-20", "2026-06-19"], 1)]
    e = R.proxima_etapa(HARAS, a, prots("tetano")[0], regs)
    assert e["due"] == "2027-01-15" and "12 meses" in e["nota"]


def test_raiva_semestral_configuravel():
    a = animal("2015-01-01")
    p = prots("raiva")[0]
    r = [reg(d(-10), "vacina", ["raiva"])]
    assert R.proxima_etapa({"raivaSemestral": False}, a, p, r)["due"] == d(355)
    assert R.proxima_etapa({"raivaSemestral": True}, a, p, r)["due"] == d(170)


def test_reforco_vencido_reinicia_primovacinacao():
    a = animal("2015-01-01")
    e = R.proxima_etapa(HARAS, a, prots("influenza")[0], [reg(d(-400), "vacina", ["influenza"])])
    assert e["etapa"] == "Reiniciar primovacinação" and e["dose"] == 1


def test_tolerancia_de_15_dias_nao_reinicia():
    a = animal("2015-01-01")
    e = R.proxima_etapa(HARAS, a, prots("influenza")[0], [reg(d(-375), "vacina", ["influenza"])])
    assert e["etapa"] == "Reforço"


def test_gatilho_por_registro_nao_agenda_sem_historico():
    assert R.proxima_etapa(HARAS, animal("2015-01-01"), prots("ferrag")[0], []) is None


def test_gestacao_agenda_rino_e_parto():
    a = animal("2018-01-01")
    cob = d(-160)
    regs = [reg(d(-130), "reprodutivo", evento="Diagnóstico positivo", dataCobertura=cob, garanhao="SAMBA")]
    g = R.gestacao(a, regs)
    assert g["parto"] == R.iso(R.add_dias(cob, 340))
    ts = R.tarefas(HARAS, [a], regs, prots())
    etapas = {t["etapa"] for t in ts if t["protocoloId"] == "rino"}
    assert etapas == {"Gestante, 5º mês", "Gestante, 7º mês", "Gestante, 9º mês"}
    assert any(t.get("parto") for t in ts)


def test_parto_encerra_gestacao():
    a = animal("2018-01-01")
    regs = [reg(d(-400), "reprodutivo", evento="Diagnóstico positivo", dataCobertura=d(-420)), reg(d(-80), "reprodutivo", evento="Parto")]
    assert R.gestacao(a, regs) is None


def test_macho_nunca_tem_gestacao():
    assert R.gestacao(animal("2018-01-01", sexo="M"), [reg(d(-10), "reprodutivo", evento="Diagnóstico positivo", dataCobertura=d(-30))]) is None


def test_pendencias_documentais():
    a = animal("2026-01-15", registro="", dna="Sem exame", bloqueado=True)
    ts = [t for t in R.tarefas(HARAS, [a], [], prots()) if t.get("doc")]
    assert {t["titulo"] for t in ts} == {"Registro ABCCMM pendente", "Exame de DNA pendente", "Animal bloqueado na ABCCMM"}
    assert all(t["status"] == "pendente" for t in ts)


def test_animal_inativo_nao_gera_tarefas():
    assert R.tarefas(HARAS, [animal("2020-01-01", vivo=False)], [], prots()) == []


def test_status_por_prazo():
    assert R.status_de(d(-1)) == "atrasado"
    assert R.status_de(d(0)) == "hoje"
    assert R.status_de(d(7)) == "semana"
    assert R.status_de(d(30)) == "mes"
    assert R.status_de(d(31)) == "futuro"


def test_multivalente_atualiza_todas_as_doencas():
    a = animal("2015-01-01")
    regs = [reg(d(-10), "vacina", ["tetano", "encefalo", "influenza"])]
    for pid in ("tetano", "encefalo", "influenza"):
        assert R.proxima_etapa(HARAS, a, prots(pid)[0], regs)["due"] == d(355)
