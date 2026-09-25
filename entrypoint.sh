#!/bin/sh
# entrypoint.sh — runs inside the Docker container on startup
#
# WHY a shell script instead of running gunicorn directly?
# We need to run `flask db upgrade` BEFORE starting the server,
# to apply any pending database migrations automatically.
# This means anyone who deploys a new version never has to manually
# run migrations — the container handles it on boot.

set -e  # exit immediately if any command fails

echo "Ensuring instance directory exists..."
mkdir -p instance

echo "Applying database migrations..."
# Stamp existing tables if they were created outside of Alembic
python -c "
from app import create_app, db
from sqlalchemy import inspect
app = create_app()
with app.app_context():
    insp = inspect(db.engine)
    tables = insp.get_table_names()
    if tables and 'alembic_version' not in tables:
        exit(0)
    exit(1)
" 2>/dev/null && flask db stamp head || true

flask db upgrade

echo "Starting gunicorn server..."
# --workers 2: 2 worker processes (good for a free-tier host with 1-2 vCPUs)
# --bind 0.0.0.0:8000: listen on all interfaces, port 8000
# run:app — the `app` variable inside run.py
exec gunicorn --workers 2 --bind 0.0.0.0:${PORT:-8000} --timeout 120 run:app
