# Haras360

SaaS de gestão de haras para pequenos e médios criadores de Mangalarga Marchador (até 30 animais por haras).

* **Portal Gestor** (web): plantel, importação do Relatório de Plantel ABCCMM em PDF, prontuário, agenda sanitária automática, protocolos, equipe.
* **Portal Campo** (web) e **app Android** do caseiro: tarefas do dia, registros com fotos e ocorrências, inclusive sem internet.
* **API** FastAPI com motor de regras sanitárias (protocolo VetJr. UFMG e padrões de mercado, editáveis por haras).

A especificação aprovada está em [`docs/ESPECIFICACAO.md`](docs/ESPECIFICACAO.md). O acompanhamento das etapas fica no quadro "Haras360" do Trello.

## Versões

| Versão | Data | Branch | Entrega | Situação |
|---|---|---|---|---|
| v0.1.0 | 19/11/2026 | etapa/0.1-repositorio | Código de outubro no Git, testes automatizados, documentação | Em revisão (PR) |
| v1.0.0 | | etapa/1.0-vps | Portais e API na segunda VM micro, sem Docker, 2FA, auditoria, parametrizações, pacote assinado com rollback, backup OCI | Planejada |
| v1.1.0 | | etapa/1.1-app-android | APK Android do caseiro, offline com envio no Wi-Fi | Planejada |

Notas de cada versão: [`docs/HISTORICO.md`](docs/HISTORICO.md).

## Estrutura

```
backend/   API FastAPI, motor de regras (app/regras.py), modelos, páginas montadas (app/static)
web/       fontes dos portais; após editar: python web/build.py
mobile/    app Flutter do caseiro (v1.1.0)
deploy/    instalação e atualização na VPS (v1.0.0)
docs/      especificação e histórico
tests/     testes automatizados
```

## Desenvolvimento

```bash
pip install -r requirements-dev.txt
python -m pytest          # motor, paridade com o protótipo e API (paridade exige Node.js)
python web/build.py       # monta backend/app/static a partir de web/
```

Para rodar a API localmente com SQLite:

```bash
cd backend
SECRET_KEY=dev DB_URL=sqlite:///./dev.db python -m app.cli criar-haras
SECRET_KEY=dev DB_URL=sqlite:///./dev.db uvicorn app.main:app --port 8090
```

## Fluxo de trabalho

1. Especificação antes de codar, aprovada por fase.
2. Uma branch `etapa/X.Y-nome` por etapa e um PR por entrega.
3. Merge somente com autorização do Ricardo.
4. Cada versão leva tag semântica (`vX.Y.Z`), linha nesta tabela e nota em `docs/HISTORICO.md`. O arquivo `VERSION` traz a versão atual.
