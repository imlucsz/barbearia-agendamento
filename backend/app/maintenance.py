"""Operational maintenance commands."""
import argparse
from datetime import timedelta

from app.config import settings
from app.core.clock import utc_now_naive
from app.database import SessionLocal
from app.models.user import AuditLog


def purge_audit(dry_run=False):
    cutoff = utc_now_naive() - timedelta(days=settings().retention_days)
    db = SessionLocal()
    try:
        query = db.query(AuditLog).filter(AuditLog.ocorrido_em < cutoff)
        count = query.count()
        if not dry_run:
            query.delete(synchronize_session=False)
            db.commit()
        print(f"audit_logs vencidos: {count}; removidos: {0 if dry_run else count}; dry_run={str(dry_run).lower()}")
        return count
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(prog="python -m app.maintenance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    purge = subparsers.add_parser("purge-audit")
    purge.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.command == "purge-audit":
        purge_audit(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
