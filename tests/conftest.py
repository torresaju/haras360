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


import pytest  # noqa: E402


@pytest.fixture(scope="session")
def base():
    """Plataforma de teste: administrador, Haras Teste (gestor e caseiro) e Outro Haras."""
    from app.db import SessionLocal, Usuario
    from app.migracoes import migrar
    from app.rotas_admin import criar_haras_com_gestor
    from app.seguranca import hash_senha
    migrar(silencioso=True)
    with SessionLocal() as db:
        db.add(Usuario(haras_id=None, nome="Admin Teste", email="admin@teste.com", senha_hash=hash_senha("admin1234"), perfil="admin"))
        h, _g = criar_haras_com_gestor(db, "Haras Teste", "Aracaju/SE", None, "Gestor Teste", "gestor@teste.com", "senha1234")
        db.add(Usuario(haras_id=h.id, nome="Caseiro Teste", email="caseiro@teste.com", senha_hash=hash_senha("campo1234"), perfil="operador"))
        h2, _ = criar_haras_com_gestor(db, "Outro Haras", "", None, "Outro Gestor", "outro@teste.com", "senha1234")
        db.commit()
        return {"haras": h.id, "outro": h2.id}

