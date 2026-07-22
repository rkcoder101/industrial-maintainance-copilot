SHELL := /bin/bash

.PHONY: setup dev down logs test lint format health clean

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

test:
	apps/api/.venv/bin/pytest apps/api
	npm test

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

clean:
	docker compose down --volumes --remove-orphans
	rm -rf apps/api/.venv apps/api/.pytest_cache apps/api/.ruff_cache apps/api/.mypy_cache
	rm -rf node_modules apps/web/node_modules apps/web/.next apps/web/coverage
