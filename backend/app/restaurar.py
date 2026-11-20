"""Restaura um backup gerado por app.backup_db (lê o SQL da entrada padrão).

Uso: gunzip -c backups/banco-AAAAMMDD-HHMM.sql.gz | docker compose exec -T haras360 python -m app.restaurar
"""
import sys

from .backup_db import conectar


def main():
    con = conectar()
    n = 0
    with con.cursor() as c:
        for linha in sys.stdin:
            linha = linha.rstrip("\n")
            if not linha or linha.startswith("--"):
                continue
            c.execute(linha[:-1] if linha.endswith(";") else linha)
            n += 1
    con.commit()
    con.close()
    print(f"Restauração concluída: {n} instruções executadas.")


if __name__ == "__main__":
    main()
