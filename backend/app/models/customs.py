"""Phase 19 CHA/customs coordination models."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text

from app.db.session import Base


class CustomsCase(Base):
    __tablename__ = "customs_cases"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    case_number = Column(String(60), nullable=False, unique=True, index=True)
    customs_direction = Column(String(10), nullable=False, index=True)
    case_type = Column(String(40), nullable=False, default="shipping_bill", index=True)
    status = Column(String(40), nullable=False, default="not_started", index=True)
    priority = Column(String(10), nullable=False, default="p3")
    cha_party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    cha_name = Column(String(255), nullable=True)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to_name = Column(String(150), nullable=True)
    port_of_filing = Column(String(120), nullable=True)
    customs_location = Column(String(255), nullable=True)
    filing_mode = Column(String(40), nullable=True)
    target_filing_date = Column(DateTime, nullable=True)
    filed_at = Column(DateTime, nullable=True)
    cleared_at = Column(DateTime, nullable=True)
    ooc_at = Column(DateTime, nullable=True)
    leo_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class CustomsCaseMilestone(Base):
    __tablename__ = "customs_case_milestones"
    id = Column(Integer, primary_key=True, index=True)
    customs_case_id = Column(Integer, ForeignKey("customs_cases.id"), nullable=False, index=True)
    milestone_key = Column(String(80), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    planned_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_by_name = Column(String(150), nullable=True)
    evidence_document_version_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class CustomsChecklistItem(Base):
    __tablename__ = "customs_checklist_items"
    id = Column(Integer, primary_key=True, index=True)
    customs_case_id = Column(Integer, ForeignKey("customs_cases.id"), nullable=False, index=True)
    item_key = Column(String(80), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    required = Column(Boolean, nullable=False, default=True)
    blocking = Column(Boolean, nullable=False, default=False)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to_name = Column(String(150), nullable=True)
    due_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_by_name = Column(String(150), nullable=True)
    source = Column(String(40), nullable=False, default="system")
    linked_document_version_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class CustomsDocumentRequirement(Base):
    __tablename__ = "customs_document_requirements"
    id = Column(Integer, primary_key=True, index=True)
    customs_case_id = Column(Integer, ForeignKey("customs_cases.id"), nullable=False, index=True)
    document_type = Column(String(80), nullable=False)
    required = Column(Boolean, nullable=False, default=True)
    status = Column(String(20), nullable=False, default="pending")
    visible_to_customer = Column(Boolean, nullable=False, default=True)
    visible_to_cha = Column(Boolean, nullable=False, default=True)
    linked_document_version_id = Column(Integer, nullable=True)
    required_by_role = Column(String(30), nullable=True)
    due_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class CustomsQuery(Base):
    __tablename__ = "customs_queries"
    id = Column(Integer, primary_key=True, index=True)
    customs_case_id = Column(Integer, ForeignKey("customs_cases.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    query_number = Column(String(60), nullable=True, index=True)
    query_type = Column(String(40), nullable=False, default="other", index=True)
    source = Column(String(40), nullable=False, default="customs_query")
    status = Column(String(20), nullable=False, default="open", index=True)
    severity = Column(String(20), nullable=False, default="medium")
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    raised_by = Column(String(150), nullable=True)
    raised_at = Column(DateTime, nullable=True)
    due_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_by_name = Column(String(150), nullable=True)
    linked_exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class CustomsQueryComment(Base):
    __tablename__ = "customs_query_comments"
    id = Column(Integer, primary_key=True, index=True)
    customs_query_id = Column(Integer, ForeignKey("customs_queries.id"), nullable=False, index=True)
    author_type = Column(String(20), nullable=False, default="internal_user")
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    author_name = Column(String(150), nullable=True)
    comment_text = Column(Text, nullable=False)
    visible_to_customer = Column(Boolean, nullable=False, default=False)
    visible_to_cha = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class CustomsPartyAssignment(Base):
    __tablename__ = "customs_party_assignments"
    id = Column(Integer, primary_key=True, index=True)
    customs_case_id = Column(Integer, ForeignKey("customs_cases.id"), nullable=False, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False, index=True)
    party_role = Column(String(30), nullable=False, default="cha")
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_by_name = Column(String(150), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)


class CustomsDutyRecord(Base):
    __tablename__ = "customs_duty_records"
    id = Column(Integer, primary_key=True, index=True)
    customs_case_id = Column(Integer, ForeignKey("customs_cases.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    duty_type = Column(String(40), nullable=False, default="basic_customs_duty")
    currency = Column(String(10), nullable=False, default="INR")
    assessed_amount = Column(Numeric(14, 2), nullable=True)
    paid_amount = Column(Numeric(14, 2), nullable=True)
    outstanding_amount = Column(Numeric(14, 2), nullable=True)
    payment_status = Column(String(20), nullable=False, default="pending")
    payment_reference = Column(String(120), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recorded_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class CustomsReferenceNumber(Base):
    __tablename__ = "customs_reference_numbers"
    id = Column(Integer, primary_key=True, index=True)
    customs_case_id = Column(Integer, ForeignKey("customs_cases.id"), nullable=False, index=True)
    reference_type = Column(String(40), nullable=False, index=True)
    reference_value = Column(String(255), nullable=False)
    issued_at = Column(DateTime, nullable=True)
    source = Column(String(40), nullable=False, default="manual")
    verified = Column(Boolean, nullable=False, default=False)
    verified_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class CustomsActivityLog(Base):
    __tablename__ = "customs_activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    customs_case_id = Column(Integer, ForeignKey("customs_cases.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    activity_type = Column(String(60), nullable=False)
    safe_summary = Column(Text, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)
