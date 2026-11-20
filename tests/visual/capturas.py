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
    alvo = p.locator(f'[data-act="nav"][data-v="{view}"]').first
    if not alvo.is_visible():  # está dentro de um menu agrupado
        grupo = alvo.locator("xpath=ancestor::div[contains(@class,'drop-m')]/preceding-sibling::button")
        grupo.click()
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
    g.wait_for_selector(".kpi")
    foto(g, "painel")
    for v in ("animais", "importar", "agenda", "protocolos", "equipe", "parametros", "auditoria", "plano", "notificacoes", "assistente", "sobre", "glossario"):
        ir(g, v)
        assert g.inner_text("#view").strip(), f"tela vazia: {v}"
        if v in ("importar", "agenda", "equipe", "parametros", "auditoria"):
            if v in ("equipe", "auditoria"):
                g.wait_for_selector("#sessoes table, #aud-t table", timeout=5000)
            foto(g, v)
    ir(g, "animais")
    g.click("tr:has-text('BRISA DA SERRA AZUL')")
    g.wait_for_selector(".gest")
    foto(g, "ficha")
    for aba in ("agenda", "dados", "prontuario"):
        g.click(f'[data-act="tab"][data-t="{aba}"]')
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
    for v in ("animais", "avisos", "assistente", "hoje"):
        k.click(f'#tnav [data-v="{v}"]')
        k.wait_for_timeout(200)

    # ---------- gestor no celular: menu hambúrguer ----------
    cel2 = nav.new_context(viewport={"width": 390, "height": 844}, locale="pt-BR", timezone_id="America/Sao_Paulo", is_mobile=True, has_touch=True, bypass_csp=True)
    gm = nova_pagina(cel2, "gestor-celular")
    entrar(gm, "gestor@demonstracao.local")
    gm.click('[data-act="hamb"]')
    assert gm.is_visible("#menu-principal"), "menu do celular não abriu"
    gm.click('#menu-principal [data-v="equipe"]')
    larg = gm.evaluate("document.documentElement.scrollWidth")
    assert larg <= 392, f"rolagem horizontal no celular ({larg}px)"

    # ---------- administrador ----------
    desk2 = nav.new_context(viewport={"width": 1280, "height": 860}, locale="pt-BR", timezone_id="America/Sao_Paulo", bypass_csp=True)
    a = nova_pagina(desk2, "admin")
    entrar(a, "admin@demonstracao.local")
    a.wait_for_selector(".hcard")
    foto(a, "admin-haras")
    for v, nome in (("parametros", "admin-parametros"), ("atualizacao", "admin-atualizacao"), ("auditoria", None), ("sobre", None), ("glossario", None)):
        ir(a, v)
        if v == "auditoria":
            a.wait_for_selector("#aud-t table")
        if nome:
            foto(a, nome)
    nav.close()

if ERROS:
    print("Erros de JavaScript encontrados:")
    print("\n".join(ERROS))
    sys.exit(1)
print(f"Verificação visual concluída sem erros. Capturas em {SAIDA}")
