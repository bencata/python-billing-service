import asyncio
import logging
from app.database import AsyncSessionLocal
from app.repositories.outbox import OutboxRepository
from app.worker import process_usage_task

logger = logging.getLogger(__name__)

async def start_outbox_publisher(shutdown_event: asyncio.Event) -> None:
    """
    Background loop that polls SQLite for PENDING outbox events,
    dispatches them to Celery, and updates their status to PUBLISHED.
    """
    logger.info("Outbox publisher background task started.")
    while not shutdown_event.is_set():
        try:
            async with AsyncSessionLocal() as session:
                repo = OutboxRepository(session)
                pending = await repo.get_pending(limit=20)
                
                if pending:
                    for event in pending:
                        try:
                            # Enqueue the Celery task
                            process_usage_task.delay(event.payload)
                            
                            # Mark as published in same transaction
                            await repo.mark_published(event.id)
                        except Exception as celery_err:
                            logger.error(
                                f"Failed to dispatch outbox event {event.id} to Celery: {celery_err}. "
                                "Leaving it in PENDING state."
                            )
                            # If Celery is down, leave the event as PENDING so it will be retried
                            continue
                    
                    await session.commit()
        except Exception as e:
            logger.error(f"Error in outbox publisher loop: {e}")
        
        # Wait a short duration before checking again
        try:
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break
    logger.info("Outbox publisher background task stopped.")
