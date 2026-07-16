from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class TransactionResponse(BaseModel):
    id: str
    customer_id: str
    amount: Decimal
    product_id: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price_at_time: Optional[Decimal] = None
    created_at: datetime

    class Config:
        from_attributes = True
