#!/usr/bin/env bash
# -----------------------------------------------------------------------
# build.sh — Render build script
# -----------------------------------------------------------------------
# Render runs this during the "build" phase before starting the app.
# It installs Python dependencies and applies database migrations.
# -----------------------------------------------------------------------

set -o errexit  # exit on error

echo "==> Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Ensuring instance directory exists..."
mkdir -p instance

echo "==> Running database migrations..."
# If the DB exists but has no alembic_version table (e.g. tables were created
# by db.create_all() instead of migrations), stamp it at head so Alembic
# knows the schema is already up to date, then run upgrade for any new migrations.
if python -c "
from app import create_app, db
from sqlalchemy import inspect
app = create_app()
with app.app_context():
    engine = db.engine
    insp = inspect(engine)
    tables = insp.get_table_names()
    # Tables exist but no alembic tracking = needs stamping
    if tables and 'alembic_version' not in tables:
        exit(0)
    exit(1)
" 2>/dev/null; then
    echo "==> Existing tables found without migration history — stamping at head..."
    flask db stamp head
fi

flask db upgrade

echo "==> Build complete!"
