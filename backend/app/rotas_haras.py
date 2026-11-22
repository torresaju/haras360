"""Rotas dos usuários de um haras (gestor e caseiro)."""
import base64
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy import select

from . import logos as L
from . import imagens as IMG
from . import parametros as P
from . import regras as R
from .config import FOTOS_DIR, LOGOS_DIR, VERSAO
from .db import Animal, Audio, Auditoria, Foto, Haras, Importacao, NotifLida, Protocolo, Registro, Usuario
from .seguranca import auditar, do_haras, erro, gestor, get_db, hash_senha, revogar_sessoes, usuario_atual, validar_senha_nova

r = APIRouter()


def nid():
    return uuid.uuid4().hex[:10]


def _iso(v):
    return v.isoformat() if v else ""


def _data(v, campo, obrigatorio=True):
    if not v:
        if obrigatorio:
            erro(400, f"Informe {campo}.")
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        erro(400, f"Data inválida em {campo}.")


def _txt(v, n=200):
    return str(v or "").strip()[:n]


DO_GESTOR = ("Portal Gestor", "App do gestor")  # origens que não são registros do campo


def origem_de(request: Request, u: Usuario = None):
    o = {"gestor": "Portal Gestor", "campo": "Portal Cliente", "app": "App"}.get(request.headers.get("x-portal", ""), "Portal Cliente")
    if o == "App" and u is not None and u.perfil == "gestor":
        return "App do gestor"  # v1.5.0
    return o


# ---------------- leitura do estado ----------------
def animal_out(a: Animal):
    return {"id": a.id, "nome": a.nome, "livro": a.livro or "", "registro": a.registro or "", "sexo": a.sexo, "bloqueado": bool(a.bloqueado), "vivo": bool(a.vivo),
            "dna": a.dna or "", "nascimento": _iso(a.nascimento), "chip": a.chip or "", "pelagem": a.pelagem or "", "genealogia": a.genealogia or {},
            "origem": a.origem or "", "importadoEm": _iso(a.importado_em), "criadoEm": _iso(a.criado_em.date() if a.criado_em else None),
            "baixa": ({"data": _iso(a.baixa_data), "motivo": a.baixa_motivo or "", "destino": a.baixa_destino or "", "obs": a.baixa_obs or ""}
                      if a.baixa_data else None),
            "certificado": a.certificado or None, "externo": bool(a.externo), "contato": a.contato or {}}


def _dose_out(v):
    return int(v) if v and str(v).isdigit() else (v or "unica")


def registro_out(rg: Registro, fotos, audios=None):
    o = {"id": rg.id, "animalId": rg.animal_id, "data": _iso(rg.data), "tipo": rg.tipo, "protocolos": rg.protocolos or [], "dose": _dose_out(rg.dose),
         "obs": rg.obs or "", "autor": rg.autor, "origem": rg.origem, "fotos": [f"/fotos/{f}" for f in fotos.get(rg.id, [])]}
    au = (audios or {}).get(rg.id)
    if au:
        o["audio"] = {"url": f"/audios/{au.id}", "duracao": au.duracao}
    o.update(rg.dados or {})
    return o


def protocolos_haras(db, haras_id):
    ps = [p.dados for p in db.scalars(select(Protocolo).where(Protocolo.haras_id == haras_id))]
    if not ps:
        for p in R.protocolos_padrao():
            db.add(Protocolo(haras_id=haras_id, pid=p["id"], dados=p))
        db.commit()
        ps = R.protocolos_padrao()
    return sorted(ps, key=lambda p: p.get("ordem", 99))


def haras_out(db, h: Haras):
    o = {"id": h.id, "nome": h.nome, "proprietario": h.proprietario or "", "municipio": h.municipio or "", "raivaSemestral": bool(h.raiva_semestral),
         "associadoABCCMM": h.associado_abccmm or "", "logo": L.url(h)}
    o.update(P.todos(db, h.id))
    return o


def carregar_base(db, haras_id):
    h = db.get(Haras, haras_id)
    animais = [animal_out(a) for a in db.scalars(select(Animal).where(Animal.haras_id == haras_id).order_by(Animal.nome))]
    fmap = {}
    for f in db.scalars(select(Foto).where(Foto.haras_id == haras_id).order_by(Foto.ordem)):
        fmap.setdefault(f.registro_id, []).append(f.id)
    amap = {a.registro_id: a for a in db.scalars(select(Audio).where(Audio.haras_id == haras_id))}
    regs = [registro_out(x, fmap, amap) for x in db.scalars(select(Registro).where(Registro.haras_id == haras_id).order_by(Registro.data, Registro.criado_em))]
    return h, animais, regs, protocolos_haras(db, haras_id)


@r.get("/api/estado")
def estado(u: Usuario = Depends(do_haras), db=Depends(get_db)):
    h, animais, regs, prots = carregar_base(db, u.haras_id)
    if u.perfil != "gestor":  # o caseiro não vê animais de fora do haras (v1.6.0)
        fora = {a["id"] for a in animais if a.get("externo")}
        animais = [a for a in animais if a["id"] not in fora]
        regs = [x for x in regs if x["animalId"] not in fora]
    hd = haras_out(db, h)
    ts = R.tarefas(hd, animais, regs, prots)
    usuarios = []
    if u.perfil == "gestor":
        usuarios = [{"id": x.id, "nome": x.nome, "email": x.email, "perfil": x.perfil, "ativo": bool(x.ativo), "doisFatores": bool(x.totp_ativo)}
                    for x in db.scalars(select(Usuario).where(Usuario.haras_id == u.haras_id).order_by(Usuario.id))]
    lidas = list(db.scalars(select(NotifLida.nid).where(NotifLida.usuario_id == u.id)))
    plano = P.plano_do_haras(db, h)
    ativos = sum(1 for a in animais if a["vivo"])
    faixas = P.ler(db, "faixas")
    return {
        "versao": VERSAO, "hoje": R.iso(R.hoje()), "limiteAnimais": plano["limite"],
        "plano": dict(plano, faixas=faixas, mensalidade=P.mensalidade(faixas, ativos), modulosNomes=P.MODULOS),
        "normas": P.ler(db, "normas_abccmm") if u.perfil == "gestor" else [],
        "haras": hd, "usuario": {"id": u.id, "nome": u.nome, "email": u.email, "perfil": u.perfil},
        "usuarios": usuarios, "animais": animais, "registros": regs, "protocolos": prots,
        "notifPrefs": {**R.notif_prefs_padrao(), **(h.notif_prefs or {})}, "lidas": lidas,
        "tarefas": ts, "gestacoes": {a["id"]: R.gestacao(a, regs, hd["gestacaoDias"]) for a in animais},
        "notificacoes": R.notificacoes(hd, animais, regs, prots, ts),
        "imagens": IMG.descrever(db, u.haras_id),
    }


# ---------------- animais ----------------
def _limite(db, haras_id):
    return P.plano_do_haras(db, db.get(Haras, haras_id))["limite"]


def _ativos(db, haras_id, excluir=None):
    q = select(Animal).where(Animal.haras_id == haras_id, Animal.vivo.is_(True), Animal.externo.isnot(True))
    return [a for a in db.scalars(q) if a.id != excluir]


def _aplicar_animal(a: Animal, b: dict, db, haras_id, limite):
    nome = _txt(b.get("nome"), 160).upper()
    if not nome:
        erro(400, "Informe o nome do animal.")
    sexo = _txt(b.get("sexo"), 1).upper()
    if sexo not in ("M", "F"):
        erro(400, "Sexo deve ser M ou F.")
    if a.externo and not b.get("nascimento"):
        nasc = None  # animal de fora: o nascimento é opcional
    else:
        nasc = _data(b.get("nascimento"), "a data de nascimento")
    if nasc and nasc > R.hoje():
        erro(400, "A data de nascimento não pode ser futura.")
    registro = _txt(b.get("registro"), 20)
    if not re.search(r"\d", registro):
        registro = ""  # "sem registro", "*****" e afins: o animal fica sem registro (v1.5.2)
    if registro:
        dup = db.scalar(select(Animal).where(Animal.haras_id == haras_id, Animal.registro == registro, Animal.id != (a.id or "")))
        if dup:
            erro(409, f"O registro {registro} já pertence a {dup.nome}.")
    vivo = bool(b.get("vivo", True)) and not a.baixa_data and not a.externo  # baixado ou externo fica fora do plantel ativo
    if vivo and (a.vivo is not True) and len(_ativos(db, haras_id, a.id)) >= limite:
        erro(400, f"O plano deste haras atende até {limite} animais ativos.")
    a.nome, a.sexo, a.nascimento, a.registro, a.vivo = nome, sexo, nasc, registro, vivo
    a.livro = _txt(b.get("livro"), 120)
    a.bloqueado = bool(b.get("bloqueado", False))
    a.dna = _txt(b.get("dna"), 40)
    a.chip = _txt(b.get("chip"), 30)
    if not re.search(r"\d", a.chip):
        a.chip = ""
    a.pelagem = _txt(b.get("pelagem"), 60)
    g = b.get("genealogia") or {}
    # mantém a árvore completa lida do certificado (v1.6.0) e atualiza os seis nomes do formulário
    a.genealogia = {**(a.genealogia or {}), **{k: _txt(g.get(k), 160).upper() for k in ("pai", "mae", "avoPaterno", "avoPaterna", "avoMaterno", "avoMaterna")}}
    if a.externo:
        c = b.get("contato") or {}
        email = _txt(c.get("email"), 160)
        if email and "@" not in email:
            erro(400, "E-mail do contato inválido.")
        a.contato = {"proprietario": _txt(c.get("proprietario"), 160), "telefone": _txt(c.get("telefone"), 40), "email": email, "obs": _txt(c.get("obs"), 500)}


@r.post("/api/animais")
def criar_animal(request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    externo = bool(body.get("externo"))
    a = Animal(id="a" + nid(), haras_id=u.haras_id, origem="Externo" if externo else "Cadastro manual", vivo=None, externo=externo)
    _aplicar_animal(a, body, db, u.haras_id, _limite(db, u.haras_id))
    db.add(a)
    auditar(db, "animal_criado", usuario=u, alvo=a.nome + (" (externo)" if externo else ""), request=request)
    db.commit()
    return {"id": a.id, "resumo": f"{a.nome} cadastrado como animal externo." if externo else f"{a.nome} cadastrado. A agenda sanitária foi gerada."}


@r.put("/api/animais/{aid}")
def editar_animal(aid: str, request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    a = db.get(Animal, aid)
    if not a or a.haras_id != u.haras_id:
        erro(404, "Animal não encontrado.")
    _aplicar_animal(a, body, db, u.haras_id, _limite(db, u.haras_id))
    auditar(db, "animal_editado", usuario=u, alvo=a.nome, request=request)
    db.commit()
    return {"id": a.id, "resumo": f"Dados de {a.nome} salvos."}


@r.post("/api/importacao")
def importar(request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    h = db.get(Haras, u.haras_id)
    if not P.modulo_liberado(db, h, "importacao"):
        erro(403, "A importação ABCCMM não está incluída no plano deste haras.")
    lst = body.get("animais") or []
    if not isinstance(lst, list) or not lst:
        erro(400, "Nenhum animal selecionado para importar.")
    if len(lst) > 200:
        erro(400, "Arquivo com animais demais para um haras.")
    limite = _limite(db, u.haras_id)
    impresso = _data(body.get("impresso"), "a data do relatório", obrigatorio=False) or R.hoje()
    existentes = list(db.scalars(select(Animal).where(Animal.haras_id == u.haras_id)))
    norm = lambda s: re.sub(r"\s+", " ", (s or "").strip().upper())  # noqa: E731
    ativos = len([a for a in existentes if a.vivo])
    novos = atual = 0
    baixados = []
    for n in lst:
        reg, chip, nome = _txt(n.get("registro"), 20), _txt(n.get("chip"), 30), norm(n.get("nome"))
        ex = next((a for a in existentes if (reg and a.registro == reg) or (chip and a.chip == chip) or norm(a.nome) == nome), None)
        if ex is None:
            if bool(n.get("vivo", True)) and ativos >= limite:
                erro(400, f"A importação ultrapassa o limite de {limite} animais ativos do plano. Desmarque alguns animais.")
            a = Animal(id="a" + nid(), haras_id=u.haras_id, origem="Importação ABCCMM", importado_em=impresso, vivo=None, genealogia={})
            _aplicar_animal(a, dict(n, genealogia={}), db, u.haras_id, limite)
            db.add(a)
            db.flush()
            existentes.append(a)
            ativos += 1 if a.vivo else 0
            novos += 1
        else:
            _aplicar_animal(ex, dict(n, genealogia=ex.genealogia or {}, pelagem=ex.pelagem), db, u.haras_id, limite)
            ex.importado_em = impresso
            atual += 1
            if ex.baixa_data:
                baixados.append(ex.nome)
    if body.get("associado"):
        h.associado_abccmm = _txt(body.get("associado"), 160)
    arquivo = _txt(body.get("arquivo"), 200)
    db.add(Importacao(haras_id=u.haras_id, usuario_id=u.id, arquivo=arquivo, associado=_txt(body.get("associado"), 160), impresso=impresso,
                      novos=novos, atualizados=atual))
    auditar(db, "importacao", usuario=u, alvo=arquivo, detalhe={"novos": novos, "atualizados": atual}, request=request)
    db.commit()
    resumo = f"{novos} animal(is) importado(s) e {atual} atualizado(s). A agenda sanitária foi recalculada."
    if baixados:
        resumo += f" Continuam baixados (fora do plantel ativo): {', '.join(baixados)}."
    return {"novos": novos, "atualizados": atual, "baixados": baixados, "resumo": resumo}


# ---------------- baixa do plantel (v1.4.0) ----------------
def _animal_do_haras(db, aid, u):
    a = db.get(Animal, aid)
    if not a or a.haras_id != u.haras_id:
        erro(404, "Animal não encontrado.")
    return a


@r.post("/api/animais/{aid}/baixa")
def dar_baixa(aid: str, request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    a = _animal_do_haras(db, aid, u)
    if a.externo:
        erro(400, "Animais externos não fazem parte do plantel e não recebem baixa.")
    if a.baixa_data:
        erro(400, f"{a.nome} já está baixado desde {R.br(a.baixa_data)}.")
    data = _data(body.get("data"), "a data da baixa")
    if data > R.hoje():
        erro(400, "A data da baixa não pode ser futura.")
    if a.nascimento and data < a.nascimento:
        erro(400, "A data da baixa não pode ser anterior ao nascimento.")
    motivo = _txt(body.get("motivo"), 20)
    if motivo not in R.MOTIVOS_BAIXA:
        erro(400, "Escolha o motivo: venda, morte, doação ou transferência.")
    a.baixa_data, a.baixa_motivo = data, motivo
    a.baixa_destino, a.baixa_obs = _txt(body.get("destino"), 160), _txt(body.get("obs"), 2000)
    a.vivo = False
    auditar(db, "animal_baixa", usuario=u, alvo=a.nome, detalhe={"data": _iso(data), "motivo": motivo, "destino": a.baixa_destino}, request=request)
    db.commit()
    return {"resumo": f"Baixa de {a.nome} registrada ({motivo.lower()} em {R.br(data)}). O animal saiu do plantel ativo e da agenda."}


@r.delete("/api/animais/{aid}/baixa")
def desfazer_baixa(aid: str, request: Request, u: Usuario = Depends(gestor), db=Depends(get_db)):
    a = _animal_do_haras(db, aid, u)
    if not a.baixa_data:
        erro(400, f"{a.nome} não está baixado.")
    limite = _limite(db, u.haras_id)
    if len(_ativos(db, u.haras_id, a.id)) >= limite:
        erro(400, f"O plano deste haras atende até {limite} animais ativos.")
    detalhe = {"data": _iso(a.baixa_data), "motivo": a.baixa_motivo, "destino": a.baixa_destino}
    a.baixa_data = a.baixa_motivo = a.baixa_destino = a.baixa_obs = None
    a.vivo = True
    auditar(db, "animal_baixa_desfeita", usuario=u, alvo=a.nome, detalhe=detalhe, request=request)
    db.commit()
    return {"resumo": f"{a.nome} voltou ao plantel ativo. A agenda foi recalculada."}


# ---------------- registros e fotos ----------------
CAMPOS_DADOS = {"produto": 160, "lote": 40, "ferrador": 120, "resultado": 120, "exame": 80, "procedimento": 80, "evento": 40, "garanhao": 160,
                "dataCobertura": 10, "titulo": 160, "gravidade": 20, "sinais": 200, "ovario": 10, "foliculo": 3, "edema": 1,
                "semen": 12, "central": 120}
SEMEN = ("Fresco", "Refrigerado", "Congelado")
OVARIOS = ("Esquerdo", "Direito")
ASSINATURAS = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp"}
ID_CLIENTE = re.compile(r"^[A-Za-z0-9-]{8,40}$")


def _salvar_foto(data_url, haras_id):
    m = re.match(r"^data:image/(jpeg|png|webp);base64,(.+)$", data_url or "", re.S)
    if not m:
        erro(400, "Formato de foto não suportado. Use JPG, PNG ou WebP.")
    raw = base64.b64decode(m.group(2), validate=False)
    if len(raw) > 4 * 1024 * 1024:
        erro(400, "Cada foto pode ter no máximo 4 MB.")
    ext = next((e for sig, e in ASSINATURAS.items() if raw.startswith(sig)), None)
    if not ext:
        erro(400, "O arquivo enviado não é uma imagem válida.")
    pasta = Path(FOTOS_DIR) / str(haras_id)
    pasta.mkdir(parents=True, exist_ok=True)
    fid = uuid.uuid4().hex
    arq = f"{fid}.{ext}"
    (pasta / arq).write_bytes(raw)
    return fid, arq


@r.post("/api/registros")
def criar_registro(request: Request, body: dict = Body(...), u: Usuario = Depends(do_haras), db=Depends(get_db)):
    h = db.get(Haras, u.haras_id)
    if u.perfil == "operador" and not P.modulo_liberado(db, h, "caseiro"):
        erro(403, "O acesso do caseiro não está incluído no plano deste haras.")
    # Identificador gerado no aparelho: reenvio do mesmo registro não duplica.
    rid = _txt(body.get("id"), 40)
    if rid:
        if not ID_CLIENTE.match(rid):
            erro(400, "Identificador de registro inválido.")
        ja = db.get(Registro, rid)
        if ja:
            if ja.haras_id != u.haras_id:
                erro(409, "Identificador de registro em uso.")
            return {"id": ja.id, "resumo": "Registro já recebido anteriormente.", "duplicado": True}
    a = db.get(Animal, _txt(body.get("animalId"), 16))
    if not a or a.haras_id != u.haras_id or (a.externo and u.perfil != "gestor"):
        erro(404, "Animal não encontrado.")
    tipo = _txt(body.get("tipo"), 20)
    if tipo not in R.CATS or tipo == "documental":
        erro(400, "Tipo de registro inválido.")
    if a.externo and tipo != "reprodutivo":
        erro(400, "Animais externos recebem só registros de reprodução.")
    data = _data(body.get("data"), "a data do registro")
    if data > R.hoje():
        erro(400, "A data não pode ser futura.")
    prots = {p["id"] for p in protocolos_haras(db, u.haras_id)}
    pl = [p for p in (body.get("protocolos") or []) if p in prots]
    if tipo == "vacina" and not pl:
        erro(400, "Marque ao menos uma doença coberta pela vacina.")
    dose = str(body.get("dose") or "unica")
    if dose not in ("1", "2", "3", "reforco", "unica"):
        erro(400, "Dose inválida.")
    dados = {k: _txt(body.get(k), n) for k, n in CAMPOS_DADOS.items() if body.get(k) not in (None, "")}
    if tipo == "reprodutivo":
        if dados.get("evento") not in R.EVENTOS_REPRO:
            erro(400, "Evento reprodutivo inválido.")
        if a.sexo != "F" and dados["evento"] != "Cobertura":
            erro(400, "Eventos de gestação só se aplicam a fêmeas.")
        if dados["evento"] == "Diagnóstico positivo":
            cob = _data(dados.get("dataCobertura"), "a data da cobertura")
            if cob > data:
                erro(400, "A cobertura deve ser anterior ao diagnóstico.")
        if dados["evento"] == "Cio":
            if dados.get("ovario") and dados["ovario"] not in OVARIOS:
                erro(400, "Ovário deve ser esquerdo ou direito.")
            if dados.get("foliculo") and not (dados["foliculo"].isdigit() and 5 <= int(dados["foliculo"]) <= 80):
                erro(400, "Tamanho do folículo deve ficar entre 5 e 80 mm.")
            if dados.get("edema") and dados["edema"] not in ("0", "1", "2", "3"):
                erro(400, "Edema uterino deve ser de 0 a 3.")
        else:
            for k in ("sinais", "ovario", "foliculo", "edema"):
                dados.pop(k, None)
        if dados["evento"] == "Inseminação":  # v1.6.0: tipo de sêmen e central ou origem
            if dados.get("semen") and dados["semen"] not in SEMEN:
                erro(400, "Tipo de sêmen deve ser fresco, refrigerado ou congelado.")
        else:
            dados.pop("semen", None)
            dados.pop("central", None)
        dados["garanhao"] = dados.get("garanhao", "").upper()
    if tipo == "ocorrencia" and not dados.get("titulo"):
        erro(400, "Descreva a ocorrência em poucas palavras.")
    fotos = body.get("fotos") or []
    if len(fotos) > 4:
        erro(400, "Envie no máximo 4 fotos por registro.")
    rg = Registro(id=rid or "r" + nid(), haras_id=u.haras_id, animal_id=a.id, data=data, tipo=tipo, protocolos=pl, dose=dose, obs=_txt(body.get("obs"), 4000),
                  dados=dados, autor=u.nome, autor_id=u.id, origem=origem_de(request, u))
    db.add(rg)
    db.flush()
    salvos = []
    try:
        for i, f in enumerate(fotos):
            fid, arq = _salvar_foto(f, u.haras_id)
            salvos.append(arq)
            db.add(Foto(id=fid, registro_id=rg.id, haras_id=u.haras_id, arquivo=arq, ordem=i))
        db.commit()
    except Exception:
        db.rollback()
        for arq in salvos:
            (Path(FOTOS_DIR) / str(u.haras_id) / arq).unlink(missing_ok=True)
        raise
    h, animais, regs, prs = carregar_base(db, u.haras_id)
    ro = next(x for x in regs if x["id"] == rg.id)
    return {"id": rg.id, "resumo": R.resumo_registro(haras_out(db, h), animais, regs, prs, ro)}


@r.delete("/api/registros/{rid}")
def excluir_registro(rid: str, request: Request, u: Usuario = Depends(gestor), db=Depends(get_db)):
    rg = db.get(Registro, rid)
    if not rg or rg.haras_id != u.haras_id:
        erro(404, "Registro não encontrado.")
    a = db.get(Animal, rg.animal_id)
    for f in db.scalars(select(Foto).where(Foto.registro_id == rid)):
        (Path(FOTOS_DIR) / str(f.haras_id) / f.arquivo).unlink(missing_ok=True)
        db.delete(f)
    for au in db.scalars(select(Audio).where(Audio.registro_id == rid)):
        (Path(FOTOS_DIR) / str(au.haras_id) / au.arquivo).unlink(missing_ok=True)
        db.delete(au)
    auditar(db, "registro_excluido", usuario=u, alvo=f"{a.nome if a else ''} · {rg.tipo} de {_iso(rg.data)}",
            detalhe={"autor": rg.autor, "origem": rg.origem, "tipo": rg.tipo, "dados": rg.dados, "obs": rg.obs}, request=request)
    db.delete(rg)
    db.commit()
    return {"resumo": "Registro excluído. A agenda foi recalculada."}


@r.get("/fotos/{fid}")
def foto(fid: str, u: Usuario = Depends(do_haras), db=Depends(get_db)):
    f = db.get(Foto, fid)
    if not f or f.haras_id != u.haras_id:
        erro(404, "Foto não encontrada.")
    p = Path(FOTOS_DIR) / str(f.haras_id) / f.arquivo
    if not p.exists():
        erro(404, "Arquivo da foto não encontrado.")
    return FileResponse(p, headers={"Cache-Control": "private, max-age=86400"})


@r.get("/audios/{aid}")
def audio(aid: str, u: Usuario = Depends(do_haras), db=Depends(get_db)):
    a = db.get(Audio, aid)
    if not a or a.haras_id != u.haras_id:
        erro(404, "Áudio não encontrado.")
    p = Path(FOTOS_DIR) / str(a.haras_id) / a.arquivo
    if not p.exists():
        erro(404, "Arquivo do áudio não encontrado.")
    return FileResponse(p, media_type="audio/mp4", headers={"Cache-Control": "private, max-age=86400"})


# ---------------- protocolos e parâmetros do haras ----------------
@r.put("/api/protocolos")
def salvar_protocolos(request: Request, body: list = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    protocolos_haras(db, u.haras_id)
    atuais = {p.pid: p for p in db.scalars(select(Protocolo).where(Protocolo.haras_id == u.haras_id))}
    mudancas = []
    for item in body:
        p = atuais.get(item.get("id"))
        if not p:
            continue
        dd = dict(p.dados)
        antes = {k: dd.get(k) for k in ("ativo", "idadeMeses", "serie", "reforcoDias")}
        dd["ativo"] = bool(item.get("ativo", dd.get("ativo")))
        try:
            if "idadeMeses" in item:
                v = int(item["idadeMeses"])
                if not 0 <= v <= 120:
                    raise ValueError
                dd["idadeMeses"] = v
            if "serie" in item:
                s = [int(x) for x in item["serie"]]
                if any(x < 1 or x > 400 for x in s) or len(s) > 5:
                    raise ValueError
                dd["serie"] = s
            if "reforcoDias" in item:
                v = int(item["reforcoDias"])
                if not 1 <= v <= 1500:
                    raise ValueError
                dd["reforcoDias"] = v
        except (TypeError, ValueError):
            erro(400, f"Valor inválido em {dd['nome']}.")
        depois = {k: dd.get(k) for k in antes}
        if depois != antes:
            mudancas.append({"protocolo": dd["nome"], "antes": antes, "depois": depois})
        p.dados = dd
    if mudancas:
        auditar(db, "protocolos_alterados", usuario=u, alvo=", ".join(m["protocolo"] for m in mudancas), detalhe={"mudancas": mudancas}, request=request)
    db.commit()
    return {"resumo": "Protocolos salvos. A agenda de todos os animais foi recalculada."}


@r.post("/api/protocolos/restaurar")
def restaurar_protocolos(request: Request, u: Usuario = Depends(gestor), db=Depends(get_db)):
    for p in db.scalars(select(Protocolo).where(Protocolo.haras_id == u.haras_id)):
        db.delete(p)
    auditar(db, "protocolos_restaurados", usuario=u, request=request)
    db.commit()
    protocolos_haras(db, u.haras_id)
    return {"resumo": "Protocolos restaurados para o padrão."}


@r.put("/api/haras")
def editar_haras(request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    h = db.get(Haras, u.haras_id)
    antes = haras_out(db, h)
    if "raivaSemestral" in body:
        h.raiva_semestral = bool(body["raivaSemestral"])
    for k in ("nome", "proprietario", "municipio"):
        if k in body and _txt(body[k], 120):
            setattr(h, k, _txt(body[k], 120))
    try:
        novos = P.validar_haras(body)
        de, ate = novos.get("cioPotroDe", antes["cioPotroDe"]), novos.get("cioPotroAte", antes["cioPotroAte"])
        if de > ate:
            raise ValueError("A janela do cio do potro precisa começar antes de terminar.")
        for k, v in novos.items():
            P.gravar(db, k, v, h.id)
    except ValueError as e:
        erro(400, str(e))
    db.flush()
    depois = haras_out(db, h)
    dif = {k: {"antes": antes[k], "depois": depois[k]} for k in depois if antes.get(k) != depois[k]}
    if dif:
        auditar(db, "parametro_alterado", usuario=u, alvo="haras", detalhe=dif, request=request)
    db.commit()
    return {"resumo": "Parametrizações do haras salvas. A agenda foi recalculada."}


@r.put("/api/haras/logo")
def trocar_logo(request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    h = db.get(Haras, u.haras_id)
    L.salvar(h, body.get("imagem"))
    auditar(db, "logo_alterado", usuario=u, alvo=h.nome, request=request)
    db.commit()
    return {"resumo": "Logotipo do haras atualizado.", "logo": L.url(h)}


@r.delete("/api/haras/logo")
def remover_logo(request: Request, u: Usuario = Depends(gestor), db=Depends(get_db)):
    h = db.get(Haras, u.haras_id)
    L.remover_arquivo(h.logo)
    h.logo = None
    auditar(db, "logo_alterado", usuario=u, alvo=f"{h.nome} (removido)", request=request)
    db.commit()
    return {"resumo": "Logotipo removido. O portal volta a mostrar a marca Haras360."}


@r.get("/logos/{nome}")
def ver_logo(nome: str, u: Usuario = Depends(usuario_atual), db=Depends(get_db)):
    m = re.fullmatch(r"(\d+)-[0-9a-f]{12}\.(png|jpg|webp)", nome)
    if not m or (u.perfil != "admin" and str(u.haras_id) != m.group(1)):
        erro(404, "Logotipo não encontrado.")
    p = LOGOS_DIR / nome
    if not p.is_file():
        erro(404, "Logotipo não encontrado.")
    return FileResponse(p, headers={"Cache-Control": "private, max-age=604800"})


@r.put("/api/notif-prefs")
def prefs(body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    h = db.get(Haras, u.haras_id)
    base = R.notif_prefs_padrao()
    for t in base:
        for c in base[t]:
            v = (body.get(t) or {}).get(c)
            if v is not None:
                base[t][c] = bool(v)
    h.notif_prefs = base
    db.commit()
    return {"ok": True}


@r.post("/api/notificacoes/lidas")
def marcar_lidas(body: dict = Body(...), u: Usuario = Depends(do_haras), db=Depends(get_db)):
    ja = set(db.scalars(select(NotifLida.nid).where(NotifLida.usuario_id == u.id)))
    for n in (body.get("ids") or [])[:500]:
        n = _txt(n, 190)
        if n and n not in ja:
            db.add(NotifLida(usuario_id=u.id, nid=n))
            ja.add(n)
    db.commit()
    return {"ok": True}


# ---------------- equipe ----------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@r.post("/api/usuarios")
def criar_usuario(request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    nome, email, perfil, senha = _txt(body.get("nome"), 120), _txt(body.get("email"), 160).lower(), body.get("perfil"), str(body.get("senha") or "")
    if not nome:
        erro(400, "Informe o nome.")
    if not EMAIL_RE.match(email):
        erro(400, "Informe um e-mail válido.")
    if perfil not in ("gestor", "operador"):
        erro(400, "Perfil inválido.")
    if perfil == "operador" and not P.modulo_liberado(db, db.get(Haras, u.haras_id), "caseiro"):
        erro(403, "O usuário caseiro não está incluído no plano deste haras.")
    validar_senha_nova(senha)
    if db.scalar(select(Usuario).where(Usuario.email == email)):
        erro(409, "Já existe um usuário com esse e-mail.")
    db.add(Usuario(haras_id=u.haras_id, nome=nome, email=email, perfil=perfil, senha_hash=hash_senha(senha), ativo=True))
    auditar(db, "usuario_criado", usuario=u, alvo=f"{nome} <{email}> ({perfil})", request=request)
    db.commit()
    extra = " No primeiro acesso, o gestor cadastra o 2FA." if perfil == "gestor" else ""
    return {"resumo": f"{nome} adicionado. Envie o endereço e a senha inicial para o primeiro acesso.{extra}"}


def _usuario_do_haras(db, uid, u):
    x = db.get(Usuario, uid)
    if not x or x.haras_id != u.haras_id:
        erro(404, "Usuário não encontrado.")
    return x


@r.patch("/api/usuarios/{uid}")
def editar_usuario(uid: int, request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    x = _usuario_do_haras(db, uid, u)
    if x.id == u.id:
        erro(400, "Você não pode desativar o próprio acesso.")
    if "ativo" in body:
        x.ativo = bool(body["ativo"])
        if not x.ativo:
            revogar_sessoes(db, x.id)
        auditar(db, "usuario_ativado" if x.ativo else "usuario_desativado", usuario=u, alvo=f"{x.nome} <{x.email}>", request=request)
    db.commit()
    return {"ok": True}


@r.post("/api/usuarios/{uid}/senha")
def redefinir_senha(uid: int, request: Request, body: dict = Body(...), u: Usuario = Depends(gestor), db=Depends(get_db)):
    x = _usuario_do_haras(db, uid, u)
    senha = str(body.get("senha") or "")
    validar_senha_nova(senha)
    x.senha_hash = hash_senha(senha)
    revogar_sessoes(db, x.id)
    auditar(db, "senha_redefinida", usuario=u, alvo=f"{x.nome} <{x.email}>", request=request)
    db.commit()
    return {"resumo": f"Senha de {x.nome} redefinida. As sessões abertas dele foram encerradas."}


@r.post("/api/usuarios/{uid}/2fa/redefinir")
def redefinir_2fa(uid: int, request: Request, u: Usuario = Depends(gestor), db=Depends(get_db)):
    x = _usuario_do_haras(db, uid, u)
    if x.id == u.id:
        erro(400, "Para refazer o seu próprio 2FA, peça a outro gestor ou ao administrador.")
    if x.perfil != "gestor":
        erro(400, "Só gestores usam 2FA.")
    x.totp_ativo, x.totp_segredo, x.recuperacao = False, None, None
    revogar_sessoes(db, x.id)
    auditar(db, "2fa_redefinido", usuario=u, alvo=f"{x.nome} <{x.email}>", request=request)
    db.commit()
    return {"resumo": f"2FA de {x.nome} redefinido. No próximo login ele cadastra um novo aplicativo autenticador."}


# ---------------- auditoria ----------------
def consultar_auditoria(db, haras_id=None, acao="", texto="", de="", ate="", limite=200):
    q = select(Auditoria)
    if haras_id is not None:
        q = q.where(Auditoria.haras_id == haras_id)
    if acao:
        q = q.where(Auditoria.acao == acao)
    if texto:
        t = f"%{texto[:60]}%"
        q = q.where((Auditoria.usuario.like(t)) | (Auditoria.alvo.like(t)) | (Auditoria.ip.like(t)))
    if de:
        q = q.where(Auditoria.quando >= datetime.fromisoformat(str(_data(de, "a data inicial"))))
    if ate:
        q = q.where(Auditoria.quando < datetime.fromisoformat(str(_data(ate, "a data final"))) + timedelta(days=1))
    q = q.order_by(Auditoria.quando.desc(), Auditoria.id.desc()).limit(max(1, min(int(limite), 1000)))
    return [{"id": a.id, "quando": a.quando.isoformat(timespec="seconds"), "usuario": a.usuario, "ip": a.ip, "acao": a.acao, "alvo": a.alvo,
             "resultado": a.resultado, "detalhe": a.detalhe, "harasId": a.haras_id} for a in db.scalars(q)]


@r.get("/api/auditoria")
def auditoria_haras(acao: str = "", texto: str = "", de: str = "", ate: str = "", limite: int = 200, u: Usuario = Depends(gestor), db=Depends(get_db)):
    return consultar_auditoria(db, u.haras_id, acao, texto, de, ate, limite)
