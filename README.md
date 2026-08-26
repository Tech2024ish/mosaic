# MOSAIC

MOSAIC is a supply-chain decision intelligence platform for mid-market distributors, beginning with African distribution businesses. It sits above existing ERP, inventory, accounting, POS, and spreadsheet systems to explain what is happening, why it is happening, and what the business should do next.

This repository contains the initial production-oriented foundation: a modular-monolith FastAPI backend, PostgreSQL persistence and migrations, a minimal React frontend, Docker Compose development services, and automated quality checks. Decision-engine functionality is intentionally not implemented yet.

## Quick start

### With Docker

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Open the API at <http://localhost:8000/docs> and the frontend at <http://localhost:5173>.

The backend runs migrations on container startup. The database health endpoint is `GET /health` and the versioned API root is `GET /api/v1`.

### Local development

Requirements: Python 3.12+, Node.js 20+, npm, and PostgreSQL 15+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
alembic -c backend/alembic.ini upgrade head
uvicorn app.main:app --app-dir backend --reload
```

If the configured local PostgreSQL database does not exist yet, provision it using the credentials in `.env`:

```powershell
python -m scripts.provision_database
```

Run that command from `backend/` while the virtual environment is active, then apply migrations.

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

## Common commands

```powershell
pytest
ruff check .
ruff format --check .
mypy backend/app
alembic -c backend/alembic.ini upgrade head
```

## Repository layout

- `backend/app/core`: settings, security, and shared application concerns.
- `backend/app/models`: SQLAlchemy persistence models.
- `backend/app/schemas`: Pydantic API contracts.
- `backend/app/routers`: thin HTTP endpoints.
- `backend/app/services`: application orchestration and transaction boundaries.
- `backend/app/domain`: framework-independent future decision-engine modules.
- `backend/app/infrastructure`: database and external infrastructure adapters.
- `frontend`: React + TypeScript + Vite shell.
- `docs`: architecture and development documentation.
- `docker`: container entrypoint scripts.

## Scope boundary

The foundation does not include forecasting, machine learning, optimization, scenario simulation, recommendations, ERP capabilities, or a complete authentication product. Those will be added incrementally, beginning with the data-ingestion pipeline.

## Authentication

Register an account, log in, and use the returned bearer token for protected endpoints:

```powershell
$account = @{ email = "analyst@example.com"; name = "Amina Ndlovu"; password = "Secure password 123!" } | ConvertTo-Json
$registered = Invoke-RestMethod http://localhost:8000/api/v1/auth/register -Method Post -ContentType "application/json" -Body $account
$login = Invoke-RestMethod http://localhost:8000/api/v1/auth/login -Method Post -ContentType "application/json" -Body $account
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod http://localhost:8000/api/v1/auth/me -Headers $headers
```

Equivalent endpoints are `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, and authenticated `GET /api/v1/auth/me`. Registration creates a new organization; organization IDs are never accepted from clients.

## Phase 2 data ingestion

The first ingestion workflow supports tenant-aware sales-history CSV imports. See [docs/data-ingestion.md](docs/data-ingestion.md) and [examples/sales_history.csv](examples/sales_history.csv) for the format, lifecycle, validation, and idempotency rules. Authenticated requests use a signed bearer token; token issuance is intentionally deferred until the authentication milestone.
