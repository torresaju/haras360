# Haras360 · Especificação v1

**Situação:** aprovada pelo Ricardo em 19/11/2026 (fases 1 a 7).

Base: protótipo web validado em 01/10/2026, pacote `haras360-vps.tar.gz` de 01/10/2026 e o padrão de desenvolvimento do Journey.

## Fluxo de desenvolvimento (padrão Journey)
* Especificação antes de codar, com aprovação por fase.
* Uma branch por etapa e um PR por entrega. Merge só quando o Ricardo autorizar.
* Cada versão leva tag semântica, linha na tabela do README e nota em `docs/HISTORICO.md`.
* O conteúdo é apresentado primeiro no chat e só depois vira arquivo.
* Perguntas interativas antes de qualquer decisão ambígua.
* Testes automatizados por módulo e verificação visual em instância de demonstração com dados fictícios.
* Repositório: `torresaju/haras360`. Acompanhamento: quadro "Haras360" no Trello.

## Fase 1. Escopo e perfis
| Perfil | Acesso | Funções | Login |
|---|---|---|---|
| Administrador da plataforma | Portal web | Cria haras, planos, parametrizações globais, atualizações | Senha + 2FA |
| Gestor (proprietário) | Portal Gestor por HTTP, com atalho na tela inicial do celular | Plantel, importação ABCCMM, prontuário, protocolos, equipe, indicadores | Senha + 2FA |
| Caseiro (operador) | **App Android (APK)**, canal principal, e Portal Campo web como alternativa | Tarefas do dia, registros com fotos, ocorrências, avisos | Senha, aparelho vinculado ao usuário |

* Apenas Android neste momento. iOS fica no backlog.
* Limite de 30 animais ativos por haras. Gratuito até 3 animais, cobrança escalonada a partir do 4º (valores em branco até definição).
* Sem HTTPS, o Chrome não instala o portal como aplicativo completo. O gestor usa atalho na tela inicial, que exige internet. A instalação completa passa a funcionar quando houver subdomínio com HTTPS.

## Fase 2. Arquitetura e servidor
* Segunda VM AMD micro da Oracle Cloud (1 GB), Ubuntu, swap de 2 GB criado pelo instalador.
* Sem Docker: API FastAPI em uvicorn como serviço systemd, Caddy na frente servindo os portais e fazendo proxy da API.
* Acesso por `http://IP:8090`, sem HTTPS, apenas para testes.
* MariaDB local na VM, com memória ajustada para 1 GB.
* Fotos em disco no servidor, entregues só a usuários logados do mesmo haras.
* Pastas: `/opt/haras360/releases/X.Y.Z`, atalho `atual`, três versões guardadas.

## Fase 3. Atualização, backup e instalação
* `deploy/gerar-pacote.sh` gera `haras360-X.Y.Z.tar.gz` a partir de um commit; versão lida do arquivo `VERSION`.
* Assinatura na máquina do Ricardo com `assinar-pacote.py` (Ed25519). O servidor guarda só a chave pública.
* Aplicação pelo botão "Atualizar" (menu Administração) ou por SSH com `haras360-update.sh`. O botão aciona uma unidade systemd separada, que confere SHA-256 e assinatura antes de atualizar.
* Antes de trocar a versão: backup, migrações aditivas, reinício e conferência de `/api/saude`. Em caso de falha, volta sozinha. Há rollback manual.
* Backup do ambiente inteiro (banco, fotos, configuração, chaves e versões) para bucket privado da OCI, com versionamento e ciclo de vida. O backup também gera o instalador atualizado.
* `instalar-servidor.sh` prepara uma VM nova: swap, MariaDB, Caddy, serviço e primeiro administrador.

## Fase 4. App Android do caseiro (offline)
* Banco local no celular (SQLite). Tudo funciona sem internet: tarefas, fichas, registros, fotos e avisos da última sincronização.
* Envio somente em Wi-Fi, em segundo plano, com botão "Sincronizar agora". Se o Wi-Fi cair, o envio retoma de onde parou.
* Fotos comprimidas no celular (cerca de 300 a 500 KB cada).
* Cada registro nasce com identificador gerado no celular, o que evita duplicidade em reenvios.
* O caseiro só acrescenta registros. Edição e exclusão ficam com o gestor no portal, o que elimina conflitos entre aparelhos.
* Do servidor para o celular: animais, tarefas calculadas, protocolos e avisos, a cada sincronização.
* A tela mostra quantos registros aguardam envio e a hora da última sincronização.
* O primeiro login do aparelho exige conexão; depois o app abre offline.
* APK compilado pelo GitHub Actions e publicado em Releases do repositório.

## Fase 5. Segurança
* 2FA (aplicativo autenticador) para administrador e gestor. Caseiro entra só com senha; cada aparelho autorizado aparece em Equipe e pode ser revogado pelo gestor.
* Limite de tentativas de login configurável. Toda exclusão pede confirmação.
* Auditoria de login, importação, exclusão, alteração de protocolo, atualização e acesso de aparelho.
* Revisão de código e varredura OWASP ZAP antes de cada versão maior.
* CPF lido no PDF da ABCCMM não é gravado.
* Risco registrado: sem HTTPS, senhas e códigos 2FA trafegam sem criptografia. Migrar para domínio antes de dados reais de clientes.

## Fase 6. Menus e parametrizações
* Barra superior: marca à esquerda; menu, nome, perfil e Sair à direita; menu hambúrguer em telas estreitas.
* Menus agrupados: Painel; Plantel (Animais, Importar ABCCMM); Manejo (Agenda, Protocolos); Equipe; Assistente; Administração (Parametrizações, Auditoria, Atualização, Plano); Ajuda (Sobre, Manual, Glossário).
* Parametrizações: planos e valores por faixa, limite de animais, tempo de gestação (340 dias), tolerância para reiniciar primovacinação (15 dias), validade de exames AIE e Mormo (60 dias), política de sincronização do app, SMTP e e-mail de contato.
* Módulos fora do plano aparecem esmaecidos.

## Fase 7. Roadmap
| Versão | Branch | Entrega |
|---|---|---|
| v0.1.0 | etapa/0.1-repositorio | Código de outubro no Git, testes no GitHub Actions, README, HISTORICO |
| v1.0.0 | etapa/1.0-vps | Instalação sem Docker, Caddy, swap, 2FA, auditoria, parametrizações, menus, pacote assinado com rollback, backup OCI |
| v1.1.0 | etapa/1.1-app-android | APK Flutter do caseiro, offline com envio no Wi-Fi |

## Decisões registradas
| Data | Decisão |
|---|---|
| 01/10/2026 | Stack: FastAPI + MySQL/MariaDB; app Flutter; importação do Relatório de Plantel ABCCMM em PDF |
| 19/11/2026 | Adotado o padrão de desenvolvimento do Journey |
| 19/11/2026 | Segunda VM micro da Oracle, sem Docker (Caddy + systemd), acesso por IP e porta sem HTTPS |
| 19/11/2026 | 2FA só para gestor e administrador |
| 19/11/2026 | Sincronização do app somente no Wi-Fi |
| 19/11/2026 | Gestor no portal web por HTTP, com atalho na tela inicial; caseiro com app Android e Portal Campo; apenas Android neste momento |
| 19/11/2026 | Especificação aprovada (fases 1 a 7) |
