# Haras360 · Especificação detalhada da v1.5.0

**Situação:** aprovada pelo Ricardo em 21/11/2026. Branch `etapa/1.5-app-gestor`.

Escolhas do Ricardo: Android agora e iOS depois; um app só, por perfil; gestor entra com e-mail, senha e 2FA; consultar, registrar, avisos no celular e relatórios; avisos sem Firebase; gestor sincroniza no 4G e o caseiro só no Wi-Fi; digital ou PIN do celular; um perfil por celular. O HTTPS fica para quando o domínio chegar: o login do gestor no app exige HTTPS, com uma chave de teste do administrador.

## A. Um app só, por perfil
* O mesmo app Haras360 (um APK, distribuído e atualizado pelo servidor) abre a visão do caseiro ou do gestor.
* Abertura com dois caminhos: **Sou caseiro** (QR Code, como hoje) e **Sou gestor** (e-mail, senha e 2FA).
* Um perfil por celular: **Sair** apaga a sessão; registros pendentes precisam ser enviados antes.
* A sessão do app do gestor aparece em Equipe › Sessões e aparelhos ativos, onde pode ser encerrada.

## B. Acesso e proteção
* Login do portal com 2FA obrigatório (código do autenticador ou de recuperação), bloqueio por tentativas e auditoria (`app_gestor_entrou`, `app_saiu`).
* Exige o servidor em HTTPS. Parametrização global do administrador "App do gestor sem HTTPS (somente teste)", desligada por padrão, com aviso em vermelho e auditoria.
* O app pede a digital ou o bloqueio de tela do Android ao abrir e ao voltar depois de 5 minutos em segundo plano.
* A sessão expira após 30 dias sem uso (parametrizável de 7 a 90). Troca de senha, redefinição do 2FA ou desativação do gestor encerram as sessões do app.

## C. Telas do gestor
Barra de baixo: **Dashboard, Animais, Agenda, Relatórios e Mais**.
* **Dashboard:** indicadores, Atenção agora, próximos eventos e últimos registros do campo.
* **Animais:** plantel com busca e filtro ativos ou baixados; ficha com prontuário (fotos e áudios), agenda do animal, gestação e próximo cio; **Dar baixa** (só com internet).
* **Agenda:** atrasados, hoje e próximos 30 dias, incluindo partos e cios; a tarefa abre o registro pré-preenchido.
* **Registrar:** mesmos tipos do caseiro, com cio e exame, fotos e áudio, offline.
* **Relatórios:** quatro abas com indicadores, gráficos e tabelas principais; **Enviar planilha** (Excel ou CSV) pelo compartilhar do Android. Só com internet; respeita o módulo do plano.
* **Mais:** avisos, envio, preferências de avisos, versão e Sair.

## D. Sincronização
* Gestor: Wi-Fi e 4G, inclusive fotos e áudios. Caseiro: só Wi-Fi, como hoje.
* Gestor também trabalha offline: estado guardado no celular e fila enviada quando a rede volta.

## E. Avisos no celular (sem Firebase)
* Consulta em segundo plano a cada 15 minutos (mínimo do Android) e notificação do sistema; pode atrasar em economia de bateria. Pede a permissão de notificação no Android 13 ou mais novo.
* Tipos: procedimentos atrasados, parto previsto em até 7 dias, cio previsto para hoje, pendências da ABCCMM e **ocorrência grave registrada pelo caseiro** (novo tipo de aviso crítico, também no portal).
* Em Mais: liga ou desliga cada tipo e define o horário de silêncio (padrão 21h às 6h). Sem repetir o mesmo aviso; tocar abre a ficha.

## F. Fora desta versão
* iOS e App Store; push imediato pelo Firebase; editar protocolos, equipe e parametrizações pelo app; HTTPS (virá com o domínio).

## G. Testes e entrega
* Servidor: login do app com 2FA, exigência de HTTPS e chave de teste, sessão por celular, saída, troca de senha encerrando o app, aviso de ocorrência grave.
* Emulador: teste do gestor (login com 2FA, Dashboard, ficha, registro offline, envio, relatório) além do teste do caseiro.
* Manual, HISTORICO, README e Trello.
