# Haras360 · Especificação da v1.5.1

**Situação:** aprovada pelo Ricardo em 21/11/2026. Branch `etapa/1.5.1-normas-abccmm`.

O assistente com IA (card "Assistente ABCCMM com IA real") fica no Backlog. Nesta versão, o Portal do Gestor e o app do gestor ganham links diretos para as normas oficiais da ABCCMM.

## A. Links
* Padrão (parametrizável pelo administrador em Parametrizações › Normas da ABCCMM, até 8 links, formato "Título | endereço", só http ou https):
  * Estatuto e Regulamentos (site da ABCCMM): https://www.abccmm.org.br/estatutos.aspx
  * Regulamento do Serviço de Registro Genealógico (PDF): http://leia.abccmm.org.br/portal/regulamentos/regulamentosrg.pdf
  * Estatuto da ABCCMM (PDF): http://leia.abccmm.org.br/portal/estatuto.pdf
* Abrem em nova aba (portal) ou no navegador do celular (app). Somente para o gestor.

## B. Onde aparecem
* Administração › Assistente: quadro "Normas oficiais da ABCCMM" acima do chat.
* Ajuda › Normas da ABCCMM: tela com os links e o aviso de que os documentos são mantidos pela ABCCMM.
* Animais › Importar ABCCMM: atalho para as normas.
* App do gestor: Mais › Normas da ABCCMM.

## C. Testes e entrega
* API (links padrão, validação de endereço, só gestor), verificação visual (links nas duas telas, nova aba), manual, HISTORICO, README e Trello.
