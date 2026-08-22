#!/bin/sh
set -e

echo "=== NutriGuard Startup ==="
echo "Running Alembic migrations..."
python -m alembic upgrade head

echo "Running seed data..."
python -m data.seed

echo "Starting FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
