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

For local frontend development, copy `frontend/.env.example` to `frontend/.env` when the API is not running at `http://localhost:8000`. The frontend reads `VITE_API_URL` at build time; it never embeds credentials, tokens, or tenant identifiers.

## Phase 0 baseline

The repository baseline is a modular monolith with centralized environment configuration, explicit SQLAlchemy session lifetimes, migration-managed PostgreSQL schema, authenticated tenant-scoped queries, safe API error handling, request correlation, and typed frontend API configuration. Production settings reject debug mode and development-only signing keys. `X-Request-ID` and `Server-Timing` are exposed to browser clients for operational diagnosis without exposing secrets.

Run the complete backend checks from the repository root:

```powershell
py -m pytest
py -m ruff check .
py -m ruff format --check .
py -m mypy .
```

Run migration and frontend checks from their respective directories:

```powershell
cd backend
py -m alembic current
cd ..\frontend
npm run build
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

## Phase 6 master data and inventory

The shared `POST /api/v1/imports` pipeline supports `products`, `warehouses`, `suppliers`, and `inventory_snapshots` in addition to `sales_history`. Master-data APIs are authenticated and tenant-scoped. Product, warehouse, and supplier codes are unique per organization; duplicate rows become validation errors. Inventory snapshots are historical and resolve product and warehouse references within the authenticated organization.

See [docs/data-ingestion.md](docs/data-ingestion.md) for supported CSV formats. Forecasting, optimization, ERP synchronization, and distributed ingestion infrastructure remain deferred.

## Scope boundary

The foundation does not include forecasting, machine learning, optimization, scenario simulation, recommendations, or ERP capabilities. Those will be added incrementally after the ingestion and operations foundations.

## Phase 12 sales analytics query

`GET /api/v1/analytics/sales` supports tenant-scoped summary metrics and optional grouped results. Use `group_by=date|product|warehouse`, `period=day|week|month` for date groups, and `limit=1..100`. Existing `date_from`, `date_to`, `product_code`, and `warehouse_code` filters remain supported. Example:

```text
GET /api/v1/analytics/sales?group_by=product&date_from=2026-01-01&date_to=2026-01-31
```

The endpoint requires a bearer token and performs aggregation in PostgreSQL using the authenticated user's organization scope. No database migration was required.

## Authentication

Register an account, log in, and use the returned bearer token for protected endpoints. Login creates a revocable database-backed session:

```powershell
$account = @{ email = "analyst@example.com"; name = "Amina Ndlovu"; password = "Secure password 123!" } | ConvertTo-Json
$registered = Invoke-RestMethod http://localhost:8000/api/v1/auth/register -Method Post -ContentType "application/json" -Body $account
$login = Invoke-RestMethod http://localhost:8000/api/v1/auth/login -Method Post -ContentType "application/json" -Body $account
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod http://localhost:8000/api/v1/auth/me -Headers $headers
Invoke-RestMethod http://localhost:8000/api/v1/auth/logout -Method Post -Headers $headers
```

The authentication endpoints are `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, authenticated `GET /api/v1/auth/me`, and authenticated `POST /api/v1/auth/logout`. Registration creates a new organization; organization IDs are never accepted from clients. Logout revokes only the current user's session.

## Phase 2 data ingestion

The first ingestion workflow supports tenant-aware sales-history CSV imports. See [docs/data-ingestion.md](docs/data-ingestion.md) and [examples/sales_history.csv](examples/sales_history.csv) for the format, lifecycle, validation, and idempotency rules. Authenticated requests use a signed bearer token tied to an active database session.

Phase 4 adds authenticated import history, detail/error inspection, retry controls for failed jobs, and tenant-scoped ingestion statistics. Distributed queues, Redis, Kafka, Celery, Kubernetes, advanced analytics, ML, forecasting, and optimization remain deferred.

Phase 5 adds cooperative import cancellation, tenant-scoped import activity history, streamed validation-error reports, structured ingestion logs, and lightweight operational metrics through the existing statistics API.

## Phase 7 reliability foundation

Phase 7 adds validated `X-Request-ID` correlation IDs, centralized safe operational logging, processing-attempt telemetry, failure categories, and the protected `GET /api/v1/imports/{import_id}/attempts` endpoint. `/ready` reports database-dependent readiness while `/health` remains available for health checks. Import statistics include attempt totals and average processing duration.

Job submission is behind an internal executor interface. The current adapter uses FastAPI `BackgroundTasks` and is intentionally not durable across restarts. A future durable queue can replace the adapter without changing API contracts or domain logic. Redis, Celery, Kafka, and distributed tracing remain deferred.

## Phase 8 performance and production hardening

Tenant-owned master-data list endpoints use database-side `offset`/`limit` pagination with a maximum page size of 100. Database pool sizing is configurable through `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, and `DB_POOL_TIMEOUT_SECONDS`; SQLite test runs do not receive PostgreSQL-only pool arguments. Request responses expose application duration through `Server-Timing`, while `X-Request-ID` remains the diagnostic correlation identifier.

The application remains a modular monolith. No cache, distributed queue, microservice, or external observability platform was added. Import processing remains streaming at file-read level and uses the existing transaction/state-transition protections; very large valid-row/error batches remain a future optimization boundary.

## Phase 9 business data API

Authenticated users can explore tenant-scoped products, warehouses, suppliers, inventory snapshots, and sales history. Master-data endpoints support `search`, whitelisted `sort`/`order`, and bounded `offset`/`limit` pagination. Sales history is available through `GET /api/v1/sales` with product, warehouse, date-range, sorting, and pagination filters. The frontend business-data panel uses these APIs without loading unbounded datasets.

## Phase 10 analytics and reporting

Analytics endpoints aggregate existing tenant-owned data in PostgreSQL:

- `GET /api/v1/analytics/summary` returns sales, revenue, average sale, master-data counts, and latest inventory totals.
- `GET /api/v1/analytics/sales` returns filtered sales totals for an optional date range, product, or warehouse.
- `GET /api/v1/analytics/sales/trend?period=day|week|month` returns database-grouped sales time series.
- `GET /api/v1/analytics/products/top?limit=10` ranks products by revenue.
- `GET /api/v1/analytics/warehouses/performance?limit=10` ranks warehouses by revenue.
- `GET /api/v1/analytics/inventory` summarizes inventory records for optional date, product, and warehouse filters.

Every analytics endpoint requires authentication and derives its organization filter from the authenticated user. Date ranges are validated, ranking limits are bounded to 100, and grouping/filter parameters are explicitly constrained. The frontend analytics overview presents summary cards, monthly trend rows, top products, and warehouse performance without loading raw sales data into the browser. Forecasting, low-stock thresholds, supplier performance scoring, and decision recommendations remain deferred.

## Phase 11 reporting and export

Reports compose the Phase 10 analytics layer into reusable business outputs:

- `GET /api/v1/reports/sales`
- `GET /api/v1/reports/products`
- `GET /api/v1/reports/inventory`
- `GET /api/v1/reports/warehouses`
- `GET /api/v1/reports/{sales|products|inventory|warehouses}/export?format=csv`

Reports accept validated date, product, warehouse, period, and bounded limit filters. CSV exports use stable UTF-8 columns, safe generated filenames, tenant-scoped database queries, and streaming responses. Sales and inventory exports are capped by `REPORT_EXPORT_MAX_ROWS` (50,000 by default); aggregate product and warehouse exports remain bounded by the report limit. No PDF, Excel, persistent report files, or separate reporting database was introduced.
