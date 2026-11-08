"""Distinguish credential rejection from neutral login outcomes, without backfill."""
from alembic import op
import sqlalchemy as sa

revision = "20261107_02"
down_revision = "20261107_01"
branch_labels = None
depends_on = None


def upgrade():
    # NULL explicitly identifies legacy binary history, including old writers.
    # Existing rows, defaults, and indexes are left untouched.
    op.add_column("login_attempts", sa.Column("resultado", sa.String(24), nullable=True))
    op.add_column("login_attempts", sa.Column("motivo_finalizacao", sa.String(40), nullable=True))


def downgrade():
    raise RuntimeError("Downgrade is disabled; use a forward-only recovery")
