# Data ingestion

Phase 2 supports one dataset: `sales_history`. Uploads are tenant-owned and use this canonical schema:

| Column | Rules |
|---|---|
| `product_code` | Required, non-empty string. `SKU`, `Product ID`, and `product_id` are accepted aliases. |
| `sale_date` | Required ISO date: `YYYY-MM-DD`. |
| `quantity` | Required decimal greater than zero. |
| `unit_price` | Required decimal greater than or equal to zero. |
| `warehouse_code` | Required, non-empty string. `Warehouse` and `warehouse id` are accepted aliases. |

`examples/sales_history.csv` is a working sample.

## Lifecycle

`POST /api/v1/imports` accepts a multipart CSV upload and returns `202 Accepted` with a pending job. The server streams the file to local storage, records a SHA-256 identity, and schedules in-process background processing. Processing moves the job through `pending → processing → completed`; infrastructure or malformed-file failures become `failed`. Row validation failures do not fail the whole job: they are retained in `import_errors`, while valid rows are persisted to `sales_history`.

Use `GET /api/v1/imports/{import_id}` for status and summary, and `GET /api/v1/imports/{import_id}/errors` for displayable row errors. Both lookups require an authenticated user and always filter by that user’s organization.

## Tenant isolation and security

The organization is derived from the authenticated user record, never from a request organization ID. Jobs, staging rows, and sales rows all store organization ownership. Reads apply organization predicates; foreign keys provide referential integrity. The current authentication foundation uses signed HS256 bearer tokens, with login/token issuance intentionally deferred to the authentication milestone.

Authentication is now available through `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, and `GET /api/v1/auth/me`. Send the login response as `Authorization: Bearer <access_token>` when calling the import endpoints. Registration creates and associates a new organization server-side; clients cannot select a tenant.

Uploads are limited by `MAX_UPLOAD_SIZE_BYTES` (25 MB by default), streamed in 1 MB chunks, stored under generated UUID keys, and never opened using the client filename. CSV content is decoded as UTF-8 and parsed structurally; invalid headers and malformed records are reported. Stored files are local-development infrastructure behind `LocalFileStorage`, ready for an object-storage adapter later.

## Idempotency and duplicates

An import identity is SHA-256(content) scoped by organization and dataset type. A matching identity returns `409 Conflict`, so filename changes cannot cause a duplicate import. Normalized row fingerprints are SHA-256 hashes of the canonical row and are unique in `sales_history`; duplicate rows within a file or across imports become row-level `duplicate_record` errors. This conservative policy avoids double-counting but means a later correction must use a future explicit replacement/reconciliation workflow.

## Phase 4 operations

Authenticated operations endpoints are `GET /api/v1/imports`, `GET /api/v1/imports/{import_id}`, `GET /api/v1/imports/{import_id}/errors?offset=0&limit=50`, and `GET /api/v1/imports/stats`. They return only the current user's organization's jobs, errors, and aggregates. `POST /api/v1/imports/{import_id}/retry` is allowed only for failed jobs. It retains the source file and tenant, clears stale staging/errors, resets counters, and reuses the existing background processor. The state transition is `failed -> pending -> processing -> completed|failed`; row and file fingerprint duplicate protection remains active.

## Extension and performance

## Phase 6 master-data datasets

The same authenticated upload endpoint accepts these additional dataset types:

| Dataset | Required CSV columns |
|---|---|
| `products` | `product_code,product_name` |
| `warehouses` | `warehouse_code,warehouse_name` |
| `suppliers` | `supplier_code,supplier_name` |
| `inventory_snapshots` | `snapshot_date,product_code,warehouse_code,quantity_on_hand` |

Optional product columns are `description`, `category`, `unit_of_measure`, and `is_active`. Warehouses may include `location,is_active`; suppliers may include `contact_name,contact_email,contact_phone,is_active`; inventory may include `unit_cost`.

Codes are trimmed and normalized to uppercase. Required values, ISO dates, non-negative quantities/costs, booleans, and supplier email syntax are validated. Existing master-data codes and duplicate codes in a file are rejected as row-level `duplicate_record` errors; imports do not silently overwrite master data. Inventory references must resolve to product and warehouse records in the authenticated organization. Snapshots are historical and a repeated organization/product/warehouse/date is rejected.

Master-data APIs are `GET/POST /api/v1/products`, `GET/PATCH /api/v1/products/{id}`, `GET/POST /api/v1/warehouses`, `GET/PATCH /api/v1/warehouses/{id}`, `GET/POST /api/v1/suppliers`, `GET/PATCH /api/v1/suppliers/{id}`, and `GET/POST /api/v1/inventory` with `GET /api/v1/inventory/{id}`. All use the JWT-authenticated user's organization; no client organization ID is accepted for authorization. Existing history, retry, cancellation, audit-event, error-report, and statistics endpoints apply to every dataset.

The frontend provides dataset selection during upload and a tenant-scoped reference-data browser. Processing remains in-process and cooperative, so jobs are not durable across process restarts.

## Phase 7 reliability

Processing attempts are persisted in `import_processing_attempts`. Every processing run, including retries, records its ordinal number, timestamps, final status, duration, and safe failure category. `GET /api/v1/imports/{import_id}/attempts` is authenticated, paginated, deterministically ordered, and tenant-scoped. Import statistics include attempt totals and average duration.

Uploads continue through the internal executor boundary using FastAPI `BackgroundTasks`. This keeps local deployment simple while allowing a future durable worker adapter without changing the import API or domain logic. `X-Request-ID` is generated or safely propagated on every request and included in operational logs. `/ready` verifies the database dependency.

## Phase 5 administration and auditability

Import operations are available only to authenticated users and remain scoped to the user's organization. `POST /api/v1/imports/{import_id}/cancel` cooperatively cancels pending or processing imports. A processor checks for cancellation between rows and uses a conditional completion update; it is not forcibly terminated. Completed, failed, and already-cancelled imports cannot be cancelled.

`GET /api/v1/imports/{import_id}/events` exposes a paginated, deterministic activity history. Events include creation, processing start, completion, failure, retry request, and cancellation. `GET /api/v1/imports/{import_id}/errors/report` streams a server-generated CSV validation report with a safe generated filename. `GET /api/v1/imports/stats` includes cancellations and retry counts in addition to row totals.

Dataset dispatch is isolated in `domain/ingestion/registry.py`; a future inventory handler can register its parser, validator, and normalizer without changing upload orchestration. The parser is iterator-based and storage reads are chunked. Database writes use SQLAlchemy’s unit of work and can be batched as volumes grow; the current in-process worker is intentionally simple and is not durable across process restarts. A durable queue/worker should be introduced when job volume or runtime makes that limitation material.
