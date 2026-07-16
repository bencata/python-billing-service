import uuid
from sqlalchemy import Column, String, Numeric
from sqlalchemy.orm import relationship
from app.database import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    # Using NUMERIC(18, 4) to store monetary balance safely
    balance = Column(Numeric(18, 4), nullable=False, default=0.0)

    # Relationship to transactions (resolved dynamically)
    transactions = relationship("BalanceTransaction", back_populates="customer", cascade="all, delete-orphan")
