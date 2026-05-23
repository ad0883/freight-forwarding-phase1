from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class BLManagement(Base):
    __tablename__ = "bl_management"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), unique=True, nullable=False, index=True)
    bl_type = Column(String(40), nullable=False, default="Ocean")
    draft_received = Column(Date, nullable=True)
    corrections = Column(Text, nullable=True)
    approval_date = Column(Date, nullable=True)
    final_bl_date = Column(Date, nullable=True)
    surrender_done = Column(Boolean, nullable=False, default=False)
    telex_release = Column(Boolean, nullable=False, default=False)
    file_url = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    shipment = relationship("Shipment", back_populates="bl_management")
