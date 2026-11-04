"""Add shared password recovery admission limits without changing existing rows."""
from alembic import op
import sqlalchemy as sa

revision = "20261103_01"
down_revision = "20261031_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "password_reset_limits",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("window_started_at", sa.DateTime(), nullable=False),
        sa.Column("requests", sa.Integer(), nullable=False),
        sa.Column("next_allowed_at", sa.DateTime(), nullable=False),
        sa.Column("lease_until", sa.DateTime(), nullable=False),
        sa.Column("reservation", sa.String(64), nullable=True),
    )
    op.create_index("ix_password_reset_limits_window_started_at", "password_reset_limits", ["window_started_at"])


def downgrade():
    # Never silently discard active security limits, even on a manual rollback.
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        connection.execute(sa.text("SET LOCAL lock_timeout = '5s'"))
        connection.execute(sa.text("LOCK TABLE password_reset_limits IN ACCESS EXCLUSIVE MODE"))
    elif connection.dialect.name == "sqlite" and not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    if connection.execute(sa.text("SELECT 1 FROM password_reset_limits LIMIT 1")).first():
        raise RuntimeError("Downgrade requires an empty password_reset_limits table; active limits must be preserved.")
    op.drop_index("ix_password_reset_limits_window_started_at", table_name="password_reset_limits")
    op.drop_table("password_reset_limits")
