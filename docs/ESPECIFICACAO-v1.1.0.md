# Haras360 · Especificação detalhada da v1.1.0

**Situação:** aprovada pelo Ricardo em 20/11/2026 (partes A a G). Branch `etapa/1.1-app-android`.

## A. App Android do caseiro (Flutter)
* Android 8.0 ou superior (API 26+). Somente perfil caseiro (operador); gestor continua no portal web.
* Telas: Tarefas do dia (atrasadas, hoje, próximos 7 dias), Animais (lista e ficha com histórico e próximas etapas), Registrar (vacina, vermífugo, casqueamento, ocorrência, com até 3 fotos), Avisos e Sincronização.
* Ao tocar em Registrar em uma tarefa, o formulário já vem preenchido (como no Portal Campo).
* Logotipo e nome do haras no topo. Textos e cores seguem o Portal Campo.

## B. Funcionamento offline
* Banco local SQLite no aparelho com animais, tarefas calculadas, protocolos, avisos e a fila de registros a enviar.
* Tudo abre e funciona sem internet depois do primeiro acesso. As tarefas mostradas são as da última sincronização; registros feitos offline já tiram a tarefa da lista no aparelho.
* Cada registro nasce com identificador gerado no celular (UUID), o que torna o reenvio seguro.
* O caseiro só acrescenta registros. Edição e exclusão ficam com o gestor no portal.
* Fotos comprimidas no aparelho (lado maior 1600 px, JPEG, cerca de 300 a 500 KB).

## C. Sincronização somente no Wi-Fi
* Em segundo plano (WorkManager), com rede sem medição (Wi-Fi), a cada 1 hora e sempre que o app abre no Wi-Fi. Botão "Sincronizar agora", que também respeita o Wi-Fi.
* Ordem: envia os registros da fila, depois as fotos uma a uma, depois baixa o estado do haras. Se a conexão cair, retoma de onde parou.
* A tela mostra quantos registros e fotos aguardam envio e a hora da última sincronização.
* Token do aparelho guardado no armazenamento seguro do Android. Se o gestor revogar o aparelho, o app avisa e pede novo vínculo, sem perder a fila local.

## D. Vínculo do aparelho por QR Code
* Em Equipe, o gestor toca em "Vincular celular" na linha do caseiro. Aparece um QR Code válido por 10 minutos, de uso único.
* O app lê o QR Code (endereço do servidor + código) e recebe o token do aparelho, sem digitar senha no campo. Alternativa: e-mail e senha do caseiro, com o endereço do servidor digitado.
* O aparelho aparece em Sessões e aparelhos ativos, com nome do modelo, e pode ser encerrado pelo gestor. Vínculo e revogação entram na auditoria.
* Duração da sessão do app pela parametrização `sessao_app_dias` (90 dias), renovada a cada sincronização.

## E. Servidor
* `POST /api/app/vincular` troca o código do QR Code por um token de aparelho.
* `POST /api/usuarios/{id}/vinculo` (gestor) gera o código e o QR Code.
* `GET /api/app/sincronizar` devolve o estado do haras para o aparelho: animais, registros recentes, tarefas calculadas, protocolos, avisos e logotipo.
* `POST /api/registros` aceita o envio do app (já idempotente pelo identificador do registro).
* `POST /api/app/fotos` recebe uma foto por vez (multipart), ligada ao registro, idempotente pelo identificador da foto.
* `GET /api/app/versao` informa a versão do APK publicada no servidor.
* Migração aditiva para o vínculo (tabela de códigos) e identificador de foto vindo do aparelho.

## F. Distribuição do APK pelo servidor
* O APK assinado vai dentro do pacote do servidor (`haras360-X.Y.Z.tar.gz`) e é servido em `/app/haras360.apk`.
* Portal Campo ganha o botão "Instalar o app Android", com QR Code do link para abrir no celular.
* Ao sincronizar, o app compara a própria versão com `/api/app/versao` e oferece a atualização. O Android só aceita a nova versão se for assinada pela mesma chave.

## G. Assinatura do APK, build e testes
* Chave Android (PKCS12, RSA 3072, validade de 30 anos) criada pelo Ricardo no Windows com `deploy/gerar-chave-android.py`. A chave fica no computador dele, com cópia de segurança; o GitHub recebe só os segredos `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_SENHA`, `ANDROID_CHAVE_ALIAS` e `ANDROID_CHAVE_SENHA`.
* GitHub Actions compila o APK assinado a cada versão, confere a impressão digital do certificado e anexa o APK à Release e ao pacote do servidor. Sem os segredos, o build de teste usa uma chave descartável e o APK não é publicado.
* Testes: unitários do app (fila, sincronização, regras de tela), testes da API nova, teste de integração do app contra o servidor de demonstração e capturas de tela para o manual.
* Manual (Ajuda) ganha a seção do app: instalar, vincular, trabalhar offline, sincronizar.
