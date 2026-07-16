import asyncio
import os
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from alembic.config import Config
from alembic import command

# Point configuration to a local test-specific SQLite database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_billing.db"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.database import get_db
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

@pytest.fixture
async def db():
    # Create engine and configure immediate write transaction lock listener for SQLite tests
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    from sqlalchemy import event
    @event.listens_for(engine.sync_engine, "begin")
    def do_begin(conn):
        conn.exec_driver_sql("BEGIN IMMEDIATE")

    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with async_session() as session:
        yield session
        await session.rollback()
    await engine.dispose()

@pytest.fixture
async def client(db):
    # Override get_db dependency in FastAPI app with test db session
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    # entering AsyncClient context manager triggers startup and shutdown lifespan events
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
