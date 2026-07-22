SHELL := /bin/bash
HOST_DATABASE_URL ?= postgresql+psycopg://maintenance:maintenance@localhost:5433/maintenance_copilot

.PHONY: setup dev down logs migrate migration-check seed process-demo-documents extract-demo-documents extraction-status test test-ingestion test-parsing test-extraction lint format health clean-uploads clean-parsed clean

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

process-demo-documents:
	cd apps/api && DATABASE_URL="$(HOST_DATABASE_URL)" .venv/bin/python -m app.db.process_demo_documents

extract-demo-documents:
	cd apps/api && DATABASE_URL="$(HOST_DATABASE_URL)" EXTRACTION_PROVIDER="$${EXTRACTION_PROVIDER:-mock}" .venv/bin/python -m app.db.extract_demo_documents

extraction-status:
	cd apps/api && DATABASE_URL="$(HOST_DATABASE_URL)" .venv/bin/python -m app.db.extraction_status

test:
	apps/api/.venv/bin/pytest apps/api
	npm test

test-ingestion:
	apps/api/.venv/bin/pytest apps/api/tests/test_ingestion_*.py

test-parsing:
	apps/api/.venv/bin/pytest apps/api/tests/test_processing_*.py apps/api/tests/test_parsers.py apps/api/tests/test_chunking.py

test-extraction:
	EXTRACTION_PROVIDER=mock apps/api/.venv/bin/pytest apps/api/tests/test_extraction_*.py apps/api/tests/test_extraction.py

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

clean-parsed:
	cd apps/api && APP_ENV="$${APP_ENV:-development}" .venv/bin/python -m app.db.clean_parsed

clean:
	docker compose down --volumes --remove-orphans
	rm -rf apps/api/.venv apps/api/.pytest_cache apps/api/.ruff_cache apps/api/.mypy_cache
	rm -rf node_modules apps/web/node_modules apps/web/.next apps/web/coverage
