#!/bin/sh
set -e

echo "Applying database migrations (alembic upgrade head)..."
alembic upgrade head

APP_SERVER="${APP_SERVER:-uvicorn}"
echo "Starting API server with ${APP_SERVER}..."

if [ "$APP_SERVER" = "gunicorn" ]; then
  exec gunicorn app.main:app -c /app/gunicorn_conf.py
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
