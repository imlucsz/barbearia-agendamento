"""Create the application schema or validate a local create_all legacy schema.

Revision ID: 20261028_01
Revises: 20261027_01
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa


revision = "20261028_01"
down_revision = "20261027_01"
branch_labels = None
depends_on = None


TABLE_COLUMNS = {
    "users": {"id", "nome", "email", "senha_hash", "role", "bloqueado", "ativo", "consentimento_lgpd", "consentimento_em"},
    "services": {"id", "nome", "preco", "duracao_minutos"},
    "appointments": {"id", "user_id", "nome_cliente", "service_id", "barbeiro_id", "data_hora", "status", "preco", "duracao_minutos", "valor_cobrado", "reschedule_count"},
    "avaliacoes": {"id", "appointment_id", "nota", "comentario", "criada_em", "oculta"},
    "informacoes_institucionais": {"id", "nome", "endereco", "telefone", "email", "site", "horario_funcionamento", "dias_atendimento", "endereco_maps", "criado_em", "atualizado_em"},
    "jornadas_trabalho": {"id", "barbeiro_id", "dia_semana", "hora_inicio", "hora_fim", "ativo"},
    "bloqueios_horario": {"id", "barbeiro_id", "inicio", "fim", "motivo", "tipo", "ativo"},
    "barbeiros_servicos": {"id", "barbeiro_id", "service_id"},
    "password_reset_tokens": {"id", "user_id", "token", "expires_at", "used"},
}

NON_NULL_COLUMNS = {
    "users": {"id", "nome", "email", "senha_hash", "consentimento_lgpd"},
    "services": {"id", "nome", "preco"},
    "appointments": {"id", "barbeiro_id", "data_hora", "preco", "duracao_minutos"},
    "avaliacoes": {"id", "nota"},
    "informacoes_institucionais": {"id", "nome", "endereco", "telefone", "horario_funcionamento", "dias_atendimento"},
    "jornadas_trabalho": {"id", "barbeiro_id", "dia_semana", "hora_inicio", "hora_fim"},
    "bloqueios_horario": {"id", "barbeiro_id", "inicio", "fim", "tipo"},
    "barbeiros_servicos": {"id", "barbeiro_id", "service_id"},
    "password_reset_tokens": {"id", "user_id", "token", "expires_at"},
}

TYPE_FAMILIES = {
    "users": {"id": "integer", "nome": "string", "email": "string", "senha_hash": "string", "role": "string", "bloqueado": "boolean", "ativo": "boolean", "consentimento_lgpd": "boolean", "consentimento_em": "datetime"},
    "services": {"id": "integer", "nome": "string", "preco": "float", "duracao_minutos": "integer"},
    "appointments": {"id": "integer", "user_id": "integer", "nome_cliente": "string", "service_id": "integer", "barbeiro_id": "integer", "data_hora": "datetime", "status": "string", "preco": "float", "duracao_minutos": "integer", "valor_cobrado": "float", "reschedule_count": "integer"},
    "avaliacoes": {"id": "integer", "appointment_id": "integer", "nota": "integer", "comentario": "string", "criada_em": "datetime", "oculta": "boolean"},
    "informacoes_institucionais": {"id": "integer", "nome": "string", "endereco": "string", "telefone": "string", "email": "string", "site": "string", "horario_funcionamento": "string", "dias_atendimento": "string", "endereco_maps": "string", "criado_em": "datetime", "atualizado_em": "datetime"},
    "jornadas_trabalho": {"id": "integer", "barbeiro_id": "integer", "dia_semana": "integer", "hora_inicio": "string", "hora_fim": "string", "ativo": "boolean"},
    "bloqueios_horario": {"id": "integer", "barbeiro_id": "integer", "inicio": "datetime", "fim": "datetime", "motivo": "string", "tipo": "string", "ativo": "boolean"},
    "barbeiros_servicos": {"id": "integer", "barbeiro_id": "integer", "service_id": "integer"},
    "password_reset_tokens": {"id": "integer", "user_id": "integer", "token": "string", "expires_at": "datetime", "used": "boolean"},
}

EXPECTED_FOREIGN_KEYS = {
    "appointments": {("user_id", "users", "id"), ("service_id", "services", "id"), ("barbeiro_id", "users", "id")},
    "avaliacoes": {("appointment_id", "appointments", "id")},
    "jornadas_trabalho": {("barbeiro_id", "users", "id")},
    "bloqueios_horario": {("barbeiro_id", "users", "id")},
    "barbeiros_servicos": {("barbeiro_id", "users", "id"), ("service_id", "services", "id")},
    "password_reset_tokens": {("user_id", "users", "id")},
}

EXPECTED_INDEXES = {
    "users": {(('id',), False), (('email',), True)},
    "services": {(('id',), False)},
    "appointments": {(('id',), False)},
    "avaliacoes": {(('id',), False), (('appointment_id',), True)},
    "informacoes_institucionais": {(('id',), False)},
    "jornadas_trabalho": {(('id',), False)},
    "bloqueios_horario": {(('id',), False)},
    "barbeiros_servicos": {(('id',), False)},
    "password_reset_tokens": {(('id',), False), (('token',), True)},
}


def _type_family(column_type):
    if isinstance(column_type, sa.Boolean):
        return "boolean"
    if isinstance(column_type, sa.DateTime):
        return "datetime"
    if isinstance(column_type, sa.Float):
        return "float"
    if isinstance(column_type, sa.Integer):
        return "integer"
    if isinstance(column_type, sa.String):
        return "string"
    return "unknown"


def _foreign_keys(inspector, table):
    return {
        (item["constrained_columns"][0], item["referred_table"], item["referred_columns"][0])
        for item in inspector.get_foreign_keys(table)
    }


def _unique_indexes(inspector, table):
    unique = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints(table)
    }
    indexes = {
        (tuple(item["column_names"]), bool(item["unique"]))
        for item in inspector.get_indexes(table)
    }
    index_shapes = {(columns, is_unique) for columns, is_unique in indexes}
    for columns in unique:
        index_shapes.add((columns, True))
    return index_shapes


def _validate_existing_schema(bind):
    inspector = sa.inspect(bind)
    actual_tables = set(inspector.get_table_names()) - {"alembic_version"}
    if actual_tables != set(TABLE_COLUMNS):
        raise RuntimeError(
            "Existing database schema is not a supported create_all development schema; "
            "preserve the database and inspect it before migration."
        )

    for table, expected_columns in TABLE_COLUMNS.items():
        columns = {column["name"]: column for column in inspector.get_columns(table)}
        if set(columns) != expected_columns:
            raise RuntimeError(
                f"Existing database table {table} has an unsupported column set; "
                "preserve the database and inspect it before migration."
            )
        for name, column in columns.items():
            expected_family = TYPE_FAMILIES[table][name]
            nullable = name not in NON_NULL_COLUMNS[table]
            if _type_family(column["type"]) != expected_family or bool(column["nullable"]) != nullable:
                raise RuntimeError(
                    f"Existing database column {table}.{name} differs from the supported schema; "
                    "preserve the database and inspect it before migration."
                )

        primary_key = set(inspector.get_pk_constraint(table).get("constrained_columns") or [])
        if primary_key != {"id"}:
            raise RuntimeError(f"Existing database table {table} has an unsupported primary key.")

        foreign_keys = _foreign_keys(inspector, table)
        if foreign_keys != EXPECTED_FOREIGN_KEYS.get(table, set()):
            raise RuntimeError(f"Existing database table {table} has unsupported foreign keys.")

        if _unique_indexes(inspector, table) != EXPECTED_INDEXES[table]:
            raise RuntimeError(f"Existing database table {table} has unsupported indexes or unique constraints.")


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names()) - {"alembic_version"}
    if existing_tables:
        _validate_existing_schema(bind)
        return

    role = sa.Enum("CLIENTE", "BARBEIRO", "ADMIN", name="roleenum")
    appointment_status = sa.Enum(
        "PENDENTE", "CONFIRMADO", "CONCLUIDO", "CANCELADO", "FALTA", "AVALIADO",
        name="appointmentstatusenum",
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("senha_hash", sa.String(), nullable=False),
        sa.Column("role", role, nullable=True),
        sa.Column("bloqueado", sa.Boolean(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=True),
        sa.Column("consentimento_lgpd", sa.Boolean(), nullable=False),
        sa.Column("consentimento_em", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("preco", sa.Float(), nullable=False),
        sa.Column("duracao_minutos", sa.Integer(), nullable=True),
    )
    op.create_index("ix_services_id", "services", ["id"])

    op.create_table(
        "informacoes_institucionais",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("endereco", sa.String(), nullable=False),
        sa.Column("telefone", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("site", sa.String(), nullable=True),
        sa.Column("horario_funcionamento", sa.String(), nullable=False),
        sa.Column("dias_atendimento", sa.String(), nullable=False),
        sa.Column("endereco_maps", sa.String(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_informacoes_institucionais_id", "informacoes_institucionais", ["id"])

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("nome_cliente", sa.String(), nullable=True),
        sa.Column("service_id", sa.Integer(), nullable=True),
        sa.Column("barbeiro_id", sa.Integer(), nullable=False),
        sa.Column("data_hora", sa.DateTime(), nullable=False),
        sa.Column("status", appointment_status, nullable=True),
        sa.Column("preco", sa.Float(), nullable=False),
        sa.Column("duracao_minutos", sa.Integer(), nullable=False),
        sa.Column("valor_cobrado", sa.Float(), nullable=True),
        sa.Column("reschedule_count", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.ForeignKeyConstraint(["barbeiro_id"], ["users.id"]),
    )
    op.create_index("ix_appointments_id", "appointments", ["id"])

    op.create_table(
        "avaliacoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_id", sa.Integer(), nullable=True),
        sa.Column("nota", sa.Integer(), nullable=False),
        sa.Column("comentario", sa.String(), nullable=True),
        sa.Column("criada_em", sa.DateTime(), nullable=True),
        sa.Column("oculta", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.UniqueConstraint("appointment_id"),
    )
    op.create_index("ix_avaliacoes_id", "avaliacoes", ["id"])

    op.create_table(
        "jornadas_trabalho",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("barbeiro_id", sa.Integer(), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=False),
        sa.Column("hora_inicio", sa.String(), nullable=False),
        sa.Column("hora_fim", sa.String(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["barbeiro_id"], ["users.id"]),
    )
    op.create_index("ix_jornadas_trabalho_id", "jornadas_trabalho", ["id"])

    op.create_table(
        "bloqueios_horario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("barbeiro_id", sa.Integer(), nullable=False),
        sa.Column("inicio", sa.DateTime(), nullable=False),
        sa.Column("fim", sa.DateTime(), nullable=False),
        sa.Column("motivo", sa.String(), nullable=True),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["barbeiro_id"], ["users.id"]),
    )
    op.create_index("ix_bloqueios_horario_id", "bloqueios_horario", ["id"])

    op.create_table(
        "barbeiros_servicos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("barbeiro_id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["barbeiro_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
    )
    op.create_index("ix_barbeiros_servicos_id", "barbeiros_servicos", ["id"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_password_reset_tokens_id", "password_reset_tokens", ["id"])
    op.create_index("ix_password_reset_tokens_token", "password_reset_tokens", ["token"], unique=True)


def downgrade():
    raise RuntimeError(
        "Downgrade is disabled for the initial schema because dropping these tables would delete application data."
    )
