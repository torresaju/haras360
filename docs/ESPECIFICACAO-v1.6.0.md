# Haras360 · Especificação da v1.6.0

**Situação:** aprovada pelo Ricardo em 22/11/2026 ("siga para a próxima versão"). Branch `etapa/1.6-certificado-venda-externos`.

Pedido do Ricardo em 22/11/2026 com o certificado da BERIBELA DA TERRARUNA como base. Escolhas: certificado no Novo animal, na ficha, em lote e guardado; genealogia de 4 gerações, pelagem e datas, criador e proprietário, mensurações; externos (garanhões e éguas), tipo de sêmen e cadastro pelo certificado; comprador com contato, CPF ou CNPJ, nº ABCCMM e reutilizável; à vista ou parcelado, baixa de parcelas, avisos e relatório; pendência de transferência; só o gestor vê valores.

## A. Certificado de registro da ABCCMM
* Novo animal: "Preencher pelo certificado (PDF)". Ficha: "Atualizar pelo certificado" com antes e depois. Importar ABCCMM › Certificados: vários PDFs com prévia (novo, atualizar, igual) e confirmação.
* O PDF fica guardado na ficha (Documentos) e entra no backup.
* Dados: nome, livro, registro, volume e página, nascimento, sexo, DNA, chip, pelagem, datas da resenha e do registro, criador e proprietário (nome, nº de cadastro, propriedade, município e UF), mensurações e genealogia de 4 gerações (registro, DNA e livro de cada ancestral), em árvore na ficha.
* Recusa PDF que não seja certificado ABCCMM; avisa registro de outro animal e nome divergente; "*****" vira vazio.

## B. Animais externos
* Animais › Externos: garanhões e éguas de fora, com nome, sexo, registro, livro, DNA, proprietário ou haras, telefone, e-mail e observação; também pelo certificado.
* Fora do limite do plano, sem agenda sanitária e fora do app do caseiro.
* Garanhão da cobertura lista machos do haras e externos, com "+ Novo externo". Éguas externas recebem eventos reprodutivos e entram no relatório reprodutivo.
* Inseminação: tipo de sêmen (fresco, refrigerado, congelado) e central ou origem.

## C. Venda com comprador e parcelas (somente gestor)
* Compradores reutilizáveis: nome, CPF ou CNPJ (dígitos conferidos, cifrado, mascarado, ver completo vai para a auditoria), nº ABCCMM, telefone, e-mail, cidade e UF. Comprador sem venda pode ser excluído.
* Baixa por Venda: comprador, valor total, à vista (data e meio) ou parcelado (entrada opcional, 2 a 60 parcelas mensais, centavos na última, editáveis).
* Tela Vendas: total, recebido e saldo; marcar parcela paga (data, valor, meio, obs) ou estornar, com confirmação e auditoria. Desfazer a baixa só sem parcela paga.
* Avisos: parcela vencendo em 7 dias e vencida (sino, Dashboard "A receber", app do gestor).
* Pendência "Comunicar a transferência na ABCCMM" até ser marcada como feita.
* Relatório Vendas com Excel e CSV. App do gestor: Mais › Vendas.

## D. Fora desta versão
* Boleto ou Pix, contrato ou recibo em PDF, nota fiscal, juros e multa automáticos.

## E. Testes e entrega
* Certificado anonimizado como caso de teste, genealogia, PDF inválido, externos fora do limite e da agenda, parcelas e centavos, CPF/CNPJ, avisos e relatório de vendas; verificação visual; emulador; manual, HISTORICO, README e Trello.
