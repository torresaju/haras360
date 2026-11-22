"""Migrações numeradas do banco do Haras360.

Cada migração é aplicada uma única vez e registrada em `schema_versao`.
Regra: somente acréscimos (tabela nova, coluna nova com valor padrão, índice).
Nunca apagar ou renomear, para que a versão anterior siga funcionando após um rollback.

Uso: python -m app.migracoes
"""
import time

from sqlalchemy import inspect, select, text
from sqlalchemy.exc import OperationalError

from .db import Audio, Base, Cliente, Cobranca, Comprador, ImagemMarca, Parcela, SchemaVersao, SessionLocal, Venda, VinculoApp, engine


def _m001_base(conn):
    """Esquema inicial da v1.0.0."""
    Base.metadata.create_all(conn)


def _m002_vinculo_app(conn):
    """v1.1.0: códigos de vínculo do app Android por QR Code."""
    VinculoApp.__table__.create(conn, checkfirst=True)


def _m003_audios(conn):
    """v1.2.0: áudios dos registros do caseiro."""
    Audio.__table__.create(conn, checkfirst=True)


def _m004_imagens(conn):
    """v1.3.0: logotipo e imagens da plataforma e de cada haras."""
    ImagemMarca.__table__.create(conn, checkfirst=True)


def _m005_baixa(conn):
    """v1.4.0: baixa de animais do plantel (data, motivo, destino e observação)."""
    existentes = {c["name"] for c in inspect(conn).get_columns("animais")}
    for nome, tipo in (("baixa_data", "DATE"), ("baixa_motivo", "VARCHAR(20)"), ("baixa_destino", "VARCHAR(160)"), ("baixa_obs", "TEXT")):
        if nome not in existentes:
            conn.execute(text(f"ALTER TABLE animais ADD COLUMN {nome} {tipo} NULL"))


def _m006_certificado_externos_vendas(conn):
    """v1.6.0: dados do certificado e animais externos; compradores, vendas e parcelas."""
    existentes = {c["name"] for c in inspect(conn).get_columns("animais")}
    for nome, tipo in (("certificado", "JSON"), ("externo", "BOOLEAN"), ("contato", "JSON")):
        if nome not in existentes:
            conn.execute(text(f"ALTER TABLE animais ADD COLUMN {nome} {tipo} NULL"))
    conn.execute(text("UPDATE animais SET externo = 0 WHERE externo IS NULL"))
    for tb in (Comprador, Venda, Parcela):
        tb.__table__.create(conn, checkfirst=True)


def _m007_financeiro(conn):
    """v1.7.0: clientes (contratantes) e cobranças das mensalidades da plataforma."""
    for tb in (Cliente, Cobranca):
        tb.__table__.create(conn, checkfirst=True)


# (número, descrição, função). Acrescente novas migrações ao final.
MIGRACOES = [
    (1, "Esquema inicial da v1.0.0", _m001_base),
    (2, "Vínculo do app Android por QR Code (v1.1.0)", _m002_vinculo_app),
    (3, "Áudios dos registros (v1.2.0)", _m003_audios),
    (4, "Logotipo e imagens da plataforma e dos haras (v1.3.0)", _m004_imagens),
    (5, "Baixa de animais do plantel (v1.4.0)", _m005_baixa),
    (6, "Certificado, animais externos e vendas (v1.6.0)", _m006_certificado_externos_vendas),
    (7, "Financeiro da plataforma: clientes e mensalidades (v1.7.0)", _m007_financeiro),
]


def aguardar_banco(tentativas=30):
    for i in range(tentativas):
        try:
            with engine.connect():
                return
        except OperationalError as e:
            if i == tentativas - 1:
                raise
            print(f"Aguardando o banco de dados ({i + 1}/{tentativas}): {str(e.orig)[:160] if getattr(e, 'orig', None) else e.__class__.__name__}", flush=True)
            time.sleep(2)


def migrar(silencioso=False):
    aguardar_banco()
    if "schema_versao" not in inspect(engine).get_table_names():
        SchemaVersao.__table__.create(engine)
    with SessionLocal() as db:
        aplicadas = set(db.scalars(select(SchemaVersao.versao)))
    novas = []
    for num, desc, fn in MIGRACOES:
        if num in aplicadas:
            continue
        with engine.begin() as conn:
            fn(conn)
        with SessionLocal() as db:
            db.add(SchemaVersao(versao=num, descricao=desc))
            db.commit()
        novas.append(num)
        if not silencioso:
            print(f"Migração {num:03d} aplicada: {desc}")
    if not silencioso and not novas:
        print("Banco já está atualizado.")
    return novas


def versao_banco():
    with SessionLocal() as db:
        return db.scalar(select(SchemaVersao.versao).order_by(SchemaVersao.versao.desc()).limit(1)) or 0


if __name__ == "__main__":
    migrar()
