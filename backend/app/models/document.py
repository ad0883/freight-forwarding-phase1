from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    doc_type = Column(String(80), nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    date_received = Column(Date, nullable=True)
    date_sent = Column(Date, nullable=True)
    file_url = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_required = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    shipment = relationship("Shipment", back_populates="documents")
