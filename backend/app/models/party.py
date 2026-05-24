from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class Party(Base):
    __tablename__ = "parties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(40), nullable=False)
    contact_person = Column(String(150), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(80), nullable=True)
    country = Column(String(120), nullable=True)
    gstin = Column(String(80), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    deactivated_at = Column(DateTime, nullable=True)
    deactivated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    deactivation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    export_shipments = relationship(
        "Shipment", back_populates="exporter", foreign_keys="Shipment.exporter_id"
    )
    import_shipments = relationship(
        "Shipment", back_populates="importer", foreign_keys="Shipment.importer_id"
    )
    followups = relationship("FollowUpLog", back_populates="party")
    charges = relationship("Charge", back_populates="party")
