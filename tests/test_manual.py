"""Manual (Ajuda): toda imagem citada precisa existir no pacote (v1.7.1)."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_imagens_do_manual_existem():
    html = (RAIZ / "web" / "ajuda.html").read_text(encoding="utf-8")
    nomes = sorted(set(re.findall(r"/ajuda/img/([A-Za-z0-9_.-]+)", html)))
    assert nomes, "o manual deveria citar imagens"
    faltam = [n for n in nomes if not (RAIZ / "backend" / "app" / "static" / "ajuda" / n).is_file()]
    assert not faltam, f"imagens do manual sem arquivo em backend/app/static/ajuda: {faltam}"
