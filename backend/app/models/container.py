from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class Container(Base):
    __tablename__ = "containers"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    container_number = Column(String(20), nullable=False, index=True)
    container_size = Column(String(10), nullable=True)
    container_type = Column(String(20), nullable=True)
    soc_coc = Column(String(10), nullable=True)
    seal_number = Column(String(40), nullable=True)
    gross_weight = Column(Numeric(12, 2), nullable=True)
    tare_weight = Column(Numeric(12, 2), nullable=True)
    package_count = Column(Integer, nullable=True)
    current_status = Column(String(60), nullable=False, default="CONTAINER_PLANNED", index=True)
    current_location = Column(String(150), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Export lifecycle dates
    planned_date = Column(Date, nullable=True)
    empty_release_date = Column(Date, nullable=True)
    empty_pickup_date = Column(Date, nullable=True)
    factory_arrival_date = Column(Date, nullable=True)
    stuffing_start_date = Column(Date, nullable=True)
    stuffing_completed_date = Column(Date, nullable=True)
    sealed_date = Column(Date, nullable=True)
    gate_in_date = Column(Date, nullable=True)
    loaded_on_vessel_date = Column(Date, nullable=True)
    departed_date = Column(Date, nullable=True)

    # Import lifecycle dates
    expected_arrival_date = Column(Date, nullable=True)
    discharge_date = Column(Date, nullable=True, index=True)
    do_received_date = Column(Date, nullable=True)
    gate_out_date = Column(Date, nullable=True)
    delivery_date = Column(Date, nullable=True, index=True)
    empty_return_deadline = Column(Date, nullable=True, index=True)
    empty_return_date = Column(Date, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Free-day overrides
    demurrage_free_days = Column(Integer, nullable=True)
    detention_free_days = Column(Integer, nullable=True)
    demurrage_start_date = Column(Date, nullable=True)
    demurrage_end_date = Column(Date, nullable=True)
    detention_start_date = Column(Date, nullable=True)
    detention_end_date = Column(Date, nullable=True)

    metadata_json = Column(JSON, nullable=True)

    shipment = relationship("Shipment", backref="containers")
    events = relationship(
        "ContainerEvent", back_populates="container", cascade="all, delete-orphan"
    )
    demurrage_records = relationship(
        "ContainerDemurrageRecord",
        back_populates="container",
        cascade="all, delete-orphan",
    )
    detention_records = relationship(
        "ContainerDetentionRecord",
        back_populates="container",
        cascade="all, delete-orphan",
    )


class ContainerEvent(Base):
    __tablename__ = "container_events"

    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    event_type = Column(String(60), nullable=False, index=True)
    event_date = Column(Date, nullable=True, index=True)
    location = Column(String(150), nullable=True)
    source = Column(String(40), nullable=False, default="user", index=True)
    description = Column(Text, nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    container = relationship("Container", back_populates="events")


class DemurrageDetentionRule(Base):
    __tablename__ = "demurrage_detention_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    rule_type = Column(String(20), nullable=False, index=True)
    shipment_direction = Column(String(20), nullable=True)
    container_size = Column(String(10), nullable=True)
    container_type = Column(String(20), nullable=True)
    free_days = Column(Integer, nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="INR")
    rate_per_day = Column(Numeric(12, 2), nullable=True)
    slab_json = Column(JSON, nullable=True)
    source = Column(String(60), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContainerDemurrageRecord(Base):
    __tablename__ = "container_demurrage_records"

    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    free_days = Column(Integer, nullable=False, default=0)
    days_used = Column(Integer, nullable=False, default=0)
    chargeable_days = Column(Integer, nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="INR")
    estimated_amount = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String(30), nullable=False, default="estimated", index=True)
    source = Column(String(60), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    container = relationship("Container", back_populates="demurrage_records")


class ContainerDetentionRecord(Base):
    __tablename__ = "container_detention_records"

    id = Column(Integer, primary_key=True, index=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    free_days = Column(Integer, nullable=False, default=0)
    days_used = Column(Integer, nullable=False, default=0)
    chargeable_days = Column(Integer, nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="INR")
    estimated_amount = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String(30), nullable=False, default="estimated", index=True)
    source = Column(String(60), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    container = relationship("Container", back_populates="detention_records")
