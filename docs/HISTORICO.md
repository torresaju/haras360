# Histórico do Haras360

Uma nota por versão, da mais recente para a mais antiga.

## v0.1.0 · 19/11/2026 · Repositório e base do projeto
* Código entregue em 01/10/2026 (`haras360-vps.tar.gz`) importado sem alterações de comportamento.
* Estrutura: `backend/` (API FastAPI, motor de regras, scripts da instalação Docker de outubro), `web/` (fontes dos portais), `mobile/` e `deploy/` reservados para as próximas versões, `docs/` e `tests/`.
* `web/build.py` passou a gravar as páginas em `backend/app/static`.
* Testes automatizados no GitHub Actions:
  * motor de regras (15 casos: séries iniciais, reforço aos 12 meses, raiva semestral, reinício da primovacinação, gestação, pendências documentais);
  * paridade com o motor do protótipo validado (tarefas, gestações e notificações idênticas);
  * API (login, perfis, importação, registros com foto, validações, protocolos, troca de senha);
  * conferência de que as páginas montadas correspondem às fontes.
* Especificação v1 aprovada em `docs/ESPECIFICACAO.md`.
* Versionamento automático: a cada merge na `main`, o GitHub Actions lê o `VERSION` e, se a tag ainda não existir, cria a tag e a Release com esta nota.

## Antes do repositório
* 01/10/2026: protótipo navegável publicado (Portal Gestor e Portal Campo) e validado.
* 01/10/2026: pacote de implantação com API FastAPI, MySQL, login, perfis e fotos no servidor (Docker, porta 8090). Não chegou a ser instalado.
