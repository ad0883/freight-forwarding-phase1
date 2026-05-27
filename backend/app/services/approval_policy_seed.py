"""Seed default approval policies."""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.approval import ApprovalPolicy

logger = logging.getLogger(__name__)

DEFAULT_POLICIES = [
    {"name": "Finance Hold Waiver - High", "approval_type": "finance_hold_waiver", "risk_level": "high", "required_approver_role": "ADMIN", "required_steps": 1, "maker_checker_required": True, "auto_expire_hours": 48},
    {"name": "Finance Hold Waiver - Critical", "approval_type": "finance_hold_waiver", "risk_level": "critical", "required_approver_role": "ADMIN", "required_steps": 2, "maker_checker_required": True, "auto_expire_hours": 24},
    {"name": "Release Action - High", "approval_type": "release_action", "risk_level": "high", "required_approver_role": "ADMIN", "required_steps": 1, "maker_checker_required": True, "auto_expire_hours": 48},
    {"name": "Release Action - Critical", "approval_type": "release_action", "risk_level": "critical", "required_approver_role": "ADMIN", "required_steps": 2, "maker_checker_required": True, "auto_expire_hours": 24},
    {"name": "Document Intelligence Apply - Medium", "approval_type": "document_intelligence_apply", "risk_level": "medium", "required_approver_role": "STAFF", "required_steps": 1, "maker_checker_required": False, "auto_expire_hours": 72},
    {"name": "Document Intelligence Apply - High", "approval_type": "document_intelligence_apply", "risk_level": "high", "required_approver_role": "ADMIN", "required_steps": 1, "maker_checker_required": True, "auto_expire_hours": 48},
    {"name": "Gmail Suggestion Apply - Medium", "approval_type": "gmail_suggestion_apply", "risk_level": "medium", "required_approver_role": "STAFF", "required_steps": 1, "maker_checker_required": False, "auto_expire_hours": 72},
    {"name": "Gmail Suggestion Apply - High", "approval_type": "gmail_suggestion_apply", "risk_level": "high", "required_approver_role": "ADMIN", "required_steps": 1, "maker_checker_required": True, "auto_expire_hours": 48},
    {"name": "Workflow Transition - High", "approval_type": "workflow_transition", "risk_level": "high", "required_approver_role": "ADMIN", "required_steps": 1, "maker_checker_required": True, "auto_expire_hours": 48},
    {"name": "Credit Limit Override", "approval_type": "credit_limit_override", "risk_level": "high", "required_approver_role": "ADMIN", "required_steps": 1, "maker_checker_required": True, "auto_expire_hours": 48},
    {"name": "Bot Action", "approval_type": "bot_action", "risk_level": "medium", "required_approver_role": "ADMIN", "required_steps": 1, "maker_checker_required": False, "auto_expire_hours": 72},
    {"name": "Bot Action - High", "approval_type": "bot_action", "risk_level": "high", "required_approver_role": "ADMIN", "required_steps": 2, "maker_checker_required": True, "auto_expire_hours": 48},
]


def seed_default_approval_policies(db: Session) -> None:
    existing_count = db.query(ApprovalPolicy).count()
    if existing_count > 0:
        return
    now = datetime.utcnow()
    for p in DEFAULT_POLICIES:
        policy = ApprovalPolicy(
            name=p["name"],
            approval_type=p["approval_type"],
            risk_level=p["risk_level"],
            is_active=True,
            required_approver_role=p["required_approver_role"],
            required_steps=p["required_steps"],
            maker_checker_required=p["maker_checker_required"],
            admin_override_allowed=True,
            auto_expire_hours=p.get("auto_expire_hours"),
            created_at=now,
            updated_at=now,
        )
        db.add(policy)
    db.commit()
    logger.info("Seeded %d default approval policies", len(DEFAULT_POLICIES))
