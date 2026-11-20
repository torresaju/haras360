"""Personalização por imagens (v1.3.0): marca da plataforma e imagens de cada haras."""
import base64

from fastapi.testclient import TestClient

from app.main import app
from test_api import H, PNG, entrar

PNG_BYTES = base64.b64decode(PNG.split(",", 1)[1])
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 40


def _env(c, url, dados=WEBP, foco="centro", nome="i.webp"):
    return c.post(url, data={"foco": foco}, files={"arquivo": (nome, dados, "image/webp")}, headers=H)


def test_padrao_sem_imagens(base):
    g = entrar("gestor@teste.com", "senha1234")
    im = g.get("/api/estado").json()["imagens"]
    assert set(im) == {"logo", "entrada", "cabecalho", "banner", "app"} and all(v is None for v in im.values())
    assert TestClient(app).get("/api/marca").json() == {"logo": None, "entrada": None}


def test_plataforma_define_padrao_e_haras_sobrepoe(base):
    adm = entrar("admin@teste.com", "admin1234")
    assert _env(adm, "/api/admin/marca/logo", PNG_BYTES, nome="l.png").status_code == 200
    assert _env(adm, "/api/admin/marca/banner", foco="topo").status_code == 200
    pub = TestClient(app).get("/api/marca").json()
    assert pub["logo"]["url"].startswith("/marca/logo?v=")
    r = TestClient(app).get(pub["logo"]["url"])  # pública: a entrada aparece antes do login
    assert r.status_code == 200 and r.content == PNG_BYTES and "public" in r.headers["cache-control"]

    g = entrar("gestor@teste.com", "senha1234")
    im = g.get("/api/estado").json()["imagens"]
    assert im["banner"]["origem"] == "plataforma" and im["banner"]["foco"] == "topo"
    # o haras envia o próprio banner e passa a vê-lo no lugar do padrão
    assert _env(g, "/api/haras/imagens/banner", foco="base").status_code == 200
    im = g.get("/api/estado").json()["imagens"]
    assert im["banner"]["origem"] == "haras" and im["banner"]["url"].startswith("/imagens/banner?v=")
    assert g.get(im["banner"]["url"]).content == WEBP
    # outro haras continua com o padrão da plataforma e não enxerga a imagem do primeiro
    o = entrar("outro@teste.com", "senha1234")
    assert o.get("/api/estado").json()["imagens"]["banner"]["origem"] == "plataforma"
    assert o.get("/imagens/banner").status_code == 404
    assert TestClient(app).get("/imagens/banner").status_code == 401
    # ponto de foco e volta ao padrão
    assert g.patch("/api/haras/imagens/banner", json={"foco": "topo"}, headers=H).json()["imagens"]["banner"]["foco"] == "topo"
    assert g.delete("/api/haras/imagens/banner", headers=H).json()["imagens"]["banner"]["origem"] == "plataforma"
    acoes = [a["acao"] for a in g.get("/api/auditoria").json()]
    assert "imagem_alterada" in acoes and "imagem_removida" in acoes
    # limpa a marca para os outros testes
    adm.delete("/api/admin/marca/logo", headers=H)
    adm.delete("/api/admin/marca/banner", headers=H)
    assert TestClient(app).get("/api/marca").json()["logo"] is None


def test_validacoes(base):
    g = entrar("gestor@teste.com", "senha1234")
    assert _env(g, "/api/haras/imagens/banner", b"<svg onload=alert(1)>").status_code == 400  # SVG/HTML recusado
    assert _env(g, "/api/haras/imagens/banner", b"RIFF\x00\x00\x00\x00AVI " + b"\x00" * 20).status_code == 400
    assert _env(g, "/api/haras/imagens/banner", WEBP + b"\x00" * (3 * 1024 * 1024)).status_code == 400
    assert _env(g, "/api/haras/imagens/banner", foco="esquerda").status_code == 400
    assert _env(g, "/api/haras/imagens/logo").status_code == 404  # logotipo do haras tem rota própria
    assert _env(g, "/api/admin/marca/logo").status_code == 403  # gestor não mexe na marca da plataforma
    k = entrar("caseiro@teste.com", "campo1234", {"X-Haras360": "1", "X-Portal": "campo"})
    assert _env(k, "/api/haras/imagens/banner").status_code == 403  # caseiro só vê


def test_app_recebe_imagens_na_sincronizacao(base):
    from test_app import _vincular
    g = entrar("gestor@teste.com", "senha1234")
    assert _env(g, "/api/haras/imagens/app").status_code == 200
    _q, v = _vincular(g)
    a = TestClient(app, headers={"Authorization": f"Bearer {v['token']}"})
    im = a.get("/api/app/sincronizar").json()["imagens"]
    assert im["app"]["origem"] == "haras" and im["app"]["versao"] > 0
    assert a.get(im["app"]["url"]).content == WEBP  # o app baixa com o token do aparelho
    g.delete("/api/haras/imagens/app", headers=H)
