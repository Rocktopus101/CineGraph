# CineGraph

AI-powered movie recommendations built on your Letterboxd viewing history, TMDB metadata, and pgvector semantic search.

## Architecture

- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, React Query, Firebase Auth
- **Backend**: FastAPI, SQLAlchemy, Alembic, Pydantic
- **Database**: PostgreSQL 16 + pgvector (HNSW indexes)
- **AI**: Pluggable LLM providers (default: **Gemini** `gemini-embedding-001` + `gemini-2.0-flash`; also supports OpenAI and local fallback)
- **External**: TMDB API for movie enrichment, Letterboxd ZIP import

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys. For local development without Firebase:

```env
DEV_MODE=true
DEV_SKIP_ONBOARDING=true
DEV_FIREBASE_UID=dev-user-local
DEV_ADMIN=true
NEXT_PUBLIC_DEV_MODE=true
```

### 2. Start with Docker

```bash
docker compose up --build
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- PostgreSQL: localhost:5432

### 3. Seed dev data

```bash
docker compose exec backend python /scripts/seed.py
```

### 4. Import sample Letterboxd export

```bash
docker compose exec backend python /scripts/import_letterboxd.py /sample-export
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `LLM_PROVIDER` | `gemini` (default), `openai`, or `local` |
| `EMBEDDING_DIM` | Vector dimension (default `768` for Gemini; use `1536` for OpenAI) |
| `GEMINI_API_KEY` | Gemini API key — get free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `GEMINI_EMBEDDING_MODEL` | Default: `gemini-embedding-001` (replaces deprecated `text-embedding-004`) |
| `GEMINI_CHAT_MODEL` | Default: `gemini-2.0-flash` |
| `OPENAI_API_KEY` | OpenAI API key (only if `LLM_PROVIDER=openai`) |
| `EMBEDDING_MODEL` | OpenAI embedding model (default: `text-embedding-3-small`) |
| `CHAT_MODEL` | OpenAI chat model (default: `gpt-4o-mini`) |
| `TMDB_API_KEY` | The Movie Database API key |
| `FIREBASE_PROJECT_ID` | Firebase project ID (Admin SDK) |
| `FIREBASE_CLIENT_EMAIL` | Firebase service account email |
| `FIREBASE_PRIVATE_KEY` | Firebase service account private key |
| `DEV_MODE` | Bypass Firebase auth in development |
| `DEV_SKIP_ONBOARDING` | Skip import requirement for gated pages |
| `DEV_FIREBASE_UID` | Dev user Firebase UID placeholder |
| `DEV_ADMIN` | Grant admin access to dev user |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins (backend CORS) |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend |
| `NEXT_PUBLIC_FIREBASE_*` | Firebase client SDK config |
| `NEXT_PUBLIC_DEV_MODE` | Enable dev mode on frontend |

## API Routes

| Prefix | Endpoints |
|--------|-----------|
| `/auth` | `POST /sync`, `GET /me` |
| `/import` | `POST /letterboxd`, `GET /jobs`, `GET /jobs/{id}` |
| `/movies` | `GET /search`, `GET /{id}`, `GET /{id}/similar` |
| `/history` | `GET /`, `GET /top-rated` |
| `/profile` | `GET /taste`, `GET /analytics`, `POST /taste/refresh` |
| `/recommendations` | `POST /chat`, `POST /generate` |
| `/reviews` | `GET /feed` |
| `/watchlist` | CRUD |
| `/lists` | `GET /`, `GET /{id}` |
| `/admin/ai` | `GET /queries`, `GET /queries/{id}/events`, `GET /stats` |
| `/eval` | `GET /metrics`, `GET /recent-retrievals` |

## Project Structure

```
CineGraph/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── api/routes/       # REST endpoints
│   │   ├── core/             # config, auth, database
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # business logic
│   │   ├── ai/               # agent orchestration + LLM providers
│   │   │   └── providers/    # GeminiProvider, OpenAIProvider, LocalProvider
│   │   ├── retrieval/        # RAG / vector search
│   │   └── ingestion/        # Letterboxd + TMDB
│   └── alembic/              # migrations
├── frontend/
│   └── src/
│       ├── app/              # Next.js pages
│       ├── components/       # UI components
│       └── lib/              # API client, auth, types
└── scripts/
    ├── seed.py
    └── import_letterboxd.py
```

## Features

- **Letterboxd Import**: ZIP upload with incremental merge, TMDB enrichment, embedding generation
- **Onboarding Wizard**: 6-step flow with export guide linking to [letterboxd.com/user/exportdata/](https://letterboxd.com/user/exportdata/)
- **Taste Analytics**: Genre/director/decade stats with LLM narrative summary
- **Synthetic Lists**: Auto-generated taste lists (Highest Rated, Top Genre, Recently Loved, Watch Next)
- **AI Agent**: 7-tool orchestration with citation enforcement
- **RAG Retrieval**: Hybrid semantic search with metadata filters and reciprocal rank fusion
- **Observability**: AI query logging with event timelines (admin page)
- **Evaluation**: Retrieval quality metrics and citation coverage

## Production Deployment (Firebase)

See **[docs/FIREBASE_DEPLOYMENT.md](docs/FIREBASE_DEPLOYMENT.md)** for step-by-step setup.

**Path B (no Cloud SQL billing)** — recommended for personal projects:

1. Steps 1–4: Firebase project, Auth, web app config, service account
2. **Neon** free-tier PostgreSQL + `CREATE EXTENSION vector`
3. **Render** backend (`render.yaml` in repo root)
4. **Vercel** frontend (root dir: `frontend`) + Firebase Auth client config

**Path A (all GCP):** Cloud SQL + Cloud Run + Firebase App Hosting

## Development Notes

- **Apple Silicon Docker (SIGILL / exit 132)**: If the backend dies with `Illegal instruction` after Alembic, the cause is a bad native wheel — usually `cryptography` 43+ (pulled in by `firebase-admin`). The backend Dockerfile pins `cryptography==42.0.8` and uses `platform: linux/arm64`. Rebuild after dependency changes: `docker compose build --no-cache backend`
- Backend runs Alembic migrations on container startup, then starts uvicorn without `--reload` (avoids `watchfiles` SIGILL on Apple Silicon Docker)
- After backend code changes, restart the backend container: `docker compose restart backend`
- For local hot reload outside Docker: `cd backend && uvicorn app.main:app --reload --port 8000`
- Without `GEMINI_API_KEY` (or with `LLM_PROVIDER=local`), embeddings use zero vectors and taste summaries use fallback text
- **Gemini free tier** (100 embed RPM, 30k TPM, 1k RPD): imports batch embeddings (`EMBEDDING_BATCH_SIZE=8`) and auto-retry on 429. A full ~400-film import may take 5–15 minutes for the embedding step — this is normal. Re-imports skip unchanged content via content hashes.
- Switching from Gemini to OpenAI requires `LLM_PROVIDER=openai`, `EMBEDDING_DIM=1536`, and re-running import/seed to regenerate embeddings
- Without `TMDB_API_KEY`, movies are created from Letterboxd data only (no poster enrichment)
- Production requires proper Firebase Admin SDK credentials
