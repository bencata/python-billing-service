from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.product import Product
from app.schemas.product import ProductCreate

class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, schema: ProductCreate) -> Product:
        product = Product(name=schema.name, price_per_unit=schema.price_per_unit)
        self.db.add(product)
        await self.db.flush()
        return product

    async def get_by_id(self, product_id: str) -> Optional[Product]:
        result = await self.db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()
