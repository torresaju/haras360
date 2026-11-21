"""Parametrizações do Haras360: globais (administrador) e por haras (gestor).

Nada que o negócio possa querer mudar fica fixo no código. Cada chave tem um
valor padrão aqui; o banco guarda apenas o que foi alterado.
"""
import copy

from sqlalchemy import select

from .db import Parametro

MODULOS = {
    "importacao": "Importação ABCCMM",
    "assistente": "Assistente ABCCMM",
    "caseiro": "Usuário caseiro (app e Portal Campo)",
    "audio": "Áudio nos registros do app",
    "relatorios": "Relatórios e exportação",
}

PADRAO_GLOBAL = {
    # Planos: cada um define o limite de animais ativos e os módulos liberados.
    "planos": {
        "Padrão": {"limite": 30, "modulos": {m: True for m in MODULOS}},
    },
    # Mensalidade por faixa de animais ativos. Valores em branco até a definição comercial.
    "faixas": [
        {"de": 1, "ate": 3, "valor": 0},
        {"de": 4, "ate": 10, "valor": None},
        {"de": 11, "ate": 20, "valor": None},
        {"de": 21, "ate": 30, "valor": None},
    ],
    "login_tentativas": 8,
    "login_janela_min": 15,
    "sessao_dias": 7,
    "sessao_app_dias": 90,
    # App do gestor (v1.5.0): sessão expira após N dias sem uso; exige HTTPS, salvo a chave de teste
    "sessao_app_gestor_dias": 30,
    "app_gestor_sem_https": False,
    "audio_max_seg": 120,
    "smtp": {"host": "", "porta": 587, "usuario": "", "senha": "", "remetente": "", "tls": True},
    "email_contato": "",
}

PADRAO_HARAS = {
    "gestacaoDias": 340,
    "toleranciaReinicio": 15,
    # Reprodução (v1.4.0): previsão do cio e janela do cio do potro
    "previsaoCio": True,
    "cicloDias": 21,
    "cioPotroDe": 7,
    "cioPotroAte": 12,
    # v1.5.0: ocorrência grave do caseiro vira aviso crítico (tipo "ocorrencia")
    "avisoOcorrenciaGrave": True,
}

LIMITES = {
    "login_tentativas": (3, 50),
    "login_janela_min": (1, 1440),
    "sessao_dias": (1, 90),
    "sessao_app_dias": (7, 365),
    "sessao_app_gestor_dias": (7, 90),
    "audio_max_seg": (15, 300),
    "gestacaoDias": (300, 380),
    "toleranciaReinicio": (0, 90),
    "cicloDias": (18, 25),
    "cioPotroDe": (5, 15),
    "cioPotroAte": (6, 20),
}


def _escopo(haras_id):
    return "global" if haras_id is None else f"haras:{haras_id}"


def ler(db, chave, haras_id=None):
    padrao = PADRAO_GLOBAL if haras_id is None else PADRAO_HARAS
    p = db.get(Parametro, (_escopo(haras_id), chave))
    if p is not None and p.valor is not None:
        return p.valor.get("v") if isinstance(p.valor, dict) and "v" in p.valor else p.valor
    return copy.deepcopy(padrao.get(chave))


def todos(db, haras_id=None):
    padrao = PADRAO_GLOBAL if haras_id is None else PADRAO_HARAS
    out = copy.deepcopy(padrao)
    for p in db.scalars(select(Parametro).where(Parametro.escopo == _escopo(haras_id))):
        if p.chave in out:
            out[p.chave] = p.valor.get("v") if isinstance(p.valor, dict) and "v" in p.valor else p.valor
    return out


def gravar(db, chave, valor, haras_id=None):
    p = db.get(Parametro, (_escopo(haras_id), chave))
    if p is None:
        db.add(Parametro(escopo=_escopo(haras_id), chave=chave, valor={"v": valor}))
    else:
        p.valor = {"v": valor}


def plano_do_haras(db, haras):
    planos = ler(db, "planos")
    nome = haras.plano if haras.plano in planos else next(iter(planos))
    p = planos[nome]
    modulos = {m: bool(p.get("modulos", {}).get(m, True)) for m in MODULOS}
    return {"nome": nome, "limite": int(p.get("limite", 30)), "modulos": modulos}


def modulo_liberado(db, haras, modulo):
    return plano_do_haras(db, haras)["modulos"].get(modulo, True)


def mensalidade(faixas, n):
    """Soma progressiva por faixa. Retorna None se alguma faixa usada não tiver valor definido."""
    total = 0.0
    for f in faixas:
        q = max(0, min(n, f["ate"]) - f["de"] + 1)
        if q:
            if f.get("valor") is None:
                return None
            total += q * float(f["valor"])
    return round(total, 2)


# ---------------- validação do que chega pelas telas ----------------
def _int(chave, v):
    try:
        v = int(v)
    except (TypeError, ValueError):
        raise ValueError(f"Valor inválido em {chave}.")
    lo, hi = LIMITES[chave]
    if not lo <= v <= hi:
        raise ValueError(f"{chave} deve ficar entre {lo} e {hi}.")
    return v


def validar_global(body, atual):
    novo = {}
    for k in ("login_tentativas", "login_janela_min", "sessao_dias", "sessao_app_dias", "sessao_app_gestor_dias", "audio_max_seg"):
        if k in body:
            novo[k] = _int(k, body[k])
    if "app_gestor_sem_https" in body:
        novo["app_gestor_sem_https"] = bool(body["app_gestor_sem_https"])
    if "email_contato" in body:
        e = str(body["email_contato"] or "").strip()[:160]
        if e and "@" not in e:
            raise ValueError("E-mail de contato inválido.")
        novo["email_contato"] = e
    if "smtp" in body:
        s = body["smtp"] or {}
        smtp = dict(atual["smtp"])
        for k in ("host", "usuario", "remetente"):
            if k in s:
                smtp[k] = str(s[k] or "").strip()[:160]
        if "porta" in s:
            p = int(s["porta"] or 0)
            if not 1 <= p <= 65535:
                raise ValueError("Porta SMTP inválida.")
            smtp["porta"] = p
        if "tls" in s:
            smtp["tls"] = bool(s["tls"])
        if s.get("senha"):  # senha só muda quando informada
            smtp["senha"] = str(s["senha"])[:200]
        novo["smtp"] = smtp
    if "faixas" in body:
        fx = []
        for f in body["faixas"]:
            de, ate = int(f["de"]), int(f["ate"])
            v = f.get("valor")
            v = None if v in (None, "") else round(float(v), 2)
            if de < 1 or ate < de or (v is not None and v < 0):
                raise ValueError("Faixa de preço inválida.")
            fx.append({"de": de, "ate": ate, "valor": v})
        fx.sort(key=lambda f: f["de"])
        for a, b in zip(fx, fx[1:]):
            if b["de"] != a["ate"] + 1:
                raise ValueError("As faixas de preço precisam ser contínuas, sem sobreposição.")
        novo["faixas"] = fx
    if "planos" in body:
        planos = {}
        for nome, p in (body["planos"] or {}).items():
            nome = str(nome).strip()[:60]
            if not nome:
                raise ValueError("Todo plano precisa de nome.")
            lim = int(p.get("limite", 30))
            if not 1 <= lim <= 500:
                raise ValueError(f"Limite de animais inválido no plano {nome}.")
            planos[nome] = {"limite": lim, "modulos": {m: bool((p.get("modulos") or {}).get(m, True)) for m in MODULOS}}
        if not planos:
            raise ValueError("Mantenha ao menos um plano.")
        novo["planos"] = planos
    return novo


def validar_haras(body):
    novo = {}
    for k in ("gestacaoDias", "toleranciaReinicio", "cicloDias", "cioPotroDe", "cioPotroAte"):
        if k in body:
            novo[k] = _int(k, body[k])
    if "previsaoCio" in body:
        novo["previsaoCio"] = bool(body["previsaoCio"])
    return novo


def publico_global(valores):
    """Parâmetros globais sem a senha do SMTP."""
    v = copy.deepcopy(valores)
    v["smtp"]["senhaDefinida"] = bool(v["smtp"].get("senha"))
    v["smtp"]["senha"] = ""
    return v
