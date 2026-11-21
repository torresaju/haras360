# Haras360 · Especificação detalhada da v1.4.0

**Situação:** aprovada pelo Ricardo em 20/11/2026 ("Faça o merge e siga"). Branch `etapa/1.4-relatorios-cio`.

Escolhas do Ricardo: os quatro relatórios; tela com gráficos e planilha (Excel e CSV); cio com previsão, dados do exame, cio do potro e registro pelo caseiro; relatórios só para o gestor; baixa de animais com data e motivo; previsão até o diagnóstico positivo; módulo Relatórios por plano.

## A. Baixa de animais
* Na ficha do animal, botão **Dar baixa**: data, motivo (venda, morte, doação ou transferência), destino ou comprador (opcional) e observação.
* O animal baixado sai do plantel ativo, da Agenda, do Dashboard e do app, mas continua consultável no filtro "Baixados", com o prontuário completo.
* **Desfazer baixa** com confirmação e auditoria. Respeita o limite de animais do plano.
* Se um animal baixado aparecer de novo na importação ABCCMM, continua baixado e o resumo da importação avisa.
* Entrada no plantel: nascimento (quando o parto da mãe foi registrado no haras, até 15 dias de diferença), importação ABCCMM ou cadastro manual.
* Migração 005 (colunas de baixa em `animais`). Auditoria: `animal_baixa`, `animal_baixa_desfeita`.

## B. Registro de cio
* Novo evento **Cio** na Reprodução: Portal do Gestor, Portal Campo e app (offline).
* Campos: data e sinais observados; dados do exame opcionais: ovário (esquerdo ou direito), folículo (5 a 80 mm), edema uterino (0 a 3) e observação.
* **Previsão do próximo cio:** base no último cio, cobertura, inseminação ou aborto, mais o ciclo (21 dias, ajustável de 18 a 25). Vira a tarefa "Observar cio" na Agenda e na tela Hoje. A previsão atrasada aparece por até 3 dias e depois passa ao ciclo seguinte.
* A égua sai da previsão com diagnóstico positivo e volta depois de diagnóstico negativo, aborto ou parto.
* **Cio do potro:** depois do parto sem cio registrado, tarefa "Cio do potro" na janela do 7º ao 12º dia (ajustável). Passada a janela, a previsão segue o ciclo a partir do 7º dia.
* Avisos de cio entram como informação (nunca como crítico).
* Parametrizações › Reprodução: ligar ou desligar a previsão, duração do ciclo e janela do cio do potro.

## C. Relatórios (somente gestor)
* Menu **Relatórios** com quatro abas e filtros de período (padrão: do mesmo mês do ano anterior até hoje), animal e categoria (éguas, machos, potros, outros).
* **Sanitário:** procedimentos no período, atrasados hoje, animais em dia (%), vacinas aplicadas; gráficos por mês e por tipo; tabelas de procedimentos realizados, pendências de hoje e por protocolo.
* **Reprodutivo:** cios, coberturas e inseminações, taxa de prenhez (positivos sobre diagnósticos), partos, éguas prenhes, intervalo médio entre partos; gráficos de eventos, prenhes e vazias e eventos por mês; tabelas de situação das éguas (com próximo cio), eventos e intervalo entre partos.
* **Plantel:** ativos, fêmeas e machos, entradas e saídas; gráficos por categoria, faixa de idade e saídas por motivo; tabelas do plantel ativo, entradas e saídas.
* **Atividade do campo:** registros do caseiro, pelo app, ocorrências, fotos e áudios; gráficos por mês, tipo e origem; tabelas por pessoa e lista de registros.
* Exportação **Excel (.xlsx)** com aba Resumo e uma aba por tabela, cabeçalho verde, filtros e link "Abrir" para a ficha; **CSV** com ponto e vírgula e acentos para o Excel. Cada exportação vai para a auditoria (`relatorio_exportado`).
* Novo módulo "Relatórios e exportação" na grade de planos, liberado por padrão.

## D. Fora desta versão
* Relatórios em PDF, relatórios para o caseiro e valores financeiros.

## E. Testes e entrega
* Testes do motor (previsão, ciclo, cio do potro, gestação, baixa), da API (cio, baixa, parâmetros, relatórios, exportações, módulo e perfil).
* Verificação visual das quatro abas, da baixa e do cio; emulador com cio registrado no app sem Wi-Fi.
* Manual, HISTORICO, README e Trello.
