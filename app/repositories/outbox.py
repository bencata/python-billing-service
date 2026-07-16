from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.outbox import OutboxEvent

class OutboxRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, event_type: str, payload: dict) -> OutboxEvent:
        event = OutboxEvent(
            event_type=event_type,
            payload=payload,
            status="PENDING",
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_pending(self, limit: int = 100) -> List[OutboxEvent]:
        result = await self.db.execute(
            select(OutboxEvent)
            .where(OutboxEvent.status == "PENDING")
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_published(self, event_id: str) -> None:
        result = await self.db.execute(
            select(OutboxEvent).where(OutboxEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        if event:
            event.status = "PUBLISHED"
            await self.db.flush()

    async def mark_failed(self, event_id: str) -> None:
        result = await self.db.execute(
            select(OutboxEvent).where(OutboxEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        if event:
            event.status = "FAILED"
            await self.db.flush()
