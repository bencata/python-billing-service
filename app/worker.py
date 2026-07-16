import asyncio
from decimal import Decimal
from celery import Celery
from app.config import settings
from app.database import AsyncSessionLocal
from app.services.billing import BillingService

# Initialize Celery app
celery_app = Celery(
    "billing_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,          # Tasks acknowledged only AFTER successful completion
    worker_prefetch_multiplier=1,  # Fair work distribution for concurrent processing
)

async def _async_process_usage(payload: dict) -> None:
    async with AsyncSessionLocal() as session:
        # SQLite IMMEDIATE transaction is opened by database connection listeners.
        # This will block until database lock is cleared or timeout.
        billing_service = BillingService(session)
        await billing_service.execute_usage_billing(
            idempotency_key=payload["idempotency_key"],
            customer_id=payload["customer_id"],
            product_id=payload["product_id"],
            quantity=Decimal(payload["quantity"]),
        )
        await session.commit()

@celery_app.task(name="app.worker.process_usage_task", bind=True, max_retries=5)
def process_usage_task(self, payload: dict) -> None:
    """
    Celery task that executes async DB operations inside a synchronous thread execution context.
    """
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(_async_process_usage(payload)))
            future.result()
    except Exception as exc:
        # Retry with exponential backoff on transient errors (e.g. database locks)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
