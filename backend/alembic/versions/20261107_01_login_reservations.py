"""Add account identity and admission leases while preserving login history."""
from alembic import op
import sqlalchemy as sa

revision = "20261107_01"
down_revision = "20261031_01"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable identity preserves legacy rows; false default marks completed history.
    op.add_column("login_attempts", sa.Column("account_key", sa.String(64), nullable=True))
    op.add_column("login_attempts", sa.Column("em_andamento", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("login_attempts", sa.Column("expira_em", sa.DateTime(), nullable=True))
    op.create_index("ix_login_attempts_account_rota_ocorrido", "login_attempts", ["account_key", "rota", "ocorrido_em"])


def downgrade():
    # Dropping these columns would discard security history/live reservations.
    # Follow the repository's forward-only recovery policy without touching data.
    raise RuntimeError("Downgrade is disabled; use a forward-only recovery")
