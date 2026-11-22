# Haras360 · Especificação v1.7.0 · Financeiro da plataforma (clientes e mensalidades)

Aprovada por Ricardo Torres em 22/11/2026 ("pode seguir").

## A. Acesso
* Menu **Financeiro** no portal do administrador.
* Novo perfil **Financeiro** (criado pelo administrador em Administradores): vê só o Financeiro, com 2FA obrigatório e auditoria. O administrador vê tudo.

## B. Cliente (contratante de cada haras)
* Contrato: início, situação (Teste, Ativo, Suspenso, Cancelado), dia de vencimento (1 a 28), observações.
* Contratante: nome ou razão social; CPF ou CNPJ conferido pelos dígitos, cifrado, mostrado mascarado, ver completo auditado.
* Contato financeiro (nome, e-mail, telefone) e endereço completo (logradouro, número, complemento, bairro, cidade, UF, CEP).
* Ajuste de preço: nenhum, desconto em % ou valor fixo combinado, com validade opcional.
* Período de teste parametrizável (padrão 30 dias): na situação Teste não há cobrança.

## C. Mensalidades
* Geradas 10 dias antes do vencimento (antecedência parametrizável), pelas faixas de preço e animais ativos naquele dia, com o ajuste do cliente. O cálculo fica guardado na cobrança.
* Mensalidade zero (faixa gratuita) não gera cobrança.
* Registrar pagamento (data, valor, meio, observação), estornar, cancelar com motivo, cobrança avulsa e recalcular antes do vencimento.
* Situações: em aberto, vence em 7 dias, atrasada, paga, cancelada.

## D. Atraso e bloqueio
* Aviso ao gestor (sino e app) 7 dias antes, no vencimento e no atraso.
* Com 15 dias de atraso (parametrizável), portal e app do gestor ficam só para consulta, com a faixa "Mensalidade em atraso". O caseiro continua registrando.
* O pagamento libera na hora; o financeiro pode liberar por prazo, com motivo auditado.

## E. Minha assinatura (gestor)
* Plano, animais ativos, valor do próximo mês com o cálculo, histórico de cobranças.
* Como pagar: chave Pix e dados bancários parametrizados pelo administrador; QR Code Pix copia e cola estático com valor e identificador da cobrança.

## F. Painel financeiro
* Clientes por situação, novos e cancelados no mês, haras e animais na plataforma.
* MRR, faturado, recebido e a receber no mês, evolução em 12 meses.
* Inadimplência por faixa (1 a 15, 16 a 30, mais de 30 dias).
* Listas com filtros e exportação Excel e CSV (clientes, cobranças, recebimentos).

## G. Fora desta versão
* Gateway (Pix e boleto com baixa automática), nota fiscal, envio de e-mail.

## H. Técnico
* Migração 007: tabelas `clientes` e `cobrancas`. Geração diária no servidor e ao abrir o painel, sem duplicar o mês.
* Testes da API, verificação visual e aviso no emulador. Branch `etapa/1.7-financeiro`, PR, tag v1.7.0.
