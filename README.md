# Industrial Maintenance Knowledge Copilot

Asset-centered foundation for a cited, explainable industrial maintenance knowledge platform.

## Current Status

Phase 5 is complete. The repository contains a Next.js frontend, FastAPI backend, PostgreSQL, Qdrant health integration, Docker Compose, Alembic migrations, an asset-centric canonical relational model, seed equipment data, secure document ingestion, parsing/OCR/chunking, and structured extraction APIs with provenance-rich fact auditing.

Embeddings, document-content indexing in Qdrant, retrieval, RCA, automated compliance findings, graph visualization, and frontend document/equipment pages are intentionally deferred.

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

The canonical database model is centered on `equipment` and includes components, documents, pages, blocks, chunks, events, failure details, measurements, procedures, maintenance actions, work orders, compliance rules/findings, graph edges, citations, ingestion jobs, processing runs, extraction runs, chunk extraction runs, extracted facts, and equipment aliases.

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

Process parsed artifacts and run structured extraction over local documents:

```bash
make process-demo-documents
make extract-demo-documents
make extraction-status
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
- `POST /api/v1/documents/{document_id}/process`
- `POST /api/v1/documents/{document_id}/process/retry`
- `GET /api/v1/documents/{document_id}/processing`
- `GET /api/v1/documents/{document_id}/processing/runs`
- `GET /api/v1/documents/{document_id}/pages`
- `GET /api/v1/documents/{document_id}/pages/{page_number}`
- `GET /api/v1/documents/{document_id}/pages/{page_number}/image`
- `GET /api/v1/documents/{document_id}/chunks`
- `GET /api/v1/documents/{document_id}/chunks/{chunk_id}`
- `POST /api/v1/documents/{document_id}/extract`
- `POST /api/v1/documents/{document_id}/extract/retry`
- `GET /api/v1/documents/{document_id}/extraction`
- `GET /api/v1/documents/{document_id}/extraction/runs`
- `GET /api/v1/extraction/runs/{run_id}`
- `GET /api/v1/extraction/runs/{run_id}/facts`
- `GET /api/v1/extraction/facts/{fact_id}`

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

## Document Processing

Phase 4 processing turns uploaded files into pages, structural blocks, rendered page images where supported, and deterministic chunks with citation labels. Supported parsers cover PDF, DOCX, XLSX, CSV, TXT, PNG, JPG, and JPEG. PDFs use PyMuPDF with an explicit fallback warning until a richer layout parser is introduced.

Processing is synchronous in the API for now. Force processing replaces parsed pages, blocks, chunks, and rendered images while preserving processing run history.

## Structured Extraction

Phase 5 extraction reads parsed chunks and writes audited facts plus conservative canonical records. The default provider is `mock`, so local tests and demos do not require a paid API key. Optional local Ollama can be enabled with `EXTRACTION_PROVIDER=ollama` and `OLLAMA_BASE_URL`.

Extraction records candidate signals, chunk-level provider attempts, strict validation outcomes, confidence gates, evidence spans, source document/page/chunk IDs, duplicate status, and canonical links where a fact is accepted. Compliance candidates and relationships are staged for review; Phase 5 does not create compliance findings, embeddings, retrieval indexes, or Qdrant document vectors.

## Testing

```bash
make test
```

Backend tests cover application import, liveness, readiness response shape, settings validation, model rules, migration coverage, repositories, seed idempotency, equipment APIs, ingestion validation, storage, parsing, chunking, extraction validation, idempotency, retry behavior, provenance, and document/extraction APIs. Frontend tests cover a basic rendered component.

Run only extraction tests with the mock provider:

```bash
make test-extraction
```

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
- If local tooling is missing, install Node.js 20.19+, npm 10+, Python 3.12+, and Docker Compose v2.
- If extraction returns `extraction_not_ready`, process the document first with `POST /api/v1/documents/{document_id}/process`.
- If Ollama extraction fails, confirm `OLLAMA_BASE_URL` is reachable from the API process. The mock provider remains the default for automated tests.

## Next Phase

Phase 6 should add embeddings and retrieval over the Phase 4/5 artifacts without weakening provenance or local/offline test behavior.
