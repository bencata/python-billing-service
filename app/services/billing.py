from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.customer import CustomerRepository
from app.repositories.transaction import TransactionRepository
from app.models.transaction import BalanceTransaction

class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.customer_repo = CustomerRepository(db)
        self.transaction_repo = TransactionRepository(db)

    async def add_credit(self, customer_id: str, amount: Decimal) -> BalanceTransaction:
        # Fetch the customer
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found."
            )
        
        # Update balance and write a transaction record
        customer.balance += amount
        transaction = await self.transaction_repo.create(
            customer_id=customer_id,
            amount=amount,
        )
        return transaction
