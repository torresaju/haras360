"""Leitura do Certificado de Registro Genealógico da ABCCMM (v1.6.0).

O certificado é um PDF com texto (gerado pelo sistema da ABCCMM). A leitura usa a posição de cada
linha na página: os rótulos ("Nome do animal:", "Registro:", ...) ficam à esquerda do valor, na mesma
altura, e a genealogia ocupa quatro colunas (pais, avós, bisavós e trisavós), cada ancestral com o
nome numa linha e "Reg.: ... | DNA ... | livro |" na linha de baixo.
"""
import io
import re

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextLine

VAZIO = re.compile(r"^\*+$")
# Posições da árvore: P = pai, M = mãe; PM = mãe do pai; e assim por diante (4 gerações, 30 ancestrais).
POSICOES = [[("P", "M")[i] for i in range(2)]]
for _g in range(1, 4):
    POSICOES.append([p + s for p in POSICOES[-1] for s in ("P", "M")])
MENSURACOES = {
    "Altura": ["Cernelha", "Garupa"],
    "Comprimento": ["Cabeça", "Pescoço", "Dorso lombo", "Garupa", "Espádua", "Corpo"],
    "Largura": ["Cabeça", "Ancas"],
    "Perímetro": ["Tórax", "Canela"],
}


class CertificadoInvalido(ValueError):
    pass


def linhas_do_pdf(dados: bytes):
    """[(y, x, texto)] da primeira página, y crescendo para baixo."""
    try:
        paginas = list(extract_pages(io.BytesIO(dados), laparams=LAParams(line_margin=0.2, char_margin=1.5), maxpages=1))
    except Exception as e:  # PDF corrompido ou cifrado
        raise CertificadoInvalido("Não foi possível ler o PDF. Envie o certificado original da ABCCMM.") from e
    if not paginas:
        raise CertificadoInvalido("O PDF está vazio.")
    pg = paginas[0]
    out = []

    def andar(o):
        if isinstance(o, LTTextLine):
            t = re.sub(r"\s+", " ", o.get_text()).strip()
            if t:
                out.append((round(pg.height - o.y1, 1), round(o.x0, 1), t))
        elif hasattr(o, "__iter__"):
            for c in o:
                andar(c)

    andar(pg)
    return sorted(out)


def _vazio(v):
    v = (v or "").strip()
    return "" if not v or VAZIO.match(v.replace(" ", "")) else v


def _direita(linhas, rotulo, tol=2.6, ate=None, depois_de_y=None, antes_de_y=None):
    """Texto na mesma altura, logo à direita do rótulo (o mais próximo)."""
    cands = [(y, x, t) for y, x, t in linhas if t.startswith(rotulo)
             and (depois_de_y is None or y > depois_de_y) and (antes_de_y is None or y < antes_de_y)]
    if not cands:
        return ""
    y0, x0, t0 = cands[0]
    resto = t0[len(rotulo):].strip()
    if resto and not resto.endswith(":"):
        return resto
    viz = [(x, t) for y, x, t in linhas if abs(y - y0) <= tol and x > x0 + 1 and (ate is None or x < ate) and not t.endswith(":")]
    return min(viz)[1] if viz else ""


def _reg(t):
    """'Reg.: 044255 | DNA - VP | MM5 | MM7' -> registro, dna, livros."""
    partes = [p.strip() for p in t.split("|")]
    reg = _vazio(partes[0].replace("Reg.:", "").strip()) if partes else ""
    dna = _vazio(partes[1]) if len(partes) > 1 else ""
    livros = [p for p in (_vazio(x) for x in partes[2:]) if p]
    return reg, dna, " / ".join(livros)


def _arvore(linhas):
    colunas = {}
    for y, x, t in linhas:
        if 152 <= y <= 440 and x < 600:
            colunas.setdefault(round(x / 40), []).append((y, x, t))
    # as quatro colunas mais à esquerda com nomes de ancestrais, da esquerda para a direita
    chaves = sorted(colunas)
    grupos = []
    for k in chaves:
        if grupos and abs(min(x for _, x, _ in colunas[k]) - min(x for _, x, _ in grupos[-1])) < 30:
            grupos[-1].extend(colunas[k])
        else:
            grupos.append(list(colunas[k]))
    grupos = [sorted(g) for g in grupos]
    arvore = []
    for gen, col in enumerate(grupos[:4]):
        nomes = []
        for i, (y, x, t) in enumerate(col):
            if t.startswith("Reg.:") or t.startswith("*****|") or re.match(r"^\*+\s*\|", t):
                continue
            prox = next((tt for yy, xx, tt in col[i + 1:] if yy > y), "")
            reg, dna, livro = _reg(prox) if prox.startswith("Reg.:") else ("", "", "")
            nomes.append({"nome": _vazio(t).upper(), "registro": reg, "dna": dna, "livro": livro})
        if len(nomes) != len(POSICOES[gen]):
            raise CertificadoInvalido(f"A genealogia do certificado não pôde ser lida ({gen + 1}ª geração com {len(nomes)} nomes).")
        for pos, n in zip(POSICOES[gen], nomes):
            if n["nome"]:
                arvore.append(dict(n, pos=pos))
    return arvore


def _mensuracoes(linhas):
    secoes = sorted((y, t.rstrip(":")) for y, x, t in linhas if x > 600 and t.rstrip(":") in MENSURACOES and t.endswith(":"))
    out = {}
    for i, (y0, sec) in enumerate(secoes):
        y1 = secoes[i + 1][0] if i + 1 < len(secoes) else y0 + 40
        for rot in MENSURACOES[sec]:
            lab = [(y, x, t) for y, x, t in linhas if y0 < y < y1 and x > 600 and (t.rstrip(":") == rot or t.startswith(rot + ":"))]
            if not lab:
                continue
            ly, lx, lt = lab[0]
            junto = re.match(r"^.*?:\s*(\d+[.,]\d+)", lt)  # rótulo e valor na mesma linha ("Cabeça: 0.51")
            val = [(lx, junto.group(1))] if junto else sorted(
                (x, t) for y, x, t in linhas if abs(y - ly) <= 3.5 and x > lx and re.match(r"^\d+[.,]\d+$", t))
            if val:
                out.setdefault({"Altura": "altura", "Comprimento": "comprimento", "Largura": "largura", "Perímetro": "perimetro"}[sec], {})[rot] = float(val[0][1].replace(",", "."))
    return out


def _pessoa(linhas, rotulo, apos_y=None):
    """Criador ou proprietário: nome, nº de cadastro e, na linha de baixo, propriedade, município e UF."""
    lin = [(y, x, t) for y, x, t in linhas if t.startswith(rotulo) and (apos_y is None or y > apos_y)]
    if not lin:
        return {}, None
    y0 = lin[0][0]
    nome = _direita(linhas, rotulo, ate=240, depois_de_y=y0 - 1, antes_de_y=y0 + 1)
    cad = _direita(linhas, "Nº Cadastro:", depois_de_y=y0 - 3, antes_de_y=y0 + 3)
    yp = y0 + 10
    prop = _direita(linhas, "Propriedade:", ate=240, depois_de_y=yp - 4, antes_de_y=yp + 4)
    mun = _direita(linhas, "Município:", ate=460, depois_de_y=yp - 4, antes_de_y=yp + 4)
    uf = _direita(linhas, "UF:", depois_de_y=yp - 4, antes_de_y=yp + 4)
    return {"nome": _vazio(nome), "cadastro": _vazio(cad), "propriedade": _vazio(prop), "municipio": _vazio(mun), "uf": _vazio(uf)}, y0


def _data(t):
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", t or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def ler(dados: bytes) -> dict:
    if not dados.startswith(b"%PDF"):
        raise CertificadoInvalido("O arquivo não é um PDF.")
    linhas = linhas_do_pdf(dados)
    texto = " ".join(t for _, _, t in linhas)
    if "CERTIFICADO DE REGISTRO GENEAL" not in texto.upper() or "MANGALARGA MARCHADOR" not in texto.upper():
        raise CertificadoInvalido("Este PDF não é um Certificado de Registro Genealógico da ABCCMM.")
    nome = _direita(linhas, "Nome do animal:", ate=460).upper()
    if not nome:
        raise CertificadoInvalido("Não encontrei o nome do animal no certificado.")
    sexo_t = _direita(linhas, "Sexo:", ate=240)
    dna = _direita(linhas, "Exame:", ate=95)
    dna = re.sub(r"^DNA\s*-?\s*", "DNA - ", dna) if dna.upper().startswith("DNA") else (dna or "Sem exame")
    codigos = [t.strip("!") for _, _, t in linhas if re.match(r"^!\d+!$", t)]
    chip = next((c for c in codigos if len(c) == 15), "")
    classif = next((m.group(1) for _, x, t in linhas if x > 500 for m in [re.match(r"^([A-Z]\d)(?:\b|Livro)", t)] if m), "")
    criador, yc = _pessoa(linhas, "Criador:")
    proprietario, _ = _pessoa(linhas, "Proprietário:", apos_y=yc)
    arvore = _arvore(linhas)
    pos = {n["pos"]: n["nome"] for n in arvore}
    serie = next((t.split(":", 1)[1].strip() for _, _, t in linhas if t.startswith("Número de série:")), "")
    return {
        "nome": nome,
        "registro": _vazio(_direita(linhas, "Registro:", ate=360)),
        "livro": _vazio(_direita(linhas, "Livro:", ate=240)),
        "volume": _vazio(_direita(linhas, "Volume:", ate=460)),
        "pagina": _vazio(_direita(linhas, "Página:")),
        "nascimento": _data(_direita(linhas, "Data de nascimento:")),
        "sexo": "F" if sexo_t.lower().startswith("f") else "M" if sexo_t.lower().startswith("m") else "",
        "dna": _vazio(dna) or "Sem exame",
        "chip": chip,
        "pelagem": _vazio(_direita(linhas, "Pelagem:")).upper(),
        "classificacao": classif,
        "dataResenha": _data(_direita(linhas, "Data da resenha:")),
        "dataRegistro": _data(_direita(linhas, "Data do registro:")),
        "criador": criador,
        "proprietario": proprietario,
        "mensuracoes": _mensuracoes(linhas),
        "genealogia": {"pai": pos.get("P", ""), "mae": pos.get("M", ""), "avoPaterno": pos.get("PP", ""), "avoPaterna": pos.get("PM", ""),
                       "avoMaterno": pos.get("MP", ""), "avoMaterna": pos.get("MM", ""), "arvore": arvore},
        "serie": serie,
    }
