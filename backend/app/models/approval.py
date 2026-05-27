"""Phase 16 approval engine + HOD bot governance models."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    approval_number = Column(String(60), nullable=False, unique=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    approval_type = Column(String(60), nullable=False, index=True)
    source = Column(String(60), nullable=False, index=True)
    status = Column(String(40), nullable=False, default="draft", index=True)
    risk_level = Column(String(20), nullable=False, default="medium", index=True)
    priority = Column(String(10), nullable=False, default="p3", index=True)
    entity_type = Column(String(80), nullable=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=True, index=True)
    requested_action = Column(String(255), nullable=False)
    requested_payload_json = Column(JSON, nullable=True)
    safe_summary_json = Column(JSON, nullable=True)
    requested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    requested_by_name = Column(String(150), nullable=True)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    assigned_to_name = Column(String(150), nullable=True)
    assigned_to_role = Column(String(30), nullable=True)
    current_step_no = Column(Integer, nullable=False, default=1)
    required_steps = Column(Integer, nullable=False, default=1)
    due_at = Column(DateTime, nullable=True, index=True)
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    final_decision_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    final_decision_by_name = Column(String(150), nullable=True)
    final_decision_notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps = relationship("ApprovalStep", back_populates="approval_request", cascade="all, delete-orphan")
    evidence = relationship("ApprovalRequestEvidence", back_populates="approval_request", cascade="all, delete-orphan")


class ApprovalStep(Base):
    __tablename__ = "approval_steps"

    id = Column(Integer, primary_key=True, index=True)
    approval_request_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=False, index=True)
    step_no = Column(Integer, nullable=False, default=1)
    approver_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approver_name = Column(String(150), nullable=True)
    approver_role = Column(String(30), nullable=True)
    status = Column(String(30), nullable=False, default="pending")
    decision = Column(String(30), nullable=True)
    decision_notes = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    approval_request = relationship("ApprovalRequest", back_populates="steps")


class ApprovalPolicy(Base):
    __tablename__ = "approval_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    approval_type = Column(String(60), nullable=False, index=True)
    risk_level = Column(String(20), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    required_approver_role = Column(String(30), nullable=False, default="ADMIN")
    required_steps = Column(Integer, nullable=False, default=1)
    maker_checker_required = Column(Boolean, nullable=False, default=False)
    admin_override_allowed = Column(Boolean, nullable=False, default=True)
    auto_expire_hours = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    rules = relationship("ApprovalPolicyRule", back_populates="policy", cascade="all, delete-orphan")


class ApprovalPolicyRule(Base):
    __tablename__ = "approval_policy_rules"

    id = Column(Integer, primary_key=True, index=True)
    approval_policy_id = Column(Integer, ForeignKey("approval_policies.id"), nullable=False, index=True)
    rule_key = Column(String(120), nullable=False)
    condition_json = Column(JSON, nullable=True)
    effect = Column(String(40), nullable=False, default="require_approval")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    policy = relationship("ApprovalPolicy", back_populates="rules")


class ApprovalRequestEvidence(Base):
    __tablename__ = "approval_request_evidence"

    id = Column(Integer, primary_key=True, index=True)
    approval_request_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=False, index=True)
    evidence_type = Column(String(60), nullable=False)
    linked_type = Column(String(80), nullable=True)
    linked_id = Column(Integer, nullable=True)
    label = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    approval_request = relationship("ApprovalRequest", back_populates="evidence")


class ApprovalActionLock(Base):
    __tablename__ = "approval_action_locks"

    id = Column(Integer, primary_key=True, index=True)
    approval_request_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=True, index=True)
    entity_type = Column(String(80), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    action_key = Column(String(120), nullable=False, index=True)
    lock_reason = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    released_at = Column(DateTime, nullable=True)
    released_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    released_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class ApprovalDelegation(Base):
    __tablename__ = "approval_delegations"

    id = Column(Integer, primary_key=True, index=True)
    delegator_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    delegate_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_scope = Column(String(30), nullable=True)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class ApprovalOverride(Base):
    __tablename__ = "approval_overrides"

    id = Column(Integer, primary_key=True, index=True)
    approval_request_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=True, index=True)
    entity_type = Column(String(80), nullable=True)
    entity_id = Column(Integer, nullable=True)
    action_key = Column(String(120), nullable=False)
    override_reason = Column(Text, nullable=False)
    risk_level = Column(String(20), nullable=False, default="medium")
    overridden_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    overridden_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class BotGovernanceAction(Base):
    __tablename__ = "bot_governance_actions"

    id = Column(Integer, primary_key=True, index=True)
    bot_name = Column(String(120), nullable=True, index=True)
    action_type = Column(String(60), nullable=False, index=True)
    source = Column(String(60), nullable=False, default="system")
    status = Column(String(30), nullable=False, default="proposed", index=True)
    risk_level = Column(String(20), nullable=False, default="medium")
    confidence = Column(Numeric(5, 2), nullable=True)
    entity_type = Column(String(80), nullable=True)
    entity_id = Column(Integer, nullable=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    approval_request_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=True, index=True)
    proposed_payload_json = Column(JSON, nullable=True)
    safe_summary_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)
