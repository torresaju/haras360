"""Gera um PDF de teste a partir de linhas (y, x, texto), sem bibliotecas externas.

Usado para montar um certificado da ABCCMM com dados fictícios (tests/fixtures/certificado_teste.json),
na mesma posição do original, e testar a leitura completa (PDF -> dados).
"""
import json
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "certificado_teste.json"


def _esc(t):
    return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_de_linhas(linhas, largura=841, altura=595, tamanho=7):
    corpo = []
    for y, x, t in linhas:
        base = altura - y - tamanho * 0.75  # y é o topo da linha, medido de cima
        corpo.append(f"BT /F1 {tamanho} Tf {x:.1f} {base:.1f} Td ({_esc(t)}) Tj ET")
    stream = "\n".join(corpo).encode("cp1252")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {largura} {altura}] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    pos = []
    for i, o in enumerate(objs, 1):
        pos.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for p in pos:
        out += f"{p:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def certificado_teste(**troca):
    """PDF do certificado fictício; troca={'texto antigo': 'novo'} altera linhas (ex.: outro nome)."""
    linhas = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for velho, novo in troca.items():
        linhas = [[y, x, t.replace(velho, novo)] for y, x, t in linhas]
    return pdf_de_linhas(linhas)
