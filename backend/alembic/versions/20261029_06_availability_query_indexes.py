"""Add indexes for batched availability reads."""
from alembic import op

revision = "20261029_06"
down_revision = "20261029_05"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_appointments_barbeiro_data_hora", "appointments", ["barbeiro_id", "data_hora"])
    op.create_index("ix_jornadas_barbeiro_dia_ativo", "jornadas_trabalho", ["barbeiro_id", "dia_semana", "ativo"])
    op.create_index("ix_bloqueios_barbeiro_inicio_fim_ativo", "bloqueios_horario", ["barbeiro_id", "inicio", "fim", "ativo"])


def downgrade():
    raise RuntimeError("Downgrade is disabled for availability indexes.")
