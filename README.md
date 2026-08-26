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
