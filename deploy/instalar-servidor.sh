#!/usr/bin/env bash
# Instalação do Haras360 em uma VM Ubuntu nova (pensado para a VM AMD micro da Oracle, 1 GB).
#
# Uso, dentro da pasta extraída do pacote haras360-X.Y.Z:
#   sudo ./deploy/instalar-servidor.sh
#
# Sem perguntas (testes automatizados), por variáveis de ambiente:
#   H360_ADMIN_NOME, H360_ADMIN_EMAIL, H360_ADMIN_SENHA   primeiro administrador
#   H360_PORTA=8090        porta pública (Caddy)
#   H360_SEM_SWAP=1        não cria swap      H360_SEM_FIREWALL=1  não mexe no firewall
#   H360_RESTAURAR=<pasta> restauração a partir de um backup (usado por restaurar-servidor.sh)
set -euo pipefail
PACOTE="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
. "$PACOTE/deploy/lib/comum.sh"
exige_root

VERSAO="$(tr -d ' \r\n' < "$PACOTE/VERSION")"
PORTA="${H360_PORTA:-8090}"
PORTA_APP=8000
REST="${H360_RESTAURAR:-}"
gerar() { head -c 64 /dev/urandom | od -An -tx1 | tr -d ' \n' | head -c "$1"; }

. /etc/os-release
[ "${ID:-}" = "ubuntu" ] || falha "Este instalador é para Ubuntu (encontrado: ${PRETTY_NAME:-desconhecido})."
[ -L "$H360_ATUAL" ] && falha "O Haras360 já está instalado ($(versao_atual)). Para atualizar use: sudo haras360-update <pacote> <assinatura>"
if ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]$PORTA\$"; then falha "A porta $PORTA já está em uso. Rode com outra: sudo H360_PORTA=8091 $0"; fi
info "Instalando o Haras360 $VERSAO em $(hostname) (Ubuntu $VERSION_ID)"

# ---------- 1. swap ----------
if [ -z "${H360_SEM_SWAP:-}" ]; then
  SWAP_MB="$(free -m | awk '/^Swap:/{print $2}')"
  if [ "${SWAP_MB:-0}" -lt 1800 ] && [ ! -f /swapfile ]; then
    info "Criando swap de 2 GB (a VM tem pouca memória)"
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none
    chmod 600 /swapfile; mkswap /swapfile >/dev/null; swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
  printf 'vm.swappiness=10\nvm.vfs_cache_pressure=50\n' > /etc/sysctl.d/99-haras360.conf
  sysctl -q -p /etc/sysctl.d/99-haras360.conf || true
fi

# ---------- 2. pacotes do sistema ----------
info "Instalando pacotes do sistema (MariaDB, Python, Caddy)"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip python3-cryptography mariadb-server curl gnupg debian-keyring debian-archive-keyring apt-transport-https ca-certificates >/dev/null
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || falha "É preciso Python 3.10 ou mais novo (Ubuntu 22.04 ou 24.04)."
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq && apt-get install -y -qq caddy >/dev/null
fi

# ---------- 3. usuário e pastas ----------
id "$H360_USUARIO" >/dev/null 2>&1 || useradd --system --home-dir "$H360_BASE" --shell /usr/sbin/nologin "$H360_USUARIO"
install -d -m 755 -o root -g root "$H360_BASE" "$H360_RELEASES" "$H360_PACOTES"
install -d -m 750 -o "$H360_USUARIO" -g "$H360_USUARIO" "$H360_COMP" "$H360_COMP/fotos" "$H360_FILA" "$H360_FILA/entrada"
install -d -m 711 -o root -g root "$H360_BACKUPS"
install -d -m 700 -o root -g root "$H360_VARLIB"
install -d -m 750 -o root -g "$H360_USUARIO" "$H360_ETC"

# ---------- 4. banco ----------
info "Configurando o MariaDB para 1 GB de memória"
install -m 644 "$PACOTE/deploy/mariadb/90-haras360.cnf" /etc/mysql/mariadb.conf.d/90-haras360.cnf
systemctl enable mariadb >/dev/null 2>&1; systemctl restart mariadb
if [ -n "$REST" ]; then
  cp -a "$REST/config/etc-haras360/." "$H360_ETC/"
  DB_SENHA="$(grep -E '^H360_DB_SENHA=' "$H360_ETC/haras360.env" | cut -d= -f2)"
else
  DB_SENHA="$(gerar 32)"
fi
mysql <<SQL
CREATE DATABASE IF NOT EXISTS haras360 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'haras360'@'localhost' IDENTIFIED BY '$DB_SENHA';
ALTER USER 'haras360'@'localhost' IDENTIFIED BY '$DB_SENHA';
GRANT ALL PRIVILEGES ON haras360.* TO 'haras360'@'localhost';
FLUSH PRIVILEGES;
SQL

# ---------- 5. configuração ----------
if [ -z "$REST" ]; then
  umask 027
  cat > "$H360_ETC/haras360.env" <<ENV
# Haras360 · gerado pelo instalador em $(date '+%d/%m/%Y %H:%M'). Contém segredos.
DB_URL=mysql+pymysql://haras360:$DB_SENHA@localhost/haras360?charset=utf8mb4&unix_socket=/run/mysqld/mysqld.sock
SECRET_KEY=$(gerar 64)
COOKIE_SECURE=0
TZ=America/Sao_Paulo
H360_COMPARTILHADO=$H360_COMP
H360_RELEASES=$H360_RELEASES
H360_PORTA=$PORTA
H360_PORTA_APP=$PORTA_APP
H360_DB_NOME=haras360
H360_DB_SENHA=$DB_SENHA
ENV
  umask 022
fi
chown root:"$H360_USUARIO" "$H360_ETC/haras360.env"; chmod 640 "$H360_ETC/haras360.env"
PORTA="$(grep -E '^H360_PORTA=' "$H360_ETC/haras360.env" | cut -d= -f2)"; PORTA="${PORTA:-8090}"
if [ ! -f "$H360_ETC/chave-publica.pem" ] && [ -f "$PACOTE/deploy/chave-publica.pem" ]; then
  install -m 644 "$PACOTE/deploy/chave-publica.pem" "$H360_ETC/chave-publica.pem"
fi
[ -f "$H360_ETC/chave-publica.pem" ] || aviso "Sem chave pública de atualização. Instale depois com: sudo haras360-chave chave-publica.pem"

# ---------- 6. versão ----------
info "Instalando a versão $VERSAO"
DEST="$H360_RELEASES/$VERSAO"
rm -rf "$DEST"; install -d -m 755 "$DEST"
cp -a "$PACOTE/." "$DEST/"
rm -rf "$DEST/venv"
python3 -m venv "$DEST/venv"
"$DEST/venv/bin/pip" install -q --no-input --disable-pip-version-check --cache-dir "$H360_VARLIB/cache-pip" -r "$DEST/backend/requirements.txt"
chown -R root:root "$DEST"; chmod -R go-w "$DEST"
ln -sfn "$DEST" "$H360_ATUAL"
for f in "$PACOTE"/../haras360-"$VERSAO".tar.gz "$PACOTE"/../haras360-"$VERSAO".tar.gz.sig "$REST"/haras360-"$VERSAO".tar.gz "$REST"/haras360-"$VERSAO".tar.gz.sig; do
  [ -f "$f" ] && cp "$f" "$H360_PACOTES/"
done
instalar_scripts_do_release "$DEST"

# ---------- 7. restauração de dados ----------
if [ -n "$REST" ]; then
  info "Restaurando banco e fotos do backup"
  gunzip -c "$REST/banco.sql.gz" | mysql haras360
  tar -xzf "$REST/fotos.tar.gz" -C "$H360_COMP"
  chown -R "$H360_USUARIO":"$H360_USUARIO" "$H360_COMP/fotos"
fi

# ---------- 8. banco e serviços ----------
info "Aplicando migrações"
( set -a; . "$H360_ETC/haras360.env"; set +a; cd "$DEST/backend" && runuser -u "$H360_USUARIO" -- "$DEST/venv/bin/python" -m app.migracoes )
sed -e "s/__PORTA__/$PORTA/" -e "s/__PORTA_APP__/$PORTA_APP/" "$DEST/deploy/caddy/Caddyfile.modelo" > /etc/caddy/Caddyfile
install -d -m 755 -o caddy -g caddy /var/log/caddy 2>/dev/null || install -d -m 755 /var/log/caddy
systemctl enable --now haras360.service haras360-tarefa.path haras360-backup.timer >/dev/null 2>&1
systemctl restart haras360 caddy
aguardar_saude "$VERSAO" 90 || { journalctl -u haras360 -n 40 --no-pager; falha "A aplicação não respondeu. Veja o registro acima."; }

# ---------- 9. firewall ----------
if [ -z "${H360_SEM_FIREWALL:-}" ]; then
  info "Liberando a porta $PORTA no firewall da VM"
  if command -v ufw >/dev/null && ufw status 2>/dev/null | grep -q "Status: active"; then
    ufw allow "$PORTA/tcp" >/dev/null
  elif command -v iptables >/dev/null; then
    # As imagens Ubuntu da Oracle trazem uma regra REJECT no fim da cadeia INPUT: a liberação entra antes dela.
    iptables -C INPUT -p tcp --dport "$PORTA" -m state --state NEW -j ACCEPT 2>/dev/null || iptables -I INPUT 1 -p tcp --dport "$PORTA" -m state --state NEW -j ACCEPT
    if command -v netfilter-persistent >/dev/null; then netfilter-persistent save >/dev/null 2>&1
    else apt-get install -y -qq iptables-persistent >/dev/null 2>&1 && netfilter-persistent save >/dev/null 2>&1 || aviso "Instale iptables-persistent para manter a regra após reiniciar."; fi
  fi
fi

# ---------- 10. primeiro administrador ----------
if [ -z "$REST" ]; then
  info "Cadastro do administrador da plataforma"
  ARGS=()
  [ -n "${H360_ADMIN_NOME:-}" ] && ARGS+=(--nome "$H360_ADMIN_NOME")
  [ -n "${H360_ADMIN_EMAIL:-}" ] && ARGS+=(--email "$H360_ADMIN_EMAIL")
  [ -n "${H360_ADMIN_SENHA:-}" ] && ARGS+=(--senha "$H360_ADMIN_SENHA")
  cli_app criar-admin "${ARGS[@]}"
fi
auditar parametro_alterado "servidor instalado na versão $VERSAO$( [ -n "$REST" ] && echo ' a partir de backup')"

IP="$(curl -fsS --max-time 4 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
info "Haras360 $VERSAO instalado"
cat <<FIM

  Acesso:  http://$IP:$PORTA/entrar
           O administrador cadastra o 2FA no primeiro login e cria os haras em /admin.

  Falta no console da Oracle Cloud:
    Networking > Virtual Cloud Networks > (sua VCN) > Security Lists > Add Ingress Rule
    Origem 0.0.0.0/0, protocolo TCP, porta de destino $PORTA.

  Backup para o bucket da OCI:   sudo haras360-configurar-backup
  Comandos:                      sudo haras360 listar | sudo haras360-rollback | journalctl -u haras360 -f

FIM
