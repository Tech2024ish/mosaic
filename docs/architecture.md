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
