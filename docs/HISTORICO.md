# Histórico do Haras360

Uma nota por versão, da mais recente para a mais antiga.

## v1.5.2 · 22/11/2026 · Correções do prontuário e do cadastro sem registro
* **Prontuário desconfigurado:** a lista "Próximos eventos" do Dashboard (v1.3.0) usava o mesmo nome de estilo da linha do prontuário e espremia o texto numa coluna estreita, quebrando ocorrências letra por letra. Os estilos foram separados; as observações mantêm as quebras de linha.
* **Vários animais sem registro:** caixa "Sem registro na ABCCMM" no Novo animal e na ficha. O servidor passa a tratar como vazio qualquer registro ou chip sem números ("sem registro", "*****"), que antes contava como registro repetido. Registros de verdade continuam únicos.
* **Origem dos registros:** o prontuário mostra "Portal Campo", "Portal do Gestor", "App do caseiro" e "App do gestor".
* **Testes:** 1 teste novo da API (88 no total) e verificação visual com ocorrência longa e dois animais sem registro.

## v1.5.1 · 21/11/2026 · Links para as normas da ABCCMM
* O assistente com IA ficou para depois (card no Backlog). Para facilitar as consultas, o gestor tem links diretos para o Estatuto e o Regulamento do Registro Genealógico no site da ABCCMM:
  * Administração › Assistente (quadro acima do chat), Ajuda › Normas da ABCCMM, atalho em Importar ABCCMM e Mais › Normas da ABCCMM no app do gestor;
  * os links abrem em nova aba ou no navegador do celular.
* O administrador mantém os links em Parametrizações › Normas da ABCCMM (até 8, título e endereço http ou https), para atualizar quando a ABCCMM publicar versões novas.
* Testes: 1 teste novo da API (87 no total) e verificação visual dos links.

## v1.5.0 · 21/11/2026 · App do gestor (Android)
* **Um app só, por perfil:** a abertura tem "Sou caseiro" (QR Code, como antes) e "Sou gestor" (e-mail, senha e 2FA). Um perfil por celular; Mais › Sair encerra a sessão e apaga os dados do haras do celular (só com tudo enviado).
* **Segurança:**
  * login do gestor no app com 2FA obrigatório (código do autenticador ou de recuperação), bloqueio por tentativas e auditoria (`app_gestor_entrou`, `app_saiu`);
  * exige o servidor em HTTPS; o administrador tem a chave "App do gestor sem HTTPS (somente teste)", desligada por padrão, com aviso em vermelho e auditoria;
  * digital ou bloqueio de tela do Android ao abrir e ao voltar depois de 5 minutos;
  * sessão do app do gestor expira após 30 dias sem uso (parametrizável de 7 a 90); troca de senha e redefinição do 2FA encerram o app.
* **Telas do gestor:** Dashboard (indicadores, Atenção agora, próximos 7 dias, campo), Animais (ativos, baixados ou todos; ficha com fotos e áudios; Dar baixa e Desfazer baixa), Agenda, Relatórios (quatro abas, gráficos e tabelas, envio da planilha Excel ou CSV pelo compartilhar do Android) e Mais.
* **Sincronização:** o gestor usa Wi-Fi e dados móveis, inclusive para fotos e áudios, e também trabalha offline. O caseiro continua só no Wi-Fi. Registros do app do gestor têm a origem "App do gestor" e não entram na atividade do campo.
* **Avisos no celular (sem Firebase):** consulta a cada 15 minutos e notificação do Android para procedimentos atrasados, parto em até 7 dias, cio de hoje, pendências da ABCCMM e ocorrência grave do caseiro (novo tipo de aviso crítico, também no portal). Preferências por tipo e horário de silêncio (21h às 6h); tocar abre a ficha.
* **Testes:** 7 testes novos da API (86 no total), testes de unidade dos avisos, e um segundo teste no emulador com o gestor (2FA, Dashboard, baixados, registro sem internet, envio, relatórios), conferido no servidor.

## v1.4.0 · 20/11/2026 · Relatórios, registro de cio e baixa de animais
* **Relatórios (Portal do Gestor):**
  * menu Relatórios com quatro abas: Sanitário, Reprodutivo, Plantel e Atividade do campo;
  * filtros de período (padrão: últimos 12 meses), animal e categoria; indicadores, gráficos (linha, barras e rosca) e tabelas; linha clicável abre a ficha;
  * indicadores principais: animais em dia, taxa de prenhez, éguas prenhes, intervalo médio entre partos, entradas e saídas, registros do caseiro por pessoa e origem;
  * exportação Excel (.xlsx, aba Resumo e uma aba por tabela, com link para a ficha) e CSV (ponto e vírgula, acentos para o Excel), registrada na auditoria;
  * só para o gestor; novo módulo "Relatórios e exportação" na grade de planos, liberado por padrão.
* **Registro de cio:**
  * evento Cio no Portal do Gestor, no Portal Campo e no app (offline), com sinais observados e dados do exame (ovário, folículo em mm, edema uterino de 0 a 3);
  * previsão do próximo cio pelo ciclo (21 dias, ajustável de 18 a 25) a partir do último cio, cobertura, inseminação ou aborto, até o diagnóstico positivo; tarefa "Observar cio" na Agenda e na tela Hoje;
  * cio do potro do 7º ao 12º dia após o parto (janela ajustável);
  * Parametrizações › Reprodução: ligar ou desligar a previsão, ciclo e janela.
* **Baixa de animais:** Dar baixa na ficha (venda, morte, doação ou transferência, com destino e observação), filtro Baixados no plantel, Desfazer baixa com confirmação, auditoria e importação ABCCMM que não reativa animal baixado. Migração 005.
* **Ajustes:** botão vermelho nas confirmações de ação sensível; nomes das ações de imagem, baixa e exportação na auditoria; termos novos no glossário.
* **Testes:** 13 testes novos do motor e da API (79 no total), testes de unidade do app para o cio, verificação visual das quatro abas com download das planilhas, do cio e da baixa, e emulador com cio registrado sem Wi-Fi e conferido no servidor.

## v1.3.0 · 20/11/2026 · Nova identidade visual e personalização por imagens
* **Identidade visual nova nos portais e no app:**
  * logotipo próprio (perfil de cavalo com arco dourado) e ícone novo do app;
  * paleta verde haras `#193D30`, dourado `#D5A064`, areia `#F3F1E9`, grafite `#292F2B` e verde sálvia `#82978A`;
  * títulos em Manrope e texto em Inter, embutidas no APK para funcionar offline;
  * ícones lineares e ilustração própria do Haras360 (cavalo ao pôr do sol), usada quando não há imagem enviada.
* **Portal do Gestor:**
  * menu lateral por módulo: Dashboard; Animais (Plantel, Importar ABCCMM); Sanidade (Vacinas e manejos, Protocolos); Reprodução; Agenda; Relatórios (em breve); Administração (Equipe, Parametrizações, Auditoria, Assistente, Plano) e Ajuda. No celular, o menu abre pelo botão ☰;
  * cabeçalho com imagem, logotipo e nome do haras, sino de avisos e menu do usuário;
  * Dashboard novo: cinco indicadores, próximos eventos, composição do rebanho, situação reprodutiva, Atenção agora, últimos registros do campo e banner;
  * telas novas Sanidade › Vacinas e manejos e Reprodução.
* **Portal Campo:** cabeçalho com imagem e logotipo, botão Registrar ocorrência no topo, barra de baixo com Hoje, Animais, Agenda e Mais.
* **App Android:** abertura com o fundo do haras, tela Hoje com cabeçalho e botão grande Registrar ocorrência, abas Hoje, Animais, Agenda (30 dias) e Mais (Avisos, Envio, versão, vincular de novo).
* **Personalização por imagens (tudo parametrizável):**
  * o administrador troca, em Marca e imagens, o logotipo da plataforma e as imagens padrão (tela de entrada, cabeçalho, banner do Dashboard e fundo do app);
  * o gestor troca, em Parametrizações › Imagens do haras, o cabeçalho, o banner do Dashboard e o fundo do app (o logotipo do haras continua em Parametrizações). A imagem do haras vale sobre a da plataforma;
  * PNG, JPG ou WebP até 3 MB, conferidos pelo conteúdo, reduzidos no navegador, com foco (centro, topo ou base) e botão Usar a padrão. Cada troca vai para a auditoria;
  * o app baixa o fundo e o logotipo no Wi-Fi e guarda no celular, para funcionar sem internet;
  * a tela de entrada mostra a imagem e o logotipo da plataforma.
* **Servidor:** migração 004 (tabela `imagens_marca`), rotas `/api/marca`, `/marca/{tipo}`, `/imagens/{tipo}`, `/api/haras/imagens/{tipo}` e `/api/admin/marca/{tipo}`. As imagens ficam em `compartilhado/imagens` e entram no backup diário.
* **Testes:** 4 testes novos da API de imagens (66 no total); a verificação visual envia um banner, confere no Dashboard e volta ao padrão; o teste no emulador percorre Hoje, Animais, Agenda e Mais.

## v1.2.0 · 20/11/2026 · Áudio nos registros do caseiro
* **App:** botão Gravar áudio no registro (até 2 minutos, AAC mono a 32 kbps, cerca de 250 KB por minuto), com contador, ouvir e apagar antes de salvar. Funciona sem internet: o áudio entra na fila e vai só no Wi-Fi, depois do registro e das fotos. A ficha do animal toca os áudios, inclusive os que ainda estão no celular.
* **Servidor:** `POST /api/app/audios` (um por registro, tipo conferido pelo conteúdo, idempotente), `/audios/{id}` só para o mesmo haras, exclusão junto com o registro e migração 003.
* **Portal do gestor:** player no prontuário e nos últimos registros do campo do Painel.
* **Parametrização:** módulo "Áudio nos registros do app" na grade de planos e duração máxima em Parametrizações › App do caseiro (15 a 300 segundos, padrão 120).
* **Correções da primeira atualização real:**
  * a chave pública de atualização (a do Journey) ficava fora do pacote por uma regra do `.gitignore`; agora vai no pacote, o pacote não é gerado sem ela e o teste de instalação confere a impressão digital;
  * uma atualização recusada antes de começar agora aparece na tela, em vez de "Nenhuma";
  * o campo SHA-256 da tela de atualização funciona em HTTP (a conferência fica no servidor).
* **Testes:** 6 testes da API de áudio, teste de unidade da duração e teste no emulador com áudio numa ocorrência sem Wi-Fi, conferido no servidor.

## v1.1.1 · 20/11/2026 · Instalação em VM compartilhada e tela de Administradores
Correções vindas da primeira instalação real, na VM que já roda a plataforma de reservatórios.
* **Instalador convive com outra aplicação:**
  * usa a primeira porta interna livre a partir da 8000 (antes era fixa e falhava com "address already in use");
  * acrescenta o Haras360 a um Caddy existente com uma linha `import`, guardando cópia do original (antes sobrescrevia o Caddyfile); o site fica em `/etc/caddy/haras360.caddy`;
  * avisa quando o MariaDB já atende outras bases;
  * ajusta o fuso da VM de UTC para America/Sao_Paulo (backup às 02:30 de Brasília).
  * Novo teste no GitHub Actions instala ao lado de outra aplicação e confere que as duas continuam funcionando.
* **QR Codes sem corte:** o QR Code do cadastro do 2FA aparecia cortado e não era lido pelo autenticador. Agora escala sem perder as bordas.
* **App Android mais fácil de achar:** botão Instalar o app no topo do Portal Campo, e link com QR Code de download na janela Vincular celular do gestor.
* **Administração › Administradores:** criar, desativar e reativar, redefinir senha e 2FA de outro administrador. Cada ação pede a senha de quem faz e vai para a auditoria. Ninguém desativa a si mesmo e a plataforma nunca fica sem administrador ativo.

## v1.1.0 · 20/11/2026 · App Android do caseiro
* **App Android (Flutter, Android 8 ou superior)** para o caseiro: tarefas do dia, animais com ficha e histórico, avisos e registro de vacina, vermífugo, odontologia, casqueamento, exame, reprodução e ocorrência, com até 4 fotos.
* **Funciona sem internet:** banco local no celular com o último retrato do haras e a fila de registros. A situação das tarefas é recalculada com a data do dia, e o registro feito no pasto já tira a tarefa da lista.
* **Envio somente no Wi-Fi:**
  * em segundo plano a cada hora e sempre que o app abre no Wi-Fi, com botão "Sincronizar agora";
  * registros primeiro, depois as fotos uma a uma (comprimidas no celular), depois o estado do haras;
  * se a conexão cai, retoma de onde parou, sem duplicar (identificador gerado no celular);
  * registros recusados pelo servidor ficam visíveis em Envio, com "Tentar de novo".
* **Vínculo do celular por QR Code:** o gestor gera em Equipe › Vincular celular um código de uso único, válido por 10 minutos. O celular aparece em Sessões e aparelhos ativos e pode ser encerrado. Alternativas: digitar o código ou entrar com e-mail e senha. Comando `haras360 vincular-celular` para suporte.
* **APK distribuído pelo próprio servidor:** vai dentro do pacote de atualização e fica em Portal Campo › Instalar o app Android, com QR Code. O app avisa quando o servidor tem versão mais nova.
* **Assinatura do APK** com chave Android própria (RSA 3072, 30 anos), criada no Windows com `deploy/gerar-chave-android.py`. O GitHub guarda só os segredos; a impressão digital do certificado é conferida no build.
* **API nova:** `/api/usuarios/{id}/vinculo`, `/api/app/vincular`, `/api/app/sincronizar`, `/api/app/fotos`, `/api/app/versao`, `/api/app/instalar` e `/app/haras360.apk`. Migração 002 (códigos de vínculo).
* **Testes:** 17 testes de unidade do app, 8 testes da API do app e teste de ponta a ponta no emulador Android contra a instância de demonstração (vínculo, registro sem Wi-Fi, envio, capturas de tela).

## v1.0.0 · 19/11/2026 · Portais e API na segunda VM micro
* **Servidor sem Docker:** `deploy/instalar-servidor.sh` instala na VM micro da Oracle:
  * swap de 2 GB e MariaDB ajustado para 1 GB;
  * aplicação como serviço systemd com limite de memória, atrás do Caddy na porta 8090;
  * liberação da porta no firewall da VM, inclusive a regra das imagens Oracle.
* **Atualização por pacote assinado (Ed25519):**
  * o GitHub Actions gera o pacote e anexa à Release, e a assinatura é feita no Windows com `assinar-pacote.py`;
  * o envio pode ser pelo botão Administração › Atualização ou por SSH;
  * antes de trocar de versão: conferência de SHA-256, assinatura e manifesto, backup e migrações aditivas;
  * se a nova versão não responder, volta sozinha; há volta manual e três versões guardadas.
* **Chave de assinatura compartilhada com o Journey:**
  * chave pública em `deploy/chave-publica.pem`, impressão digital `ba29:5bc9:c550:322d:2b24:bdb1:14fe:ba98`;
  * `assinar-pacote.py` usa `journey-chaves\journey-assinatura.key` por padrão;
  * texto assinado próprio do Haras360, para os pacotes de um sistema não valerem no outro.
* **Backup do ambiente inteiro**, todo dia às 02:30: banco, fotos, logotipos, configuração, chaves, serviços, pacote em uso e instalador. Envio ao bucket privado da OCI por link pré-autenticado. `restaurar-servidor.sh` reconstrói uma VM nova a partir dele.
* **Segurança:**
  * 2FA por aplicativo autenticador para administrador e gestor, com códigos de recuperação;
  * sessões gravadas no banco, que podem ser encerradas em Equipe;
  * auditoria completa, com consulta filtrada;
  * limite de tentativas de login parametrizável;
  * cabeçalhos de segurança e CSP;
  * varredura OWASP ZAP no GitHub Actions.
* **Perfil Administrador da plataforma:** haras e gestores, planos, parametrizações globais, atualização e backup.
* **Planos e módulos por parametrização**, com tudo liberado por padrão. Módulos fora do plano aparecem esmaecidos e são recusados pela API.
* **Parametrizações do haras:** reforço da raiva, dias de gestação e tolerância para reiniciar a primovacinação, que agora são lidos pelo motor de regras.
* **Logotipo de cada haras:** enviado pelo gestor ou pelo administrador, com recorte automático das margens. Aparece na barra superior dos portais.
* **Interface:**
  * barra superior com menus agrupados e menu hambúrguer no celular;
  * novas telas: Parametrizações, Auditoria, Plano, Sobre, Glossário e Manual com capturas da instância de demonstração;
  * login com 2FA.
* Registro com identificador gerado no aparelho não duplica em reenvio, como preparação para o app Android.
* Instalação Docker de outubro removida.
* Testes:
  * 45 testes de motor, paridade e API;
  * verificação visual de todas as telas;
  * teste de instalação completo no GitHub Actions, com atualização, volta automática, recusa de pacote adulterado, volta manual e backup.

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
