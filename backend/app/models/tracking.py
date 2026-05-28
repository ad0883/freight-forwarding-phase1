"""Phase 21 Tracking Adapters models."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text

from app.db.session import Base


class TrackingProvider(Base):
    __tablename__ = "tracking_providers"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    provider_key = Column(String(60), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False)
    provider_type = Column(String(40), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    base_url = Column(String(500), nullable=True)
    supports_container_tracking = Column(Boolean, nullable=False, default=False)
    supports_vessel_tracking = Column(Boolean, nullable=False, default=False)
    supports_transport_tracking = Column(Boolean, nullable=False, default=False)
    supports_terminal_tracking = Column(Boolean, nullable=False, default=False)
    requires_credentials = Column(Boolean, nullable=False, default=False)
    is_manual = Column(Boolean, nullable=False, default=False)
    is_mock = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class TrackingAdapterConfig(Base):
    __tablename__ = "tracking_adapter_configs"
    id = Column(Integer, primary_key=True, index=True)
    tracking_provider_id = Column(Integer, ForeignKey("tracking_providers.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    config_name = Column(String(150), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    auth_type = Column(String(20), nullable=False, default="none")
    safe_config_json = Column(JSON, nullable=True)
    secret_ref = Column(String(255), nullable=True)
    last_verified_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class TrackingWatchItem(Base):
    __tablename__ = "tracking_watch_items"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    tracking_provider_id = Column(Integer, ForeignKey("tracking_providers.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=True, index=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=True)
    customs_case_id = Column(Integer, ForeignKey("customs_cases.id"), nullable=True)
    watch_type = Column(String(30), nullable=False, index=True)
    tracking_identifier = Column(String(120), nullable=False, index=True)
    secondary_identifier = Column(String(120), nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    last_sync_at = Column(DateTime, nullable=True)
    last_observation_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class TrackingObservation(Base):
    __tablename__ = "tracking_observations"
    id = Column(Integer, primary_key=True, index=True)
    tracking_watch_item_id = Column(Integer, ForeignKey("tracking_watch_items.id"), nullable=True, index=True)
    tracking_provider_id = Column(Integer, ForeignKey("tracking_providers.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=True)
    observation_type = Column(String(40), nullable=False, index=True)
    source = Column(String(40), nullable=False, default="manual")
    raw_status = Column(String(255), nullable=True)
    normalized_status = Column(String(80), nullable=False)
    status_time = Column(DateTime, nullable=True)
    location_text = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    eta = Column(DateTime, nullable=True)
    etd = Column(DateTime, nullable=True)
    vessel_name = Column(String(150), nullable=True)
    voyage_no = Column(String(60), nullable=True)
    confidence = Column(Float, nullable=False, default=0.5)
    is_customer_visible = Column(Boolean, nullable=False, default=False)
    observed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class TrackingEvent(Base):
    __tablename__ = "tracking_events"
    id = Column(Integer, primary_key=True, index=True)
    tracking_observation_id = Column(Integer, ForeignKey("tracking_observations.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=True)
    event_key = Column(String(80), nullable=False, index=True)
    event_label = Column(String(255), nullable=False)
    event_time = Column(DateTime, nullable=True)
    location_text = Column(String(255), nullable=True)
    confidence = Column(Float, nullable=False, default=0.5)
    matched_internal_state = Column(String(80), nullable=True)
    match_status = Column(String(30), nullable=False, default="new_information")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class TrackingSuggestedUpdate(Base):
    __tablename__ = "tracking_suggested_updates"
    id = Column(Integer, primary_key=True, index=True)
    tracking_observation_id = Column(Integer, ForeignKey("tracking_observations.id"), nullable=True, index=True)
    tracking_event_id = Column(Integer, ForeignKey("tracking_events.id"), nullable=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=True)
    suggestion_type = Column(String(40), nullable=False, index=True)
    target_entity_type = Column(String(30), nullable=False)
    target_entity_id = Column(Integer, nullable=True)
    target_field = Column(String(80), nullable=False)
    current_value = Column(String(255), nullable=True)
    suggested_value = Column(String(255), nullable=True)
    confidence = Column(Float, nullable=False, default=0.5)
    risk_level = Column(String(20), nullable=False, default="low")
    status = Column(String(20), nullable=False, default="pending_review", index=True)
    approval_request_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=True)
    exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class TrackingMismatch(Base):
    __tablename__ = "tracking_mismatches"
    id = Column(Integer, primary_key=True, index=True)
    tracking_observation_id = Column(Integer, ForeignKey("tracking_observations.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=True)
    mismatch_type = Column(String(40), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="medium")
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    linked_exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class TrackingSyncRun(Base):
    __tablename__ = "tracking_sync_runs"
    id = Column(Integer, primary_key=True, index=True)
    tracking_provider_id = Column(Integer, ForeignKey("tracking_providers.id"), nullable=True, index=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="queued", index=True)
    scope = Column(String(30), nullable=False, default="manual")
    watch_items_processed = Column(Integer, nullable=False, default=0)
    observations_created = Column(Integer, nullable=False, default=0)
    suggestions_created = Column(Integer, nullable=False, default=0)
    mismatches_created = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class TrackingActivityLog(Base):
    __tablename__ = "tracking_activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=True)
    tracking_provider_id = Column(Integer, ForeignKey("tracking_providers.id"), nullable=True)
    activity_type = Column(String(60), nullable=False)
    safe_summary = Column(Text, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)
