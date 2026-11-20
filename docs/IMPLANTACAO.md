# Implantação do Haras360 na VM da Oracle

Roteiro para a segunda VM AMD micro (Ubuntu 22.04 ou 24.04, 1 GB de memória).

## 1. Chave de assinatura (uma única vez, no Windows)

1. Instale o Python 3 em python.org (marque "Add python.exe to PATH").
2. No Prompt de Comando:
   ```
   pip install cryptography
   python assinar-pacote.py gerar-chaves
   ```
   O `assinar-pacote.py` vem anexado em cada Release do GitHub.
3. Escolha uma senha forte (mínimo 12 caracteres) e não a perca.
   * A chave privada fica em `%USERPROFILE%\.haras360\chave-privada.pem`. Guarde uma cópia em local seguro, fora do computador.
   * A chave pública é gravada como `chave-publica.pem` na pasta atual.
4. Envie o conteúdo de `chave-publica.pem` para entrar no repositório em `deploy/chave-publica.pem`. A chave pública não é segredo. Ela também pode ser instalada direto no servidor com `sudo haras360-chave chave-publica.pem`.

## 2. Instalação na VM nova

```bash
# no seu computador
scp haras360-1.0.0.tar.gz ubuntu@IP_DA_VM:/tmp/

# na VM
cd /tmp && tar xzf haras360-1.0.0.tar.gz
sudo bash haras360-1.0.0/deploy/instalar-servidor.sh
```

O instalador:
* cria 2 GB de swap;
* instala MariaDB (ajustado para 1 GB), Python e Caddy;
* cria o usuário `haras360`, o banco e a configuração com segredos aleatórios;
* instala a versão, os serviços e o backup diário;
* libera a porta 8090 no firewall da VM;
* pede os dados do administrador da plataforma.

Depois, no console da Oracle: **Networking > Virtual Cloud Networks > sua VCN > Security Lists > Add Ingress Rule**, origem `0.0.0.0/0`, TCP, porta `8090`.

Acesse `http://IP_DA_VM:8090/entrar`. O administrador cadastra o 2FA no primeiro login e cria os haras em Administração.

## 3. Backup para o bucket da OCI

1. No console da Oracle: **Storage > Buckets > Create bucket** (privado). Ative o versionamento e, em Lifecycle Policy Rules, apague objetos com mais de 30 dias.
2. No bucket: **Pre-Authenticated Requests > Create**, com alvo Bucket, acesso "Permit object writes" e validade longa.
3. Na VM: `sudo haras360-configurar-backup` e cole a URL.

O backup roda todo dia às 02:30, também pode ser pedido em Administração › Atualização e backup, ou com `sudo haras360-backup`.

## 4. Atualização

1. Baixe `haras360-X.Y.Z.tar.gz` e `assinar-pacote.py` na Release da versão.
2. No Windows: `python assinar-pacote.py haras360-X.Y.Z.tar.gz`. Isso gera `haras360-X.Y.Z.tar.gz.sig`.
3. Em Administração › Atualização e backup, envie os dois arquivos. Também é possível por SSH: `sudo haras360-update haras360-X.Y.Z.tar.gz haras360-X.Y.Z.tar.gz.sig`.

O servidor faz o seguinte:
* confere o SHA-256 e a assinatura;
* faz backup e aplica as migrações;
* troca de versão e testa a aplicação por até 60 segundos;
* se algo falhar, volta sozinho para a versão anterior.

Para voltar manualmente: botão "Voltar para esta" na mesma tela, ou `sudo haras360-rollback X.Y.Z`.

## 5. Reconstruir o servidor a partir de um backup

```bash
tar xzf haras360-backup-AAAAMMDD-HHMMSS.tar.gz
cd haras360-backup-AAAAMMDD-HHMMSS
sudo ./restaurar-servidor.sh .
```

Os usuários entram com as mesmas senhas e o mesmo 2FA.

## Comandos úteis

| Tarefa | Comando |
|---|---|
| Situação do serviço | `systemctl status haras360` |
| Registros | `journalctl -u haras360 -f` |
| Haras e usuários | `sudo haras360 listar` |
| Redefinir senha | `sudo haras360 redefinir-senha --email x@y` |
| Redefinir 2FA | `sudo haras360 redefinir-2fa --email x@y` |
| Versões guardadas | `sudo haras360-rollback` |
| Trocar a chave pública | `sudo haras360-chave chave-publica.pem` |

## Onde fica cada coisa

| Caminho | Conteúdo |
|---|---|
| `/opt/haras360/releases/X.Y.Z` | cada versão instalada, com o seu ambiente Python |
| `/opt/haras360/atual` | atalho para a versão em uso |
| `/opt/haras360/compartilhado` | fotos, logotipos, fila de tarefas e backups |
| `/etc/haras360/haras360.env` | configuração e segredos (permissão 640) |
| `/etc/haras360/chave-publica.pem` | chave que confere os pacotes |
| `/etc/caddy/Caddyfile` | porta pública 8090 |
