# Senior Python Home Assignment: Usage-Based Billing Service

## Overview

Build a small usage-based billing service for a SaaS platform. Customers have a prepaid balance, products have a price per unit, and usage reports reduce the customer's balance.

The assignment is intentionally compact, but the core workflow must remain correct when requests are retried, duplicated, or processed concurrently. We are interested not only in working code, but also in the architectural decisions behind it.

## Assignment Goals

This assignment is designed to evaluate your ability to:

- Design a clear and maintainable Python service.
- Model a financial workflow and protect its invariants.
- Handle retries, duplicate requests, and concurrent updates safely.
- Make pragmatic architectural decisions and explain their trade-offs.
- Design a service that can evolve beyond a single local instance.
- Deliver code that is easy to run, test, and review.

## Expected Time

Please spend approximately **6-8 hours** on the assignment. We prefer a focused and well-explained solution over a large or over-engineered one.

If you do not complete everything, document what remains and explain what you would do next.

## Technology Requirements

- Python 3.10 or later.
- FastAPI or another well-justified Python web framework.
- SQLAlchemy, SQLModel, or another well-justified ORM/persistence approach.
- SQLite for the local implementation.
- Automated tests using a Python testing framework of your choice (e.g., pytest).

You may use additional libraries when they provide clear value. Please explain any important dependency or framework choice.

## Domain Model

The service should support the following concepts:

- **Customer**: has an identifier, name, and current prepaid balance.
- **Product**: has an identifier, name, and price per unit.
- **Usage event**: reports that a customer consumed a quantity of a product.
- **Balance transaction**: records every credit or charge applied to a customer.

Store monetary values using a safe representation. Avoid floating-point arithmetic for money.

## The Five Stages

### Stage 1: Core API and Persistence

Create the initial API and persistent data model.

The API must allow a caller to:

- Create and retrieve customers.
- Create and retrieve products.
- Add credit to a customer's balance.
- Retrieve a customer's current balance.
- List a customer's balance transactions.

At minimum, validate required fields, reject invalid monetary values, return appropriate HTTP status codes, and persist data between application restarts.

Provide database migrations or an equivalent repeatable database setup process. Include a small seed mechanism or clear API examples so the system can be evaluated quickly.

### Stage 2: Usage Processing

Add an endpoint that accepts a usage event containing:

- A caller-provided event or idempotency identifier.
- Customer identifier.
- Product identifier.
- Quantity consumed.

When valid usage is accepted, the service must calculate the charge using the product's current unit price, reduce the customer's balance, and create an immutable balance transaction.

The operation must fail without changing any data when the customer or product does not exist, the quantity is invalid, or the customer has insufficient funds.

The product price used for the charge must be stored with the transaction so that historical charges remain explainable after a product price changes.

### Stage 3: Reliability and Concurrency

Make usage processing safe under retries and concurrent requests.

The following behavior is required:

- Repeating the same request with the same idempotency identifier must not charge the customer twice.
- Reusing an idempotency identifier with a different request payload must be rejected.
- Two concurrent requests must not allow a customer's balance to become negative.
- Updating the balance and writing the corresponding transaction must succeed or fail as one logical operation.
- A failed request must be safe to retry.

Add automated tests that demonstrate these guarantees. At minimum, include tests for duplicate delivery, conflicting idempotency reuse, insufficient funds, and two concurrent charges competing for the same balance.

Briefly explain the consistency mechanism you selected, such as optimistic concurrency, a guarded atomic update, or another approach. Describe why it is appropriate for this implementation and where its limits are.

### Stage 4: Scale and Evolution

Assume the service may eventually process millions of usage events per day and run on multiple application instances.

Implement the following practical foundations:

- Paginated transaction history with deterministic ordering.
- Database indexes that support the main access patterns.
- Cancellation token propagation for database and request operations.
- Clear separation between API concerns, business rules, and persistence concerns.

Add a short **Scaling Notes** section to your project README covering:

- Which part of the current design will become the first bottleneck and why.
- How you would move from SQLite to a production database such as PostgreSQL or SQL Server.
- How idempotency remains correct across multiple service instances.
- Whether usage ingestion should remain synchronous or move to a queue, and what consistency trade-offs that introduces.
- How you would partition or archive a very large transaction ledger.
- How you would handle backpressure, transient failures, and poison messages if asynchronous processing were introduced.

You are not expected to implement distributed infrastructure. We are evaluating the quality and practicality of your reasoning.

### Stage 5: Production Readiness

Prepare the service so another engineer can evaluate and operate it easily.

Include:

- Unit and integration tests for the critical business flows.
- Structured logging with useful request and operation context, without logging secrets or sensitive data.
- Health endpoints that distinguish basic process health from dependency readiness.
- Centralized error handling with consistent error responses.
- OpenAPI/Swagger documentation.
- A Dockerfile and either Docker Compose or clear container run instructions.
- Configuration through environment variables, .env files, or standard Python configuration management (e.g., Pydantic Settings).
- A concise README with setup, run, migration, test, and API usage instructions.

The application should start with a small number of documented commands on a clean machine with the required SDK or Docker installed.

## Minimum Submission Requirements

A valid submission must include:

- A runnable Python service using Python 3.10 or later.
- SQLite persistence and a repeatable database setup process.
- Customers, products, credit operations, usage processing, and transaction history.
- Correct balance updates with an immutable transaction record.
- Idempotent usage processing that detects conflicting payloads.
- Protection against overspending during concurrent requests.
- Pagination and relevant database indexes.
- Automated tests for the critical correctness scenarios.
- Swagger/OpenAPI documentation.
- Container support.
- A project README containing setup instructions, architecture notes, assumptions, trade-offs, and scaling notes.

## Bonus Options

Bonus work is optional. Complete the core requirements before attempting it.

- Process usage asynchronously through a queue while preserving idempotency.
- Implement the transactional outbox pattern for reliable event publication.
- Add authentication and authorization with clearly defined permissions.
- Add rate limiting and demonstrate how limits are selected.
- Expose application metrics for request rate, latency, failures, duplicate events, and processing throughput.
- Add distributed tracing with correlation across API and background processing.
- Add caching where appropriate and document cache invalidation behavior.
- Provide a CI pipeline that builds, tests, scans dependencies, and builds the container image.
- Add a simple load test and summarize the result, bottleneck, and next optimization.
- Support multiple currencies without mixing balances or performing implicit conversion.

Bonus items are evaluated by their correctness and reasoning, not by quantity.

## General Guidelines

- Keep the solution focused. A modular monolith is completely acceptable.
- Prefer explicit, understandable code over unnecessary abstractions.
- Apply SOLID principles where they improve boundaries and testability, but do not create layers without a clear responsibility.
- Treat the transaction history as an audit trail. Avoid silently editing financial records.
- Enforce important invariants as close to the data as reasonably possible.
- Do not rely only on in-memory locks; assume more than one service instance may exist in the future.
- Do not commit secrets, credentials, generated build output, or local database files.
- Document assumptions rather than hiding ambiguity in the implementation.
- Make failure behavior explicit and return useful, consistent errors.
- You may simplify non-essential features if you explain the decision.

## Submission

Submit a link to a Git repository containing the complete solution.

Your repository should include:

- Source code.
- Automated tests.
- Database migrations.
- Docker and configuration files.
- A README with exact setup and verification instructions.
- A short description of architectural decisions, known limitations, and what you would improve with more time.

Please include example requests or a small API collection that demonstrates the main workflow:

1. Create a product.
2. Create a customer.
3. Add credit.
4. Report usage.
5. Retry the same usage event.
6. Retrieve the resulting balance and transaction history.

## Evaluation Criteria

The submission will be evaluated based on:

- **Correctness**: financial invariants, transactionality, idempotency, and concurrency behavior.
- **Architecture**: clear responsibilities, sensible boundaries, and justified trade-offs.
- **Code quality**: readability, maintainability, validation, and appropriate use of Python conventions (e.g., PEP 8, type hints).
- **Testing**: meaningful coverage of business-critical and failure scenarios.
- **Scalability thinking**: practical understanding of bottlenecks, multi-instance behavior, queues, and data growth.
- **Operational readiness**: observability, configuration, health checks, migrations, and containerization.
- **Documentation**: clear setup instructions, assumptions, limitations, and design reasoning.

We do not expect a production-scale platform within the time limit. We do expect production-minded decisions around the parts that matter most.
