"""Certificado de registro da ABCCMM (v1.6.0), com um certificado fictício montado na posição do original."""
import json

import pytest

from app import certificado as C
from pdf_teste import certificado_teste, pdf_de_linhas
from test_api import H, entrar


def test_leitura_completa():
    d = C.ler(certificado_teste())
    assert (d["nome"], d["registro"], d["livro"], d["nascimento"], d["sexo"], d["dna"], d["chip"], d["pelagem"]) == (
        "BERIBELA DE TESTE", "0185916", "MM6 - DEFINITIVO FECHADO FÊMEA", "2017-01-13", "F", "DNA - VP", "900000000000999", "TORDILHA")
    assert (d["volume"], d["pagina"], d["classificacao"], d["dataResenha"], d["dataRegistro"]) == ("310", "516", "A2", "2020-10-20", "2020-12-16")
    assert d["criador"] == {"nome": "JOÃO CRIADOR DE TESTE", "cadastro": "11111-1", "propriedade": "HARAS DO CRIADOR", "municipio": "Brasília", "uf": "DF"}
    assert d["proprietario"]["nome"] == "MARIA PROPRIETÁRIA DE TESTE" and d["proprietario"]["uf"] == "SE"
    assert d["mensuracoes"]["altura"] == {"Cernelha": 1.44, "Garupa": 1.43}
    assert d["mensuracoes"]["comprimento"]["Cabeça"] == 0.51 and d["mensuracoes"]["perimetro"]["Tórax"] == 1.63
    g = d["genealogia"]
    assert (g["pai"], g["mae"], g["avoPaterno"], g["avoMaterna"]) == ("ANJO DA TODAY", "CIGANA DA CHALANA", "ALEGRE DA TODAY", "AFRODITE AMERUJ")
    arv = {n["pos"]: n for n in g["arvore"]}
    assert len(arv) == 22  # 30 posições, 8 desconhecidas ("*****")
    assert arv["P"]["registro"] == "044255" and arv["P"]["dna"] == "DNA - VP" and arv["P"]["livro"] == "MM5"
    assert arv["PMP"]["nome"] == "TRUC DO MORRO GRANDE" and arv["PMP"]["livro"] == "MM5 / MM7"
    assert arv["MMMM"]["nome"] == "UBERABA B.R." and "PPP" not in arv


def test_pdf_invalido():
    with pytest.raises(C.CertificadoInvalido, match="não é um PDF"):
        C.ler(b"texto qualquer")
    with pytest.raises(C.CertificadoInvalido, match="não é um Certificado"):
        C.ler(pdf_de_linhas([[50, 50, "Relatório qualquer"]]))


@pytest.fixture(scope="module")
def g(base):
    return entrar("gestor@teste.com", "senha1234")


def _arq(pdf, nome="cert.pdf"):
    return ("arquivos", (nome, pdf, "application/pdf"))


def test_previa_e_criacao_por_certificado(g):
    r = g.post("/api/certificados/previa", files=[_arq(certificado_teste()), _arq(b"nada", "ruim.pdf")], headers=H)
    assert r.status_code == 200, r.text
    c, ruim = r.json()["certificados"]
    assert c["situacao"] == "novo" and c["dados"]["nome"] == "BERIBELA DE TESTE" and not ruim["ok"]
    gv = g.post("/api/certificados/gravar", files=[_arq(certificado_teste()), _arq(b"nada", "ruim.pdf")],
                data={"acoes": json.dumps([{"acao": "criar"}, {"acao": "ignorar"}])}, headers=H)
    assert gv.status_code == 200, gv.text
    aid = gv.json()["ids"][0]
    a = next(x for x in g.get("/api/estado").json()["animais"] if x["id"] == aid)
    assert a["registro"] == "0185916" and a["origem"] == "Certificado ABCCMM" and a["certificado"]["criador"]["cadastro"] == "11111-1"
    assert len(a["genealogia"]["arvore"]) == 22 and a["genealogia"]["mae"] == "CIGANA DA CHALANA"
    pdf = g.get(f"/api/animais/{aid}/certificado.pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    # o mesmo certificado de novo: reconhece o animal e não há o que mudar
    c2 = g.post("/api/certificados/previa", files=[_arq(certificado_teste())], headers=H).json()["certificados"][0]
    assert c2["situacao"] == "igual" and c2["animalId"] == aid
    # editar os dados à mão mantém a árvore completa
    g.put(f"/api/animais/{aid}", json={"nome": "BERIBELA DE TESTE", "sexo": "F", "nascimento": "2017-01-13", "registro": "0185916",
                                       "genealogia": {"pai": "ANJO DA TODAY"}}, headers=H)
    a = next(x for x in g.get("/api/estado").json()["animais"] if x["id"] == aid)
    assert len(a["genealogia"]["arvore"]) == 22


def test_atualizar_ficha_e_conflitos(g):
    aid = g.post("/api/animais", json={"nome": "Estrela Sem Certificado", "sexo": "F", "nascimento": "2018-05-05"}, headers=H).json()["id"]
    outro = certificado_teste(**{"BERIBELA DE TESTE": "ESTRELA SEM CERTIFICADO", "0185916": "0777777", "900000000000999": "900000000000777"})
    p = g.post("/api/certificados/previa", files=[_arq(outro)], data={"animalId": aid}, headers=H).json()["certificados"][0]
    assert p["situacao"] == "atualizar" and any(x["campo"] == "Registro" and x["depois"] == "0777777" for x in p["diferencas"])
    gv = g.post("/api/certificados/gravar", files=[_arq(outro)], data={"acoes": json.dumps([{"acao": "atualizar", "animalId": aid}])}, headers=H).json()
    assert gv["ids"] == [aid]
    a = next(x for x in g.get("/api/estado").json()["animais"] if x["id"] == aid)
    assert a["registro"] == "0777777" and a["nascimento"] == "2017-01-13" and a["pelagem"] == "TORDILHA"
    # registro que já é de outro animal: avisa na prévia e não grava
    p = g.post("/api/certificados/previa", files=[_arq(certificado_teste())], data={"animalId": aid}, headers=H).json()["certificados"][0]
    assert any("já pertence" in x for x in p["avisos"]) and any("diferente" in x for x in p["avisos"])
    gv = g.post("/api/certificados/gravar", files=[_arq(certificado_teste())], data={"acoes": json.dumps([{"acao": "anexar", "animalId": aid}])}, headers=H).json()
    assert gv["ids"] == [None] and "já pertence" in gv["falhas"][0]


def test_caseiro_nao_usa_certificado(base):
    from test_api import HC
    c = entrar("caseiro@teste.com", "campo1234", HC)
    assert c.post("/api/certificados/previa", files=[_arq(certificado_teste())], headers=HC).status_code == 403
