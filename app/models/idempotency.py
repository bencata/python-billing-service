from sqlalchemy import Column, String, DateTime, JSON, func
from app.database import Base

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String(255), primary_key=True)
    request_path = Column(String(255), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    status = Column(String(50), nullable=False)  # e.g., PENDING, SUCCESS, FAILED
    response_body = Column(JSON, nullable=True)   # Holds cached response body
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
