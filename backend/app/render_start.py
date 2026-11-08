"""Run release migrations once before starting this Render service process."""

import os
from pathlib import Path
import sys


def main():
    try:
        from dotenv import load_dotenv

        load_dotenv()
        from alembic import command
        from alembic.config import Config
        from app.database import check_schema_revision, engine

        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.upgrade(config, "head")
        ready, _revision = check_schema_revision(engine)
        engine.dispose()
        if not ready:
            raise RuntimeError("Schema verification failed")
    except Exception as exc:
        # Exception text/tracebacks can include connection credentials or row data.
        print(f"Migration failed ({type(exc).__name__}); API was not started.",
              file=sys.stderr, flush=True)
        return 1

    print("Migrations verified; starting API.", flush=True)
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app",
                            "--host", "0.0.0.0", "--port", os.environ.get("PORT", "10000"),
                            "--no-proxy-headers"])


if __name__ == "__main__":
    raise SystemExit(main())
