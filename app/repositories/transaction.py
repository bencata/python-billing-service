from typing import List, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.transaction import BalanceTransaction

class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        customer_id: str,
        amount: Decimal,
        product_id: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        unit_price_at_time: Optional[Decimal] = None,
    ) -> BalanceTransaction:
        transaction = BalanceTransaction(
            customer_id=customer_id,
            amount=amount,
            product_id=product_id,
            quantity=quantity,
            unit_price_at_time=unit_price_at_time,
        )
        self.db.add(transaction)
        await self.db.flush()
        return transaction

    async def list_by_customer_id(
        self, customer_id: str, limit: int = 20, offset: int = 0
    ) -> List[BalanceTransaction]:
        result = await self.db.execute(
            select(BalanceTransaction)
            .where(BalanceTransaction.customer_id == customer_id)
            .order_by(BalanceTransaction.created_at.desc(), BalanceTransaction.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
