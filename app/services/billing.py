from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.customer import CustomerRepository
from app.repositories.product import ProductRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.idempotency import IdempotencyRepository
from app.models.transaction import BalanceTransaction

class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.customer_repo = CustomerRepository(db)
        self.product_repo = ProductRepository(db)
        self.transaction_repo = TransactionRepository(db)
        self.idempotency_repo = IdempotencyRepository(db)

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

    async def process_usage_sync(
        self,
        idempotency_key: str,
        request_path: str,
        payload_hash: str,
        customer_id: str,
        product_id: str,
        quantity: Decimal
    ) -> dict:
        """
        Processes a usage event synchronously with concurrency and idempotency checks.
        """
        # 1. Idempotency Check
        ik = await self.idempotency_repo.get(idempotency_key)
        if ik:
            if ik.payload_hash != payload_hash:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Idempotency key conflict: payload mismatch."
                )
            if ik.status == "PENDING":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Request is already processing."
                )
            if ik.status == "SUCCESS":
                return ik.response_body

        # 2. Create or Update Idempotency Record to PENDING
        if ik:
            await self.idempotency_repo.update(idempotency_key, "PENDING")
        else:
            await self.idempotency_repo.create(idempotency_key, request_path, payload_hash)

        # Flush to database to make sure other concurrent processes see PENDING
        await self.db.flush()

        try:
            async with self.db.begin_nested():
                # 3. Fetch Customer & Product
                customer = await self.customer_repo.get_by_id(customer_id)
                if not customer:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Customer with ID {customer_id} not found."
                    )

                product = await self.product_repo.get_by_id(product_id)
                if not product:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Product with ID {product_id} not found."
                    )

                # 4. Perform Business Logic Calculations & Invariant Checks
                charge = quantity * product.price_per_unit
                if customer.balance < charge:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient funds. Required: {charge}, Available: {customer.balance}"
                    )

                # 5. Deduct Balance & Create Transaction
                customer.balance -= charge
                tx = await self.transaction_repo.create(
                    customer_id=customer_id,
                    amount=-charge,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price_at_time=product.price_per_unit,
                )

                response_data = {
                    "transaction_id": tx.id,
                    "customer_id": customer_id,
                    "amount": str(-charge),
                    "remaining_balance": str(customer.balance),
                    "product_id": product_id,
                    "quantity": str(quantity),
                    "unit_price": str(product.price_per_unit)
                }

                # 6. Update Idempotency status to SUCCESS and save response
                await self.idempotency_repo.update(idempotency_key, "SUCCESS", response_body=response_data)
                return response_data

        except Exception as e:
            # The nested transaction (savepoint) has rolled back the customer/transaction changes.
            # We now update the idempotency key status to FAILED in the active parent transaction.
            await self.idempotency_repo.update(idempotency_key, "FAILED")
            await self.db.commit()
            
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred during processing: {str(e)}"
            ) from e

    async def execute_usage_billing(
        self,
        idempotency_key: str,
        customer_id: str,
        product_id: str,
        quantity: Decimal
    ) -> None:
        """
        Executes the actual billing logic asynchronously inside the Celery worker.
        """
        ik = await self.idempotency_repo.get(idempotency_key)
        if not ik:
            raise ValueError(f"Idempotency record not found for key: {idempotency_key}")

        if ik.status == "SUCCESS":
            # Already completed: skip (idempotency safety)
            return

        try:
            customer = await self.customer_repo.get_by_id(customer_id)
            if not customer:
                raise ValueError(f"Customer with ID {customer_id} not found.")

            product = await self.product_repo.get_by_id(product_id)
            if not product:
                raise ValueError(f"Product with ID {product_id} not found.")

            charge = quantity * product.price_per_unit
            if customer.balance < charge:
                # Insufficient funds business error: mark key as FAILED and save details
                ik.status = "FAILED"
                ik.response_body = {"detail": f"Insufficient funds. Required: {charge}, Available: {customer.balance}"}
                await self.db.flush()
                return

            customer.balance -= charge
            tx = await self.transaction_repo.create(
                customer_id=customer_id,
                amount=-charge,
                product_id=product_id,
                quantity=quantity,
                unit_price_at_time=product.price_per_unit,
            )

            response_data = {
                "transaction_id": tx.id,
                "customer_id": customer_id,
                "amount": str(-charge),
                "remaining_balance": str(customer.balance),
                "product_id": product_id,
                "quantity": str(quantity),
                "unit_price": str(product.price_per_unit)
            }

            ik.status = "SUCCESS"
            ik.response_body = response_data
            await self.db.flush()

        except Exception as e:
            # Let the database transaction rollback naturally.
            # We don't mark FAILED for system exceptions here, because we want Celery to retry
            # the task if there's a transient failure (e.g. SQLite database locked).
            raise e
