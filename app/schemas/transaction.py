from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class TransactionResponse(BaseModel):
    id: str
    customer_id: str
    amount: Decimal
    product_id: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price_at_time: Optional[Decimal] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedTransactionsResponse(BaseModel):
    items: List[TransactionResponse]
    next_cursor: Optional[str] = None

