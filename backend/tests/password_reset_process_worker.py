"""Spawn-safe worker for real database concurrency tests; never sends email."""
def reserve_in_process(database_url, email, ip, now, barrier, results):
    import os
    os.environ["DATABASE_URL"] = database_url
    os.environ["APP_ENV"] = "test"
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.config import settings
    from app.core.password_reset_limits import reserve_request
    engine = create_engine(database_url)
    try:
        configured = settings()
        barrier.wait(timeout=20)
        with Session(engine) as db:
            accepted = reserve_request(db, email, ip, now, configured)
        results.put(("ok", accepted is not None))
    except Exception as error:
        # Diagnostics intentionally omit SQL, connection URLs and identifiers.
        results.put(("error", type(error).__name__))
    finally:
        engine.dispose()
