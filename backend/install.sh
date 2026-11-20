#!/usr/bin/env bash
# Instalação do Haras360 na VPS (Docker + MySQL já existente).
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

PORTA="${PORTA:-8090}"
DB_NAME="haras360"
DB_USER="haras360"
REDE="haras360-db"

info()  { echo -e "\n\033[1;32m==>\033[0m $*"; }
aviso() { echo -e "\033[1;33m[atenção]\033[0m $*"; }
falha() { echo -e "\033[1;31m[erro]\033[0m $*" >&2; exit 1; }
gerar() { head -c 64 /dev/urandom | od -An -tx1 | tr -d ' \n' | head -c "$1"; }

[ "$(id -u)" -eq 0 ] || falha "Rode como administrador: sudo ./install.sh"
command -v docker >/dev/null || falha "Docker não encontrado."
docker compose version >/dev/null 2>&1 || falha "Plugin 'docker compose' não encontrado. Instale o pacote docker-compose-plugin."
[ -f .env ] && falha "Já existe uma instalação nesta pasta (.env encontrado). Para atualizar use: sudo ./update.sh"

if ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]${PORTA}\$"; then
  falha "A porta ${PORTA} já está em uso. Rode com outra porta, ex.: sudo PORTA=8091 ./install.sh"
fi

# ---------- localizar o MySQL existente ----------
info "Procurando o MySQL/MariaDB que já roda na VPS"
mapfile -t CANDS < <(docker ps --format '{{.Names}}|{{.Image}}' | grep -Ei 'mysql|mariadb|percona' || true)
MODO=""; MYSQL_CT=""
if [ "${#CANDS[@]}" -gt 0 ]; then
  if [ "${#CANDS[@]}" -eq 1 ]; then
    MYSQL_CT="${CANDS[0]%%|*}"
  else
    echo "Encontrei mais de um container de banco:"
    for i in "${!CANDS[@]}"; do echo "  $((i+1))) ${CANDS[$i]%%|*}  (imagem ${CANDS[$i]#*|})"; done
    read -rp "Qual deles usar? [1-${#CANDS[@]}]: " ESC
    [[ "$ESC" =~ ^[0-9]+$ ]] && [ "$ESC" -ge 1 ] && [ "$ESC" -le "${#CANDS[@]}" ] || falha "Opção inválida."
    MYSQL_CT="${CANDS[$((ESC-1))]%%|*}"
  fi
  MODO="container"
  echo "Usando o container: ${MYSQL_CT}"
elif ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq '[:.]3306$'; then
  MODO="host"
  echo "MySQL encontrado rodando direto na VPS (porta 3306)."
else
  falha "Nenhum MySQL encontrado (nem em container, nem na porta 3306 da VPS)."
fi

read -rp "Usuário administrador do MySQL [root]: " ADMIN_USER
ADMIN_USER="${ADMIN_USER:-root}"
read -rsp "Senha do usuário ${ADMIN_USER} no MySQL: " ADMIN_PASS; echo
[ -n "$ADMIN_PASS" ] || falha "Senha não informada."
export ADMIN_USER ADMIN_PASS

# ---------- rede e acesso ao banco ----------
if [ "$MODO" = "container" ]; then
  info "Ligando o Haras360 ao container ${MYSQL_CT} por uma rede própria (${REDE})"
  docker network inspect "$REDE" >/dev/null 2>&1 || docker network create "$REDE" >/dev/null
  if ! docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' "$MYSQL_CT" | grep -qw "$REDE"; then
    docker network connect "$REDE" "$MYSQL_CT"
    echo "Rede adicionada ao ${MYSQL_CT} sem reiniciá-lo. O sistema de reservatórios não é afetado."
  fi
  SUBNET="$(docker network inspect "$REDE" -f '{{(index .IPAM.Config 0).Subnet}}')"
  APP_HOSTS="$(echo "$SUBNET" | cut -d. -f1-2).%"
  DB_HOST="$MYSQL_CT"
  NET_ARGS=(--network "$REDE")
else
  APP_HOSTS="localhost,127.0.0.1"
  DB_HOST="127.0.0.1"
  NET_ARGS=(--network host)
fi
DB_PORT=3306

# ---------- docker-compose ----------
info "Gerando docker-compose.yml (modo: ${MODO})"
if [ "$MODO" = "container" ]; then
cat > docker-compose.yml <<YML
services:
  haras360:
    build: .
    image: haras360:latest
    container_name: haras360
    restart: unless-stopped
    env_file: .env
    ports:
      - "${PORTA}:${PORTA}"
    volumes:
      - ./dados/fotos:/dados/fotos
    networks:
      - dbnet
networks:
  dbnet:
    external: true
    name: ${REDE}
YML
else
cat > docker-compose.yml <<YML
services:
  haras360:
    build: .
    image: haras360:latest
    container_name: haras360
    restart: unless-stopped
    env_file: .env
    network_mode: host
    volumes:
      - ./dados/fotos:/dados/fotos
YML
fi

info "Construindo a imagem do Haras360 (alguns minutos na primeira vez)"
docker compose build

# ---------- banco ----------
info "Criando o banco ${DB_NAME} e o usuário ${DB_USER}"
APP_PASS="$(gerar 32)"
export APP_PASS
docker run --rm "${NET_ARGS[@]}" -e ADMIN_USER -e ADMIN_PASS -e APP_PASS \
  -e DB_HOST="$DB_HOST" -e DB_PORT="$DB_PORT" -e DB_NAME="$DB_NAME" -e APP_USER="$DB_USER" -e APP_HOSTS="$APP_HOSTS" \
  --entrypoint python haras360:latest -m app.provisionar
unset ADMIN_PASS

# ---------- configuração ----------
umask 077
cat > .env <<ENV
# Gerado pelo install.sh em $(date '+%d/%m/%Y %H:%M'). Mantenha este arquivo em sigilo.
DB_URL=mysql+pymysql://${DB_USER}:${APP_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}?charset=utf8mb4
SECRET_KEY=$(gerar 64)
TZ=America/Sao_Paulo
HOST=0.0.0.0
PORTA=${PORTA}
LIMITE_ANIMAIS=30
COOKIE_SECURE=0
# usados pelo backup.sh
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASS=${APP_PASS}
MODO=${MODO}
ENV
umask 022
chmod 600 .env
mkdir -p dados/fotos backups
chown -R 10001:10001 dados

info "Iniciando o Haras360"
docker compose up -d
echo -n "Aguardando a aplicação responder"
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${PORTA}/api/saude" >/dev/null 2>&1; then echo " ok"; break; fi
  echo -n "."; sleep 2
  [ "$i" -eq 60 ] && { echo; docker compose logs --tail 40; falha "A aplicação não respondeu. Veja os logs acima."; }
done

# ---------- primeiro haras e gestor ----------
info "Cadastro do haras e do primeiro gestor"
docker compose exec haras360 python -m app.cli criar-haras || aviso "Cadastro não concluído. Rode depois: docker compose exec haras360 python -m app.cli criar-haras"

# ---------- firewall da VPS ----------
info "Liberando a porta ${PORTA} no firewall da VPS"
if command -v firewall-cmd >/dev/null && firewall-cmd --state >/dev/null 2>&1; then
  firewall-cmd --permanent --add-port="${PORTA}/tcp" >/dev/null && firewall-cmd --reload >/dev/null && echo "firewalld: porta ${PORTA} liberada."
elif command -v ufw >/dev/null && ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw allow "${PORTA}/tcp" >/dev/null && echo "ufw: porta ${PORTA} liberada."
elif command -v iptables >/dev/null; then
  if ! iptables -C INPUT -p tcp --dport "$PORTA" -m state --state NEW -j ACCEPT 2>/dev/null; then
    iptables -I INPUT -p tcp --dport "$PORTA" -m state --state NEW -j ACCEPT
  fi
  if command -v netfilter-persistent >/dev/null; then netfilter-persistent save >/dev/null 2>&1 && echo "iptables: porta ${PORTA} liberada e regra salva."
  else aviso "iptables: porta liberada, mas instale 'iptables-persistent' para manter a regra após reiniciar."; fi
fi

# ---------- backup diário ----------
DIR="$(pwd)"
echo "30 2 * * * root ${DIR}/backup.sh >> /var/log/haras360-backup.log 2>&1" > /etc/cron.d/haras360-backup
chmod 644 /etc/cron.d/haras360-backup
echo "Backup diário agendado para 02:30 em ${DIR}/backups (mantém 14 dias)."

IP="$(curl -fsS --max-time 4 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
info "Haras360 instalado"
cat <<FIM

  Login:          http://${IP}:${PORTA}/entrar
  Portal Gestor:  http://${IP}:${PORTA}/gestor
  Portal Campo:   http://${IP}:${PORTA}/campo

  Falta um passo no console da Oracle Cloud:
  Networking > Virtual Cloud Networks > (sua VCN) > Security Lists > Add Ingress Rule
  Origem 0.0.0.0/0, protocolo TCP, porta de destino ${PORTA}.

  Comandos úteis (nesta pasta):
    docker compose logs -f            acompanhar os logs
    sudo ./update.sh                  aplicar uma nova versão
    sudo ./backup.sh                  backup manual
    docker compose exec haras360 python -m app.cli listar
    docker compose exec haras360 python -m app.cli redefinir-senha

FIM
