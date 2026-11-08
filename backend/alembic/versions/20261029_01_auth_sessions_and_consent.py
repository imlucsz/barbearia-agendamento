"""Add versioned LGPD consent and rotating refresh token storage.

Revision ID: 20261029_01
Revises: 20261028_01
"""
from alembic import op
import sqlalchemy as sa


revision = "20261029_01"
down_revision = "20261028_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "consentimentos_lgpd",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("versao_termos", sa.String(length=100), nullable=False),
        sa.Column("aceito_em", sa.DateTime(), nullable=False),
        sa.Column("ip_origem", sa.String(length=45), nullable=False),
        sa.Column("origem", sa.String(length=255), nullable=False),
    )
    op.create_index("ix_consentimentos_lgpd_user_id", "consentimentos_lgpd", ["user_id"])
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("replaced_by_id", sa.Integer(), sa.ForeignKey("refresh_tokens.id"), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])


def downgrade():
    raise RuntimeError(
        "Downgrade is disabled because dropping consent or refresh-token history would delete data."
    )
