from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Demurrage(Base):
    __tablename__ = "demurrage"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), unique=True, nullable=False, index=True)
    free_days = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=True)
    rate_per_day = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(10), nullable=False, default="INR")
    alert_at_days = Column(Integer, nullable=False, default=3)
    container_count = Column(Integer, nullable=False, default=1)
    status = Column(String(40), nullable=False, default="not_started")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    shipment = relationship("Shipment", back_populates="demurrage")
