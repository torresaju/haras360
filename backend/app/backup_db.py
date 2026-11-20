"""Exporta o banco do Haras360 em SQL (uma instrução por linha), sem depender do mysqldump.

Uso: python -m app.backup_db > banco.sql
"""
import datetime
import decimal
import os
import sys

import pymysql
from sqlalchemy.engine import make_url


def conectar():
    u = make_url(os.environ["DB_URL"])
    return pymysql.connect(host=u.host, port=u.port or 3306, user=u.username, password=u.password, database=u.database, charset="utf8mb4")


def main():
    con = conectar()

    def lit(v):
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "1" if v else "0"
        if isinstance(v, (int, float, decimal.Decimal)):
            return str(v)
        if isinstance(v, (datetime.datetime, datetime.date, datetime.time, datetime.timedelta)):
            return "'" + str(v) + "'"
        if isinstance(v, (bytes, bytearray)):
            return "0x" + bytes(v).hex() if v else "''"
        return con.escape(str(v))

    out = sys.stdout
    out.write(f"-- Haras360 backup {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n")
    out.write("SET FOREIGN_KEY_CHECKS=0;\nSET NAMES utf8mb4;\n")
    with con.cursor() as c:
        c.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
        tabelas = [r[0] for r in c.fetchall()]
        for t in tabelas:
            c.execute(f"SHOW CREATE TABLE `{t}`")
            ddl = c.fetchone()[1].replace("\n", " ")
            out.write(f"DROP TABLE IF EXISTS `{t}`;\n{ddl};\n")
            c.execute(f"SELECT * FROM `{t}`")
            cols = ", ".join(f"`{d[0]}`" for d in c.description)
            for row in c.fetchall():
                out.write(f"INSERT INTO `{t}` ({cols}) VALUES (" + ", ".join(lit(v) for v in row) + ");\n")
    out.write("SET FOREIGN_KEY_CHECKS=1;\n")
    con.close()


if __name__ == "__main__":
    main()
