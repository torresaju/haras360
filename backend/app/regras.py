"""Motor de regras do Haras360 (porta fiel do motor validado no protótipo web).

Trabalha com dicionários simples e datas em texto ISO (AAAA-MM-DD), o mesmo
formato que a API devolve aos portais e que o app mobile vai usar.
"""
import calendar
import math
from datetime import date, timedelta

GESTACAO_DIAS = 340
TOLERANCIA_REINICIO = 15

CATS = {
    "vacina": "Vacinação",
    "vermifugacao": "Vermifugação",
    "odontologia": "Odontologia",
    "ferrageamento": "Ferrageamento",
    "exame": "Exame clínico",
    "reprodutivo": "Reprodução",
    "ocorrencia": "Ocorrência",
    "documental": "Documentação",
}
EVENTOS_REPRO = ["Cio", "Cobertura", "Inseminação", "Diagnóstico positivo", "Diagnóstico negativo", "Parto", "Aborto"]
CICLO_DIAS = 21
CIO_POTRO = (7, 12)
CIO_TOLERANCIA = 3  # dias em que a previsão atrasada ainda aparece antes de passar ao ciclo seguinte
MOTIVOS_BAIXA = ["Venda", "Morte", "Doação", "Transferência"]
TIPOS_NOTIF = ["atrasado", "semana", "parto", "documental", "campo"]


def protocolos_padrao():
    vet = "VetJr. UFMG"
    mer = "Padrão de mercado"
    lst = [
        dict(id="raiva", nome="Raiva", cat="vacina", obrig="Obrigatória", gatilho="idade", idadeMeses=4, serie=[30], reforcoDias=365, via="SC ou IM (ver bula)", fonte=vet, ativo=True, nota="Reforço semestral em regiões endêmicas (configurável por haras)"),
        dict(id="tetano", nome="Tétano", cat="vacina", obrig="Recomendada", gatilho="idade", idadeMeses=3, serie=[30, 30], reforcoDias=365, via="IM", fonte=vet, ativo=True),
        dict(id="encefalo", nome="Encefalomielite", cat="vacina", obrig="Obrigatória para transporte", gatilho="idade", idadeMeses=3, serie=[30, 30], reforcoDias=365, via="IM", fonte=vet, ativo=True),
        dict(id="influenza", nome="Influenza", cat="vacina", obrig="Recomendada", gatilho="idade", idadeMeses=3, serie=[30, 30], reforcoDias=365, via="IM", fonte=vet, ativo=True, nota="Semestral ou anual, a critério do veterinário"),
        dict(id="rino", nome="Rinopneumonite", cat="vacina", obrig="Exigida por alguns estabelecimentos", gatilho="idade", idadeMeses=6, serie=[25, 180], reforcoDias=365, via="IM", fonte=vet, ativo=True, gestacao=[5, 7, 9], nota="1ª dose na desmama (6 meses). Gestantes no 5º, 7º e 9º mês"),
        dict(id="lepto", nome="Leptospirose", cat="vacina", obrig="Recomendada", gatilho="idade", idadeMeses=4, serie=[30], reforcoDias=180, via="IM", fonte=vet, ativo=True),
        dict(id="garrotilho", nome="Garrotilho (adenite)", cat="vacina", obrig="Conforme risco", gatilho="idade", idadeMeses=4, serie=[], reforcoDias=180, via="IM ou SC (ver bula)", fonte=vet, ativo=False, nota="Ative quando houver risco no plantel"),
        dict(id="vermi", nome="Vermifugação", cat="vermifugacao", gatilho="idade", idadeMeses=2, serie=[], reforcoDias=90, fonte=mer, ativo=True),
        dict(id="odonto", nome="Avaliação odontológica", cat="odontologia", gatilho="idade", idadeMeses=24, serie=[], reforcoDias=365, fonte=mer, ativo=True),
        dict(id="aparelho", nome="Retorno de aparelho dentário", cat="odontologia", gatilho="registro", serie=[], reforcoDias=730, fonte=mer, ativo=True, nota="Começa a contar quando um aparelho é registrado"),
        dict(id="ferrag", nome="Ferrageamento", cat="ferrageamento", gatilho="registro", serie=[], reforcoDias=45, fonte=mer, ativo=True, nota="Começa a contar no primeiro ferrageamento registrado"),
        dict(id="aie", nome="Exame de Anemia Infecciosa (AIE)", cat="exame", gatilho="registro", serie=[], reforcoDias=60, fonte=mer, ativo=True, nota="Validade usual para GTA. Confirme a regra do seu estado"),
        dict(id="mormo", nome="Exame de Mormo", cat="exame", gatilho="registro", serie=[], reforcoDias=60, fonte=mer, ativo=True, nota="Validade usual para GTA. Confirme a regra do seu estado"),
    ]
    for i, p in enumerate(lst):
        p["ordem"] = i
    return lst


def notif_prefs_padrao():
    return {
        "atrasado": {"push": True, "email": True, "web": True},
        "semana": {"push": True, "email": False, "web": True},
        "parto": {"push": True, "email": True, "web": True},
        "documental": {"push": False, "email": True, "web": True},
        "campo": {"push": False, "email": False, "web": True},
        "ocorrencia": {"push": True, "email": True, "web": True},
    }


# ---------------- datas ----------------
def hoje():
    return date.today()


def d(v):
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def iso(v):
    return d(v).isoformat()


def add_dias(v, n):
    return d(v) + timedelta(days=n)


def add_meses(v, n):
    x = d(v)
    m = x.month - 1 + n
    y = x.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(x.day, calendar.monthrange(y, m)[1]))


def dias(a, b):
    return (d(b) - d(a)).days


def br(v):
    x = d(v)
    return x.strftime("%d/%m/%Y") if x else "-"


def relativo(due):
    n = dias(hoje(), due)
    if n == 0:
        return "hoje"
    if n == 1:
        return "amanhã"
    if n == -1:
        return "ontem"
    if n < 0:
        return f"há {-n} dias"
    return f"em {n} dias"


def status_de(due):
    n = dias(hoje(), due)
    if n < 0:
        return "atrasado"
    if n == 0:
        return "hoje"
    if n <= 7:
        return "semana"
    if n <= 30:
        return "mes"
    return "futuro"


# ---------------- regras ----------------
def _por_data(regs):
    return sorted(regs, key=lambda r: r["data"])


def _protocolo(prots, pid):
    return next((p for p in prots if p["id"] == pid), None)


def reforco_dias(haras, p):
    if p["id"] == "raiva":
        return 180 if haras.get("raivaSemestral") else 365
    return p["reforcoDias"]


def gestacao(animal, registros, dias_gestacao=GESTACAO_DIAS):
    if not animal or animal.get("sexo") != "F":
        return None
    ev = _por_data([r for r in registros if r["animalId"] == animal["id"] and r["tipo"] == "reprodutivo" and r.get("evento")])
    g = None
    for r in ev:
        if r["evento"] == "Diagnóstico positivo":
            g = {"cobertura": r.get("dataCobertura") or r["data"], "diagnostico": r["data"], "garanhao": r.get("garanhao") or ""}
        elif r["evento"] in ("Parto", "Aborto", "Diagnóstico negativo"):
            g = None
    if not g:
        return None
    g["dias"] = dias(g["cobertura"], hoje())
    g["mes"] = math.floor(g["dias"] / 30.44) + 1
    g["parto"] = iso(add_dias(g["cobertura"], dias_gestacao))
    g["faltam"] = dias(hoje(), g["parto"])
    g["pct"] = max(0, min(100, math.floor(g["dias"] / dias_gestacao * 100 + 0.5)))
    return g


def previsao_cio(haras, animal, registros, gest=None):
    """Próximo cio de uma égua (v1.4.0).

    Base: último cio, cobertura, inseminação ou aborto. Depois de um parto sem cio registrado,
    vale a janela do cio do potro. Égua gestante (diagnóstico positivo) não entra na previsão.
    """
    if not haras.get("previsaoCio") or not animal or animal.get("sexo") != "F":
        return None
    if gest:
        return None
    ciclo = int(haras.get("cicloDias") or CICLO_DIAS)
    de, ate = int(haras.get("cioPotroDe") or CIO_POTRO[0]), int(haras.get("cioPotroAte") or CIO_POTRO[1])
    ev = _por_data([r for r in registros if r["animalId"] == animal["id"] and r["tipo"] == "reprodutivo" and r.get("evento")])
    base = parto = None
    for r in ev:
        if r["evento"] in ("Cio", "Cobertura", "Inseminação", "Aborto"):
            base = r["data"]
        elif r["evento"] == "Parto":
            parto, base = r["data"], None
    t = hoje()

    def projetar(inicio):
        n = max(1, math.ceil((dias(inicio, t) - CIO_TOLERANCIA) / ciclo))
        return add_dias(inicio, n * ciclo)

    if base is None and parto:
        ini, fim = add_dias(parto, de), add_dias(parto, ate)
        if t <= fim:
            due = ini if t < ini else t
            return {"due": iso(due), "titulo": "Cio do potro", "etapa": "Observar cio do potro",
                    "nota": f"Janela do {de}º ao {ate}º dia após o parto de {br(parto)}"}
        due = projetar(ini)
        return {"due": iso(due), "titulo": "Observar cio", "etapa": "Previsão do cio",
                "nota": f"Ciclo de {ciclo} dias contado do cio do potro ({br(ini)})"}
    if base is None:
        return None
    due = projetar(d(base))
    return {"due": iso(due), "titulo": "Observar cio", "etapa": "Previsão do cio",
            "nota": f"Ciclo de {ciclo} dias a partir de {br(base)}"}


def _dose_num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def proxima_etapa(haras, animal, p, registros):
    regs = _por_data([r for r in registros if r["animalId"] == animal["id"] and p["id"] in (r.get("protocolos") or [])])
    serie = p.get("serie") or []
    serie_n = 1 + len(serie)
    dose = "unica"
    if not regs:
        if p.get("gatilho") != "idade" or not animal.get("nascimento"):
            return None
        due = add_meses(animal["nascimento"], p["idadeMeses"])
        if p["cat"] == "vacina":
            etapa = "1ª dose (primovacinação)" if serie_n > 1 else "1ª dose"
            dose = 1
        else:
            etapa = "Primeira avaliação" if p["cat"] == "odontologia" else "Primeira aplicação"
        nota = f"Indicada a partir de {p['idadeMeses']} meses de idade"
    else:
        last = regs[-1]
        ld = last.get("dose")
        if ld in ("reforco", "unica") or not ld:
            pos = serie_n
        else:
            pos = min(_dose_num(ld) or serie_n, serie_n)
        if pos < serie_n:
            due = add_dias(last["data"], serie[pos - 1])
            etapa = f"{pos + 1}ª dose"
            dose = pos + 1
            nota = f"Intervalo de {serie[pos - 1]} dias após a {pos}ª dose"
        else:
            rd = reforco_dias(haras, p)
            due = add_dias(last["data"], rd)
            dose = "reforco" if p["cat"] == "vacina" else "unica"
            if p["cat"] == "vacina":
                etapa = "Reforço"
            elif p["cat"] == "exame":
                etapa = "Renovação do exame"
            elif p["id"] == "aparelho":
                etapa = "Retorno"
            else:
                etapa = "Próxima aplicação"
            per = "anual" if rd >= 365 else ("semestral" if rd == 180 else f"de {rd} dias")
            nota = ("Reforço " if p["cat"] == "vacina" else "Intervalo ") + per
            if p["cat"] == "vacina" and animal.get("nascimento") and ld != "reforco":
                m12 = add_meses(animal["nascimento"], 12)
                if m12 > d(last["data"]) and m12 < due:
                    due = m12
                    nota = "Primeiro reforço aos 12 meses de idade, após a primovacinação"
            if p["cat"] == "vacina" and dias(due, hoje()) > haras.get("toleranciaReinicio", TOLERANCIA_REINICIO):
                nota = f"Reforço vencido há {dias(due, hoje())} dias. O protocolo indica reiniciar a primovacinação"
                etapa = "Reiniciar primovacinação"
                dose = 1
    return {"due": iso(due), "etapa": etapa, "nota": nota, "dose": dose}


def tarefas(haras, animais, registros, prots, animal_id=None):
    dg = haras.get("gestacaoDias", GESTACAO_DIAS)
    out = []
    for a in animais:
        if not a.get("vivo") or a.get("baixa"):
            continue
        if animal_id and a["id"] != animal_id:
            continue
        g = gestacao(a, registros, dg)
        for p in prots:
            if not p.get("ativo"):
                continue
            e = proxima_etapa(haras, a, p, registros)
            if not e:
                continue
            if g and p["id"] == "rino" and e["etapa"] not in ("2ª dose", "3ª dose"):
                continue
            out.append({"id": f"{a['id']}:{p['id']}", "animalId": a["id"], "animal": a["nome"], "protocoloId": p["id"], "cat": p["cat"], "titulo": p["nome"], "etapa": e["etapa"], "nota": e["nota"], "dose": e["dose"], "due": e["due"]})
        if g:
            rino = _protocolo(prots, "rino")
            if rino and rino.get("ativo"):
                regs = [r for r in registros if r["animalId"] == a["id"] and "rino" in (r.get("protocolos") or [])]
                for m in (rino.get("gestacao") or [5, 7, 9]):
                    dt = add_meses(g["cobertura"], m)
                    if any(abs(dias(r["data"], dt)) <= 20 for r in regs):
                        continue
                    out.append({"id": f"{a['id']}:rino-g{m}", "animalId": a["id"], "animal": a["nome"], "protocoloId": "rino", "cat": "vacina", "titulo": "Rinopneumonite", "etapa": f"Gestante, {m}º mês", "nota": "Protocolo de éguas gestantes (5º, 7º e 9º mês)", "dose": "reforco", "due": iso(dt)})
            nota = f"Cobertura em {br(g['cobertura'])}" + (f" com {g['garanhao']}" if g["garanhao"] else "") + f". Estimativa de {dg} dias"
            out.append({"id": f"{a['id']}:parto", "animalId": a["id"], "animal": a["nome"], "protocoloId": None, "cat": "reprodutivo", "titulo": "Previsão de parto", "etapa": f"{g['mes']}º mês de gestação", "nota": nota, "dose": None, "due": g["parto"], "parto": True})
        c = previsao_cio(haras, a, registros, g)
        if c:
            out.append({"id": f"{a['id']}:cio", "animalId": a["id"], "animal": a["nome"], "protocoloId": None, "cat": "reprodutivo", "titulo": c["titulo"],
                        "etapa": c["etapa"], "nota": c["nota"], "dose": None, "due": c["due"], "cio": True})
        t = iso(hoje())
        base = {"animalId": a["id"], "animal": a["nome"], "cat": "documental", "etapa": "Documentação", "due": t, "doc": True}
        if not a.get("registro"):
            out.append(dict(base, id=f"{a['id']}:reg", titulo="Registro ABCCMM pendente", nota="Animal sem número de registro no relatório de plantel"))
        dna = a.get("dna") or ""
        if "sem exame" in dna.lower() or not dna:
            out.append(dict(base, id=f"{a['id']}:dna", titulo="Exame de DNA pendente", nota="Necessário para o registro genealógico"))
        if a.get("bloqueado"):
            out.append(dict(base, id=f"{a['id']}:bloq", titulo="Animal bloqueado na ABCCMM", nota="Verifique a situação junto à associação", critico=True))
    for t in out:
        t["status"] = "pendente" if t.get("doc") else status_de(t["due"])
    out.sort(key=lambda t: t["due"])
    return out


def titulo_registro(prots, r):
    tipo = r["tipo"]
    if tipo == "vacina":
        return "Vacina " + " + ".join((_protocolo(prots, pid) or {"nome": pid})["nome"] for pid in (r.get("protocolos") or []))
    if tipo == "reprodutivo":
        return r.get("evento") or "Evento reprodutivo"
    if tipo == "ocorrencia":
        return r.get("titulo") or "Ocorrência"
    if tipo == "exame":
        return "Exame: " + (r.get("exame") or "clínico")
    if tipo == "odontologia":
        return r.get("procedimento") or "Odontologia"
    if tipo == "ferrageamento":
        return "Ferrageamento"
    if tipo == "vermifugacao":
        return "Vermifugação"
    return CATS.get(tipo, "Registro")


def notificacoes(haras, animais, registros, prots, ts=None):
    ts = ts if ts is not None else tarefas(haras, animais, registros, prots)
    n = []
    for t in ts:
        if t.get("cio"):
            if t["status"] in ("atrasado", "hoje", "semana") and dias(hoje(), t["due"]) <= 3:
                n.append({"id": f"n:{t['id']}:{t['due']}", "tipo": "semana", "sev": "info", "titulo": f"{t['titulo']} · {t['animal']}",
                          "texto": f"{t['etapa']} {relativo(t['due'])}, em {br(t['due'])}.", "animalId": t["animalId"], "tarefa": t})
        elif t["status"] == "atrasado":
            n.append({"id": f"n:{t['id']}:{t['due']}", "tipo": "atrasado", "sev": "critico", "titulo": f"{t['titulo']} · {t['animal']}", "texto": f"{t['etapa']} prevista para {br(t['due'])} ({relativo(t['due'])}).", "animalId": t["animalId"], "tarefa": t})
        elif t.get("parto") and dias(hoje(), t["due"]) <= 45:
            n.append({"id": f"n:{t['id']}", "tipo": "parto", "sev": "alerta", "titulo": f"Parto previsto · {t['animal']}", "texto": f"Previsão para {br(t['due'])} ({relativo(t['due'])}). Prepare a baia de maternidade.", "animalId": t["animalId"]})
        elif t["status"] in ("hoje", "semana"):
            n.append({"id": f"n:{t['id']}:{t['due']}", "tipo": "semana", "sev": "alerta", "titulo": f"{t['titulo']} · {t['animal']}", "texto": f"{t['etapa']} {relativo(t['due'])}, em {br(t['due'])}.", "animalId": t["animalId"], "tarefa": t})
        elif t.get("doc"):
            n.append({"id": f"n:{t['id']}", "tipo": "documental", "sev": "critico" if t.get("critico") else "info", "titulo": f"{t['titulo']} · {t['animal']}", "texto": t["nota"] + ".", "animalId": t["animalId"]})
    limite = iso(add_dias(hoje(), -7))
    nomes = {a["id"]: a["nome"] for a in animais}
    campo = [r for r in registros if r.get("origem") not in ("Portal Gestor", "App do gestor") and r["data"] >= limite]
    for r in reversed(_por_data(campo)):
        if haras.get("avisoOcorrenciaGrave") and r["tipo"] == "ocorrencia" and r.get("gravidade") == "Grave":
            n.append({"id": f"n:ocorrencia:{r['id']}", "tipo": "ocorrencia", "sev": "critico", "titulo": f"Ocorrência grave · {nomes.get(r['animalId'], '')}",
                      "texto": f"{r.get('autor', '')} registrou {(r.get('titulo') or 'uma ocorrência').lower()} em {br(r['data'])}.", "animalId": r["animalId"], "registroId": r["id"]})
            continue
        sev = "alerta" if r["tipo"] == "ocorrencia" and r.get("gravidade") != "Leve" else "info"
        n.append({"id": f"n:campo:{r['id']}", "tipo": "campo", "sev": sev, "titulo": f"Registro do campo · {nomes.get(r['animalId'], '')}", "texto": f"{r.get('autor', '')} registrou {titulo_registro(prots, r).lower()} em {br(r['data'])}.", "animalId": r["animalId"]})
    ordem = {"critico": 0, "alerta": 1, "info": 2}
    n.sort(key=lambda x: ordem[x["sev"]])
    return n


def resumo_registro(haras, animais, registros, prots, r):
    a = next((x for x in animais if x["id"] == r["animalId"]), None)
    if r["tipo"] == "reprodutivo" and r.get("evento") == "Diagnóstico positivo":
        g = gestacao(a, registros, haras.get("gestacaoDias", GESTACAO_DIAS))
        if g:
            return f"Gestação registrada. Parto previsto para {br(g['parto'])} e doses de rinopneumonite no 5º, 7º e 9º mês agendadas."
    p = _protocolo(prots, r["protocolos"][0]) if r.get("protocolos") else None
    if p and a:
        e = proxima_etapa(haras, a, p, registros)
        if e:
            return f"Registro salvo. Próxima etapa de {p['nome']}: {e['etapa'].lower()} em {br(e['due'])}."
    return f"Registro salvo no prontuário de {a['nome'] if a else 'animal'}."
