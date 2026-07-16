from decimal import Decimal
from pydantic import BaseModel, Field

class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: str
    balance: Decimal

    class Config:
        from_attributes = True

class CreditRequest(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0.0"), decimal_places=4)

