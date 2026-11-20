# Haras360 · Especificação detalhada da v1.2.0

**Situação:** aprovada pelo Ricardo em 20/11/2026 (partes A a E). Branch `etapa/1.2-audio`.

## A. App do caseiro
* Botão "Gravar áudio" no formulário de registro, abaixo das fotos. Até 2 minutos (para sozinho no limite), com contador.
* Ouvir, apagar e gravar de novo antes de salvar. Um áudio por registro.
* AAC mono, cerca de 32 kbps (até uns 500 KB). Permissão de microfone pedida só na primeira gravação.
* Offline: o áudio entra na fila com as fotos e vai somente no Wi-Fi, depois do registro, com retomada.
* Na ficha do animal, o histórico mostra o ícone de áudio e permite ouvir, inclusive os ainda não enviados.

## B. Servidor
* `POST /api/app/audios`: um por registro, até 1 MB, tipo conferido pelo conteúdo (não pela extensão), idempotente pelo identificador gerado no celular.
* Guardado junto das fotos, entregue só a usuários logados do mesmo haras, incluído no backup.
* Migração aditiva com a tabela de áudios.

## C. Portal do gestor
* Player de áudio com a duração no registro do prontuário.
* Ícone de áudio nos "últimos registros do caseiro" do Painel.
* Ao excluir o registro, o áudio sai junto (confirmação e auditoria).

## D. Parametrização
* Módulo "Áudio nos registros" na grade de planos e módulos (padrão: liberado).
* Duração máxima ajustável (padrão 2 minutos).

## E. Testes
* API: envio, duplicidade, tamanho, tipo falso, isolamento entre haras e exclusão.
* App: unidade da fila; emulador com áudio simulado numa ocorrência sem Wi-Fi e chegada ao servidor.
* Verificação visual do player no prontuário e captura para o manual.

**Fora do escopo:** transcrição para texto (entra com o assistente de IA) e recado avulso sem registro.
