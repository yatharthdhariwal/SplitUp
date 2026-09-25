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
flask db upgrade

echo "==> Build complete!"
