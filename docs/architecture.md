# MOSAIC architecture

## Product boundary

MOSAIC is a decision layer above operational systems. Its first customer profile is a multi-warehouse, multi-supplier African distributor. The foundation deliberately stops before forecasting, optimization, scenarios, and recommendations.

## Why a modular monolith

The early product needs strong domain boundaries but does not yet have independently scalable or independently deployable workloads. A modular monolith keeps transactions, debugging, local development, and tenant authorization straightforward while separating HTTP, application orchestration, domain logic, persistence, and infrastructure. Later, a proven computational boundary (for example a long-running optimization job) can be extracted behind an explicit interface without first paying the operational cost of distributed systems.

## Boundaries

- Routers translate HTTP requests into application calls and return Pydantic schemas.
- Services own application workflows and transaction boundaries.
- Domain modules remain independent of FastAPI and persistence concerns.
- Models define PostgreSQL persistence shape and relationships.
- Infrastructure owns the SQLAlchemy engine and adapters for future queues, caches, and object storage.

## Multi-tenancy direction

Organizations are first-class records and users belong to exactly one organization. Future tenant-aware services must derive organization context from authenticated identity, scope every query through that context, and enforce ownership in service-level authorization checks. Database foreign keys and indexes provide integrity and lookup support; they are not treated as the entire isolation strategy. Row-level security can be evaluated when the data model and deployment topology warrant it.

## Data and migrations

PostgreSQL is the system of record. SQLAlchemy models use UUID identifiers, timezone-aware timestamps, explicit foreign keys, and exact types appropriate to each domain. Alembic is the production schema-change mechanism; runtime automatic table creation is intentionally absent.

## Security and operations

Configuration comes from environment variables. Password hashing uses `pwdlib`, CORS is explicit, errors are normalized at the application boundary, and health checks distinguish API availability from database availability. CI runs formatting, linting, type checking, and tests.

## Phase 3 authentication and sessions

Authentication remains inside the modular monolith. Registration creates a user and a new organization, while login verifies the password with `pwdlib`, creates a `user_sessions` record, and issues an HS256 JWT containing the user ID and session ID. `core.auth.get_current_user` remains the single bearer-token dependency used by imports and other protected routes; session-bearing tokens are checked for ownership, revocation, and expiry.

Logout revokes the current session in the database. Organization context is always derived from the authenticated user's organization; no endpoint accepts a client-selected organization for authorization. Password hashes, session secrets, and signing keys are never returned by API schemas.

Implemented: registration, login, token issuance, authenticated user resolution, database-backed session management, logout, revocation, and tenant-aware authenticated context.

Deferred: OAuth/social login, advanced identity providers, enterprise SSO, distributed session infrastructure, Redis-backed sessions, and microservices.

## Phase 6 master data

Master data uses the same modular-monolith ingestion boundary as sales history. Dataset dispatch is centralized in the ingestion registry, while dataset-specific normalization and persistence rules live in the domain/service layers. Products, warehouses, suppliers, and inventory snapshots are tenant-owned models exposed through tenant-scoped APIs. Inventory rows resolve stable business codes to same-organization product and warehouse records before persistence. The existing import lifecycle, retry, cancellation, audit events, validation reports, and statistics remain shared across datasets.

The Phase 6 migration is `0006_master_data`; no distributed queue or analytics infrastructure is introduced.

## Phase 7 reliability and observability

Every request receives a validated `X-Request-ID`; invalid or oversized client values are replaced with a UUID. The ID is available through a context variable and returned in the response. Standard-library logging is configured centrally with safe JSON operational fields and excludes credentials, tokens, authorization headers, uploaded content, and secrets.

Import execution is submitted through the `ImportJobExecutor` boundary. The production adapter remains an in-process FastAPI `BackgroundTasks` adapter. Each processing run creates an organization-scoped `ImportProcessingAttempt` with ordinal number, timestamps, status, duration, and safe failure category. Operational queries filter by authenticated organization.

`/health` checks health/database status and `/ready` expresses request-serving readiness based on database connectivity. Database-backed attempt statistics are returned through the existing authenticated import statistics API; no global tenant data or external metrics service is exposed.

## Phase 8 performance and scalability

Large master-data reads are bounded by tenant-scoped database pagination (`offset` default 0, `limit` default 50, maximum 100). Existing composite tenant/code, tenant/date, and import-operation indexes support the principal access paths; no speculative indexes were added. Statistics continue to aggregate in PostgreSQL, and validation reports remain streamed.

Database pool settings are configuration-driven for PostgreSQL and omitted for SQLite test engines. Request duration is surfaced as a lightweight `Server-Timing` response header and request IDs remain available to structured logs. The current import processor avoids holding request sessions during background work and retains conditional state transitions for retry, cancellation, and completion races.

Caching is intentionally unchanged: authentication/session decisions and tenant data are not cached. A future durable queue or bounded cache can be introduced behind the existing infrastructure boundaries if operational load proves it necessary; Redis, Celery, Kafka, Kubernetes, and microservices are not part of this phase.

## Phase 5 ingestion operations

Import administration remains tenant-scoped and uses the existing database and in-process `BackgroundTasks` worker. Failed jobs can be retried using the existing file and row fingerprints. Pending and processing jobs can be cooperatively cancelled; the processor checks the database between rows and uses a conditional completion update so a cancellation cannot be overwritten by a late completion.

Important lifecycle events are recorded in `import_events` with the import, organization, event type, optional actor, timestamp, and safe metadata. Validation reports are streamed from tenant-verified database errors as CSV. Operational statistics include import outcomes, row counts, cancellations, and retry requests. Logs use standard-library structured `extra` fields and never include uploaded content, credentials, tokens, or secrets.
