"""Banco de dados e modelos do Haras360.

Regra das migrações: o esquema só cresce (tabelas e colunas novas), para a
versão anterior continuar funcionando se uma atualização precisar voltar.
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import DB_URL

_kw = {"pool_pre_ping": True, "pool_recycle": 3600, "pool_size": 5, "max_overflow": 5}
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
    plano: Mapped[str] = mapped_column(String(60), default="Padrão")
    logo: Mapped[str] = mapped_column(String(80), nullable=True)  # arquivo em compartilhado/logos
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    haras_id: Mapped[int] = mapped_column(ForeignKey("haras.id"), index=True, nullable=True)  # nulo para o administrador
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(100))
    perfil: Mapped[str] = mapped_column(String(20))  # admin | gestor | operador
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    totp_segredo: Mapped[str] = mapped_column(String(64), nullable=True)
    totp_ativo: Mapped[bool] = mapped_column(Boolean, default=False)
    recuperacao: Mapped[list] = mapped_column(JSON, nullable=True)  # hashes dos códigos de recuperação
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Sessao(Base):
    __tablename__ = "sessoes"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    publico: Mapped[str] = mapped_column(String(16), unique=True)  # identificador exibido e usado para encerrar
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    etapa: Mapped[str] = mapped_column(String(16), default="ok")  # ok | 2fa | cadastro2fa
    tipo: Mapped[str] = mapped_column(String(10), default="web")  # web | app
    ip: Mapped[str] = mapped_column(String(64), default="")
    agente: Mapped[str] = mapped_column(String(200), default="")
    criada_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    ultimo_uso: Mapped[datetime] = mapped_column(DateTime, default=agora)
    expira_em: Mapped[datetime] = mapped_column(DateTime)
    revogada: Mapped[bool] = mapped_column(Boolean, default=False)


class Auditoria(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quando: Mapped[datetime] = mapped_column(DateTime, default=agora, index=True)
    haras_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    usuario_id: Mapped[int] = mapped_column(Integer, nullable=True)
    usuario: Mapped[str] = mapped_column(String(160), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    acao: Mapped[str] = mapped_column(String(40), index=True)
    alvo: Mapped[str] = mapped_column(String(200), default="")
    resultado: Mapped[str] = mapped_column(String(10), default="ok")  # ok | falha
    detalhe: Mapped[dict] = mapped_column(JSON, nullable=True)


class Parametro(Base):
    __tablename__ = "parametros"
    escopo: Mapped[str] = mapped_column(String(20), primary_key=True)  # global | haras:<id>
    chave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[dict] = mapped_column(JSON, nullable=True)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora, onupdate=agora)


class SchemaVersao(Base):
    __tablename__ = "schema_versao"
    versao: Mapped[int] = mapped_column(Integer, primary_key=True)
    descricao: Mapped[str] = mapped_column(String(200), default="")
    aplicada_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


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
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
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
