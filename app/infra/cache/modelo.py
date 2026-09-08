"""Models do cache e do mapeamento vigente. **Uma tabela para os oito anexos** (P-D1).

O RGF tem `rgf_anexo01..06_cache` e o RREO nove `rreo_anexo*_cache` — seis services de cache quase
iguais, seis models, seis migrations. Aqui `anexo` é coluna, e o registry (`ANEXOS`) é a lista
fechada que a valida.

Três colunas que os irmãos não têm, e o motivo de cada uma:

- **`versao_regras`** — a regra da DCA vive em `knowledge/rules/**.yaml`, e uma correção de conta
  sem bump de código **tem** de invalidar o cache. Sem esta coluna, o ente receberia número velho.
- **`procedencia`** — explica uma divergência contra o STN sem reapurar.
- **`diagnostico`** — o que não fechou, legível sem acesso a log.

E três que a DCA dispensa (`tipo_poder`, `periodicidade`, `periodo_referencia`): a DCA é anual e
consolidada.
"""
from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, DateTime, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base

STATUS_CACHE = ("ok", "processando", "erro")

# Origem de uma vigência de mapeamento: semente versionada ou publicação administrativa.
ORIGENS_VIGENCIA = ("seed-yaml", "api-admin")


class StatusInvalido(ValueError):
    """Status fora de `STATUS_CACHE`. Recusado antes de chegar ao banco."""


def validar_status(status: str) -> str:
    """A mesma validação que o `CHECK` faz no banco, para falhar antes do `INSERT`."""
    if status not in STATUS_CACHE:
        raise StatusInvalido(
            f"status inválido: {status!r} — esperado um de {', '.join(STATUS_CACHE)}"
        )
    return status


class AnexoCache(Base):
    """`dca_anexo_cache` — resultado apurado por (ente, exercício, anexo)."""

    __tablename__ = "dca_anexo_cache"

    id_ente = Column(String(20), primary_key=True)
    an_referencia = Column(SmallInteger, primary_key=True)
    anexo = Column(String(20), primary_key=True)

    resultado = Column(JSONB, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default="ok")
    calculado_em = Column(DateTime(timezone=True), server_default=func.now())
    duracao_ms = Column(Integer)
    versao_api = Column(String(20))
    versao_regras = Column(String(64))
    procedencia = Column(JSONB)
    diagnostico = Column(JSONB)
    erro_detalhe = Column(Text)
    solicitado_por = Column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status = ANY (ARRAY['ok','processando','erro'])",
            name="chk_dca_anexo_cache_status",
        ),
        CheckConstraint("an_referencia BETWEEN 2000 AND 2100",
                        name="chk_dca_anexo_cache_exercicio"),
    )


class RegraMapeamento(Base):
    """`dca_regra_mapeamento` — vigências do mapeamento. **INSERT-only.**

    Corrigir é publicar nova vigência: não há `UPDATE` nem `DELETE`. Quem apurou com a vigência
    anterior tem de continuar podendo lê-la, ou nenhum resultado passado fica explicável.
    """

    __tablename__ = "dca_regra_mapeamento"

    anexo = Column(String(20), primary_key=True)
    ano_vigencia = Column(SmallInteger, primary_key=True)
    mes_vigencia = Column(SmallInteger, primary_key=True)

    versao = Column(String(40), nullable=False)
    linhas = Column(JSONB, nullable=False)
    origem = Column(String(20), nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    criado_por_usuario_id = Column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint("mes_vigencia BETWEEN 1 AND 12", name="chk_dca_regra_mes"),
        CheckConstraint(
            "origem = ANY (ARRAY['seed-yaml','api-admin'])",
            name="chk_dca_regra_origem",
        ),
    )
