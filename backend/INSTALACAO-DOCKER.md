# Haras360 · implantação na VPS

Portais web do Haras360 (Gestor e Campo) com API, login e fotos no servidor.
Roda em um container Docker na porta **8090** e usa o **MySQL que já existe** na VPS, em um banco próprio (`haras360`).

```
http://IP_DA_VPS:8090/entrar   tela de login
http://IP_DA_VPS:8090/gestor   Portal Gestor (proprietário)
http://IP_DA_VPS:8090/campo    Portal Campo (caseiro / operador)
```

## 1. Copiar o pacote para a VPS

No seu computador:

```bash
scp haras360-vps.tar.gz ubuntu@IP_DA_VPS:/tmp/
```

Na VPS:

```bash
sudo tar xzf /tmp/haras360-vps.tar.gz -C /opt
cd /opt/haras360
sudo ./install.sh
```

## 2. O que o install.sh faz

1. Encontra o MySQL que já roda na VPS (em container ou direto no sistema). Se houver mais de um container de banco, pergunta qual usar.
2. Pede a senha do administrador do MySQL (usada só nesta etapa e não fica gravada).
3. Cria a rede Docker `haras360-db` e conecta o container do MySQL a ela, sem reiniciá-lo. O sistema de reservatórios continua funcionando normalmente.
4. Cria o banco `haras360` e o usuário `haras360` com senha aleatória, com acesso só a esse banco.
5. Gera o `.env` (segredos, permissão 600), constrói a imagem e sobe o container.
6. Pede o nome do haras e os dados do primeiro gestor (nome, e-mail e senha).
7. Libera a porta 8090 no firewall da VPS e agenda o backup diário às 02:30.

## 3. Liberar a porta na Oracle Cloud

No console da Oracle: **Networking > Virtual Cloud Networks > sua VCN > Security Lists > Add Ingress Rule**

| Campo | Valor |
|---|---|
| Source CIDR | 0.0.0.0/0 |
| IP Protocol | TCP |
| Destination Port Range | 8090 |

## 4. Primeiro uso

1. Entre em `/entrar` com o e-mail e a senha do gestor.
2. Vá em **Importar ABCCMM** e envie o PDF do Relatório de Plantel.
3. Em **Equipe**, adicione o caseiro com perfil "Caseiro / operador" e uma senha inicial. Ele entra pelo mesmo endereço e cai direto no Portal Campo.
4. Confira os intervalos em **Protocolos** com o veterinário.

## Comandos do dia a dia (na pasta /opt/haras360)

| Tarefa | Comando |
|---|---|
| Ver logs | `docker compose logs -f` |
| Reiniciar | `docker compose restart` |
| Listar haras e usuários | `docker compose exec haras360 python -m app.cli listar` |
| Redefinir senha de alguém | `docker compose exec haras360 python -m app.cli redefinir-senha` |
| Criar outro haras (SaaS) | `docker compose exec haras360 python -m app.cli criar-haras` |
| Backup manual | `sudo ./backup.sh` |
| Atualizar para nova versão | copie o novo pacote por cima (mantendo `.env` e `dados/`) e rode `sudo ./update.sh` |

## Backup e restauração

O backup diário fica em `backups/` (14 dias): `banco-AAAAMMDD-HHMM.sql.gz` e `fotos-AAAAMMDD-HHMM.tar.gz`.

Restaurar:

```bash
cd /opt/haras360
gunzip -c backups/banco-AAAAMMDD-HHMM.sql.gz | docker compose exec -T haras360 python -m app.restaurar
sudo tar xzf backups/fotos-AAAAMMDD-HHMM.tar.gz -C dados
sudo chown -R 10001:10001 dados
```

## Segurança nesta fase

* Sem HTTPS: senhas e dados trafegam sem criptografia. Use apenas para testes.
* Login com limite de 8 tentativas a cada 15 minutos por e-mail e IP.
* O CPF do associado lido no PDF não é gravado no banco.
* Fotos só são servidas para usuários logados do mesmo haras.

Ao migrar para domínio com HTTPS, coloque um proxy (Nginx ou Caddy) na frente, mude `COOKIE_SECURE=1` no `.env` e rode `docker compose up -d`.

## Estrutura

```
app/            API (FastAPI), motor de regras, modelos e páginas prontas (app/static)
web/            fontes dos portais; após editar, rode: python3 web/build.py
Dockerfile      imagem Python 3.12
install.sh      instalação inicial
update.sh       atualização (faz backup antes)
backup.sh       backup do banco e das fotos
```

## Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| Página não abre de fora | Regra da Security List ausente | Passo 3 |
| "Não foi possível conectar ao MySQL" na instalação | Usuário ou senha do administrador incorretos | Rode `sudo ./install.sh` de novo (nada foi gravado) |
| Container reiniciando | Banco inacessível | `docker compose logs --tail 50` |
| Importação de PDF não lê nada | O PDF é digitalizado (imagem) | Gere o Relatório de Plantel de novo no Sistema de Gestão ABCCMM |
