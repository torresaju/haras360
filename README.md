# Haras360

SaaS de gestão de haras para pequenos e médios criadores de Mangalarga Marchador (até 30 animais por haras).

* **Portal Gestor** (web): plantel, importação do Relatório de Plantel ABCCMM em PDF, prontuário, agenda sanitária automática, protocolos, equipe.
* **Portal Campo** (web) e **app Android** do caseiro: tarefas do dia, registros com fotos e ocorrências, inclusive sem internet.
* **API** FastAPI com motor de regras sanitárias (protocolo VetJr. UFMG e padrões de mercado, editáveis por haras).

A especificação aprovada está em [`docs/ESPECIFICACAO.md`](docs/ESPECIFICACAO.md). O acompanhamento das etapas fica no quadro "Haras360" do Trello.

## Versões

| Versão | Data | Branch | Entrega | Situação |
|---|---|---|---|---|
| v0.1.0 | 19/11/2026 | etapa/0.1-repositorio | Código de outubro no Git, testes automatizados, documentação | Publicada |
| v1.0.0 | 19/11/2026 | etapa/1.0-vps | Portais e API na segunda VM micro, sem Docker, 2FA, auditoria, parametrizações, logotipo do haras, pacote assinado com volta automática, backup OCI | Publicada |
| v1.1.0 | 20/11/2026 | etapa/1.1-app-android | App Android do caseiro: offline, envio só no Wi-Fi, vínculo por QR Code, APK assinado servido pelo próprio servidor | Publicada |
| v1.1.1 | 20/11/2026 | etapa/1.1.1-instalador | Instalador em VM compartilhada (porta livre, Caddy preservado, fuso), QR Code do 2FA, botão do app, tela de Administradores | Publicada |
| v1.2.0 | 20/11/2026 | etapa/1.2-audio | Áudio nos registros do caseiro; chave pública no pacote; erro de atualização visível; SHA-256 em HTTP | Em teste (PR) |

Notas de cada versão: [`docs/HISTORICO.md`](docs/HISTORICO.md).

## Estrutura

```
backend/   API FastAPI, motor de regras (app/regras.py), modelos, páginas montadas (app/static)
web/       fontes dos portais; após editar: python web/build.py
mobile/    app Flutter do caseiro (v1.1.0)
deploy/    instalação, atualização assinada, backup e restauração na VPS (ver docs/IMPLANTACAO.md)
docs/      especificação e histórico
tests/     testes automatizados
```

## Desenvolvimento

```bash
pip install -r requirements-dev.txt
python -m pytest          # motor, paridade com o protótipo e API (paridade exige Node.js)
python web/build.py       # monta backend/app/static a partir de web/
```

Instância de demonstração local (SQLite, dados fictícios):

```bash
cd backend
export SECRET_KEY=dev DB_URL=sqlite:///./dev.db
python -m app.cli criar-admin --nome Admin --email admin@demonstracao.local --senha demonstracao123
python -m app.cli demonstracao            # gestor@demonstracao.local e caseiro@demonstracao.local, senha demonstracao123
uvicorn app.main:app --port 8090
python ../tests/visual/capturas.py http://127.0.0.1:8090 app/static/ajuda   # percorre as telas e refaz as capturas do manual
```

Implantação na VPS: [`docs/IMPLANTACAO.md`](docs/IMPLANTACAO.md).

## Fluxo de trabalho

1. Especificação antes de codar, aprovada por fase.
2. Uma branch `etapa/X.Y-nome` por etapa e um PR por entrega.
3. Merge somente com autorização do Ricardo.
4. Cada versão leva tag semântica (`vX.Y.Z`), linha nesta tabela e nota em `docs/HISTORICO.md`. O arquivo `VERSION` traz a versão atual.
5. A tag e a Release são criadas pelo GitHub Actions (`.github/workflows/versao.yml`) no merge, a partir do `VERSION` e da seção correspondente do `docs/HISTORICO.md`.
