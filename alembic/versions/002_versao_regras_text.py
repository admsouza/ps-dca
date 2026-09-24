"""versao_regras passa a Text — cabe hash + identidade do pedido.

A coluna era varchar(64) para o sha256 das regras. O BF no pipeline acrescenta
`|BF:c12:manual:<16>` (e o mesmo padrão para outros parâmetros do pedido): o valor gravado
ultrapassa 64 e o Postgres recusa o UPDATE com StringDataRightTruncation. TEXT remove o teto
sem inventar outro limite.

Revision ID: 002_versao_regras_text
Revises: 001_dca_cache
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "002_versao_regras_text"
down_revision = "001_dca_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "dca_anexo_cache",
        "versao_regras",
        existing_type=sa.String(64),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Valores com sufixo de pedido não cabem de volta em 64. Truncar perderia a identidade —
    # o downgrade só roda em ambiente sem linhas manuais, ou depois de limpar o cache.
    op.alter_column(
        "dca_anexo_cache",
        "versao_regras",
        existing_type=sa.Text(),
        type_=sa.String(64),
        existing_nullable=True,
    )
