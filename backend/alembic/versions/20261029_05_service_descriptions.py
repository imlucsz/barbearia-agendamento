"""Add public service descriptions for RF01."""
from alembic import op
import sqlalchemy as sa

revision = "20261029_05"
down_revision = "20261029_04"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("services", sa.Column("descricao", sa.String(length=500), nullable=True))


def downgrade():
    raise RuntimeError("Downgrade is disabled because it would discard service descriptions.")
