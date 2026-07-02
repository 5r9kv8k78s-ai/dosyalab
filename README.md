# FormatFlow

A production-ready monorepo for a document conversion platform: a Next.js frontend
for uploading files, and a FastAPI backend built to grow modular conversion
capabilities (docx → pdf, image → pdf, etc.) over time.

## Stack

- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.12
- **Tooling**: pnpm workspaces, ESLint, Prettier, ruff, black, pytest
- **Infra**: Docker, Docker Compose, GitHub Actions

## Monorepo layout

```
apps/
  web/     Next.js frontend
  api/     FastAPI backend
.github/workflows/  CI pipelines
docker-compose.yml  Local orchestration for both services
```

### Backend architecture

```
apps/api/app/
  core/       settings, logging
  api/v1/     versioned routers and endpoints (health, upload)
  schemas/    pydantic request/response models
  services/   storage and other infrastructure services
  modules/converter/   pluggable conversion module registry —
                        future formats register here without touching
                        the API layer
```

New conversion modules implement `ConversionModule` in
`apps/api/app/modules/converter/base.py` and call `register_converter(...)` to
plug into the pipeline.

### PDF → Word

The first live conversion module (`apps/api/app/modules/converter/pdf_to_docx.py`,
built on [pdf2docx](https://github.com/ArtifexSoftware/pdf2docx)). It's an async
job: submit a file, then poll for status and download the result.

- `POST /api/v1/convert/pdf-to-docx` — multipart upload, rejects non-PDF files,
  files over 100MB, and encrypted or corrupted PDFs. Returns `202` with a `job_id`.
- `GET /api/v1/convert/jobs/{job_id}` — status, progress (0-100), and a
  `download_url` once `status` is `completed`.
- `GET /api/v1/convert/jobs/{job_id}/download` — streams the `.docx` and deletes
  the job's temp files afterward. Abandoned jobs are swept automatically after
  `JOB_TTL_MINUTES`.

pdf2docx exposes no public per-page progress callback (verified empirically —
see the docstring in `pdf_to_docx.py`), so progress during the actual conversion
is approximated; it always reaches 100% only on real completion. It also has no
"Heading N" style mapping — headings survive as bold/larger-font runs on `Normal`
paragraphs rather than semantic Word heading styles.

## Getting started (local, no Docker)

### Backend

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API runs at http://localhost:8000, docs at http://localhost:8000/api/docs.

### Frontend

```bash
cd apps/web
cp .env.example .env
pnpm install
pnpm dev
```

App runs at http://localhost:3000.

## Getting started (Docker Compose)

```bash
cp .env.example .env
cp apps/web/.env.example apps/web/.env
cp apps/api/.env.example apps/api/.env
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000/api/v1/health

## Testing & linting

```bash
# Frontend
cd apps/web && pnpm lint && pnpm typecheck && pnpm build

# Backend
cd apps/api && ruff check . && black --check . && pytest
```

## CI

`.github/workflows/ci.yml` runs frontend lint/typecheck/build, backend
lint/test, and a Docker build sanity check on every push and pull request to
`main`.
