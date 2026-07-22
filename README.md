# Industrial Maintenance Knowledge Copilot

Asset-centered foundation for a cited, explainable industrial maintenance knowledge platform.

## Current Status

Phase 3 is complete. The repository contains a Next.js frontend, FastAPI backend, PostgreSQL, Qdrant, Docker Compose, health endpoints, linting, tests, Alembic migrations, the canonical asset-centric relational model, seed equipment data, read-only equipment APIs, and secure document-ingestion APIs.

Parsing, OCR, chunking, LLM extraction, embeddings, retrieval, RCA, compliance evaluation, graph visualization, and frontend document/equipment pages are intentionally deferred.

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

The canonical database model is centered on `equipment` and includes components, documents, pages, chunks, events, failure details, measurements, procedures, maintenance actions, work orders, compliance rules/findings, graph edges, citations, ingestion jobs, and extraction runs.

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

## Database Migrations And Seeds

Run migrations against the Docker Postgres host port:

```bash
make migrate
```

Seed the Phase 2 demo equipment registry:

```bash
make seed
```

The seed is idempotent and upserts equipment by `equipment_tag`.

Check for pending migration drift:

```bash
make migration-check
```

Clean local upload files in development or test only:

```bash
make clean-uploads
```

## API Endpoints

- `GET /api/v1/health`
- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `GET /api/v1/equipment/`
- `GET /api/v1/equipment/{equipment_tag_or_uuid}`
- `POST /api/v1/ingestion/documents`
- `GET /api/v1/ingestion/jobs/{job_id}`
- `POST /api/v1/ingestion/jobs/{job_id}/retry`
- `GET /api/v1/documents`
- `GET /api/v1/documents/{document_id}`

## Document Ingestion

Supported formats: `.pdf`, `.docx`, `.xlsx`, `.csv`, `.txt`, `.png`, `.jpg`, and `.jpeg`.

Default limits:

- Maximum file size: 50 MB per file
- Maximum batch size: 20 files

Upload example:

```bash
curl -X POST \
  http://localhost:8000/api/v1/ingestion/documents \
  -F "files=@data/seeds/documents/sample.pdf" \
  -F "files=@data/seeds/documents/inspection.csv" \
  -F "source_type=maintenance_record"
```

Get a job:

```bash
curl -fsS http://localhost:8000/api/v1/ingestion/jobs/{job_id}
```

List registered documents:

```bash
curl -fsS "http://localhost:8000/api/v1/documents?page=1&page_size=20"
```

Duplicate policy: duplicates are detected by SHA-256. A duplicate upload is reported as an ingestion item with `status=duplicate`, references the existing document, does not create a second canonical `Document`, and does not store the file again.

Storage behavior: files are written to a temporary file under `UPLOAD_DIR`, validated using bounded reads, and atomically moved to a generated relative storage key. API responses expose document IDs and safe metadata, not absolute filesystem paths or internal storage keys.

Retry limitation: validation failures are not retryable because rejected request streams are discarded. The retry endpoint only retries retained post-validation internal failures, such as a storage or database failure that left a quarantined internal copy.

Security limitations: Phase 3 validates file signatures and Office ZIP structure lightly, but it does not perform malware scanning. The scanner extension point reports `scanner_not_configured` until a real scanner such as ClamAV is integrated.

## Testing

```bash
make test
```

Backend tests cover application import, liveness, readiness response shape, settings validation, model rules, migration coverage, repositories, seed idempotency, equipment APIs, ingestion validation, storage, services, retry behavior, and document APIs. Frontend tests cover a basic rendered component.

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

Phase 4 should implement parsing and chunking foundations: parser interfaces, Docling/PyMuPDF integration, normalized page/block output, parser diagnostics, and structure-aware chunk creation.
