from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class BalanceTransaction(Base):
    __tablename__ = "balance_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(18, 4), nullable=False)
    
    # Nullable fields for billing usage
    product_id = Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Numeric(18, 4), nullable=True)
    unit_price_at_time = Column(Numeric(18, 4), nullable=True)
    
    # Store creation date with timezone support, indexed for pagination
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default=func.now(), index=True)

    customer = relationship("Customer", back_populates="transactions")
    product = relationship("Product")
