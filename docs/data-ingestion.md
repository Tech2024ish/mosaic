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

## Extension and performance

Dataset dispatch is isolated in `domain/ingestion/registry.py`; a future inventory handler can register its parser, validator, and normalizer without changing upload orchestration. The parser is iterator-based and storage reads are chunked. Database writes use SQLAlchemy’s unit of work and can be batched as volumes grow; the current in-process worker is intentionally simple and is not durable across process restarts. A durable queue/worker should be introduced when job volume or runtime makes that limitation material.
