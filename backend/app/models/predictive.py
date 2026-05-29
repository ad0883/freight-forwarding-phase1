"""Phase 23 Predictive Intelligence models."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text

from app.db.session import Base


class PredictionModel(Base):
    __tablename__ = "prediction_models"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    model_key = Column(String(60), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    model_type = Column(String(30), nullable=False, default="rule_based")
    status = Column(String(20), nullable=False, default="active", index=True)
    risk_domain = Column(String(40), nullable=False, index=True)
    version = Column(String(20), nullable=False, default="1.0")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class PredictionRun(Base):
    __tablename__ = "prediction_runs"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    run_number = Column(String(60), nullable=False, index=True)
    scope = Column(String(30), nullable=False, default="manual")
    status = Column(String(20), nullable=False, default="running", index=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    models_run = Column(Integer, nullable=False, default=0)
    records_created = Column(Integer, nullable=False, default=0)
    high_risk_count = Column(Integer, nullable=False, default=0)
    medium_risk_count = Column(Integer, nullable=False, default=0)
    low_risk_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class PredictionRecord(Base):
    __tablename__ = "prediction_records"
    id = Column(Integer, primary_key=True, index=True)
    prediction_run_id = Column(Integer, ForeignKey("prediction_runs.id"), nullable=True, index=True)
    prediction_model_id = Column(Integer, ForeignKey("prediction_models.id"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    prediction_key = Column(String(80), nullable=False, index=True)
    risk_domain = Column(String(40), nullable=False, index=True)
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(Integer, nullable=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=True)
    transport_job_id = Column(Integer, ForeignKey("transport_jobs.id"), nullable=True)
    customs_case_id = Column(Integer, ForeignKey("customs_cases.id"), nullable=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    risk_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String(20), nullable=False, default="low", index=True)
    confidence = Column(Float, nullable=False, default=0.5)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    predicted_event = Column(String(120), nullable=True)
    predicted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    prediction_window_start = Column(DateTime, nullable=True)
    prediction_window_end = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    linked_exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=True)
    linked_approval_request_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class PredictionExplanation(Base):
    __tablename__ = "prediction_explanations"
    id = Column(Integer, primary_key=True, index=True)
    prediction_record_id = Column(Integer, ForeignKey("prediction_records.id"), nullable=False, index=True)
    factor_key = Column(String(80), nullable=False)
    factor_label = Column(String(255), nullable=False)
    factor_value = Column(String(255), nullable=True)
    impact = Column(String(20), nullable=False, default="medium")
    weight = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class PredictionRecommendation(Base):
    __tablename__ = "prediction_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    prediction_record_id = Column(Integer, ForeignKey("prediction_records.id"), nullable=False, index=True)
    recommendation_type = Column(String(40), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), nullable=False, default="medium")
    requires_approval = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class PredictionOutcome(Base):
    __tablename__ = "prediction_outcomes"
    id = Column(Integer, primary_key=True, index=True)
    prediction_record_id = Column(Integer, ForeignKey("prediction_records.id"), nullable=False, index=True)
    outcome_status = Column(String(30), nullable=False)
    actual_event_occurred = Column(Boolean, nullable=True)
    actual_event_at = Column(DateTime, nullable=True)
    accuracy_label = Column(String(30), nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_name = Column(String(150), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)


class PredictionFeedback(Base):
    __tablename__ = "prediction_feedback"
    id = Column(Integer, primary_key=True, index=True)
    prediction_record_id = Column(Integer, ForeignKey("prediction_records.id"), nullable=False, index=True)
    feedback_type = Column(String(30), nullable=False)
    rating = Column(Integer, nullable=True)
    feedback_text = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class PredictionActivityLog(Base):
    __tablename__ = "prediction_activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    prediction_record_id = Column(Integer, ForeignKey("prediction_records.id"), nullable=True)
    prediction_run_id = Column(Integer, ForeignKey("prediction_runs.id"), nullable=True)
    activity_type = Column(String(60), nullable=False)
    safe_summary = Column(Text, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)
