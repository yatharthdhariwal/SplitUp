#!/bin/sh
# entrypoint.sh — runs inside the Docker container on startup
#
# WHY a shell script instead of running gunicorn directly?
# We need to run `flask db upgrade` BEFORE starting the server,
# to apply any pending database migrations automatically.
# This means anyone who deploys a new version never has to manually
# run migrations — the container handles it on boot.

set -e  # exit immediately if any command fails

echo "Applying database migrations..."
flask db upgrade

echo "Starting gunicorn server..."
# --workers 2: 2 worker processes (good for a free-tier host with 1-2 vCPUs)
# --bind 0.0.0.0:8000: listen on all interfaces, port 8000
# run:app — the `app` variable inside run.py
exec gunicorn --workers 2 --bind 0.0.0.0:8000 --timeout 120 run:app
