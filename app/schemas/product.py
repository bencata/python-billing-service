from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price_per_unit: Decimal = Field(..., ge=Decimal("0.0"), decimal_places=4)

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: str

    model_config = ConfigDict(from_attributes=True)
