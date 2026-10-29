"""Add append-only audit event storage."""
from alembic import op
import sqlalchemy as sa

revision = "20261029_03"
down_revision = "20261029_02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("ator_role", sa.String(32), nullable=True),
        sa.Column("acao", sa.String(100), nullable=False),
        sa.Column("entidade", sa.String(100), nullable=False),
        sa.Column("entidade_id", sa.String(100), nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("resultado", sa.String(32), nullable=False),
        sa.Column("detalhes", sa.JSON(), nullable=False),
        sa.Column("ocorrido_em", sa.DateTime(), nullable=False),
    )
    for name, columns in (
        ("ix_audit_logs_usuario_id", ["usuario_id"]),
        ("ix_audit_logs_acao", ["acao"]),
        ("ix_audit_logs_ocorrido_em", ["ocorrido_em"]),
        ("ix_audit_logs_usuario_ocorrido", ["usuario_id", "ocorrido_em"]),
        ("ix_audit_logs_acao_ocorrido", ["acao", "ocorrido_em"]),
    ):
        op.create_index(name, "audit_logs", columns)


def downgrade():
    raise RuntimeError("Downgrade is disabled because it would delete audit history.")
