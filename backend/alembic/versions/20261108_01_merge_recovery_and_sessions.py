"""Join recovery admission and session security without changing data or DDL."""

revision = "20261108_01"
down_revision = ("20261103_01", "20261107_02")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise RuntimeError("Downgrade is disabled for recovery and session security integration; use forward-only recovery.")
