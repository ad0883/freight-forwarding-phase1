"""Phase 20 Transport + GPS layer models."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, Numeric, String, Text

from app.db.session import Base


class TransportJob(Base):
    __tablename__ = "transport_jobs"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    job_number = Column(String(60), nullable=False, unique=True, index=True)
    job_type = Column(String(40), nullable=False, index=True)
    movement_type = Column(String(40), nullable=False, default="containerized")
    status = Column(String(40), nullable=False, default="planned", index=True)
    priority = Column(String(10), nullable=False, default="p3")
    transporter_party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    transporter_name = Column(String(255), nullable=True)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to_name = Column(String(150), nullable=True)
    pickup_location = Column(String(255), nullable=True)
    delivery_location = Column(String(255), nullable=True)
    origin_address = Column(Text, nullable=True)
    destination_address = Column(Text, nullable=True)
    planned_pickup_at = Column(DateTime, nullable=True)
    actual_pickup_at = Column(DateTime, nullable=True)
    planned_delivery_at = Column(DateTime, nullable=True)
    actual_delivery_at = Column(DateTime, nullable=True)
    planned_empty_return_at = Column(DateTime, nullable=True)
    actual_empty_return_at = Column(DateTime, nullable=True)
    eta = Column(DateTime, nullable=True)
    last_location_text = Column(String(255), nullable=True)
    last_latitude = Column(Float, nullable=True)
    last_longitude = Column(Float, nullable=True)
    last_location_at = Column(DateTime, nullable=True)
    delay_reason = Column(Text, nullable=True)
    vehicle_id = Column(Integer, ForeignKey("transport_vehicles.id"), nullable=True, index=True)
    driver_id = Column(Integer, ForeignKey("transport_drivers.id"), nullable=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class TransportJobContainer(Base):
    __tablename__ = "transport_job_containers"
    id = Column(Integer, primary_key=True, index=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=True, index=True)
    container_number = Column(String(20), nullable=True)
    movement_role = Column(String(30), nullable=False, default="pickup")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class TransportVehicle(Base):
    __tablename__ = "transport_vehicles"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    transporter_party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    vehicle_number = Column(String(30), nullable=False, index=True)
    vehicle_type = Column(String(30), nullable=False, default="trailer_20")
    capacity = Column(String(60), nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    insurance_valid_until = Column(DateTime, nullable=True)
    fitness_valid_until = Column(DateTime, nullable=True)
    permit_valid_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class TransportDriver(Base):
    __tablename__ = "transport_drivers"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    transporter_party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    driver_name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=True)
    license_number = Column(String(40), nullable=True)
    license_valid_until = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class TransportMilestone(Base):
    __tablename__ = "transport_milestones"
    id = Column(Integer, primary_key=True, index=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=False, index=True)
    milestone_key = Column(String(80), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    planned_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_by_name = Column(String(150), nullable=True)
    location_text = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    evidence_document_version_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class TransportLocationUpdate(Base):
    __tablename__ = "transport_location_updates"
    id = Column(Integer, primary_key=True, index=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=False, index=True)
    source = Column(String(30), nullable=False, default="manual")
    location_text = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recorded_by_name = Column(String(150), nullable=True)
    accuracy_meters = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TransportDocument(Base):
    __tablename__ = "transport_documents"
    id = Column(Integer, primary_key=True, index=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    document_version_id = Column(Integer, nullable=True)
    document_type = Column(String(60), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    visible_to_customer = Column(Boolean, nullable=False, default=False)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class TransportException(Base):
    __tablename__ = "transport_exceptions"
    id = Column(Integer, primary_key=True, index=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=True)
    exception_type = Column(String(40), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="open", index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    delay_minutes = Column(Integer, nullable=True)
    linked_exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class TransportActivityLog(Base):
    __tablename__ = "transport_activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    activity_type = Column(String(60), nullable=False)
    safe_summary = Column(Text, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class TransportChargeRef(Base):
    __tablename__ = "transport_charge_refs"
    id = Column(Integer, primary_key=True, index=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    charge_id = Column(Integer, ForeignKey("charges.id"), nullable=True)
    charge_type = Column(String(60), nullable=False, default="transport")
    estimated_amount = Column(Numeric(14, 2), nullable=True)
    actual_amount = Column(Numeric(14, 2), nullable=True)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)
