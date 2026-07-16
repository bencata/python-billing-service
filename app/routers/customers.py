from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.repositories.customer import CustomerRepository
from app.repositories.transaction import TransactionRepository
from app.services.billing import BillingService
from app.schemas.customer import CustomerCreate, CustomerResponse, CreditRequest
from app.schemas.transaction import TransactionResponse, PaginatedTransactionsResponse

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    schema: CustomerCreate,
    db: AsyncSession = Depends(get_db)
):
    repo = CustomerRepository(db)
    return await repo.create(schema)

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    repo = CustomerRepository(db)
    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return customer

@router.get("/{customer_id}/balance")
async def get_customer_balance(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    repo = CustomerRepository(db)
    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return {"customer_id": customer.id, "balance": customer.balance}

@router.post("/{customer_id}/credit", response_model=TransactionResponse)
async def add_customer_credit(
    customer_id: str,
    request: CreditRequest,
    db: AsyncSession = Depends(get_db)
):
    billing_service = BillingService(db)
    return await billing_service.add_credit(customer_id, request.amount)

@router.get("/{customer_id}/transactions", response_model=PaginatedTransactionsResponse)
async def list_customer_transactions(
    customer_id: str,
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    # Verify customer exists first
    repo = CustomerRepository(db)
    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    tx_repo = TransactionRepository(db)
    items, next_cursor = await tx_repo.list_by_customer_id_paginated(customer_id, limit, cursor)
    return {"items": items, "next_cursor": next_cursor}
