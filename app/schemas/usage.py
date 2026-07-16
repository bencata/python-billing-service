from decimal import Decimal
from pydantic import BaseModel, Field

class UsageEventRequest(BaseModel):
    customer_id: str
    product_id: str
    quantity: Decimal = Field(..., gt=Decimal("0.0"), decimal_places=4)
