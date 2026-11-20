# Histórico do Haras360

Uma nota por versão, da mais recente para a mais antiga.

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
