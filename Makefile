SHELL := /bin/bash
HOST_DATABASE_URL ?= postgresql+psycopg://maintenance:maintenance@localhost:5433/maintenance_copilot

.PHONY: setup dev down logs migrate migration-check seed test test-ingestion lint format health clean-uploads clean

setup:
	python3 -m venv apps/api/.venv
	apps/api/.venv/bin/pip install --upgrade pip
	apps/api/.venv/bin/pip install -e "apps/api[dev]"
	npm install

dev:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	cd apps/api && DATABASE_URL="$(HOST_DATABASE_URL)" .venv/bin/alembic upgrade head

migration-check:
	cd apps/api && DATABASE_URL="$(HOST_DATABASE_URL)" .venv/bin/alembic check

seed:
	cd apps/api && DATABASE_URL="$(HOST_DATABASE_URL)" .venv/bin/python -m app.db.seed

test:
	apps/api/.venv/bin/pytest apps/api
	npm test

test-ingestion:
	apps/api/.venv/bin/pytest apps/api/tests/test_ingestion_*.py

lint:
	apps/api/.venv/bin/ruff check apps/api
	apps/api/.venv/bin/mypy apps/api/app
	npm run lint
	npm run typecheck

format:
	apps/api/.venv/bin/ruff format apps/api
	npm --workspace apps/web run format

health:
	curl -fsS http://localhost:8000/api/v1/health
	curl -fsS http://localhost:8000/api/v1/health/ready
	curl -fsS http://localhost:3000/health

clean-uploads:
	cd apps/api && APP_ENV="$${APP_ENV:-development}" .venv/bin/python -m app.db.clean_uploads

clean:
	docker compose down --volumes --remove-orphans
	rm -rf apps/api/.venv apps/api/.pytest_cache apps/api/.ruff_cache apps/api/.mypy_cache
	rm -rf node_modules apps/web/node_modules apps/web/.next apps/web/coverage
