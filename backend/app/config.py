"""Configuração lida do ambiente (arquivo /etc/haras360/haras360.env na VPS)."""
import os
from pathlib import Path

RAIZ_RELEASE = Path(__file__).resolve().parents[2]


def _versao():
    for p in (RAIZ_RELEASE / "VERSION", Path(__file__).resolve().parents[1] / "VERSION"):
        if p.exists():
            return p.read_text().strip()
    return "0.0.0"


VERSAO = _versao()
DB_URL = os.environ.get("DB_URL", "sqlite:///./haras360.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"

# Pastas compartilhadas entre versões (na VPS: /opt/haras360/compartilhado)
COMPARTILHADO = Path(os.environ.get("H360_COMPARTILHADO", "./dados"))
FOTOS_DIR = Path(os.environ.get("FOTOS_DIR", COMPARTILHADO / "fotos"))
LOGOS_DIR = COMPARTILHADO / "logos"
FILA_DIR = Path(os.environ.get("H360_FILA", COMPARTILHADO / "fila"))
BACKUPS_DIR = Path(os.environ.get("H360_BACKUPS", COMPARTILHADO / "backups"))
RELEASES_DIR = Path(os.environ.get("H360_RELEASES", "./releases"))

# APK do app Android, colocado no pacote pelo GitHub Actions (static/app/haras360.apk e versao.json)
APP_DIR = Path(__file__).resolve().parent / "static" / "app"

MAX_PACOTE_MB = int(os.environ.get("H360_MAX_PACOTE_MB", "100"))

if not SECRET_KEY:
    raise SystemExit("SECRET_KEY não definida. Configure /etc/haras360/haras360.env.")
