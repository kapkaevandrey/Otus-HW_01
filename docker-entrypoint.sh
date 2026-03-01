#!/bin/bash
set -e

PORT=${2:-8000}

case "$1" in
    init)
        alembic upgrade head
        ;;
    api)
        exec uv run uvicorn app.server:app --host 0.0.0.0 --port $PORT --forwarded-allow-ips '*'
        ;;
    start)
        alembic upgrade head
        uv run uvicorn app.server:app --host 0.0.0.0 --port $PORT --reload
        ;;
    pytest)
        alembic downgrade base
        alembic upgrade head
        uv run pytest -s -vv -x tests/ --cov=. --trace-config --flake-finder --flake-runs=5
        exit 0
        ;;
    coverage)
        uv run pytest -s -vv --cov=app --cov-report=term-missing --cov-report=html
        echo "📊 Coverage report in: ./htmlcov/index.html"
        exit 0
        ;;
    check_code)
        uv run ruff check .
        uv run mypy app/ tests/
        ;;
    format_code)
        uv run ruff format .
        uv run ruff check . --fix
        ;;
    *)
        exec "$@"
        ;;
esac
