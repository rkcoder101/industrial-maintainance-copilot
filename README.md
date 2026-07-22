# Industrial Maintenance Knowledge Copilot

Asset-centered foundation for a cited, explainable industrial maintenance knowledge platform.

## Current Status

Phase 1 is infrastructure only. The repository contains a Next.js frontend, FastAPI backend, PostgreSQL, Qdrant, Docker Compose, health endpoints, linting, and test foundations. Document ingestion, extraction, retrieval, RCA, compliance, graph features, and demo data are intentionally deferred.

## Architecture

```text
apps/web  ->  apps/api  ->  PostgreSQL
   |             |
   |             ->  Qdrant
packages/shared-types
```

- `apps/web`: Next.js App Router, TypeScript, Tailwind CSS.
- `apps/api`: FastAPI, Pydantic settings, SQLAlchemy connectivity, Qdrant client.
- `packages/shared-types`: shared TypeScript API response contracts.
- `data`: local runtime directories for future uploads, parsed output, rendered pages, and seeds.

## Prerequisites

- Node.js 20.19+
- npm 10+
- Python 3.12+
- Docker and Docker Compose v2

## Environment

```bash
cp .env.example .env
```

The example values are local-development defaults. Do not place real API keys or production secrets in committed files.

## Local Setup

```bash
make setup
```

This creates `apps/api/.venv`, installs backend dev dependencies, and installs npm workspace dependencies.

## Docker Development

```bash
make dev
```

Services:

- Frontend: `http://localhost:3000`
- Frontend health page: `http://localhost:3000/health`
- Backend health: `http://localhost:8000/api/v1/health`
- Backend liveness: `http://localhost:8000/api/v1/health/live`
- Backend readiness: `http://localhost:8000/api/v1/health/ready`
- Qdrant: `http://localhost:6333`
- PostgreSQL: `localhost:5433` by default on the host, `postgres:5432` inside Compose

Stop services:

```bash
make down
```

## Testing

```bash
make test
```

Backend tests cover application import, liveness, readiness response shape, and settings validation. Frontend tests cover a basic rendered component.

## Linting And Type Checks

```bash
make lint
```

This runs Ruff, mypy, ESLint, and TypeScript type checking.

## Formatting

```bash
make format
```

## Troubleshooting

- If Postgres or Qdrant readiness is down, run `docker compose ps` and `docker compose logs api postgres qdrant`.
- If ports are busy, change `API_PORT`, `WEB_PORT`, or Compose port mappings before starting services.
- If frontend health cannot reach the API in Docker, confirm `API_INTERNAL_BASE_URL=http://api:8000`.
- If local tooling is missing, install Node.js 20+, npm 10+, Python 3.12+, and Docker Compose v2.

## Next Phase

Phase 2 should add the canonical SQLAlchemy data model, Pydantic schemas, Alembic migrations, repositories, and seed equipment only.
