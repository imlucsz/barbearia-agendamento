#!/usr/bin/env bash
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)"
PYTHON="${BACKUP_PYTHON:-$REPO_ROOT/backend/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: install backend requirements in backend/.venv or set BACKUP_PYTHON" >&2
  exit 1
fi
exec "$PYTHON" "$SCRIPT_DIR/backup.py" backup
