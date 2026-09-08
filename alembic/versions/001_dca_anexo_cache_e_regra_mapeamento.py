"""dca_anexo_cache e dca_regra_mapeamento — primeira revisão da DCA.

Duas tabelas, para os **oito** anexos. O RGF tem seis `rgf_anexo0N_cache` e o RREO nove
`rreo_anexo*_cache`; aqui `anexo` é coluna, e o registry é a lista fechada que a valida (P-D1).

Nenhum objeto de outro pipeline é criado, alterado ou removido — verificado por
`tests/pipeline/test_infra.py::test_migracao_em_banco_que_ja_tem_os_irmaos`, que varre o código
desta revisão.

Revision ID: 001_dca_cache
Revises: None — histórico próprio, sem encadear no RREO/RGF (design.md § 4).
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "001_dca_cache"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dca_anexo_cache",
        sa.Column("id_ente", sa.String(20), primary_key=True),
        sa.Column("an_referencia", sa.SmallInteger, primary_key=True),
        sa.Column("anexo", sa.String(20), primary_key=True),
        sa.Column("resultado", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ok"),
        sa.Column("calculado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("duracao_ms", sa.Integer),
        sa.Column("versao_api", sa.String(20)),
        # As três que os irmãos não têm: invalidação por regra, explicação e diagnóstico.
        sa.Column("versao_regras", sa.String(64)),
        sa.Column("procedencia", postgresql.JSONB),
        sa.Column("diagnostico", postgresql.JSONB),
        sa.Column("erro_detalhe", sa.Text),
        sa.Column("solicitado_por", sa.Integer),
        sa.CheckConstraint("status = ANY (ARRAY['ok','processando','erro'])",
                           name="chk_dca_anexo_cache_status"),
        sa.CheckConstraint("an_referencia BETWEEN 2000 AND 2100",
                           name="chk_dca_anexo_cache_exercicio"),
    )
    # O resumo agregado faz uma consulta por (ente, exercício) e projeta só metadados.
    op.create_index("ix_dca_anexo_cache_ente_exercicio", "dca_anexo_cache",
                    ["id_ente", "an_referencia"])
    op.create_index("ix_dca_anexo_cache_status", "dca_anexo_cache", ["status"])

    op.create_table(
        "dca_regra_mapeamento",
        sa.Column("anexo", sa.String(20), primary_key=True),
        sa.Column("ano_vigencia", sa.SmallInteger, primary_key=True),
        sa.Column("mes_vigencia", sa.SmallInteger, primary_key=True),
        sa.Column("versao", sa.String(40), nullable=False),
        sa.Column("linhas", postgresql.JSONB, nullable=False),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("criado_por_usuario_id", sa.Integer),
        sa.CheckConstraint("mes_vigencia BETWEEN 1 AND 12", name="chk_dca_regra_mes"),
        sa.CheckConstraint("origem = ANY (ARRAY['seed-yaml','api-admin'])",
                           name="chk_dca_regra_origem"),
    )
    # A resolução é "maior vigência <= competência pedida".
    op.create_index("ix_dca_regra_mapeamento_vigencia", "dca_regra_mapeamento",
                    ["anexo", "ano_vigencia", "mes_vigencia"])


def downgrade() -> None:
    op.drop_index("ix_dca_regra_mapeamento_vigencia", table_name="dca_regra_mapeamento")
    op.drop_table("dca_regra_mapeamento")
    op.drop_index("ix_dca_anexo_cache_status", table_name="dca_anexo_cache")
    op.drop_index("ix_dca_anexo_cache_ente_exercicio", table_name="dca_anexo_cache")
    op.drop_table("dca_anexo_cache")
