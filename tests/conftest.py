import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))

_tmp = tempfile.mkdtemp(prefix="haras360-testes-")
os.environ.setdefault("SECRET_KEY", "chave-somente-para-testes")
os.environ.setdefault("DB_URL", f"sqlite:///{_tmp}/testes.db")
os.environ.setdefault("H360_COMPARTILHADO", f"{_tmp}/compartilhado")
os.environ.setdefault("H360_RELEASES", f"{_tmp}/releases")
