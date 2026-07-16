from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import customers, products, usage
from alembic.config import Config
from alembic import command

def run_db_migrations():
    print("Running database migrations...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Database migrations complete.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations on startup
    run_db_migrations()
    yield

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

@app.get("/")
def read_root():
    return {
        "service": "Usage-Based Billing Service",
        "status": "healthy",
        "documentation": "/docs"
    }
