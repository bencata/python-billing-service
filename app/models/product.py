import uuid
from sqlalchemy import Column, String, Numeric
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    # Price per unit stored using NUMERIC(18, 4)
    price_per_unit = Column(Numeric(18, 4), nullable=False)
