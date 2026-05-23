from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    shipment_code = Column(String(40), unique=True, index=True, nullable=False)
    type = Column(String(20), nullable=False)
    status = Column(String(30), nullable=False, default="active")
    exporter_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    importer_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    shipping_line = Column(String(150), nullable=True)
    vessel_name = Column(String(150), nullable=True)
    voyage_no = Column(String(80), nullable=True)
    origin_port = Column(String(150), nullable=True)
    dest_port = Column(String(150), nullable=True)
    container_no = Column(String(80), nullable=True)
    container_type = Column(String(20), nullable=True)
    etd = Column(Date, nullable=True)
    eta = Column(Date, nullable=True)
    vgm_cutoff_date = Column(Date, nullable=True)
    bl_cutoff_date = Column(Date, nullable=True)
    si_cutoff_date = Column(Date, nullable=True)
    do_received_date = Column(Date, nullable=True)
    container_delivered_date = Column(Date, nullable=True)
    bl_number = Column(String(120), nullable=True)
    booking_ref = Column(String(120), nullable=True)
    commodity = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    creator = relationship("User", back_populates="created_shipments")
    exporter = relationship(
        "Party", back_populates="export_shipments", foreign_keys=[exporter_id]
    )
    importer = relationship(
        "Party", back_populates="import_shipments", foreign_keys=[importer_id]
    )
    documents = relationship(
        "Document", back_populates="shipment", cascade="all, delete-orphan"
    )
    tasks = relationship("Task", back_populates="shipment", cascade="all, delete-orphan")
    alerts = relationship(
        "Alert", back_populates="shipment", cascade="all, delete-orphan"
    )
    followups = relationship(
        "FollowUpLog", back_populates="shipment", cascade="all, delete-orphan"
    )
    bl_management = relationship(
        "BLManagement", back_populates="shipment", cascade="all, delete-orphan", uselist=False
    )
    demurrage = relationship(
        "Demurrage", back_populates="shipment", cascade="all, delete-orphan", uselist=False
    )
    charges = relationship(
        "Charge", back_populates="shipment", cascade="all, delete-orphan"
    )
