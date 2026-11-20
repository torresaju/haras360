"""Relatórios do gestor (v1.4.0): sanitário, reprodutivo, plantel e atividade do campo.

Cada relatório devolve o mesmo formato, usado pela tela e pelas exportações:
    {"tipo", "titulo", "periodo": {"de", "ate"}, "filtros",
     "indicadores": [{"rotulo", "valor", "dica"}],
     "graficos": [{"tipo": "barras" | "rosca" | "linha", "titulo", "serie": [{"rotulo", "valor"}]}],
     "tabelas": [{"nome", "colunas": [...], "linhas": [[...]], "links": [animalId ou None por linha]}]}
"""
import csv
import io
from collections import Counter, OrderedDict
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from . import parametros as P
from . import regras as R
from .db import Haras, Usuario
from .rotas_haras import carregar_base, haras_out
from .seguranca import auditar, erro, gestor, get_db

r = APIRouter()

TIPOS = OrderedDict([
    ("sanitario", "Relatório sanitário"),
    ("reprodutivo", "Relatório reprodutivo"),
    ("plantel", "Relatório do plantel"),
    ("campo", "Atividade do campo"),
])
SANITARIOS = ["vacina", "vermifugacao", "exame", "odontologia", "ferrageamento"]
CATEGORIAS = OrderedDict([("eguas", "Éguas"), ("machos", "Machos"), ("potros", "Potros"), ("outros", "Outros")])
ORIGENS = {"App": "App Android", "Portal Cliente": "Portal Campo", "Portal Gestor": "Portal do Gestor"}
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


# ---------------- apoio ----------------
def idade_meses(nasc, ref=None):
    if not nasc:
        return None
    n, t = R.d(nasc), ref or R.hoje()
    return (t.year - n.year) * 12 + t.month - n.month - (1 if t.day < n.day else 0)


def categoria(a, ref=None):
    m = idade_meses(a.get("nascimento"), ref)
    if m is None:
        return "outros"
    if m < 24:
        return "potros"
    return "eguas" if a.get("sexo") == "F" else "machos"


def idade_txt(nasc):
    m = idade_meses(nasc)
    if m is None:
        return "-"
    if m < 24:
        return f"{m} meses"
    return f"{m // 12} anos"


def pct(a, b):
    return f"{round(a / b * 100)}%" if b else "-"


def _meses(de, ate):
    """Rótulos AAAA-MM do período, em ordem."""
    out, y, m = [], de.year, de.month
    while (y, m) <= (ate.year, ate.month):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def _rotulo_mes(k):
    return f"{MESES[int(k[5:7]) - 1]}/{k[2:4]}"


def por_mes(datas, de, ate):
    c = Counter(x[:7] for x in datas)
    return [{"rotulo": _rotulo_mes(k), "valor": c.get(k, 0)} for k in _meses(de, ate)]


def entrada(a, regs):
    """Data e motivo da entrada no plantel: nascimento (parto da mãe registrado aqui), importação ou cadastro."""
    mae = ((a.get("genealogia") or {}).get("mae") or "").strip().upper()
    if mae and a.get("nascimento"):
        nasc = a["nascimento"]
        for r in regs:
            if r["tipo"] == "reprodutivo" and r.get("evento") == "Parto" and r.get("_mae") == mae and abs(R.dias(r["data"], nasc)) <= 15:
                return nasc, "Nascimento no haras"
    if a.get("origem") == "Importação ABCCMM":
        return a.get("importadoEm") or a.get("criadoEm") or "", "Importação ABCCMM"
    return a.get("criadoEm") or "", "Cadastro manual"


# ---------------- filtros ----------------
def filtrar(animais, regs, de, ate, animal_id="", cat=""):
    alvo = [a for a in animais if (not animal_id or a["id"] == animal_id) and (not cat or categoria(a) == cat)]
    ids = {a["id"] for a in alvo}
    no_periodo = [x for x in regs if x["animalId"] in ids and de <= x["data"] <= ate]
    return alvo, ids, no_periodo


# ---------------- relatórios ----------------
def sanitario(ctx):
    hd, animais, regs, prots, de, ate = ctx["haras"], ctx["animais"], ctx["registros"], ctx["protocolos"], ctx["de"], ctx["ate"]
    alvo, ids, per = filtrar(animais, regs, de, ate, ctx["animal"], ctx["categoria"])
    feitos = [x for x in per if x["tipo"] in SANITARIOS]
    ativos = [a for a in alvo if a.get("vivo") and not a.get("baixa")]
    ts = [t for t in R.tarefas(hd, animais, regs, prots) if t["animalId"] in ids and t["cat"] in SANITARIOS]
    atras = [t for t in ts if t["status"] == "atrasado"]
    em_dia = len(ativos) - len({t["animalId"] for t in atras})
    nomes = {a["id"]: a["nome"] for a in animais}
    por_tipo = Counter(x["tipo"] for x in feitos)
    aplic = Counter(pid for x in feitos for pid in (x.get("protocolos") or []))
    atr_p = Counter(t["protocoloId"] for t in atras)
    return {
        "indicadores": [
            {"rotulo": "Procedimentos no período", "valor": len(feitos)},
            {"rotulo": "Atrasados hoje", "valor": len(atras)},
            {"rotulo": "Animais em dia", "valor": pct(em_dia, len(ativos)), "dica": f"{em_dia} de {len(ativos)} animais ativos sem procedimento atrasado"},
            {"rotulo": "Vacinas aplicadas", "valor": por_tipo.get("vacina", 0)},
        ],
        "graficos": [
            {"tipo": "linha", "titulo": "Procedimentos por mês", "serie": por_mes([x["data"] for x in feitos], R.d(de), R.d(ate))},
            {"tipo": "barras", "titulo": "Procedimentos por tipo", "serie": [{"rotulo": R.CATS[k], "valor": por_tipo.get(k, 0)} for k in SANITARIOS]},
        ],
        "tabelas": [
            {"nome": "Procedimentos realizados", "colunas": ["Data", "Animal", "Procedimento", "Dose", "Produto", "Lote", "Registrado por", "Origem"],
             "linhas": [[R.br(x["data"]), nomes.get(x["animalId"], ""), R.titulo_registro(prots, x), _dose(x.get("dose")) if x["tipo"] == "vacina" else "-",
                         x.get("produto", ""), x.get("lote", ""), x.get("autor", ""), ORIGENS.get(x.get("origem"), x.get("origem", ""))] for x in reversed(feitos)],
             "links": [x["animalId"] for x in reversed(feitos)]},
            {"nome": "Pendências de hoje", "colunas": ["Animal", "Procedimento", "Etapa", "Prevista para", "Situação"],
             "linhas": [[t["animal"], t["titulo"], t["etapa"], R.br(t["due"]), _situacao(t["status"])] for t in ts if t["status"] in ("atrasado", "hoje", "semana")],
             "links": [t["animalId"] for t in ts if t["status"] in ("atrasado", "hoje", "semana")]},
            {"nome": "Por protocolo", "colunas": ["Protocolo", "Categoria", "Aplicações no período", "Atrasados hoje"],
             "linhas": [[p["nome"], R.CATS.get(p["cat"], ""), aplic.get(p["id"], 0), atr_p.get(p["id"], 0)] for p in prots if p.get("ativo")]},
        ],
    }


def _dose(v):
    return {"reforco": "Reforço", "1": "1ª dose", "2": "2ª dose", "3": "3ª dose", 1: "1ª dose", 2: "2ª dose", 3: "3ª dose"}.get(v, "Dose única")


def _duracao(seg):
    seg = int(seg or 0)
    return f"{seg // 60}:{seg % 60:02d}"


def _situacao(s):
    return {"atrasado": "Atrasado", "hoje": "Hoje", "semana": "Próximos 7 dias", "mes": "Próximos 30 dias", "futuro": "Futuro", "pendente": "Pendente"}.get(s, s)


def _detalhe_repro(x):
    if x.get("evento") == "Cio":
        p = [x.get("sinais", "")]
        if x.get("ovario"):
            p.append(f"ovário {x['ovario'].lower()}")
        if x.get("foliculo"):
            p.append(f"folículo {x['foliculo']} mm")
        if x.get("edema") not in (None, ""):
            p.append(f"edema {x['edema']}")
        return ", ".join(v for v in p if v)
    if x.get("evento") == "Diagnóstico positivo" and x.get("dataCobertura"):
        return f"cobertura em {R.br(x['dataCobertura'])}"
    return ""


def reprodutivo(ctx):
    hd, animais, regs, de, ate = ctx["haras"], ctx["animais"], ctx["registros"], ctx["de"], ctx["ate"]
    alvo, ids, per = filtrar(animais, regs, de, ate, ctx["animal"], ctx["categoria"])
    ev = [x for x in per if x["tipo"] == "reprodutivo" and x.get("evento")]
    c = Counter(x["evento"] for x in ev)
    pos, neg = c.get("Diagnóstico positivo", 0), c.get("Diagnóstico negativo", 0)
    nomes = {a["id"]: a["nome"] for a in animais}
    eguas = [a for a in alvo if a.get("sexo") == "F" and a.get("vivo") and not a.get("baixa") and (idade_meses(a.get("nascimento")) or 0) >= 24]
    ts = {t["animalId"]: t for t in R.tarefas(hd, animais, regs, ctx["protocolos"]) if t.get("cio")}
    linhas_eg, links_eg, prenhes = [], [], 0
    intervalos, linhas_int, links_int = [], [], []
    for a in sorted(eguas, key=lambda x: x["nome"]):
        g = R.gestacao(a, regs, hd.get("gestacaoDias", R.GESTACAO_DIAS))
        prenhes += 1 if g else 0
        meus = [x for x in regs if x["animalId"] == a["id"] and x["tipo"] == "reprodutivo" and x.get("evento")]
        ult = meus[-1] if meus else None
        cio = ts.get(a["id"])
        linhas_eg.append([a["nome"], idade_txt(a.get("nascimento")), "Prenhe" if g else "Vazia",
                          f"{ult['evento']} em {R.br(ult['data'])}" if ult else "-", R.br(g["parto"]) if g else "-", R.br(cio["due"]) if cio else "-"])
        links_eg.append(a["id"])
        partos = sorted(x["data"] for x in meus if x["evento"] == "Parto")
        if len(partos) >= 2:
            ints = [R.dias(p1, p2) for p1, p2 in zip(partos, partos[1:])]
            intervalos.extend(ints)
            linhas_int.append([a["nome"], len(partos), round(sum(ints) / len(ints)), R.br(partos[-1])])
            links_int.append(a["id"])
    media_int = round(sum(intervalos) / len(intervalos)) if intervalos else None
    eventos_ordem = R.EVENTOS_REPRO
    return {
        "indicadores": [
            {"rotulo": "Cios registrados", "valor": c.get("Cio", 0)},
            {"rotulo": "Coberturas e inseminações", "valor": c.get("Cobertura", 0) + c.get("Inseminação", 0)},
            {"rotulo": "Taxa de prenhez", "valor": pct(pos, pos + neg), "dica": f"{pos} positivo(s) em {pos + neg} diagnóstico(s) no período"},
            {"rotulo": "Partos", "valor": c.get("Parto", 0)},
            {"rotulo": "Éguas prenhes", "valor": f"{prenhes} de {len(eguas)}", "dica": "Éguas ativas com 2 anos ou mais"},
            {"rotulo": "Intervalo entre partos", "valor": f"{media_int} dias" if media_int else "-", "dica": "Média das éguas com 2 partos ou mais registrados"},
        ],
        "graficos": [
            {"tipo": "barras", "titulo": "Eventos no período", "serie": [{"rotulo": e, "valor": c.get(e, 0)} for e in eventos_ordem]},
            {"tipo": "rosca", "titulo": "Éguas", "serie": [{"rotulo": "Prenhes", "valor": prenhes}, {"rotulo": "Vazias", "valor": len(eguas) - prenhes}]},
            {"tipo": "linha", "titulo": "Eventos por mês", "serie": por_mes([x["data"] for x in ev], R.d(de), R.d(ate))},
        ],
        "tabelas": [
            {"nome": "Situação das éguas", "colunas": ["Égua", "Idade", "Situação", "Último evento", "Parto previsto", "Próximo cio"], "linhas": linhas_eg, "links": links_eg},
            {"nome": "Eventos reprodutivos", "colunas": ["Data", "Animal", "Evento", "Garanhão", "Detalhes", "Registrado por"],
             "linhas": [[R.br(x["data"]), nomes.get(x["animalId"], ""), x["evento"], x.get("garanhao", ""), _detalhe_repro(x), x.get("autor", "")] for x in reversed(ev)],
             "links": [x["animalId"] for x in reversed(ev)]},
            {"nome": "Intervalo entre partos", "colunas": ["Égua", "Partos registrados", "Intervalo médio (dias)", "Último parto"], "linhas": linhas_int, "links": links_int},
        ],
    }


def plantel(ctx):
    animais, regs, de, ate = ctx["animais"], ctx["registros"], ctx["de"], ctx["ate"]
    alvo, _ids, _per = filtrar(animais, regs, de, ate, ctx["animal"], ctx["categoria"])
    nomes_mae = {a["id"]: a["nome"].strip().upper() for a in animais}
    regs_m = [dict(x, _mae=nomes_mae.get(x["animalId"], "")) for x in regs if x["tipo"] == "reprodutivo" and x.get("evento") == "Parto"]
    ativos = [a for a in alvo if a.get("vivo") and not a.get("baixa")]
    cat = Counter(categoria(a) for a in ativos)
    faixas = OrderedDict([("Até 1 ano", 0), ("1 a 2 anos", 0), ("2 a 5 anos", 0), ("5 a 10 anos", 0), ("Mais de 10 anos", 0), ("Sem data", 0)])
    for a in ativos:
        m = idade_meses(a.get("nascimento"))
        k = "Sem data" if m is None else "Até 1 ano" if m < 12 else "1 a 2 anos" if m < 24 else "2 a 5 anos" if m < 60 else "5 a 10 anos" if m < 120 else "Mais de 10 anos"
        faixas[k] += 1
    entradas = []
    for a in alvo:
        dt, motivo = entrada(a, regs_m)
        if dt and de <= dt <= ate:
            entradas.append((dt, a, motivo))
    entradas.sort(key=lambda x: x[0], reverse=True)
    baixas = sorted([a for a in alvo if a.get("baixa") and de <= a["baixa"]["data"] <= ate], key=lambda a: a["baixa"]["data"], reverse=True)
    mot = Counter(a["baixa"]["motivo"] for a in baixas)
    return {
        "indicadores": [
            {"rotulo": "Animais ativos", "valor": len(ativos)},
            {"rotulo": "Fêmeas e machos", "valor": f"{sum(1 for a in ativos if a['sexo'] == 'F')} e {sum(1 for a in ativos if a['sexo'] == 'M')}"},
            {"rotulo": "Entradas no período", "valor": len(entradas)},
            {"rotulo": "Saídas no período", "valor": len(baixas)},
        ],
        "graficos": [
            {"tipo": "rosca", "titulo": "Por categoria", "serie": [{"rotulo": v, "valor": cat.get(k, 0)} for k, v in CATEGORIAS.items()]},
            {"tipo": "barras", "titulo": "Por faixa de idade", "serie": [{"rotulo": k, "valor": v} for k, v in faixas.items()]},
            {"tipo": "barras", "titulo": "Saídas por motivo", "serie": [{"rotulo": m, "valor": mot.get(m, 0)} for m in R.MOTIVOS_BAIXA]},
        ],
        "tabelas": [
            {"nome": "Plantel ativo", "colunas": ["Animal", "Sexo", "Idade", "Categoria", "Registro", "Livro", "Entrada"],
             "linhas": [[a["nome"], "Fêmea" if a["sexo"] == "F" else "Macho", idade_txt(a.get("nascimento")), CATEGORIAS[categoria(a)], a.get("registro") or "-",
                         a.get("livro") or "-", R.br(entrada(a, regs_m)[0]) if entrada(a, regs_m)[0] else "-"] for a in sorted(ativos, key=lambda x: x["nome"])],
             "links": [a["id"] for a in sorted(ativos, key=lambda x: x["nome"])]},
            {"nome": "Entradas", "colunas": ["Data", "Animal", "Motivo"], "linhas": [[R.br(dt), a["nome"], m] for dt, a, m in entradas], "links": [a["id"] for _, a, _ in entradas]},
            {"nome": "Saídas", "colunas": ["Data", "Animal", "Motivo", "Destino", "Observação"],
             "linhas": [[R.br(a["baixa"]["data"]), a["nome"], a["baixa"]["motivo"], a["baixa"].get("destino") or "-", a["baixa"].get("obs") or ""] for a in baixas],
             "links": [a["id"] for a in baixas]},
        ],
    }


def campo(ctx):
    animais, regs, prots, de, ate = ctx["animais"], ctx["registros"], ctx["protocolos"], ctx["de"], ctx["ate"]
    _alvo, _ids, per = filtrar(animais, regs, de, ate, ctx["animal"], ctx["categoria"])
    lst = [x for x in per if x.get("origem") != "Portal Gestor"]
    nomes = {a["id"]: a["nome"] for a in animais}
    pessoa, tipo, origem = Counter(x.get("autor") or "-" for x in lst), Counter(x["tipo"] for x in lst), Counter(ORIGENS.get(x.get("origem"), x.get("origem")) for x in lst)
    fotos = sum(len(x.get("fotos") or []) for x in lst)
    audios = sum(1 for x in lst if x.get("audio"))
    ocorr = [x for x in lst if x["tipo"] == "ocorrencia"]
    return {
        "indicadores": [
            {"rotulo": "Registros do campo", "valor": len(lst)},
            {"rotulo": "Pelo app Android", "valor": origem.get("App Android", 0)},
            {"rotulo": "Ocorrências", "valor": len(ocorr)},
            {"rotulo": "Fotos e áudios", "valor": f"{fotos} e {audios}"},
        ],
        "graficos": [
            {"tipo": "linha", "titulo": "Registros por mês", "serie": por_mes([x["data"] for x in lst], R.d(de), R.d(ate))},
            {"tipo": "barras", "titulo": "Por tipo", "serie": [{"rotulo": R.CATS.get(k, k), "valor": v} for k, v in tipo.most_common()]},
            {"tipo": "rosca", "titulo": "Por origem", "serie": [{"rotulo": k, "valor": v} for k, v in origem.most_common()]},
        ],
        "tabelas": [
            {"nome": "Registros por pessoa", "colunas": ["Pessoa", "Registros", "Ocorrências", "Com foto", "Com áudio"],
             "linhas": [[p, n, sum(1 for x in ocorr if (x.get("autor") or "-") == p), sum(1 for x in lst if (x.get("autor") or "-") == p and x.get("fotos")),
                         sum(1 for x in lst if (x.get("autor") or "-") == p and x.get("audio"))] for p, n in pessoa.most_common()]},
            {"nome": "Registros", "colunas": ["Data", "Animal", "Registro", "Registrado por", "Origem", "Fotos", "Áudio", "Observação"],
             "linhas": [[R.br(x["data"]), nomes.get(x["animalId"], ""), R.titulo_registro(prots, x), x.get("autor", ""), ORIGENS.get(x.get("origem"), x.get("origem", "")),
                         len(x.get("fotos") or []), _duracao(x["audio"]["duracao"]) if x.get("audio") else "-", (x.get("obs") or "")[:300]] for x in reversed(lst)],
             "links": [x["animalId"] for x in reversed(lst)]},
        ],
    }


GERAR = {"sanitario": sanitario, "reprodutivo": reprodutivo, "plantel": plantel, "campo": campo}


def gerar(db, haras_id, tipo, de="", ate="", animal="", cat=""):
    if tipo not in TIPOS:
        erro(404, "Relatório não encontrado.")
    try:
        fim = R.d(ate) if ate else R.hoje()
        ini = R.d(de) if de else date(fim.year - 1, fim.month, 1)
    except ValueError:
        erro(400, "Período inválido.")
    if ini > fim:
        erro(400, "A data inicial precisa ser anterior à final.")
    if (fim - ini).days > 366 * 5:
        erro(400, "Escolha um período de até 5 anos.")
    if cat and cat not in CATEGORIAS:
        erro(400, "Categoria inválida.")
    h, animais, regs, prots = carregar_base(db, haras_id)
    if animal and not any(a["id"] == animal for a in animais):
        erro(404, "Animal não encontrado.")
    ctx = {"haras": haras_out(db, h), "animais": animais, "registros": regs, "protocolos": prots,
           "de": R.iso(ini), "ate": R.iso(fim), "animal": animal, "categoria": cat}
    out = GERAR[tipo](ctx)
    nome_animal = next((a["nome"] for a in animais if a["id"] == animal), "")
    out.update({"tipo": tipo, "titulo": TIPOS[tipo], "haras": h.nome, "periodo": {"de": R.iso(ini), "ate": R.iso(fim)},
                "filtros": {"animal": nome_animal, "categoria": CATEGORIAS.get(cat, "")}, "geradoEm": R.iso(R.hoje())})
    return out


# ---------------- exportação ----------------
def _cabecalho(rel):
    linhas = [[rel["titulo"]], [rel["haras"]], [f"Período: {R.br(rel['periodo']['de'])} a {R.br(rel['periodo']['ate'])}"]]
    f = [v for v in (rel["filtros"].get("animal"), rel["filtros"].get("categoria")) if v]
    if f:
        linhas.append(["Filtro: " + ", ".join(f)])
    linhas.append([f"Gerado em {R.br(rel['geradoEm'])} pelo Haras360"])
    return linhas


def para_csv(rel):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    for ln in _cabecalho(rel):
        w.writerow(ln)
    w.writerow([])
    w.writerow(["Indicador", "Valor"])
    for i in rel["indicadores"]:
        w.writerow([i["rotulo"], i["valor"]])
    for t in rel["tabelas"]:
        w.writerow([])
        w.writerow([t["nome"]])
        w.writerow(t["colunas"])
        for ln in t["linhas"]:
            w.writerow(ln)
    return ("﻿" + buf.getvalue()).encode("utf-8")  # BOM: o Excel abre os acentos certos


def para_xlsx(rel, base_url=""):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    verde, areia = PatternFill("solid", fgColor="193D30"), PatternFill("solid", fgColor="F3F1E9")
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo"
    for i, ln in enumerate(_cabecalho(rel), 1):
        ws.cell(row=i, column=1, value=ln[0]).font = Font(bold=(i == 1), size=14 if i == 1 else 11)
    lin = len(_cabecalho(rel)) + 2
    for c, v in enumerate(("Indicador", "Valor"), 1):
        x = ws.cell(row=lin, column=c, value=v)
        x.font, x.fill = Font(bold=True, color="FFFFFF"), verde
    for i in rel["indicadores"]:
        lin += 1
        ws.cell(row=lin, column=1, value=i["rotulo"])
        ws.cell(row=lin, column=2, value=i["valor"]).alignment = Alignment(horizontal="right")
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 34, 18
    usados = {"Resumo"}
    for t in rel["tabelas"]:
        nome = t["nome"][:31]
        while nome in usados:
            nome = nome[:28] + f" {len(usados)}"
        usados.add(nome)
        s = wb.create_sheet(nome)
        colunas = t["colunas"] + (["Ficha"] if base_url and t.get("links") else [])
        for c, v in enumerate(colunas, 1):
            x = s.cell(row=1, column=c, value=v)
            x.font, x.fill = Font(bold=True, color="FFFFFF"), verde
        larg = [len(str(c)) for c in colunas]
        for i, ln in enumerate(t["linhas"], 2):
            for c, v in enumerate(ln, 1):
                s.cell(row=i, column=c, value=v)
                larg[c - 1] = max(larg[c - 1], min(len(str(v)), 60))
            if base_url and t.get("links") and t["links"][i - 2]:
                x = s.cell(row=i, column=len(colunas), value="Abrir")
                x.hyperlink = f"{base_url}/gestor?animal={t['links'][i - 2]}"
                x.font = Font(color="193D30", underline="single")
            if i % 2:
                for c in range(1, len(colunas) + 1):
                    s.cell(row=i, column=c).fill = areia
        for c, w in enumerate(larg, 1):
            s.column_dimensions[get_column_letter(c)].width = w + 3
        s.freeze_panes = "A2"
        if t["linhas"]:
            s.auto_filter.ref = f"A1:{get_column_letter(len(colunas))}{len(t['linhas']) + 1}"
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ---------------- rotas ----------------
def _liberado(db, u):
    if not P.modulo_liberado(db, db.get(Haras, u.haras_id), "relatorios"):
        erro(403, "Os relatórios não estão incluídos no plano deste haras.")


@r.get("/api/relatorios/{tipo}")
def relatorio(tipo: str, de: str = "", ate: str = "", animal: str = "", categoria: str = "", u: Usuario = Depends(gestor), db=Depends(get_db)):
    _liberado(db, u)
    return gerar(db, u.haras_id, tipo, de, ate, animal, categoria)


@r.get("/api/relatorios/{tipo}/exportar")
def exportar(tipo: str, request: Request, formato: str = "xlsx", de: str = "", ate: str = "", animal: str = "", categoria: str = "",
             u: Usuario = Depends(gestor), db=Depends(get_db)):
    _liberado(db, u)
    if formato not in ("xlsx", "csv"):
        erro(400, "Formato inválido. Use xlsx ou csv.")
    rel = gerar(db, u.haras_id, tipo, de, ate, animal, categoria)
    nome = f"haras360-{tipo}-{rel['periodo']['de']}-a-{rel['periodo']['ate']}.{formato}"
    if formato == "csv":
        corpo, mime = para_csv(rel), "text/csv; charset=utf-8"
    else:
        corpo, mime = para_xlsx(rel, str(request.base_url).rstrip("/")), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    auditar(db, "relatorio_exportado", usuario=u, alvo=f"{rel['titulo']} ({formato})",
            detalhe={"periodo": rel["periodo"], "filtros": rel["filtros"]}, request=request)
    db.commit()
    return Response(corpo, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{nome}"', "Cache-Control": "no-store"})
