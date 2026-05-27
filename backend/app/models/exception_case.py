"""Phase 15 exception engine models.

Central exception layer that ties together workflow errors, validation issues,
finance holds, document mismatches, container risks, Gmail suggestion conflicts,
overdue tasks, and manual-review cases into one controlled review center.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class ExceptionCase(Base):
    __tablename__ = "exception_cases"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    case_number = Column(String(60), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(40), nullable=False, index=True)
    source = Column(String(60), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="medium", index=True)
    priority = Column(String(10), nullable=False, default="p3", index=True)
    status = Column(String(40), nullable=False, default="open", index=True)
    risk_score = Column(Integer, nullable=False, default=0)
    dedupe_key = Column(String(255), nullable=True, index=True)
    entity_type = Column(String(80), nullable=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    assigned_to_name = Column(String(150), nullable=True)
    assigned_to_role = Column(String(30), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    due_at = Column(DateTime, nullable=True, index=True)
    first_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_by_name = Column(String(150), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    dismissed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    dismissed_by_name = Column(String(150), nullable=True)
    dismissal_reason = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    links = relationship("ExceptionCaseLink", back_populates="exception_case", cascade="all, delete-orphan")
    comments = relationship("ExceptionCaseComment", back_populates="exception_case", cascade="all, delete-orphan")
    assignments = relationship("ExceptionCaseAssignment", back_populates="exception_case", cascade="all, delete-orphan")
    status_history = relationship("ExceptionCaseStatusHistory", back_populates="exception_case", cascade="all, delete-orphan")
    escalations = relationship("ExceptionCaseEscalation", back_populates="exception_case", cascade="all, delete-orphan")
    watchers = relationship("ExceptionCaseWatcher", back_populates="exception_case", cascade="all, delete-orphan")


class ExceptionCaseLink(Base):
    __tablename__ = "exception_case_links"

    id = Column(Integer, primary_key=True, index=True)
    exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=False, index=True)
    linked_type = Column(String(80), nullable=False, index=True)
    linked_id = Column(Integer, nullable=False)
    linked_label = Column(String(255), nullable=True)
    relationship_type = Column(String(40), nullable=False, default="related")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    exception_case = relationship("ExceptionCase", back_populates="links")


class ExceptionCaseComment(Base):
    __tablename__ = "exception_case_comments"

    id = Column(Integer, primary_key=True, index=True)
    exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    author_name = Column(String(150), nullable=True)
    comment_text = Column(Text, nullable=False)
    is_internal = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    exception_case = relationship("ExceptionCase", back_populates="comments")


class ExceptionCaseAssignment(Base):
    __tablename__ = "exception_case_assignments"

    id = Column(Integer, primary_key=True, index=True)
    exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=False, index=True)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to_name = Column(String(150), nullable=True)
    assigned_to_role = Column(String(30), nullable=True)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_by_name = Column(String(150), nullable=True)
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    unassigned_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    exception_case = relationship("ExceptionCase", back_populates="assignments")


class ExceptionCaseStatusHistory(Base):
    __tablename__ = "exception_case_status_history"

    id = Column(Integer, primary_key=True, index=True)
    exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=False, index=True)
    old_status = Column(String(40), nullable=True)
    new_status = Column(String(40), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_by_name = Column(String(150), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    exception_case = relationship("ExceptionCase", back_populates="status_history")


class ExceptionCaseEscalation(Base):
    __tablename__ = "exception_case_escalations"

    id = Column(Integer, primary_key=True, index=True)
    exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=False, index=True)
    from_severity = Column(String(20), nullable=True)
    to_severity = Column(String(20), nullable=False)
    from_priority = Column(String(10), nullable=True)
    to_priority = Column(String(10), nullable=False)
    escalation_reason = Column(Text, nullable=False)
    escalated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    escalated_by_name = Column(String(150), nullable=True)
    escalated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    exception_case = relationship("ExceptionCase", back_populates="escalations")


class ExceptionCaseSlaPolicy(Base):
    __tablename__ = "exception_case_sla_policies"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(40), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    priority = Column(String(10), nullable=False, index=True)
    response_minutes = Column(Integer, nullable=False, default=60)
    resolution_minutes = Column(Integer, nullable=False, default=480)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class ExceptionCaseWatcher(Base):
    __tablename__ = "exception_case_watchers"

    id = Column(Integer, primary_key=True, index=True)
    exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role = Column(String(30), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    exception_case = relationship("ExceptionCase", back_populates="watchers")
