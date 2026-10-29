"""Allow unlinking consent and revoked sessions during subject erasure."""
from alembic import op
import sqlalchemy as sa

revision = "20261029_04"
down_revision = "20261029_03"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("consentimentos_lgpd") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("ip_origem", existing_type=sa.String(length=45), nullable=True)
    with op.batch_alter_table("refresh_tokens") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=True)


def downgrade():
    raise RuntimeError("Downgrade is disabled because it could restore identifying links to erased accounts.")
