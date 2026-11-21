"""Verificação visual e capturas do manual, na instância de demonstração.

Pré-requisitos: a API rodando com o Haras Demonstração e um administrador criados:
    python -m app.cli criar-admin --nome "Administrador Demonstração" --email admin@demonstracao.local --senha demonstracao123
    python -m app.cli demonstracao
Uso:
    python tests/visual/capturas.py http://127.0.0.1:8090 backend/app/static/ajuda

Percorre todas as telas do gestor, do caseiro e do administrador, falha se houver
erro de JavaScript e grava as capturas usadas no manual (Ajuda > Manual).
"""
import re
import sys
from pathlib import Path

import pyotp
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8090"
SAIDA = Path(sys.argv[2] if len(sys.argv) > 2 else "backend/app/static/ajuda")
SAIDA.mkdir(parents=True, exist_ok=True)
SENHA = "demonstracao123"
SEGREDOS = {}
ERROS = []


def _png_teste():
    """Imagem de teste (degradê) gerada sem bibliotecas externas."""
    import struct
    import zlib
    w, h = 600, 150
    raw = b"".join(b"\x00" + b"".join(bytes([min(255, 60 + x // 3), min(255, 80 + y), 70]) for x in range(w)) for y in range(h))
    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw)) + ch(b"IEND", b"")


IMG_TESTE = _png_teste()


def nova_pagina(ctx, nome):
    p = ctx.new_page()
    p.on("pageerror", lambda e: ERROS.append(f"[{nome}] {e}"))
    p.on("console", lambda m: m.type == "error" and not re.search(r"fonts\.g|cdnjs|ERR_|net::|status of 401", m.text) and ERROS.append(f"[{nome}] console: {m.text}"))
    return p


def foto(p, nome, pagina_inteira=False):
    p.wait_for_timeout(350)
    p.screenshot(path=str(SAIDA / f"{nome}.png"), full_page=pagina_inteira)


def entrar(p, email, captura_2fa=None):
    p.goto(BASE + "/entrar")
    if captura_2fa:  # tela de entrada com a marca da plataforma (v1.3.0)
        p.wait_for_selector("#marca-e .logo-sim, #marca-e img")
        foto(p, "entrar")
    p.fill("#email", email)
    p.fill("#senha", SENHA)
    p.click("#p-senha button.pri")
    p.wait_for_function("!location.pathname.startsWith('/entrar') || (document.querySelector('#p-cad') && (!document.querySelector('#p-cad').hidden || !document.querySelector('#p-2fa').hidden))")
    if not p.url.split("?")[0].endswith("/entrar"):
        p.wait_for_load_state("networkidle")
        return
    if p.is_visible("#p-cad"):
        p.wait_for_selector("#qr svg")
        seg = p.text_content("#segredo").replace(" ", "")
        SEGREDOS[email] = seg
        if captura_2fa:
            foto(p, captura_2fa)
        p.fill("#codigo-cad", pyotp.TOTP(seg).now())
        p.click("#p-cad button.pri")
        p.wait_for_selector("#p-codigos:not([hidden])")
        p.click("#continuar")
    elif p.is_visible("#p-2fa"):
        p.fill("#codigo", pyotp.TOTP(SEGREDOS[email]).now())
        p.click("#p-2fa button.pri")
    p.wait_for_load_state("networkidle")


def ir(p, view):
    alvo = p.locator(f'#menu-principal [data-act="nav"][data-v="{view}"]').first
    if not alvo.count():  # fora do menu lateral (o sino de avisos fica no cabeçalho)
        alvo = p.locator(f'[data-act="nav"][data-v="{view}"]').first
    elif not alvo.is_visible():  # está dentro de um grupo recolhido do menu lateral (v1.3.0)
        alvo.locator("xpath=ancestor::div[contains(@class,'sub')]/preceding-sibling::button").click()
    alvo.click()
    p.wait_for_timeout(300)
    p.wait_for_load_state("networkidle")


with sync_playwright() as pw:
    nav = pw.chromium.launch()
    desk = nav.new_context(viewport={"width": 1280, "height": 860}, locale="pt-BR", timezone_id="America/Sao_Paulo", bypass_csp=True)
    cel = nav.new_context(viewport={"width": 390, "height": 844}, locale="pt-BR", timezone_id="America/Sao_Paulo", is_mobile=True, has_touch=True, bypass_csp=True)

    # ---------- gestor ----------
    g = nova_pagina(desk, "gestor")
    entrar(g, "gestor@demonstracao.local", captura_2fa="2fa")
    g.wait_for_selector(".kpi2")
    foto(g, "painel")
    # v1.2.0: áudio do caseiro com player nos últimos registros do campo
    assert g.locator(".audio-reg audio").count() > 0, "falta o player de áudio nos registros do campo"
    g.locator(".audio-reg").first.scroll_into_view_if_needed()
    g.locator(".audio-reg").first.locator("xpath=ancestor::div[contains(@class,'card')][1]").screenshot(path=str(SAIDA / "audio-painel.png"))
    for v in ("sanidade", "reproducao", "animais", "importar", "agenda", "protocolos", "equipe", "parametros", "auditoria", "plano", "notificacoes", "assistente", "sobre", "glossario", "normas"):
        ir(g, v)
        assert g.inner_text("#view").strip(), f"tela vazia: {v}"
        if v in ("assistente", "normas"):  # v1.5.1: links para as normas da ABCCMM
            assert g.locator("a.norma").count() == 3, f"faltam os links das normas em {v}"
            assert g.get_attribute("a.norma", "target") == "_blank"
        if v == "normas":
            foto(g, "normas")
        if v in ("sanidade", "reproducao", "importar", "agenda", "equipe", "parametros", "auditoria"):
            if v in ("equipe", "auditoria"):
                g.wait_for_selector("#sessoes table, #aud-t table", timeout=5000)
            foto(g, v)
    # relatórios (v1.4.0): quatro abas com indicadores, gráficos e tabelas; exportação Excel e CSV
    ir(g, "relatorios")
    for aba in ("sanitario", "reprodutivo", "plantel", "campo"):
        g.click(f'[data-act="rel-tab"][data-t="{aba}"]')
        g.wait_for_selector(".rel-kpi")
        assert g.locator("#rel-corpo table").count() > 0, f"relatório sem tabela: {aba}"
        if aba in ("sanitario", "reprodutivo"):
            foto(g, "relatorios" if aba == "sanitario" else "relatorio-reprodutivo")
        for fmt in ("xlsx", "csv"):
            resp = g.request.get(BASE + g.get_attribute(f"#rel-{fmt}", "href"))
            assert resp.ok and len(resp.body()) > 200, f"exportação {fmt} falhou em {aba}"
    # cio (v1.4.0): formulário com os dados do exame
    ir(g, "reproducao")
    g.click('[data-act="registrar"]')
    g.select_option("#f-tipo", "reprodutivo")
    g.select_option("#f-evento", "Cio")
    g.wait_for_selector("#f-foliculo", state="visible")
    g.fill("#f-sinais", "Aceita o rufião")
    g.fill("#f-foliculo", "36")
    g.select_option("#f-ovario", "Direito")
    foto(g, "cio")
    g.click('[data-act="salvar-registro"]')
    g.wait_for_selector("#modal", state="hidden")
    # baixa (v1.4.0): filtro Baixados e janela de baixa
    ir(g, "animais")
    g.select_option("#sitF", "baixados")
    g.wait_for_selector("tr:has-text('FAROL DA VEREDA')")
    g.select_option("#sitF", "ativos")
    g.click("tr:has-text('CANELA DO RIACHO')")
    g.click('[data-act="dar-baixa"]')
    g.wait_for_selector("#b-motivo")
    foto(g, "baixa")
    g.click('#modal [data-act="fechar"]')
    # personalização (v1.3.0): o gestor envia o próprio banner e o Dashboard passa a usá-lo
    ir(g, "parametros")
    g.set_input_files("#img-banner", files=[{"name": "banner.png", "mimeType": "image/png", "buffer": IMG_TESTE}])
    g.wait_for_selector('[data-act="img-padrao"][data-tipo="banner"]', timeout=15000)
    foto(g, "imagens")
    ir(g, "painel")
    assert g.locator(".banner img.banner-img").count() == 1, "o banner do haras não apareceu no Dashboard"
    ir(g, "parametros")
    g.click('[data-act="img-padrao"][data-tipo="banner"]')
    g.click('[data-act="img-padrao"][data-tipo="banner"]')
    g.wait_for_selector('[data-act="img-padrao"][data-tipo="banner"]', state="detached", timeout=10000)
    ir(g, "animais")
    g.click("tr:has-text('BRISA DA SERRA AZUL')")
    g.wait_for_selector(".gest")
    foto(g, "ficha")
    for aba in ("agenda", "dados", "prontuario"):
        g.click(f'[data-act="tab"][data-t="{aba}"]')
    # vínculo do app Android do caseiro por QR Code (v1.1.0)
    ir(g, "equipe")
    g.click('[data-act="vincular-celular"]')
    g.wait_for_selector(".qr-box svg")
    foto(g, "vincular")
    g.click('#modal [data-act="fechar"]')
    # registro com o formulário pré-preenchido a partir de uma tarefa
    ir(g, "agenda")
    g.locator('[data-act="registrar-tarefa"]').first.click()
    g.wait_for_selector("#fr")
    g.fill("#f-obs", "Registro da verificação visual")
    g.click('[data-act="salvar-registro"]')
    g.wait_for_selector("#modal", state="hidden")

    # ---------- caseiro no celular ----------
    k = nova_pagina(cel, "campo")
    entrar(k, "caseiro@demonstracao.local")
    k.wait_for_selector(".cnt")
    foto(k, "campo")
    assert k.is_visible('[data-act="instalar-app"]'), "falta o botão Instalar o app Android no Portal Campo"
    for v in ("animais", "agenda", "mais", "hoje"):  # navegação v1.3.0: Hoje, Animais, Agenda e Mais
        k.click(f'#tnav [data-v="{v}"]')
        k.wait_for_timeout(200)
        if v == "mais":
            k.click('.mais [data-v="avisos"]')
            k.wait_for_timeout(200)

    # ---------- gestor no celular: menu hambúrguer ----------
    cel2 = nav.new_context(viewport={"width": 390, "height": 844}, locale="pt-BR", timezone_id="America/Sao_Paulo", is_mobile=True, has_touch=True, bypass_csp=True)
    gm = nova_pagina(cel2, "gestor-celular")
    entrar(gm, "gestor@demonstracao.local")
    gm.click('[data-act="hamb"]')
    assert gm.is_visible("#menu-principal"), "menu do celular não abriu"
    ir(gm, "equipe")
    larg = gm.evaluate("document.documentElement.scrollWidth")
    assert larg <= 392, f"rolagem horizontal no celular ({larg}px)"

    # ---------- administrador ----------
    desk2 = nav.new_context(viewport={"width": 1280, "height": 860}, locale="pt-BR", timezone_id="America/Sao_Paulo", bypass_csp=True)
    a = nova_pagina(desk2, "admin")
    entrar(a, "admin@demonstracao.local")
    a.wait_for_selector(".hcard")
    foto(a, "admin-haras")
    for v, nome in (("marca", "admin-marca"), ("administradores", "admin-administradores"), ("parametros", "admin-parametros"), ("atualizacao", "admin-atualizacao"), ("auditoria", None), ("sobre", None), ("glossario", None)):
        ir(a, v)
        if v == "auditoria":
            a.wait_for_selector("#aud-t table")
        if nome:
            foto(a, nome)
        if v == "parametros":  # v1.5.0: liberação de teste do app do gestor sem HTTPS (bloqueada por padrão)
            kv = a.locator('.kv:has([data-act="g-semhttps"])')
            assert kv.locator('[data-act="g-semhttps"][data-v="0"][aria-pressed="true"]').count() == 1, "app do gestor sem HTTPS deveria vir bloqueado"
            kv.scroll_into_view_if_needed()
            kv.screenshot(path=str(SAIDA / "admin-app-gestor.png"))
    nav.close()

if ERROS:
    print("Erros de JavaScript encontrados:")
    print("\n".join(ERROS))
    sys.exit(1)
print(f"Verificação visual concluída sem erros. Capturas em {SAIDA}")
