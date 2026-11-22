"""Banco de dados e modelos do Haras360.

Regra das migrações: o esquema só cresce (tabelas e colunas novas), para a
versão anterior continuar funcionando se uma atualização precisar voltar.
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
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
    # Baixa do plantel (v1.4.0): venda, morte, doação ou transferência
    baixa_data: Mapped[object] = mapped_column(Date, nullable=True)
    baixa_motivo: Mapped[str] = mapped_column(String(20), nullable=True)
    baixa_destino: Mapped[str] = mapped_column(String(160), nullable=True)
    baixa_obs: Mapped[str] = mapped_column(Text, nullable=True)
    # v1.6.0: dados do certificado de registro (volume, página, datas, criador, proprietário, mensurações, PDF guardado)
    certificado: Mapped[dict] = mapped_column(JSON, nullable=True)
    # v1.6.0: animal de fora do haras (garanhão ou égua de terceiros): fora do plantel, do limite e da agenda
    externo: Mapped[bool] = mapped_column(Boolean, default=False)
    contato: Mapped[dict] = mapped_column(JSON, nullable=True)  # externo: proprietário, telefone, e-mail, observação


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


class VinculoApp(Base):
    """Código de uso único, lido por QR Code, que vincula um celular ao caseiro (v1.1.0)."""
    __tablename__ = "vinculos_app"
    codigo_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    haras_id: Mapped[int] = mapped_column(Integer, index=True)
    criado_por: Mapped[int] = mapped_column(Integer, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    expira_em: Mapped[datetime] = mapped_column(DateTime)
    usado_em: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class Audio(Base):
    """Áudio gravado no app do caseiro, um por registro (v1.2.0)."""
    __tablename__ = "audios"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    registro_id: Mapped[str] = mapped_column(ForeignKey("registros.id", ondelete="CASCADE"), unique=True)
    haras_id: Mapped[int] = mapped_column(Integer, index=True)
    arquivo: Mapped[str] = mapped_column(String(60))
    duracao: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class ImagemMarca(Base):
    """Imagem de personalização (v1.3.0): da plataforma (haras_id nulo) ou de um haras."""
    __tablename__ = "imagens_marca"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    haras_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    arquivo: Mapped[str] = mapped_column(String(80))
    foco: Mapped[str] = mapped_column(String(10), default="centro")
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Comprador(Base):
    """Comprador de animais (v1.6.0), reutilizável entre vendas. CPF ou CNPJ cifrado; só o gestor vê."""
    __tablename__ = "compradores"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    haras_id: Mapped[int] = mapped_column(Integer, index=True)
    nome: Mapped[str] = mapped_column(String(160))
    documento: Mapped[str] = mapped_column(Text, nullable=True)  # cifrado (Fernet)
    documento_mascara: Mapped[str] = mapped_column(String(24), default="")
    cadastro_abccmm: Mapped[str] = mapped_column(String(20), default="")
    telefone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    cidade: Mapped[str] = mapped_column(String(80), default="")
    uf: Mapped[str] = mapped_column(String(2), default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Venda(Base):
    """Venda de um animal (v1.6.0): nasce da baixa por venda."""
    __tablename__ = "vendas"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    haras_id: Mapped[int] = mapped_column(Integer, index=True)
    animal_id: Mapped[str] = mapped_column(String(24), index=True)
    comprador_id: Mapped[str] = mapped_column(String(24), index=True)
    data: Mapped[object] = mapped_column(Date)
    valor_total: Mapped[int] = mapped_column(Integer)  # em centavos
    forma: Mapped[str] = mapped_column(String(12))  # avista ou parcelado
    meio: Mapped[str] = mapped_column(String(20), default="")
    transferencia_em: Mapped[object] = mapped_column(Date, nullable=True)  # comunicação da transferência na ABCCMM
    obs: Mapped[str] = mapped_column(Text, default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Parcela(Base):
    """Parcela de uma venda (número 0 = entrada; à vista = uma parcela)."""
    __tablename__ = "parcelas"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    venda_id: Mapped[str] = mapped_column(ForeignKey("vendas.id", ondelete="CASCADE"), index=True)
    numero: Mapped[int] = mapped_column(Integer)
    vencimento: Mapped[object] = mapped_column(Date)
    valor: Mapped[int] = mapped_column(Integer)  # centavos
    pago_em: Mapped[object] = mapped_column(Date, nullable=True)
    valor_pago: Mapped[int] = mapped_column(Integer, nullable=True)
    meio_pago: Mapped[str] = mapped_column(String(20), default="")
    obs: Mapped[str] = mapped_column(String(300), default="")


class Cliente(Base):
    """Contratante de um haras na plataforma (v1.7.0): contrato, dados de cobrança e ajuste de preço."""
    __tablename__ = "clientes"
    haras_id: Mapped[int] = mapped_column(ForeignKey("haras.id", ondelete="CASCADE"), primary_key=True)
    situacao: Mapped[str] = mapped_column(String(12), default="Teste")  # Teste | Ativo | Suspenso | Cancelado
    inicio: Mapped[object] = mapped_column(Date, nullable=True)
    teste_ate: Mapped[object] = mapped_column(Date, nullable=True)
    dia_vencimento: Mapped[int] = mapped_column(Integer, default=10)
    nome: Mapped[str] = mapped_column(String(160), default="")
    documento: Mapped[str] = mapped_column(Text, nullable=True)  # CPF ou CNPJ cifrado
    documento_mascara: Mapped[str] = mapped_column(String(24), default="")
    contato_nome: Mapped[str] = mapped_column(String(120), default="")
    contato_email: Mapped[str] = mapped_column(String(160), default="")
    contato_telefone: Mapped[str] = mapped_column(String(40), default="")
    endereco: Mapped[dict] = mapped_column(JSON, nullable=True)
    ajuste_tipo: Mapped[str] = mapped_column(String(10), default="nenhum")  # nenhum | desconto | fixo
    ajuste_valor: Mapped[int] = mapped_column(Integer, default=0)  # desconto em % ou valor fixo em centavos
    ajuste_ate: Mapped[object] = mapped_column(Date, nullable=True)
    liberado_ate: Mapped[object] = mapped_column(Date, nullable=True)
    liberado_motivo: Mapped[str] = mapped_column(String(300), default="")
    cancelado_em: Mapped[object] = mapped_column(Date, nullable=True)
    obs: Mapped[str] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)


class Cobranca(Base):
    """Mensalidade (uma por haras e mês de competência) ou cobrança avulsa, em centavos (v1.7.0)."""
    __tablename__ = "cobrancas"
    __table_args__ = (UniqueConstraint("haras_id", "competencia", name="uq_cobranca_mes"),)
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    haras_id: Mapped[int] = mapped_column(ForeignKey("haras.id", ondelete="CASCADE"), index=True)
    competencia: Mapped[str] = mapped_column(String(7), nullable=True)  # AAAA-MM; nula na avulsa
    descricao: Mapped[str] = mapped_column(String(160), default="")
    vencimento: Mapped[object] = mapped_column(Date)
    valor: Mapped[int] = mapped_column(Integer)
    calculo: Mapped[dict] = mapped_column(JSON, nullable=True)
    pago_em: Mapped[object] = mapped_column(Date, nullable=True)
    valor_pago: Mapped[int] = mapped_column(Integer, nullable=True)
    meio_pago: Mapped[str] = mapped_column(String(20), default="")
    obs: Mapped[str] = mapped_column(String(300), default="")
    cancelada_em: Mapped[object] = mapped_column(Date, nullable=True)
    motivo_cancelamento: Mapped[str] = mapped_column(String(300), default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
