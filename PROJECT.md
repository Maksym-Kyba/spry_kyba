# Meetings App — Repository Map & Architecture

## 1. Architecture Decision: Monorepo

* **Decision**: One repository, not three. Backend, frontend, database configuration, infrastructure, and CI live in a single repository.
* **Atomic changes**: One commit changes both the API and the client that calls it, preventing them from drifting apart.
* **Context window**: An AI agent can read the endpoint, the model, the migration, and the component that renders it in one pass, eliminating guesswork at integration time.
* **Cost**: Release cycles and CI are coupled. For a small team and an evolving product, development context outweighs independence.

---

## 2. Repository Layout
.
├── backend/                  # FastAPI app, models, migrations, tests. One Dockerfile.
│   ├── app/                  # Application package
│   │   ├── main.py           # Creates app, registers routers and CORS
│   │   ├── config.py         # Settings from environment (pydantic-settings)
│   │   ├── db.py             # Async engine and session dependency
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic request/response models
│   │   └── routers/          # HTTP layer (meetings.py, participants.py)
│   ├── alembic/              # Versioned schema migrations
│   ├── alembic.ini
│   ├── tests/                # Pytest + httpx tests
│   ├── pyproject.toml        # Backend dependencies (managed with uv)
│   └── Dockerfile
├── frontend/                 # React + TypeScript SPA built with Vite. One Dockerfile.
│   ├── src/
│   │   ├── components/ui/    # shadcn/ui components (not edited by hand)
│   │   ├── components/       # Application components (list, form, dialogs)
│   │   └── lib/api.ts        # Typed API client using relative URLs (/api/...)
│   ├── nginx.conf            # Serves static files and proxies /api to backend
│   └── Dockerfile            # Multi-stage: Node build → Nginx
├── infra/                    # CloudFormation templates and deployment scripts
├── .github/workflows/        # CI workflows (to be implemented)
├── docker-compose.yml        # Local stack orchestration
├── .env.example              # Environment variables template
├── Makefile                  # Single entry point for all routine commands
├── pyproject.toml            # Root-level Python configuration
├── SPEC.md                   # Detailed product specification
└── README.md                 # Setup and run instructions

> *Rule*: If a new folder is added, this table and map must be updated in the same commit.

---

## 3. Technology & Pinned Versions

| Layer | Choice |
|---|---|
| **Backend** | Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) with asyncpg, Alembic, uvicorn |
| **Backend tooling** | `uv`, `pytest`, `httpx`, `ruff` |
| **Frontend** | React, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query, react-hook-form, zod, date-fns |
| **Frontend tooling** | `npm`, `oxlint`, `Prettier` |
| **Database** | PostgreSQL 17 (`postgres:17-alpine` locally, Aurora in AWS) |
| **Local runtime** | Docker Compose, Nginx for frontend container |

**Pinned Image Tags:**
* Frontend: `node:24-alpine`, `nginx:1.29-alpine`
* Backend: `python:3.14-slim`
* Database: `postgres:17-alpine`

---

## 4. Contracts & Rules

### 4.1 Frontend ↔ Backend
* **Base path**: `/api`. All bodies are JSON. The frontend uses relative URLs.
* **Proxying**: In Docker, Nginx proxies `/api` to `backend:8000`. Locally without Docker, Vite dev-server proxy forwards `/api` to `localhost:8000`.
* **Datetimes**: ISO 8601 strings with timezone offset on input. Backend stores and returns UTC (`Z`). Frontend renders local time.
* **IDs**: UUIDs serialized as strings.

### 4.2 Backend ↔ Database
* Schema is created and modified **exclusively** through Alembic migrations (`Base.metadata.create_all()` is forbidden).
* Tables: `meetings`, `participants`, and association table `meeting_participants` (composite PK, both FKs `ON DELETE CASCADE`). Deleting a meeting removes its association rows but never deletes participants.
* Configuration: Loaded via `DATABASE_URL`.

### 4.3 Environment Variables
* `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: Database container initialization.
* `DB_PORT`: Host port for Postgres (default `5432`).
* `DATABASE_URL`: Async connection string for the backend.
* `CORS_ORIGINS`: Allowed browser origins.
* `.env` is gitignored; secrets are never committed.

---

## 5. Docker Compose

`docker-compose.yml` defines three services at the root:

| Service | Image / Build | Port (Host:Container) | Depends On | Readiness |
|---|---|---|---|---|
| **db** | `postgres:17-alpine` | `${DB_PORT:-5432}:5432` | None | Healthcheck with `pg_isready`; data in `pgdata` volume |
| **backend** | `build ./backend` | `8000:8000` | `db` (condition: `service_healthy`) | Answers `GET /api/health` (queries database) |
| **frontend** | `build ./frontend` | `3000:80` | `backend` | Nginx serves static files and proxies `/api` |

* **Startup order**: `db` starts and initializes $\rightarrow$ `backend` starts once healthy, runs `alembic upgrade head`, then starts `uvicorn` $\rightarrow$ `frontend` starts last.
* **Restart Policy**: All services have `restart: unless-stopped` configured.

---

## 6. Local Development (`Makefile`)

| Command | Effect |
|---|---|
| `make up` / `make down` | Start or stop the stack (auto-creates `.env` from `.env.example`) |
| `make seed` | Insert sample data |
| `make test` | Run backend tests against a separate test database |
| `make lint` / `make format` | Code linting and formatting (`ruff`, `oxlint`, `Prettier`) |
| `make migration m="..."` | Autogenerate a new Alembic migration |
| `make clean` | Stop stack and delete the database volume |
| `make dev-backend` / `make dev-frontend` | Run services outside Docker |

After `make up`, access the frontend at `http://localhost:3000` and API docs at `http://localhost:8000/api/docs`.

---

## 7. Deployment to AWS

* **Infrastructure**: Described via CloudFormation templates in `infra/` and managed through the `Makefile` (default region: `us-east-1`).
* **Backend**: AWS Lambda running the backend container image via Lambda Web Adapter (no load balancer or public IP).
* **Database**: Aurora Serverless v2 (PostgreSQL 17, scaling 0–1 ACU), running in private subnets.
* **Frontend**: Private S3 bucket behind CloudFront.
* **Credentials rules**: Access keys are never committed. CI/CD integration and OIDC authentication will be configured alongside GitHub Actions workflows.

---

## 8. CI/CD

* **Status**: GitHub Actions workflows in `.github/workflows/` are planned.
* **Current workflow**: Checks, builds, and deployments are executed locally using `Makefile` targets. Minimum expected checks on code changes: backend `ruff` and tests, frontend lint and build.

---

## 9. Out of Scope

Authentication, user accounts, editing/deleting participants, recurring meetings, per-user time zones, notifications, calendar sync, pagination. No additional queues, caches, or secondary databases are added without updating this document.
