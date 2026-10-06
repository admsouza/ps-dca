"""versao_api passa a Text — cabe o sha256 do código da apuração.

A coluna era varchar(20) para a versão escrita à mão (`0.1.0`). O identificador agora é
o hash do fonte que produz a célula, 64 hex. TEXT remove o teto, como em versao_regras.

Revision ID: 003_versao_api_text
Revises: 002_versao_regras_text
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "003_versao_api_text"
down_revision = "002_versao_regras_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "dca_anexo_cache",
        "versao_api",
        existing_type=sa.String(20),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Hash de 64 caracteres não cabe de volta em 20. O downgrade só roda com o cache limpo.
    op.alter_column(
        "dca_anexo_cache",
        "versao_api",
        existing_type=sa.Text(),
        type_=sa.String(20),
        existing_nullable=True,
    )
