from app.logging_config import setup_logging
setup_logging()

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import customers, products, usage, health
from alembic.config import Config
from alembic import command
from app.services.outbox_publisher import start_outbox_publisher

def run_db_migrations():
    print("Running database migrations...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Database migrations complete.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations on startup
    run_db_migrations()
    
    # Setup shutdown event and start Outbox Publisher background worker
    shutdown_event = asyncio.Event()
    app.state.shutdown_event = shutdown_event
    publisher_task = asyncio.create_task(start_outbox_publisher(shutdown_event))
    
    yield
    
    # Trigger publisher stop
    shutdown_event.set()
    try:
        await asyncio.wait_for(publisher_task, timeout=5.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        publisher_task.cancel()
        try:
            await publisher_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="Usage-Based Billing Service",
    description="A Python-based usage-based billing service.",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(usage.router)
app.include_router(health.router)

@app.get("/")
def read_root():
    return {
        "service": "Usage-Based Billing Service",
        "status": "healthy",
        "documentation": "/docs"
    }
