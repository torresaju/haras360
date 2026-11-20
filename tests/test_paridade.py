"""O motor em Python precisa produzir exatamente o que o motor do protótipo validado produz."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app import regras as R

SCRIPT = Path(__file__).parent / "paridade" / "gerar_referencia.js"


@pytest.fixture(scope="module")
def ref():
    if not shutil.which("node"):
        pytest.skip("Node.js não instalado")
    out = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_mesma_data(ref):
    assert ref["hoje"] == R.iso(R.hoje())


def test_tarefas_identicas(ref):
    st = ref["estado"]
    assert R.tarefas(st["haras"], st["animais"], st["registros"], st["protocolos"]) == ref["tarefas"]


def test_gestacoes_identicas(ref):
    st = ref["estado"]
    assert {a["id"]: R.gestacao(a, st["registros"]) for a in st["animais"]} == ref["gestacoes"]


def test_notificacoes_identicas(ref):
    st = ref["estado"]
    assert R.notificacoes(st["haras"], st["animais"], st["registros"], st["protocolos"]) == ref["notificacoes"]
