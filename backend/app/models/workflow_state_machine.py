from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint

from app.db.session import Base


class WorkflowStateDefinition(Base):
    __tablename__ = "workflow_state_definitions"
    __table_args__ = (
        UniqueConstraint("flow_type", "state_key", name="uq_workflow_state_def_flow_state"),
    )

    id = Column(Integer, primary_key=True, index=True)
    flow_type = Column(String(20), nullable=False, index=True)
    state_key = Column(String(80), nullable=False, index=True)
    state_label = Column(String(180), nullable=False)
    state_order = Column(Integer, nullable=False, default=0)
    description = Column(Text, nullable=True)
    is_initial = Column(Boolean, nullable=False, default=False)
    is_terminal = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowTransitionDefinition(Base):
    __tablename__ = "workflow_transition_definitions"
    __table_args__ = (
        UniqueConstraint("flow_type", "transition_key", name="uq_workflow_transition_def_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    flow_type = Column(String(20), nullable=False, index=True)
    transition_key = Column(String(160), nullable=False, index=True)
    from_state = Column(String(80), nullable=True, index=True)
    to_state = Column(String(80), nullable=False, index=True)
    label = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    requires_reason = Column(Boolean, nullable=False, default=False)
    requires_confirmation = Column(Boolean, nullable=False, default=False)
    requires_manual_review = Column(Boolean, nullable=False, default=False)
    is_sensitive = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowTransitionLog(Base):
    __tablename__ = "workflow_transition_logs"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    flow_type = Column(String(20), nullable=False, index=True)
    transition_key = Column(String(160), nullable=True, index=True)
    from_state = Column(String(80), nullable=True, index=True)
    to_state = Column(String(80), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    actor_name = Column(String(150), nullable=True)
    actor_email = Column(String(255), nullable=True)
    actor_role = Column(String(30), nullable=True)
    source = Column(String(40), nullable=False, default="user", index=True)
    status = Column(String(40), nullable=False, default="requested", index=True)
    reason = Column(Text, nullable=True)
    validation_status = Column(String(40), nullable=False, default="not_checked")
    event_id = Column(Integer, ForeignKey("operational_events.id"), nullable=True, index=True)
    validation_issue_id = Column(Integer, ForeignKey("validation_issues.id"), nullable=True, index=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
