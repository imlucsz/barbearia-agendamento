from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return an aware UTC timestamp for protocols such as JWT claims."""
    return datetime.now(timezone.utc)


def utc_now_naive() -> datetime:
    """Return UTC without tzinfo for existing database columns stored as naive."""
    return utc_now().replace(tzinfo=None)
