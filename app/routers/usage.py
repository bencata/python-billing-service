import hashlib
import json
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.usage import UsageEventRequest
from app.services.billing import BillingService

router = APIRouter(prefix="/usage", tags=["Usage Ingestion"])

def calculate_hash(data: dict) -> str:
    # Deterministic JSON hashing
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

@router.post("", status_code=status.HTTP_200_OK)
async def report_usage(
    request: Request,
    event: UsageEventRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db)
):
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header is required."
        )

    # Compute hash of incoming event payload
    payload = event.model_dump()
    payload_hash = calculate_hash(payload)

    billing_service = BillingService(db)
    
    # Process the usage event synchronously
    return await billing_service.process_usage_sync(
        idempotency_key=idempotency_key,
        request_path=request.url.path,
        payload_hash=payload_hash,
        customer_id=event.customer_id,
        product_id=event.product_id,
        quantity=event.quantity,
    )
