#!/usr/bin/env bash
# Bootstrap a local development environment for Karzar.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

echo "==> Karzar dev setup (root: $ROOT_DIR)"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Error: $PYTHON not found. Install Python 3.10+ and retry." >&2
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> Creating virtual environment at $VENV_DIR"
  "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Upgrading pip"
pip install --upgrade pip

echo "==> Installing dependencies (production + dev/test)"
pip install -r requirements-dev.txt

if [[ ! -f .env ]]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
  echo "    Review .env before running the API (SECRET_KEY, ADMIN_STEP_UP_PIN, database)."
else
  echo "==> .env already exists — skipped"
fi

echo ""
echo "Dev environment ready."
echo ""
echo "Next steps:"
echo "  source $VENV_DIR/bin/activate"
echo "  alembic upgrade head"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo "  pytest -v"
