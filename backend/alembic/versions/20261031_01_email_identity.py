"""Normalize email identities without merging existing accounts."""
from alembic import op
import sqlalchemy as sa
import re

revision = "20261031_01"
down_revision = "20261029_06"
branch_labels = None
depends_on = None

INDEX = "uq_users_email_identity"
EXPRESSION = "lower(ltrim(rtrim(email)))"


def _canonical(expression):
    for identifier in ("email", "users", INDEX):
        for left, right in [('"', '"'), ('`', '`'), ('[', ']')]:
            expression = expression.replace(left + identifier + right, identifier)
    value = re.sub(r'\s+', '', expression.lower())
    value = value.replace("(email)::text", "email").replace("email::text", "email")
    while "((email))" in value:
        value = value.replace("((email))", "(email)")
    return value


def _existing_identity_index(connection):
    incompatible = RuntimeError("Estrutura uq_users_email_identity incompatível; migração abortada sem substituir índice ou constraint.")
    inspector = sa.inspect(connection)
    constraints = (inspector.get_unique_constraints("users") + inspector.get_check_constraints("users")
                   + inspector.get_foreign_keys("users") + [inspector.get_pk_constraint("users")])
    if any((item.get("name") or "").lower() == INDEX if connection.dialect.name == "sqlite"
           else item.get("name") == INDEX for item in constraints):
        raise incompatible
    if connection.dialect.name == "sqlite":
        row = connection.execute(sa.text("SELECT type, tbl_name, sql FROM sqlite_master WHERE name = :name COLLATE NOCASE"), {"name": INDEX}).first()
        if not row:
            return False
        expected = f"createuniqueindex{INDEX}onusers({EXPRESSION})"
        definition = _canonical(row[2] or "").replace("createuniqueindexifnotexists", "createuniqueindex", 1).rstrip(";")
        if row[0] != "index" or row[1] != "users" or definition != _canonical(expected):
            raise incompatible
        return True
    if connection.dialect.name == "postgresql":
        row = connection.execute(sa.text('''
            SELECT t.relname, i.indisunique, i.indisvalid, i.indisready,
                   i.indnkeyatts, i.indnatts, pg_get_expr(i.indexprs, i.indrelid),
                   pg_get_expr(i.indpred, i.indrelid), pg_get_indexdef(c.oid)
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_index i ON i.indexrelid = c.oid
            LEFT JOIN pg_class t ON t.oid = i.indrelid
            WHERE n.nspname = current_schema() AND c.relname = :name
        '''), {"name": INDEX}).first()
        if not row:
            return False
        if (row[0] != "users" or not all(row[1:4]) or row[4:6] != (1, 1)
                or _canonical(row[6] or "") != _canonical(EXPRESSION) or row[7] is not None
                or " COLLATE " in (row[8] or "").upper()):
            raise incompatible
        return True
    raise RuntimeError("Backend não suportado para validação do índice de identidade")


def upgrade():
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, email FROM users")).all()
    identities = set()
    for _, email in rows:
        identity = email.strip().lower()
        if identity in identities:
            raise RuntimeError("Existem identidades de e-mail conflitantes. Resolva as contas antes de migrar; nenhum dado foi unido.")
        identities.add(identity)
    existing = _existing_identity_index(connection)
    for user_id, email in rows:
        connection.execute(sa.text("UPDATE users SET email = :email WHERE id = :id"),
                           {"email": email.strip().lower(), "id": user_id})
    if not existing:
        op.create_index(INDEX, "users", [sa.text(EXPRESSION)], unique=True)


def downgrade():
    raise RuntimeError("Downgrade is disabled: email identity normalization cannot be reversed safely")
