import base64
from datetime import datetime
from typing import List, Optional, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_
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

    async def list_by_customer_id_paginated(
        self, customer_id: str, limit: int = 20, cursor: Optional[str] = None
    ) -> Tuple[List[BalanceTransaction], Optional[str]]:
        """
        Retrieves a page of customer balance transactions sorted descendingly (newest first)
        using deterministic cursor-based pagination to support scaling and performance.
        """
        query = select(BalanceTransaction).where(BalanceTransaction.customer_id == customer_id)

        if cursor:
            try:
                decoded = base64.b64decode(cursor.encode("utf-8")).decode("utf-8")
                cursor_time_str, cursor_id = decoded.split("|")
                cursor_time = datetime.fromisoformat(cursor_time_str)

                # Filter items strictly older/smaller than the cursor values for desc sorting
                query = query.where(
                    or_(
                        BalanceTransaction.created_at < cursor_time,
                        and_(
                            BalanceTransaction.created_at == cursor_time,
                            BalanceTransaction.id < cursor_id
                        )
                    )
                )
            except Exception:
                # Safe fallback if cursor is corrupted
                pass

        query = query.order_by(
            BalanceTransaction.created_at.desc(),
            BalanceTransaction.id.desc()
        ).limit(limit + 1)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            last_item = items[-1]
            last_time_str = last_item.created_at.isoformat()
            cursor_str = f"{last_time_str}|{last_item.id}"
            next_cursor = base64.b64encode(cursor_str.encode("utf-8")).decode("utf-8")

        return items, next_cursor
