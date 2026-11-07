"""Run the same scoped regressions using the existing temporary SQLite harness."""
import os
import uuid
from pathlib import Path

os.environ['BOOKING_TEST_BACKEND'] = 'sqlite'
os.environ.pop('BOOKING_TEST_POSTGRES_URL', None)
os.environ['STAGE2_PG_OUTPUT'] = str(Path(__file__).resolve().parent / 'runs' / ('sqlite-' + uuid.uuid4().hex))

import run_f2_fix

raise SystemExit(0 if run_f2_fix.run_worker('f2') else 1)
