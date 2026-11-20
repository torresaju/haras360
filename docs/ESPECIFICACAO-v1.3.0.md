# Haras360 · Especificação detalhada da v1.3.0

**Situação:** aprovada pelo Ricardo em 20/11/2026 (partes A a E, logotipo opção A; parte F aprovada às 17:21). Branch `etapa/1.3-identidade-visual`.

Direção: elegância equestre e tecnologia. Visual premium sem excesso, informação importante em destaque, identidade igual no computador e no celular, universo equestre sem clichês.

## A. Marca e cores
* Logotipo opção A: perfil de cavalo em traço contínuo com arco dourado aberto (o "360"). SVG nas versões clara e escura, ícone do app e favicon.
* Paleta: verde haras `#193D30` (institucional e botões principais), dourado `#D5A064` (destaques; texto sobre o dourado sempre em grafite), areia `#F3F1E9` (fundo), grafite `#292F2B` (texto), verde sálvia `#82978A` (secundário). Na palavra "360" sobre fundo claro, dourado escuro `#B8833F` para leitura. Cores de alerta mantidas e ajustadas. Contraste conferido.
* Tipografia: Manrope (títulos) e Inter (textos). No app, fontes dentro do APK (offline).
* Ícones lineares próprios: Animais, Sanidade, Reprodução, Agenda, Relatórios, Administração.
* Ilustrações vetoriais próprias (cavalos, cerca, campo ao entardecer) no login, cabeçalho e banner. Fotos ficam para a v1.4.0.

## B. Portal do gestor
* Menu lateral permanente no computador (recolhível no celular): Dashboard; Animais (cadastro, ficha, Importar ABCCMM); Sanidade (vacinas, vermifugação, exames, protocolos); Reprodução (gestações e coberturas); Agenda; Relatórios ("em breve"); Administração (Equipe, Parametrizações, Auditoria, Assistente).
* Cabeçalho com nome e município do haras, logotipo do haras, sino de avisos e usuário.
* Dashboard: animais, vacinas vencidas, vacinas em 7 dias, gestações ativas, partos em 30 dias; próximos eventos; rebanho por categoria (éguas, machos, potros, outros); situação reprodutiva (coberturas e inseminações do mês); últimos registros do campo com áudio.
* Ficha do animal no visual novo.

## C. Portal Campo e app Android
* Navegação inferior: Hoje, Animais, Agenda, Mais (Avisos, Envio, versão).
* "Registrar ocorrência" no topo da tela Hoje.
* Entrada do app com fundo verde, ilustração, logotipo e "Ler QR Code".
* Alertas de vacinas e gestação na tela Hoje. Funcionamento offline, Wi-Fi e áudio inalterados.

## D. Entrada, Administração e Ajuda
* Mesmas cores, fontes e menu lateral; manual com capturas novas.

## E. Testes
* Testes atuais passando; verificação visual de todas as telas (computador e celular) com conferência de contraste; emulador com a navegação nova.

## F. Personalização por imagens
* Administrador da plataforma (Administração › Parametrizações › Marca): logotipo da plataforma (menu, entrada, favicon, manual) e imagens padrão (cabeçalho, banner do Dashboard, fundo do app, fundo da entrada). Sem envio, valem o logotipo A e as ilustrações vetoriais.
* Gestor do haras (Parametrizações do haras › Imagens): logotipo do haras (já existente, agora também no app), imagem do cabeçalho (3:1), banner do Dashboard (4:1) e fundo do app (9:16).
* PNG, JPG ou WebP até 8 MB; o navegador reduz e converte para WebP antes de enviar; o servidor confere o tipo real.
* Pré-visualização com ponto de foco (centro, topo, base); camada escura automática sob textos; "Voltar ao padrão"; auditoria de cada troca.
* App: imagens chegam na sincronização pelo Wi-Fi e ficam no celular (offline), baixadas de novo só quando mudam.
* Imagens do haras só para usuários do haras; as da plataforma são públicas (a entrada aparece antes do login). Tudo no backup.
* Fora do escopo: ícone do app por haras (exigiria um APK por cliente) e troca de cores.

## Próximo release (v1.4.0)
Relatórios e registro de cio.
