# Haras360 · Especificação detalhada da v1.0.0

**Situação:** aprovada pelo Ricardo em 19/11/2026 (partes A a H). Branch `etapa/1.0-vps`.

## A. Instalação do servidor (`deploy/instalar-servidor.sh`)
* Ubuntu na segunda VM AMD micro da Oracle (1 GB). Swap de 2 GB, swappiness 10.
* MariaDB local com cerca de 100 MB de cache e 30 conexões. Banco `haras360` com usuário próprio.
* Usuário de sistema `haras360`, ambiente Python isolado, serviço systemd com limite de 350 MB e um processo.
* Caddy na porta 8090: páginas, proxy da aplicação, cabeçalhos de segurança, envio de até 100 MB para o pacote de atualização.
* Firewall: abre a 8090 tratando a regra de iptables das imagens Ubuntu da Oracle. A Security List no console da Oracle continua manual.
* Pastas: `/opt/haras360/releases/X.Y.Z` com atalho `atual`; `/opt/haras360/compartilhado/` (fotos, logotipos, backups, fila de atualização); `/etc/haras360/` (configuração e chave pública).
* Primeiro administrador da plataforma criado no fim, com cadastro do 2FA no primeiro login.

## B. Pacote assinado e atualização com volta automática
* O GitHub Actions gera `haras360-X.Y.Z.tar.gz` (via `deploy/gerar-pacote.sh`) e anexa à Release: código, páginas montadas, migrações, scripts e manifesto SHA-256.
* O Ricardo assina no **Windows** com `deploy/assinar-pacote.py` (Ed25519). A chave privada fica protegida por senha na máquina dele e nunca vai ao servidor nem ao repositório.
* Aplicação pelo botão Administração › Atualização (pacote + assinatura) ou por SSH com `sudo haras360-update pacote.tar.gz pacote.sig`. O botão aciona uma unidade systemd separada, como root, que confere SHA-256 e assinatura antes de tudo.
* Sequência: assinatura, backup, extração em `releases/X.Y.Z`, migrações, troca do atalho, reinício, `/api/saude` por até 60 s. Falhou, volta sozinha. Volta manual disponível. Três versões guardadas.
* Migrações numeradas e somente aditivas.

## C. Backup do ambiente
* Diário às 02:30 por timer do systemd.
* Banco, fotos, logotipos, configuração, chave pública, Caddyfile, unidades systemd, pacote da versão em uso e instalador.
* Cópia local por 7 dias e envio ao bucket privado da OCI por **link pré-autenticado (PAR) somente de gravação**, com curl. Nenhuma credencial da conta OCI fica no servidor. Versionamento e retenção configurados no bucket.
* `restaurar-servidor.sh` reconstrói uma VM nova a partir de um backup.

## D. Segurança
* 2FA (aplicativo autenticador) obrigatório para administrador e gestor, com QR Code no primeiro login e 8 códigos de recuperação. Caseiro só com senha.
* Sessões gravadas no banco; o gestor vê e encerra sessões e aparelhos em Equipe.
* Auditoria de login (sucesso e falha), 2FA, importação, exclusão, protocolo, parametrização, usuário, logotipo, atualização e backup, com consulta filtrada.
* Limite de tentativas de login configurável (padrão 8 a cada 15 minutos).
* Toda exclusão pede confirmação na página.
* Varredura básica OWASP ZAP no GitHub Actions, com relatório no PR.

## E. Perfis, planos e parametrizações
* **Administrador da plataforma:** cria haras e gestores, define o plano de cada haras, mantém parametrizações globais, aplica atualizações e acompanha backups.
* **Planos e módulos por parametrização:** grade plano × módulo editável pelo administrador. Módulos controláveis: Importação ABCCMM, Assistente ABCCMM, Usuário caseiro (app e Portal Campo). **Padrão: tudo liberado em todos os planos.** Módulo fora do plano aparece esmaecido, com aviso, e a API recusa o uso.
* Permissões de cada perfil (gestor, caseiro) seguem a especificação v1.
* **Globais:** limite de animais por plano, faixas de preço (em branco por padrão), tentativas e bloqueio de login, duração das sessões, SMTP e e-mail de contato (gravados; envio no backlog).
* **Do haras (gestor):** reforço da raiva anual ou semestral, dias de gestação (340), tolerância para reiniciar primovacinação (15 dias), validade de AIE e Mormo (60 dias, via protocolos).
* O motor de regras lê esses valores das parametrizações. A paridade com o protótipo continua valendo com os valores padrão.

## E2. Logotipo do haras
* Cada haras pode ter seu logotipo (PNG, JPG ou WebP, até 1 MB), enviado pelo gestor em Administração › Parametrizações ou pelo administrador no cadastro e na lista de haras.
* O navegador recorta as margens vazias e reduz para 512 px. O servidor confere o tipo real do arquivo.
* Aparece na barra superior do Portal do Gestor e do Portal Campo. Sem logotipo, aparece a marca Haras360.
* Arquivo em `compartilhado/logos`, servido só a usuários do próprio haras e ao administrador, incluído no backup, troca e remoção auditadas.

## F. Menus e telas
* Barra superior no lugar da lateral: marca ou logotipo à esquerda; menus, sino, nome, perfil e Sair à direita; hambúrguer no celular.
* Grupos: Painel; Plantel (Animais, Importar ABCCMM); Manejo (Agenda, Protocolos); Equipe; Assistente; Administração (Parametrizações, Auditoria, Plano; e Atualização e backup no perfil administrador); Ajuda (Sobre, Manual, Glossário).
* Cada perfil vê só o que lhe cabe. Portal Campo mantém layout de celular.
* Ajuda: Sobre (versão), Manual HTML com capturas da instância de demonstração, Glossário.

## G. Verificação
* Testes automatizados de 2FA, sessões, auditoria, parametrizações, planos, logotipo, migrações e assinatura (inclusive recusa de pacote adulterado).
* Teste da instalação no GitHub Actions em Ubuntu limpo, com 2FA, atualização, volta automática, volta manual e backup.
* Instância de demonstração "Haras Demonstração" com plantel fictício, fonte das capturas do manual e do PR.

## H. Removido na v1.0.0
* Instalação com Docker de outubro (`backend/Dockerfile`, `install.sh`, `update.sh`, `backup.sh`, `INSTALACAO-DOCKER.md`).

## Decisões desta etapa
| Data | Decisão |
|---|---|
| 19/11/2026 | Partes A a H aprovadas |
| 19/11/2026 | Planos e módulos definidos em parametrização; padrão tudo liberado |
| 19/11/2026 | Backup para OCI por link pré-autenticado somente de gravação |
| 19/11/2026 | Assinatura dos pacotes no Windows; pacote gerado pelo GitHub Actions e anexado à Release |
| 19/11/2026 | Logotipo customizável no cadastro do haras (pedido do Ricardo durante o desenvolvimento) |
