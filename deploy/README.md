# Implantação

Reservado para a versão v1.0.0 (branch `etapa/1.0-vps`), conforme `docs/ESPECIFICACAO.md`, Fases 2 e 3:

* `instalar-servidor.sh`: primeira instalação em VM nova (swap, MariaDB, Caddy, serviço systemd, primeiro administrador)
* `gerar-pacote.sh` e `assinar-pacote.py`: pacote `haras360-X.Y.Z.tar.gz` assinado com Ed25519
* `haras360-update.sh`: atualização com backup, migrações, verificação de saúde e rollback automático

Até lá, a instalação de outubro com Docker continua em `backend/` (ver `backend/INSTALACAO-DOCKER.md`). Ela será substituída na v1.0.0.
