#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)"
PYTHON="${INSTALLATION_PYTHON:-$REPO_ROOT/backend/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then PYTHON="${PYTHON:-python3}"; fi
exec "$PYTHON" "$SCRIPT_DIR/create.py" "$@"
