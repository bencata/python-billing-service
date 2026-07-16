# Usage-Based Billing Service

A high-performance, concurrent, and reliable usage-based billing service written in Python 3.12 using FastAPI, Celery, Redis, and SQLite.

This project implements a complete prepaid balance ledger, usage event ingestion endpoint with strict idempotency guarantees, and a resilient **Transactional Outbox Pattern** to decouple ingestion from billing processing.

---

## 🚀 Getting Started

### 1. Prerequisites
- Docker & Docker Compose
- Or, Python 3.12 with [uv](https://github.com/astral-sh/uv) package manager installed locally.

### 2. Run with Docker Compose
To build and start the entire stack (FastAPI web app, Redis broker, Celery worker, and shared SQLite volume mount):
```bash
docker compose up --build
```
Once started:
- **FastAPI Server**: available at [http://localhost:8000](http://localhost:8000)
- **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Liveness Probe**: [http://localhost:8000/health](http://localhost:8000/health)
- **Readiness Probe**: [http://localhost:8000/ready](http://localhost:8000/ready)

### 3. Run Locally (without Docker)
Initialize the virtual environment and install all dependencies (including dev tools):
```bash
uv sync --extra dev
```
Start the FastAPI server:
```bash
uv run uvicorn app.main:app --reload
```
Start the Celery worker (in a separate terminal):
```bash
uv run celery -A app.worker.celery_app worker --loglevel=info
```

### 4. Running the Integration Tests
The test suite utilizes an isolated in-memory/file test SQLite database and cleans up all data before each test. To run all 11 integration, concurrency, and outbox tests:
```bash
uv run --extra dev pytest
```

---

## 🛠️ Project Structure

```text
├── app/
│   ├── models/            # SQLAlchemy database schemas
│   ├── schemas/           # Pydantic request/response validators
│   ├── repositories/      # Database query abstraction layer
│   ├── services/          # Business logic engines (billing execution, outbox publisher loop)
│   ├── routers/           # FastAPI routers (customers, products, usage ingestion, health checks)
│   ├── database.py        # SQLite connections, pool configurations, and locks
│   ├── worker.py          # Celery application & task worker wrappers
│   ├── config.py          # Pydantic env settings reader
│   └── main.py            # FastAPI entry point & lifespan hooks
├── docs/
│   ├── design_and_architecture.md  # Deep dive into patterns & sequence diagrams
│   └── api_endpoints.md            # JSON schema payloads & example curls
├── tests/                 # pytest suite (CRUD, idempotency, concurrency, outbox pipeline)
├── pyproject.toml         # Python packaging & uv configurations
└── docker-compose.yml     # Multi-container service definition
```

---

## 📑 Documentation Index

- **[System Architecture & Design Docs](docs/design_and_architecture.md)**: Deep dive into the Transactional Outbox workflow, sequence diagrams, SQLite concurrency hooks, and table schemas.
- **[API Endpoint Reference](docs/api_endpoints.md)**: HTTP method definitions, request parameters, response JSON schemas, and example payloads.

---

## 📈 Scaling & Production Readiness Notes

### 1. Database Scaling (Moving from SQLite)
While our SQLite setup is highly optimized (using **WAL mode**, **busy timeouts**, and connection-level **`BEGIN IMMEDIATE`** write locking), SQLite is fundamentally limited to a single file and a single active write lock. To scale this system to thousands of concurrent transactions:
- **Replace SQLite with PostgreSQL**: Switch the driver from `aiosqlite` to `asyncpg` in `DATABASE_URL`.
- **Row-Level Locking (`SELECT FOR UPDATE`)**: In PostgreSQL, instead of locking the entire database on writes, we can lock *only the specific customer row* being billed. Replace the SQLite connection listener with a `select(...).with_for_update()` block in `CustomerRepository.get_by_id`. This allows high-throughput concurrent billing transactions for different customers simultaneously.

### 2. Horizontal Scaling of Workers
- Since tasks are queued in Redis, you can scale out by spawning multiple Celery worker containers.
- The `worker_prefetch_multiplier=1` and `task_acks_late=True` settings are already configured to distribute tasks fairly across multiple workers and guarantee that aborted/crashed tasks are automatically retried by other workers.

### 3. Outbox Publisher Resilience
- The background Outbox Publisher operates on short-lived sessions, releasing connection locks instantly after pulling pending tasks.
- If the Redis broker or Celery is down, the publisher safely catches the exception, leaves the events in `PENDING` state, and retries on the subsequent polling loop (0.5s later), ensuring zero data loss.
