"""Comunicação com as tarefas do servidor (atualização, rollback, backup).

A aplicação roda sem privilégios. Ela apenas grava um pedido na fila; uma
unidade systemd separada, como root, executa o pedido e escreve o status.
O executor não confia no que está na fila: confere SHA-256 e assinatura.
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path

from .config import BACKUPS_DIR, FILA_DIR, RELEASES_DIR, VERSAO

ACOES = ("atualizar", "rollback", "backup")


def _ler_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def status_tarefa():
    st = _ler_json(FILA_DIR / "status.json") or {}
    st["pendente"] = (FILA_DIR / "pedido.json").exists()
    return st


def ultimo_backup():
    return _ler_json(BACKUPS_DIR / "ultimo.json")


def versoes_guardadas():
    out = []
    atual = None
    lnk = RELEASES_DIR.parent / "atual"
    if lnk.is_symlink():
        atual = Path(os.readlink(lnk)).name
    if RELEASES_DIR.is_dir():
        for d in RELEASES_DIR.iterdir():
            if d.is_dir() and re.match(r"^\d+\.\d+\.\d+$", d.name):
                out.append({"versao": d.name, "atual": d.name == atual,
                            "instalada": datetime.fromtimestamp(d.stat().st_mtime).isoformat(timespec="minutes")})
    out.sort(key=lambda x: tuple(int(n) for n in x["versao"].split(".")), reverse=True)
    return {"emUso": atual or VERSAO, "versoes": out}


def ocupado():
    st = status_tarefa()
    return st["pendente"] or st.get("estado") == "executando"


def gravar_pedido(acao, solicitante, **extra):
    if acao not in ACOES:
        raise ValueError("Ação inválida.")
    FILA_DIR.mkdir(parents=True, exist_ok=True)
    pedido = {"acao": acao, "solicitante": solicitante, "quando": datetime.now().isoformat(timespec="seconds")}
    pedido.update(extra)
    tmp = FILA_DIR / ".pedido.tmp"
    tmp.write_text(json.dumps(pedido, ensure_ascii=False), encoding="utf-8")
    tmp.replace(FILA_DIR / "pedido.json")  # gravação atômica: a unidade systemd só vê o arquivo completo
    return pedido


def caminho_entrada():
    d = FILA_DIR / "entrada"
    d.mkdir(parents=True, exist_ok=True)
    return d
