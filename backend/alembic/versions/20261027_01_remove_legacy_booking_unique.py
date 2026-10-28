"""Remove the legacy global appointment uniqueness constraint.

Revision ID: 20261027_01
Revises:
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa


revision = "20261027_01"
down_revision = None
branch_labels = None
depends_on = None


TABLE_NAME = "appointments"
TARGET_COLUMNS = {"service_id", "data_hora"}


def _target_unique_constraints(bind):
    inspector = sa.inspect(bind)
    if TABLE_NAME not in inspector.get_table_names():
        return []
    return [
        constraint
        for constraint in inspector.get_unique_constraints(TABLE_NAME)
        if set(constraint.get("column_names") or []) == TARGET_COLUMNS
    ]


def upgrade():
    bind = op.get_bind()
    matches = _target_unique_constraints(bind)
    if not matches:
        return

    if bind.dialect.name == "sqlite":
        # SQLite may report this legacy constraint without a name. The batch
        # naming convention gives that reflected constraint a droppable name.
        naming = {
            "uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s",
        }
        with op.batch_alter_table(TABLE_NAME, naming_convention=naming) as batch:
            for constraint in matches:
                columns = constraint.get("column_names") or []
                name = constraint.get("name") or (
                    f"uq_{TABLE_NAME}_{columns[0]}_{columns[1]}"
                )
                batch.drop_constraint(name, type_="unique")
        return

    for constraint in matches:
        name = constraint.get("name")
        if not name:
            raise RuntimeError(
                "Cannot safely remove the legacy appointments unique constraint: "
                "the database did not report its name"
            )
        op.drop_constraint(name, TABLE_NAME, type_="unique")


def downgrade():
    bind = op.get_bind()
    if TABLE_NAME not in sa.inspect(bind).get_table_names():
        return
    if _target_unique_constraints(bind):
        return

    duplicate = bind.execute(
        sa.text(
            "SELECT service_id, data_hora, COUNT(*) "
            "FROM appointments "
            "WHERE service_id IS NOT NULL "
            "GROUP BY service_id, data_hora "
            "HAVING COUNT(*) > 1 "
            "LIMIT 1"
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot downgrade: appointments contain duplicate service_id/data_hora "
            "values, so the legacy unique constraint cannot be restored without "
            "changing reservation data. Resolve the duplicates explicitly and retry."
        )

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(TABLE_NAME) as batch:
            batch.create_unique_constraint(
                "_service_date_uc", ["service_id", "data_hora"]
            )
    else:
        op.create_unique_constraint(
            "_service_date_uc", TABLE_NAME, ["service_id", "data_hora"]
        )
