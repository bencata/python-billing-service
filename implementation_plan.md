# Implementation Plan - Python Usage-Based Billing Service

We are building a usage-based billing service in Python with SQLite, Celery, and Redis. To ensure stability and correctness, we will build this in four distinct phases.

---

## Technical Stack & Key Patterns

- **API Framework**: FastAPI
- **Database**: SQLite (managed via SQLAlchemy `async` engine with `aiosqlite`)
- **Migrations**: Alembic
- **Task Queue**: Celery (using Redis as broker)
- **Concurrency**: SQLite natively serializes write transactions when using `IMMEDIATE` or `EXCLUSIVE` transaction modes. We will configure SQLAlchemy connection listeners to begin transactions with `BEGIN IMMEDIATE` for write operations to prevent concurrent modification issues and guarantee that the customer's balance is never overdrawn.
- **Idempotency**: Dedicated `idempotency_keys` table to record request state, payload, and response cache.
- **Asynchronous Pattern**: Transactional Outbox Pattern. API writes events to `outbox_events` table; a publisher sends them to Celery; Celery worker processes the events transactionally. Both services access the SQLite database file via a shared Docker volume.

---

## Development Phases

### Phase 1: Project Setup, SQLite Integration, and CRUD API (Stage 1)
In this phase, we establish the Docker environment (FastAPI and Redis), database schema, migrations, and core CRUD routes.

- **Tasks**:
  - Configure `docker-compose.yml` with a Redis service. FastAPI and Celery will run as services sharing a persistent Docker volume containing the SQLite database file.
  - Setup SQLAlchemy database session management and config (using `sqlite+aiosqlite:////data/billing.db`).
  - Define `Customer`, `Product`, and `BalanceTransaction` SQLAlchemy models.
  - Setup Alembic and write initial database migration.
  - Implement FastAPI routers for:
    - Creating and retrieving Customers.
    - Creating and retrieving Products.
    - Adding credit to a Customer's balance (creates a transaction).
    - Listing a Customer's balance transactions.
- **Verification**:
  - Write integration tests using a separate/temporary in-memory or file-based SQLite database.

---

### Phase 2: Usage Ingestion and Synchronous Concurrency & Idempotency (Stages 2 & 3 Baseline)
Before making the flow asynchronous, we implement and verify the core pricing, concurrency, and idempotency logic synchronously. This serves as a solid base.

- **Tasks**:
  - Define `IdempotencyKey` database model.
  - Implement synchronous `/usage` endpoint.
  - Implement business logic for processing usage events:
    - Open write transactions using SQLite's `IMMEDIATE` mode.
    - Fetch product price, calculate charge, and check for sufficient funds.
    - Deduct balance and insert `BalanceTransaction`.
    - Enforce idempotency: prevent double charging and reject payload mismatches.
- **Verification**:
  - Concurrency tests: Spin up multiple threads/tasks competing for the same customer balance. Ensure SQLite correctly handles locking and serializes the writes, preventing negative balances.
  - Idempotency tests: Ensure duplicates are handled correctly and mismatched payloads are rejected.

---

### Phase 3: Transactional Outbox Pattern and Celery Integration (Asynchronous Ingestion)
We migrate the synchronous processing to an asynchronous architecture using Celery and the Transactional Outbox Pattern.

- **Tasks**:
  - Configure Celery with Redis broker in `docker-compose.yml`, mounting the same database volume.
  - Create the `OutboxEvent` database model.
  - Refactor `/usage` endpoint:
    - Write a pending `idempotency_key` and write a `PROCESS_USAGE` event to the `outbox_events` table in a single transaction.
    - Return `202 Accepted` to the client.
  - Create an Outbox Publisher background task/process that pulls pending outbox events, enqueues them to Celery, and updates their status to `PUBLISHED`.
  - Implement the Celery task (`process_usage`) to execute the business logic built in Phase 2.
- **Verification**:
  - Run end-to-end integration tests verifying async flow (events enqueued -> outbox published -> worker executes -> balance updated).
  - Test worker failure/retry resilience.

---

### Phase 4: Production Readiness, Scaling, and Polish (Stages 4 & 5)
In this final phase, we optimize the service for operations and scaling.

- **Tasks**:
  - Implement deterministic cursor-based pagination for listing transactions.
  - Add database indexes for common search patterns (e.g., customer transactions sorted by date).
  - Implement health checks (`/health` and `/ready`).
  - Set up structured JSON logging throughout the application.
  - Write the project README containing setup instructions, architecture notes, assumptions, trade-offs, and scaling notes.
- **Verification**:
  - Verify container builds and docker-compose execution from a fresh environment.
  - Final test run and code cleanup.
