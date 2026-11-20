"""Cria o banco e o usuário do Haras360 no MySQL/MariaDB existente.

Executado pelo install.sh dentro de um container temporário. Lê tudo do ambiente
para que nenhuma senha apareça na linha de comando.
"""
import os
import sys

import pymysql


def main():
    e = os.environ
    nome = e.get("DB_NAME", "haras360")
    usuario = e.get("APP_USER", "haras360")
    senha = e["APP_PASS"]
    hosts = [h.strip() for h in e.get("APP_HOSTS", "%").split(",") if h.strip()]
    try:
        con = pymysql.connect(host=e["DB_HOST"], port=int(e.get("DB_PORT", "3306")), user=e["ADMIN_USER"], password=e["ADMIN_PASS"], autocommit=True, connect_timeout=10)
    except pymysql.err.OperationalError as err:
        sys.exit(f"Não foi possível conectar ao MySQL como {e['ADMIN_USER']}: {err.args[-1]}")
    with con.cursor() as c:
        c.execute("SELECT VERSION()")
        print(f"Conectado ao servidor {c.fetchone()[0]}")
        c.execute(f"CREATE DATABASE IF NOT EXISTS `{nome}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        for h in hosts:
            c.execute("CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s", (usuario, h, senha))
            c.execute("ALTER USER %s@%s IDENTIFIED BY %s", (usuario, h, senha))
            c.execute(f"GRANT ALL PRIVILEGES ON `{nome}`.* TO %s@%s", (usuario, h))
        c.execute("FLUSH PRIVILEGES")
    print(f"Banco '{nome}' e usuário '{usuario}' prontos (origens permitidas: {', '.join(hosts)}).")


if __name__ == "__main__":
    main()
