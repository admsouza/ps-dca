"""Engine e sessão do Postgres compartilhado, para API e worker.

Mesma instância e mesmo schema `public` de RREO e RGF (P5). A separação da DCA é por prefixo
`dca_*` nas tabelas e por `alembic_version_dca` — **não** por schema.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import config


class Base(DeclarativeBase):
    """Base dos models da DCA. Só tabelas `dca_*` a herdam."""


_engine = None
_Sessao = None


def engine():
    """Engine única por processo. Pool próprio, menor que o do RREO na mesma instância."""
    global _engine
    if _engine is None:
        cfg = config()
        _engine = create_engine(
            cfg.database_url,
            pool_size=cfg.db_pool_size,
            max_overflow=cfg.db_max_overflow,
            pool_pre_ping=True,          # conexão morta por restart do banco não vira erro do job
            echo=cfg.db_echo,
            connect_args={"connect_timeout": cfg.db_connect_timeout},
        )
    return _engine


def sessao() -> Session:
    global _Sessao
    if _Sessao is None:
        _Sessao = sessionmaker(bind=engine(), autoflush=False, expire_on_commit=False)
    return _Sessao()


def obter_sessao():
    """Dependência do FastAPI. Fecha a sessão mesmo quando a rota levanta."""
    db = sessao()
    try:
        yield db
    finally:
        db.close()


def ping() -> bool:
    """Verificação de dependência para o startup do worker."""
    from sqlalchemy import text

    with engine().connect() as conexao:
        conexao.execute(text("SELECT 1"))
    return True
