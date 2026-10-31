from sqlalchemy import func


def normalize_email(value: str) -> str:
    return value.strip().lower()


def email_key(column):
    return func.lower(func.ltrim(func.rtrim(column)))


def is_email_conflict(error):
    """Only recognize the known unique email constraints, never arbitrary prose."""
    original = error.orig
    if getattr(original, "sqlstate", None) == "23505":
        diagnostic = getattr(original, "diag", None)
        return (getattr(diagnostic, "table_name", None) == "users"
                and getattr(diagnostic, "constraint_name", None) in {
                    "uq_users_email_identity", "ix_users_email", "users_email_key",
                })
    if getattr(original, "sqlite_errorcode", None) == 2067:
        return str(original) in {
            "UNIQUE constraint failed: users.email",
            "UNIQUE constraint failed: index 'uq_users_email_identity'",
        }
    return False
