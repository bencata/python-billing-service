from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate

class CustomerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, schema: CustomerCreate) -> Customer:
        customer = Customer(name=schema.name)
        self.db.add(customer)
        await self.db.flush()
        return customer

    async def get_by_id(self, customer_id: str) -> Optional[Customer]:
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        return result.scalar_one_or_none()
