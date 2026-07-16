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
    print(">>> [Outbox Publisher] Task started.")
    while not shutdown_event.is_set():
        try:
            # 1. Fetch pending events in a short-lived session
            pending = []
            async with AsyncSessionLocal() as session:
                repo = OutboxRepository(session)
                pending_events = await repo.get_pending(limit=20)
                # Store the event data in a detached list
                pending = [{"id": e.id, "payload": e.payload} for e in pending_events]
            
            if pending:
                print(f">>> [Outbox Publisher] Found {len(pending)} pending events.")
                published_ids = []
                for event in pending:
                    try:
                        print(f">>> [Outbox Publisher] Dispatching event {event['id']} to Celery.")
                        # Enqueue the Celery task
                        process_usage_task.delay(event["payload"])
                        published_ids.append(event["id"])
                    except Exception as celery_err:
                        print(f">>> [Outbox Publisher] Error dispatching event {event['id']}: {celery_err}")
                        continue
                
                # 2. Mark them as published in a separate short-lived session
                if published_ids:
                    async with AsyncSessionLocal() as session:
                        repo = OutboxRepository(session)
                        for event_id in published_ids:
                            await repo.mark_published(event_id)
                        await session.commit()
                        print(f">>> [Outbox Publisher] Marked {len(published_ids)} events as PUBLISHED.")
        except Exception as e:
            print(f">>> [Outbox Publisher] Exception in loop: {e}")
        
        # Wait a short duration before checking again
        try:
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break
    print(">>> [Outbox Publisher] Task stopped.")
