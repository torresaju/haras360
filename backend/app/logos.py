"""Logotipo de cada haras: envio, validação, troca e remoção."""
import base64
import re
import uuid

from .config import LOGOS_DIR
from .seguranca import erro

TIPOS = {b"\x89PNG": "png", b"\xff\xd8\xff": "jpg", b"RIFF": "webp"}
MAX_BYTES = 1024 * 1024


def salvar(h, data_url):
    """Grava o logotipo enviado como data URL (o navegador já reduz para no máximo 512 px)."""
    m = re.match(r"^data:image/(png|jpeg|webp);base64,(.+)$", data_url or "", re.S)
    if not m:
        erro(400, "Envie o logotipo em PNG, JPG ou WebP.")
    raw = base64.b64decode(m.group(2), validate=False)
    if len(raw) > MAX_BYTES:
        erro(400, "O logotipo pode ter no máximo 1 MB.")
    ext = next((e for sig, e in TIPOS.items() if raw.startswith(sig)), None)
    if not ext or (ext == "webp" and raw[8:12] != b"WEBP"):
        erro(400, "O arquivo enviado não é uma imagem válida.")
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    nome = f"{h.id}-{uuid.uuid4().hex[:12]}.{ext}"
    (LOGOS_DIR / nome).write_bytes(raw)
    remover_arquivo(h.logo)
    h.logo = nome


def remover_arquivo(nome):
    if nome and re.fullmatch(r"\d+-[0-9a-f]{12}\.(png|jpg|webp)", nome):
        (LOGOS_DIR / nome).unlink(missing_ok=True)


def url(h):
    return f"/logos/{h.logo}" if h.logo else ""
