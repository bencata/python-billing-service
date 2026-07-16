import hashlib
import json
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.usage import UsageEventRequest
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.outbox import OutboxRepository

router = APIRouter(prefix="/usage", tags=["Usage Ingestion"])

def calculate_hash(data: dict) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

@router.post("", status_code=status.HTTP_202_ACCEPTED)
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

    # Compute payload hash
    payload = event.model_dump()
    payload_hash = calculate_hash(payload)

    idempotency_repo = IdempotencyRepository(db)
    outbox_repo = OutboxRepository(db)

    # 1. Idempotency validation
    ik = await idempotency_repo.get(idempotency_key)
    if ik:
        if ik.payload_hash != payload_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency key conflict: payload mismatch."
            )
        if ik.status == "SUCCESS":
            # Already completed: return cached response with HTTP 200 OK
            return JSONResponse(status_code=status.HTTP_200_OK, content=ik.response_body)
        
        if ik.status == "PENDING":
            # In progress: return 202 Accepted
            return {
                "status": "processing",
                "message": "Usage report is currently being processed.",
                "idempotency_key": idempotency_key
            }

    # 2. Key does not exist or failed previously; record as PENDING and write to Outbox
    if ik:
        await idempotency_repo.update(idempotency_key, "PENDING")
    else:
        await idempotency_repo.create(idempotency_key, request.url.path, payload_hash)

    # Setup the outbox payload
    outbox_payload = {
        "idempotency_key": idempotency_key,
        "customer_id": event.customer_id,
        "product_id": event.product_id,
        "quantity": str(event.quantity),
    }
    await outbox_repo.create(event_type="PROCESS_USAGE", payload=outbox_payload)

    # Database session will commit automatically upon exiting get_db generator
    return {
        "status": "accepted",
        "message": "Usage report received and queued for processing.",
        "idempotency_key": idempotency_key
    }
