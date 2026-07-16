import asyncio
import os
import pytest
import sqlalchemy as sa
from httpx import AsyncClient, ASGITransport
from alembic.config import Config
from alembic import command

# Point configuration to a local test-specific SQLite database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_billing.db"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# Configure Celery in eager mode for tests so tasks execute synchronously inline
from app.worker import celery_app
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)

from app.database import AsyncSessionLocal
from app.main import app

@pytest.fixture(scope="session", autouse=True)
def run_migrations():
    # Setup test database schema by running migrations
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    yield
    # Cleanup test database files
    for suffix in ["", "-wal", "-shm"]:
        path = f"./test_billing.db{suffix}"
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

@pytest.fixture(autouse=True)
async def clean_database():
    # Truncate tables before each test to ensure test isolation
    async with AsyncSessionLocal() as session:
        # SQLite does not support TRUNCATE, so we use DELETE
        await session.execute(sa.text("DELETE FROM balance_transactions;"))
        await session.execute(sa.text("DELETE FROM products;"))
        await session.execute(sa.text("DELETE FROM customers;"))
        await session.execute(sa.text("DELETE FROM idempotency_keys;"))
        await session.execute(sa.text("DELETE FROM outbox_events;"))
        await session.commit()

@pytest.fixture
async def client():
    # Manually enter app lifespan to trigger background outbox publisher
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
