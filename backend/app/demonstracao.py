"""Instância de demonstração com plantel fictício (para testes visuais, capturas do manual e apresentações).

Todos os nomes, registros e microchips são inventados.
"""
from datetime import timedelta

from sqlalchemy import select

from . import regras as R
from .db import Animal, Haras, Registro, Usuario
from .seguranca import hash_senha

NOME_HARAS = "Haras Demonstração"


def _r(db, hid, aid, data, tipo, autor, origem, n, **kw):
    dados = {k: kw.pop(k) for k in list(kw) if k in ("produto", "lote", "ferrador", "resultado", "exame", "procedimento", "evento", "garanhao",
                                                      "dataCobertura", "titulo", "gravidade", "sinais", "ovario", "foliculo", "edema")}
    db.add(Registro(id=f"demo{n:04d}", haras_id=hid, animal_id=aid, data=R.d(data), tipo=tipo, protocolos=kw.get("protocolos", []),
                    dose=str(kw.get("dose", "unica")), obs=kw.get("obs", ""), dados=dados, autor=autor, origem=origem))


def criar(db, gestor_email, gestor_senha, caseiro_email, caseiro_senha):
    from .rotas_admin import criar_haras_com_gestor
    if db.scalar(select(Haras).where(Haras.nome == NOME_HARAS)):
        raise SystemExit("O haras de demonstração já existe.")
    h, g = criar_haras_com_gestor(db, NOME_HARAS, "Aracaju/SE", None, "Gestor Demonstração", gestor_email, gestor_senha)
    db.add(Usuario(haras_id=h.id, nome="Caseiro Demonstração", email=caseiro_email.lower(), senha_hash=hash_senha(caseiro_senha), perfil="operador"))
    T = R.hoje()
    a = lambda n: (T - timedelta(days=n)).isoformat()  # noqa: E731
    animais = [
        ("d1", "AURORA DO VALE VERDE", "MM6 - DEFINITIVO FECHADO FÊMEA", "0900101", "F", "DNA - VP", "2016-03-10", "900000000000101"),
        ("d2", "BRISA DA SERRA AZUL", "MM6 - DEFINITIVO FECHADO FÊMEA", "0900102", "F", "DNA - VP", "2020-10-02", "900000000000102"),
        ("d3", "CANELA DO RIACHO", "MM6 - DEFINITIVO FECHADO FÊMEA", "0900103", "F", "DNA - VP", "2022-05-18", "900000000000103"),
        ("d4", "DOURADO DA CAATINGA", "", "", "M", "Sem exame", "2026-02-20", "900000000000104"),
        ("d5", "ESTRELO DO SERTÃO", "MM5 - DEFINITIVO FECHADO MACHO", "090105", "M", "DNA - VP", "2021-11-30", "900000000000105"),
        ("d6", "FAROL DA VEREDA", "MM5 - DEFINITIVO FECHADO MACHO", "090106", "M", "DNA - VP", "2019-08-14", "900000000000106"),
    ]
    ids = {}
    for k, nome, livro, reg, sexo, dna, nasc, chip in animais:
        an = Animal(id=f"{k}-{h.id}", haras_id=h.id, nome=nome, livro=livro, registro=reg, sexo=sexo, dna=dna, nascimento=R.d(nasc), chip=chip,
                    vivo=True, bloqueado=False, genealogia={"mae": "AURORA DO VALE VERDE"} if k == "d4" else {}, origem="Demonstração")
        if k == "d6":  # v1.4.0: animal vendido, para o relatório do plantel
            an.vivo, an.baixa_data, an.baixa_motivo, an.baixa_destino = False, T - timedelta(days=45), "Venda", "Haras Boa Esperança"
        db.add(an)
        ids[k] = an.id
    db.flush()
    G, C = ("Gestor Demonstração", "Portal Gestor"), ("Caseiro Demonstração", "Portal Cliente")
    tri = ["tetano", "encefalo", "influenza"]
    n = 0

    def reg(k, data, tipo, quem=G, **kw):
        nonlocal n
        n += 1
        _r(db, h.id, ids[k], data, tipo, quem[0], quem[1], n, **kw)

    reg("d1", a(250), "vacina", protocolos=["raiva"], dose="reforco", produto="Vacina antirrábica", lote="LT0101")
    reg("d1", a(200), "vacina", protocolos=["tetano", "encefalo"], dose="reforco", produto="Bivalente tétano + encefalomielite", lote="LT0102")
    reg("d1", a(395), "vacina", protocolos=["influenza"], dose="reforco", produto="Influenza equina", lote="LT0103")
    reg("d1", a(300), "vacina", protocolos=["rino"], dose="reforco", produto="Herpesvírus equino", lote="LT0104")
    reg("d1", a(150), "vacina", protocolos=["lepto"], dose="reforco", produto="Leptospirose equina", lote="LT0105")
    reg("d1", a(95), "vermifugacao", protocolos=["vermi"], produto="Ivermectina + praziquantel")
    reg("d1", a(340), "odontologia", protocolos=["odonto"], procedimento="Avaliação e correção")
    reg("d1", a(40), "ferrageamento", C, protocolos=["ferrag"], ferrador="Ferrador da região", obs="Quatro patas")
    reg("d1", a(50), "exame", protocolos=["aie"], exame="Anemia Infecciosa (AIE)", resultado="Negativo")
    reg("d2", a(215), "reprodutivo", evento="Cobertura", garanhao="ESTRELO DO SERTÃO")
    reg("d2", a(190), "reprodutivo", evento="Diagnóstico positivo", dataCobertura=a(215), garanhao="ESTRELO DO SERTÃO", obs="Ultrassonografia aos 25 dias")
    reg("d2", a(60), "vacina", protocolos=["rino"], dose="reforco", produto="Herpesvírus equino", lote="LT0201", obs="Dose do 5º mês")
    reg("d2", a(100), "vacina", protocolos=["raiva"], dose="reforco", produto="Vacina antirrábica", lote="LT0202")
    reg("d2", a(100), "vacina", protocolos=tri, dose="reforco", produto="Trivalente", lote="LT0203")
    reg("d2", a(170), "vacina", protocolos=["lepto"], dose="reforco", produto="Leptospirose equina", lote="LT0204")
    reg("d2", a(30), "vermifugacao", C, protocolos=["vermi"], produto="Pamoato de pirantel")
    reg("d3", a(370), "vacina", protocolos=["raiva"], dose="reforco", produto="Vacina antirrábica", lote="LT0301")
    reg("d3", a(120), "vacina", protocolos=tri, dose="reforco", produto="Trivalente", lote="LT0302")
    reg("d3", a(120), "vacina", protocolos=["rino"], dose="reforco", produto="Herpesvírus equino", lote="LT0303")
    reg("d3", a(90), "vacina", protocolos=["lepto"], dose="reforco", produto="Leptospirose equina", lote="LT0304")
    reg("d3", a(88), "vermifugacao", C, protocolos=["vermi"], produto="Ivermectina")
    reg("d3", a(700), "odontologia", protocolos=["aparelho"], procedimento="Aparelho dentário instalado")
    reg("d2", a(200), "odontologia", protocolos=["odonto"], procedimento="Avaliação", obs="Sem alterações")
    reg("d3", a(100), "odontologia", protocolos=["odonto"], procedimento="Avaliação", obs="Acompanhar aparelho")
    reg("d5", a(30), "odontologia", protocolos=["odonto"], procedimento="Avaliação e correção")
    reg("d4", a(60), "vermifugacao", C, protocolos=["vermi"], produto="Fembendazol", obs="Dose ajustada ao peso")
    reg("d5", a(20), "vacina", protocolos=["raiva"], dose="reforco", produto="Vacina antirrábica", lote="LT0501")
    reg("d5", a(20), "vacina", protocolos=tri, dose="reforco", produto="Trivalente", lote="LT0502")
    reg("d5", a(20), "vacina", protocolos=["rino", "lepto"], dose="reforco", produto="Rino + lepto", lote="LT0503")
    reg("d5", a(20), "vermifugacao", C, protocolos=["vermi"], produto="Ivermectina + praziquantel")
    reg("d5", a(44), "ferrageamento", C, protocolos=["ferrag"], ferrador="Ferrador da região")
    reg("d5", a(58), "exame", protocolos=["aie"], exame="Anemia Infecciosa (AIE)", resultado="Negativo")
    reg("d5", a(58), "exame", protocolos=["mormo"], exame="Mormo", resultado="Negativo")
    reg("d5", a(3), "ocorrencia", C, titulo="Corte superficial no boleto", gravidade="Leve", obs="Limpeza e spray cicatrizante.")
    # v1.4.0: histórico reprodutivo da Aurora (dois partos, cio com exame e cobertura) e cio da Canela
    reg("d1", "2025-01-25", "reprodutivo", evento="Parto", obs="Potra saudável")
    reg("d1", "2026-02-20", "reprodutivo", evento="Parto", obs="Nasceu o Dourado")
    reg("d1", a(12), "reprodutivo", C, evento="Cio", sinais="Aceita o rufião, urina frequente")
    reg("d1", a(11), "reprodutivo", evento="Cio", ovario="Esquerdo", foliculo="38", edema="2", obs="Exame do veterinário")
    reg("d1", a(10), "reprodutivo", evento="Cobertura", garanhao="ESTRELO DO SERTÃO")
    reg("d3", a(25), "reprodutivo", ("Caseiro Demonstração", "App"), evento="Cio", sinais="Inquieta, cauda levantada")
    nasc4 = R.d("2026-02-20")
    reg("d4", R.iso(R.add_meses(nasc4, 3)), "vacina", protocolos=tri, dose=1, produto="Trivalente", lote="LT0401")
    reg("d4", R.iso(R.add_meses(nasc4, 4)), "vacina", protocolos=tri, dose=2, produto="Trivalente", lote="LT0401")
    reg("d4", a(1), "ocorrencia", ("Caseiro Demonstração", "App"), titulo="Potro com leve secreção nasal", gravidade="Moderada",
        obs="Gravei um áudio explicando.")
    db.flush()
    _audio_demo(db, h.id)
    db.commit()
    return h


def _audio_demo(db, hid):
    """Áudio de exemplo (tom de 6 segundos) no último registro feito pelo app (v1.2.0)."""
    import shutil
    from pathlib import Path

    from .config import FOTOS_DIR
    from .db import Audio
    rg = db.scalar(select(Registro).where(Registro.haras_id == hid, Registro.origem == "App").order_by(Registro.id.desc()))
    if not rg:
        return
    pasta = Path(FOTOS_DIR) / str(hid)
    pasta.mkdir(parents=True, exist_ok=True)
    aid = "d" * 8 + "0" * 24
    shutil.copy(Path(__file__).parent / "recursos" / "demo-audio.m4a", pasta / f"{aid}.m4a")
    db.add(Audio(id=aid, registro_id=rg.id, haras_id=hid, arquivo=f"{aid}.m4a", duracao=6))
