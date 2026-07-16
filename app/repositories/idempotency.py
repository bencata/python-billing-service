from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.idempotency import IdempotencyKey

class IdempotencyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, key: str) -> Optional[IdempotencyKey]:
        result = await self.db.execute(select(IdempotencyKey).where(IdempotencyKey.key == key))
        return result.scalar_one_or_none()

    async def create(self, key: str, request_path: str, payload_hash: str) -> IdempotencyKey:
        ik = IdempotencyKey(
            key=key,
            request_path=request_path,
            payload_hash=payload_hash,
            status="PENDING",
        )
        self.db.add(ik)
        await self.db.flush()
        return ik

    async def update(self, key: str, status: str, response_body: Optional[dict] = None) -> None:
        ik = await self.get(key)
        if ik:
            ik.status = status
            if response_body is not None:
                ik.response_body = response_body
            await self.db.flush()
