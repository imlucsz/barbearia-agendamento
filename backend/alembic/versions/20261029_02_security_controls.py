"""Persisted authentication rate-limit history."""
from alembic import op
import sqlalchemy as sa

revision = "20261029_02"
down_revision = "20261029_01"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("rota", sa.String(length=80), nullable=False),
        sa.Column("sucesso", sa.Boolean(), nullable=False),
        sa.Column("ocorrido_em", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_login_attempts_ip", "login_attempts", ["ip"])
    op.create_index("ix_login_attempts_ocorrido_em", "login_attempts", ["ocorrido_em"])
    op.create_index("ix_login_attempts_ip_rota_ocorrido_em", "login_attempts", ["ip", "rota", "ocorrido_em"])

def downgrade():
    raise RuntimeError("Downgrade is disabled because it would delete authentication security history.")
