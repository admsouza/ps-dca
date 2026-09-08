"""Alembic da DCA num schema compartilhado com RREO e RGF.

Três decisões, todas de convivência (`design.md` § 4):

1. **`version_table="alembic_version_dca"`**, offline e online, com a guarda de
   `app/core/migrations.py`: se o marcador da DCA aparecer na tabela genérica, aborta — é sintoma
   de `alembic upgrade` rodado com config sem `version_table`, e seguir sobrescreveria o histórico
   de outro projeto.
2. **Advisory lock `43812/1001`**, o mesmo dos irmãos. Compartilhar a chave serializa migrations
   entre projetos, não só entre réplicas.
3. **Histórico próprio.** O RGF encadeia sobre um stub do RREO; a DCA não encadeia — encadear
   acopla o deploy dos três, e o advisory lock já resolve a concorrência.
"""
from __future__ import annotations

import logging
from logging.config import fileConfig

from sqlalchemy import inspect, text

from alembic import context
from app.core.config import config as app_config
from app.core.database import Base, engine
from app.core.migrations import LOCK, TABELA_DE_VERSAO, verificar_tabela_de_versao
from app.infra.cache import modelo  # noqa: F401 - registra os models no metadata

configuracao = context.config
if configuracao.config_file_name is not None:
    fileConfig(configuracao.config_file_name)

logger = logging.getLogger("alembic.env")
metadata_alvo = Base.metadata


class _InspetorSQLAlchemy:
    """Adapta o inspetor do SQLAlchemy à porta que a guarda espera."""

    def __init__(self, conexao) -> None:
        self._conexao = conexao
        self._inspetor = inspect(conexao)

    def tem_tabela(self, nome: str) -> bool:
        return self._inspetor.has_table(nome)

    def versao_em(self, nome: str) -> str | None:
        if not self.tem_tabela(nome):
            return None
        linha = self._conexao.execute(text(f"SELECT version_num FROM {nome} LIMIT 1")).first()  # noqa: S608
        return linha[0] if linha else None


def _incluir_objeto(objeto, nome, tipo, reflexivo, comparado):
    """Autogenerate só vê o que é da DCA.

    Sem isto, um `--autogenerate` proporia `DROP TABLE` para as 44 tabelas de RREO e RGF, que não
    estão no metadata da DCA.
    """
    if tipo == "table":
        return bool(nome and nome.startswith("dca_"))
    return True


def migrar_offline() -> None:
    context.configure(
        url=app_config().database_url,
        target_metadata=metadata_alvo,
        literal_binds=True,
        version_table=TABELA_DE_VERSAO,
        include_object=_incluir_objeto,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def migrar_online() -> None:
    classe, chave = LOCK
    timeout = app_config().alembic_lock_timeout

    with engine().connect() as conexao:
        verificar_tabela_de_versao(_InspetorSQLAlchemy(conexao))

        conexao.execute(text(f"SET lock_timeout = '{timeout}s'"))
        conexao.execute(text("SELECT pg_advisory_lock(:classe, :chave)"),
                        {"classe": classe, "chave": chave})
        logger.info("advisory lock %s/%s adquirido — migrations serializadas entre projetos",
                    classe, chave)
        try:
            context.configure(
                connection=conexao,
                target_metadata=metadata_alvo,
                version_table=TABELA_DE_VERSAO,
                include_object=_incluir_objeto,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
        finally:
            conexao.execute(text("SELECT pg_advisory_unlock(:classe, :chave)"),
                            {"classe": classe, "chave": chave})
            conexao.commit()


if context.is_offline_mode():
    migrar_offline()
else:
    migrar_online()
