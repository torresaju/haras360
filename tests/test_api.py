"""Testes da API: login, perfis, importação, registros, fotos e configurações."""
import base64

import pytest
from fastapi.testclient import TestClient

from app import regras as R
from app.db import Haras, Protocolo, SessionLocal, Usuario, iniciar_banco
from app.main import app, hash_senha

H = {"X-Haras360": "1", "X-Portal": "gestor"}
PNG = "data:image/png;base64," + base64.b64encode(bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201a1b6d5e20000000049454e44ae426082")).decode()
PLANTEL = [
    {"nome": "BERIBELA DA TERRARUNA", "livro": "MM6 - DEFINITIVO FECHADO FÊMEA", "registro": "0185916", "sexo": "F", "bloqueado": False, "vivo": True, "dna": "DNA - VP", "nascimento": "2017-01-13", "chip": "982000409602729"},
    {"nome": "NETO VÓ PQNA", "livro": "", "registro": "", "sexo": "M", "bloqueado": False, "vivo": True, "dna": "Sem exame", "nascimento": "2026-01-15", "chip": "963003101075189"},
]


@pytest.fixture(scope="module")
def base():
    iniciar_banco()
    db = SessionLocal()
    h = Haras(nome="Haras Teste", proprietario="Gestor", notif_prefs=R.notif_prefs_padrao())
    db.add(h)
    db.flush()
    for p in R.protocolos_padrao():
        db.add(Protocolo(haras_id=h.id, pid=p["id"], dados=p))
    db.add(Usuario(haras_id=h.id, nome="Gestor Teste", email="gestor@teste.com", senha_hash=hash_senha("senha1234"), perfil="gestor"))
    db.add(Usuario(haras_id=h.id, nome="Caseiro Teste", email="caseiro@teste.com", senha_hash=hash_senha("campo1234"), perfil="operador"))
    db.commit()
    return h.id


def cliente(email, senha):
    c = TestClient(app)
    r = c.post("/api/login", json={"email": email, "senha": senha}, headers=H)
    assert r.status_code == 200, r.text
    return c


def test_login_errado(base):
    c = TestClient(app)
    assert c.post("/api/login", json={"email": "gestor@teste.com", "senha": "x"}, headers=H).status_code == 401


def test_post_sem_cabecalho_recusado(base):
    assert TestClient(app).post("/api/login", json={}).status_code == 403


def test_estado_exige_login(base):
    assert TestClient(app).get("/api/estado").status_code == 401


def test_importacao_e_reimportacao(base):
    c = cliente("gestor@teste.com", "senha1234")
    r = c.post("/api/importacao", json={"arquivo": "Plantel.pdf", "associado": "ASSOCIADO", "impresso": "2026-09-02", "animais": PLANTEL}, headers=H)
    assert r.json()["novos"] == 2
    r = c.post("/api/importacao", json={"animais": PLANTEL}, headers=H)
    assert r.json() == {"novos": 0, "atualizados": 2, "resumo": r.json()["resumo"]}
    e = c.get("/api/estado").json()
    assert len(e["animais"]) == 2
    docs = {t["titulo"] for t in e["tarefas"] if t.get("doc")}
    assert docs == {"Registro ABCCMM pendente", "Exame de DNA pendente"}


def test_caseiro_registra_com_foto_e_gestor_ve(base):
    g = cliente("gestor@teste.com", "senha1234")
    animal = g.get("/api/estado").json()["animais"][0]
    k = cliente("caseiro@teste.com", "campo1234")
    r = k.post("/api/registros", json={"animalId": animal["id"], "data": R.iso(R.hoje()), "tipo": "ocorrencia", "titulo": "Mancando", "gravidade": "Leve", "fotos": [PNG]}, headers=dict(H, **{"X-Portal": "campo"}))
    assert r.status_code == 200, r.text
    regs = g.get("/api/estado").json()["registros"]
    reg = next(x for x in regs if x["id"] == r.json()["id"])
    assert reg["origem"] == "Portal Cliente" and reg["autor"] == "Caseiro Teste"
    assert g.get(reg["fotos"][0]).status_code == 200
    assert TestClient(app).get(reg["fotos"][0]).status_code == 401


def test_perfil_caseiro_restrito(base):
    k = cliente("caseiro@teste.com", "campo1234")
    assert k.post("/api/animais", json={"nome": "X"}, headers=H).status_code == 403
    assert k.put("/api/protocolos", json=[], headers=H).status_code == 403
    assert k.get("/api/estado").json()["usuarios"] == []


def test_validacoes_de_registro(base):
    g = cliente("gestor@teste.com", "senha1234")
    a = g.get("/api/estado").json()["animais"][0]
    futuro = R.iso(R.add_dias(R.hoje(), 3))
    assert g.post("/api/registros", json={"animalId": a["id"], "data": futuro, "tipo": "vermifugacao"}, headers=H).status_code == 400
    assert g.post("/api/registros", json={"animalId": a["id"], "data": R.iso(R.hoje()), "tipo": "vacina"}, headers=H).status_code == 400
    assert g.post("/api/registros", json={"animalId": a["id"], "data": R.iso(R.hoje()), "tipo": "ocorrencia", "fotos": ["data:image/png;base64,AAAA"], "titulo": "x"}, headers=H).status_code == 400


def test_protocolos_e_raiva(base):
    g = cliente("gestor@teste.com", "senha1234")
    assert g.put("/api/protocolos", json=[{"id": "vermi", "reforcoDias": 60}], headers=H).status_code == 200
    assert next(p for p in g.get("/api/estado").json()["protocolos"] if p["id"] == "vermi")["reforcoDias"] == 60
    assert g.put("/api/protocolos", json=[{"id": "vermi", "reforcoDias": 0}], headers=H).status_code == 400
    assert g.put("/api/haras", json={"raivaSemestral": True}, headers=H).status_code == 200
    assert g.get("/api/estado").json()["haras"]["raivaSemestral"] is True


def test_troca_de_senha_encerra_sessoes_antigas(base):
    antiga = cliente("caseiro@teste.com", "campo1234")
    nova = cliente("caseiro@teste.com", "campo1234")
    assert nova.post("/api/me/senha", json={"atual": "campo1234", "nova": "outra1234"}, headers=H).status_code == 200
    assert nova.get("/api/me").status_code == 200
    assert antiga.get("/api/me").status_code == 401
    assert nova.post("/api/me/senha", json={"atual": "outra1234", "nova": "campo1234"}, headers=H).status_code == 200


def test_paginas_e_saude(base):
    c = TestClient(app)
    for p in ("/entrar", "/gestor", "/campo", "/api/saude"):
        assert c.get(p).status_code == 200
