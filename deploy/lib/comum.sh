# Funções comuns aos scripts do servidor Haras360 (instalado em /usr/local/lib/haras360/comum.sh).
# shellcheck shell=bash

H360_BASE="${H360_BASE:-/opt/haras360}"
H360_ETC="${H360_ETC:-/etc/haras360}"
H360_COMP="$H360_BASE/compartilhado"
H360_FILA="$H360_COMP/fila"
H360_BACKUPS="$H360_COMP/backups"
H360_RELEASES="$H360_BASE/releases"
H360_PACOTES="$H360_BASE/pacotes"
H360_ATUAL="$H360_BASE/atual"
H360_VARLIB="/var/lib/haras360"
H360_USUARIO="haras360"
H360_LIB="/usr/local/lib/haras360"
H360_STATUS="$H360_FILA/status.json"
H360_LOG_TAREFA="${H360_LOG_TAREFA:-}"

info()  { echo -e "\033[1;32m==>\033[0m $*"; [ -n "$H360_LOG_TAREFA" ] && echo "$(date '+%H:%M:%S') $*" >> "$H360_LOG_TAREFA"; return 0; }
aviso() { echo -e "\033[1;33m[atenção]\033[0m $*"; [ -n "$H360_LOG_TAREFA" ] && echo "$(date '+%H:%M:%S') atenção: $*" >> "$H360_LOG_TAREFA"; return 0; }
falha() { echo -e "\033[1;31m[erro]\033[0m $*" >&2; [ -n "$H360_LOG_TAREFA" ] && echo "$(date '+%H:%M:%S') erro: $*" >> "$H360_LOG_TAREFA"; exit 1; }

exige_root() { [ "$(id -u)" -eq 0 ] || falha "Rode como administrador: sudo $0"; }

versao_atual() {
  if [ -L "$H360_ATUAL" ]; then basename "$(readlink -f "$H360_ATUAL")"; else echo ""; fi
}

porta_app() { grep -E '^H360_PORTA_APP=' "$H360_ETC/haras360.env" 2>/dev/null | cut -d= -f2 || true; }

# Confere /api/saude direto na aplicação (sem o Caddy) e a versão respondida.
saude_ok() {
  local esperada="$1" porta resp
  porta="$(porta_app)"; porta="${porta:-8000}"
  resp="$(curl -fsS --max-time 4 "http://127.0.0.1:$porta/api/saude" 2>/dev/null)" || return 1
  [ -z "$esperada" ] && return 0
  echo "$resp" | grep -q "\"versao\":\"$esperada\""
}

aguardar_saude() {
  local esperada="$1" limite="${2:-60}" i
  for ((i = 0; i < limite; i += 2)); do
    saude_ok "$esperada" && return 0
    sleep 2
  done
  return 1
}

# Executa o comando de linha do Haras360 como o usuário da aplicação.
cli_app() {
  ( set -a; . "$H360_ETC/haras360.env"; set +a
    cd "$H360_ATUAL/backend" && runuser -u "$H360_USUARIO" -- "$H360_ATUAL/venv/bin/python" -m app.cli "$@" )
}

auditar() {  # auditar <acao> <alvo> [resultado]
  cli_app auditar --acao "$1" --alvo "$2" --resultado "${3:-ok}" --quem "servidor" >/dev/null 2>&1 || true
}

# Status mostrado na tela Administração > Atualização e backup.
status_tarefa() {  # status_tarefa <estado> <acao> <mensagem> [versaoAnterior] [versaoNova]
  python3 - "$H360_STATUS" "$@" "${H360_LOG_TAREFA:-}" <<'PY'
import json, sys, datetime, os
caminho, estado, acao, msg = sys.argv[1:5]
ant = sys.argv[5] if len(sys.argv) > 6 else ""
nova = sys.argv[6] if len(sys.argv) > 7 else ""
logf = sys.argv[-1]
try:
    st = json.load(open(caminho, encoding="utf-8"))
except Exception:
    st = {}
agora = datetime.datetime.now().isoformat(timespec="seconds")
if estado == "executando" and st.get("estado") != "executando":
    st = {"inicio": agora}
st.update({"estado": estado, "acao": acao, "mensagem": msg})
if ant: st["versaoAnterior"] = ant
if nova: st["versaoNova"] = nova
if estado in ("concluido", "falhou"): st["fim"] = agora
if logf and os.path.exists(logf):
    st["log"] = open(logf, encoding="utf-8", errors="replace").read().splitlines()[-60:]
tmp = caminho + ".tmp"
json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
os.chmod(tmp, 0o644)
os.replace(tmp, caminho)
PY
}

instalar_scripts_do_release() {  # copia os scripts confiáveis do release para o sistema
  local rel="$1"
  install -d -m 755 "$H360_LIB"
  install -m 644 "$rel/deploy/lib/comum.sh" "$H360_LIB/comum.sh"
  for s in "$rel"/deploy/sbin/*; do install -m 755 "$s" "/usr/local/sbin/$(basename "$s")"; done
  install -m 755 "$rel/deploy/bin/haras360" /usr/local/bin/haras360
  for u in "$rel"/deploy/systemd/*; do install -m 644 "$u" "/etc/systemd/system/$(basename "$u")"; done
  systemctl daemon-reload
}

# Caddy: o site do Haras360 fica em /etc/caddy/haras360.caddy. Um Caddyfile que não é do
# Haras360 (outra aplicação na VM) é preservado: ganha só a linha "import" e uma cópia de segurança.
configurar_caddy() {  # configurar_caddy <pasta-da-versão> <porta-pública> <porta-interna>
  local dest="$1" porta="$2" porta_app="$3" cf=/etc/caddy/Caddyfile copia
  install -d -m 755 /etc/caddy
  install -d -m 755 -o caddy -g caddy /var/log/caddy 2>/dev/null || install -d -m 755 /var/log/caddy
  sed -e "s/__PORTA__/$porta/" -e "s/__PORTA_APP__/$porta_app/" "$dest/deploy/caddy/haras360.caddy.modelo" > /etc/caddy/haras360.caddy
  # Caddyfile vazio, do Haras360 ou o exemplo que vem com o pacote do Caddy (site em /usr/share/caddy): pode substituir.
  if [ ! -s "$cf" ] || grep -q "Haras360 · gerado pelo instalador" "$cf" || { grep -q "root \* /usr/share/caddy" "$cf" && [ "$(grep -cvE '^\s*(#|$)' "$cf")" -le 6 ]; }; then
    cp "$dest/deploy/caddy/Caddyfile.modelo" "$cf"
  elif ! grep -qE '^\s*import\s+/etc/caddy/haras360\.caddy' "$cf"; then
    copia="$cf.antes-haras360-$(date +%Y%m%d-%H%M%S)"
    cp -a "$cf" "$copia"
    printf '\n# Haras360 (acrescentado pelo instalador; cópia do original em %s)\nimport /etc/caddy/haras360.caddy\n' "$copia" >> "$cf"
    aviso "O Caddy já tinha outra configuração: ela foi mantida e ganhou só a linha 'import /etc/caddy/haras360.caddy' (cópia em $copia)."
  fi
  if command -v caddy >/dev/null && ! caddy validate --config "$cf" --adapter caddyfile >/dev/null 2>&1; then
    [ -n "${copia:-}" ] && cp -a "$copia" "$cf"
    caddy validate --config "$cf" --adapter caddyfile || true
    falha "A configuração do Caddy ficou inválida e foi desfeita. Veja a mensagem acima."
  fi
  # A validação roda como root e pode criar o arquivo de log; o Caddy grava como usuário caddy.
  chown -R caddy:caddy /var/log/caddy 2>/dev/null || true
}
