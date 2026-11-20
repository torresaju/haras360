"""Configuração, banco de dados e modelos do Haras360."""
import os
import time
from datetime import datetime

from sqlalchemy import (JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, create_engine)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_URL = os.environ.get("DB_URL", "sqlite:///./haras360.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
FOTOS_DIR = os.environ.get("FOTOS_DIR", "./dados/fotos")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
LIMITE_ANIMAIS = int(os.environ.get("LIMITE_ANIMAIS", "30"))

if not SECRET_KEY:
    raise SystemExit("SECRET_KEY não definida. Rode o install.sh ou configure o arquivo .env.")

_kw = {"pool_pre_ping": True, "pool_recycle": 3600}
if DB_URL.startswith("sqlite"):
    _kw = {"connect_args": {"check_same_thread": False}}
engine = create_engine(DB_URL, **_kw)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def agora():
    return datetime.now()


class Base(DeclarativeBase):
    pass


class Haras(Base):
    __tablename__ = "haras"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120))
    proprietario: Mapped[str] = mapped_column(String(120), default="")
    municipio: Mapped[str] = mapped_column(String(120), default="")
    raiva_semestral: Mapped[bool] = mapped_column(Boolean, default=False)
    associado_abccmm: Mapped[str] = mapped_column(String(160), default="")
    notif_prefs: Mapped[dict] = mapped_column(JSON, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    haras_id: Mapped[int] = mapped_column(ForeignKey("haras.id"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(100))
    perfil: Mapped[str] = mapped_column(String(20))  # gestor | operador
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Animal(Base):
    __tablename__ = "animais"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    haras_id: Mapped[int] = mapped_column(ForeignKey("haras.id"), index=True)
    nome: Mapped[str] = mapped_column(String(160))
    livro: Mapped[str] = mapped_column(String(120), default="")
    registro: Mapped[str] = mapped_column(String(20), default="", index=True)
    sexo: Mapped[str] = mapped_column(String(1))
    bloqueado: Mapped[bool] = mapped_column(Boolean, default=False)
    vivo: Mapped[bool] = mapped_column(Boolean, default=True)
    dna: Mapped[str] = mapped_column(String(40), default="")
    nascimento: Mapped[object] = mapped_column(Date, nullable=True)
    chip: Mapped[str] = mapped_column(String(30), default="")
    pelagem: Mapped[str] = mapped_column(String(60), default="")
    genealogia: Mapped[dict] = mapped_column(JSON, nullable=True)
    origem: Mapped[str] = mapped_column(String(40), default="Cadastro manual")
    importado_em: Mapped[object] = mapped_column(Date, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Registro(Base):
    __tablename__ = "registros"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    haras_id: Mapped[int] = mapped_column(ForeignKey("haras.id"), index=True)
    animal_id: Mapped[str] = mapped_column(ForeignKey("animais.id", ondelete="CASCADE"), index=True)
    data: Mapped[object] = mapped_column(Date)
    tipo: Mapped[str] = mapped_column(String(20))
    protocolos: Mapped[list] = mapped_column(JSON, nullable=True)
    dose: Mapped[str] = mapped_column(String(10), default="unica")
    obs: Mapped[str] = mapped_column(Text, nullable=True)
    dados: Mapped[dict] = mapped_column(JSON, nullable=True)
    autor: Mapped[str] = mapped_column(String(120), default="")
    autor_id: Mapped[int] = mapped_column(Integer, nullable=True)
    origem: Mapped[str] = mapped_column(String(30), default="Portal Gestor")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Foto(Base):
    __tablename__ = "fotos"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    registro_id: Mapped[str] = mapped_column(ForeignKey("registros.id", ondelete="CASCADE"), index=True)
    haras_id: Mapped[int] = mapped_column(Integer, index=True)
    arquivo: Mapped[str] = mapped_column(String(80))
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Protocolo(Base):
    __tablename__ = "protocolos"
    haras_id: Mapped[int] = mapped_column(ForeignKey("haras.id"), primary_key=True)
    pid: Mapped[str] = mapped_column(String(20), primary_key=True)
    dados: Mapped[dict] = mapped_column(JSON)


class NotifLida(Base):
    __tablename__ = "notif_lidas"
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    nid: Mapped[str] = mapped_column(String(190), primary_key=True)
    lida_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Importacao(Base):
    __tablename__ = "importacoes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    haras_id: Mapped[int] = mapped_column(ForeignKey("haras.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(Integer)
    arquivo: Mapped[str] = mapped_column(String(200), default="")
    associado: Mapped[str] = mapped_column(String(160), default="")
    impresso: Mapped[object] = mapped_column(Date, nullable=True)
    novos: Mapped[int] = mapped_column(Integer, default=0)
    atualizados: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


def iniciar_banco(tentativas=30):
    """Cria as tabelas, aguardando o MySQL ficar disponível."""
    for i in range(tentativas):
        try:
            Base.metadata.create_all(engine)
            return
        except OperationalError as e:
            if i == tentativas - 1:
                raise
            print(f"Aguardando o banco de dados ({i + 1}/{tentativas}): {e.__class__.__name__}", flush=True)
            time.sleep(2)
