"""Phase 16 bot governance service."""
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.approval import BotGovernanceAction

logger = logging.getLogger(__name__)


def record_bot_proposal(
    db: Session, data: dict[str, Any], user: Optional[AuthenticatedUser] = None,
) -> BotGovernanceAction:
    action = BotGovernanceAction(
        bot_name=data.get("bot_name"),
        action_type=data["action_type"],
        source=data.get("source", "system"),
        status="proposed",
        risk_level=data.get("risk_level", "medium"),
        confidence=data.get("confidence"),
        entity_type=data.get("entity_type"),
        entity_id=data.get("entity_id"),
        shipment_id=data.get("shipment_id"),
        proposed_payload_json=data.get("proposed_payload_json"),
        safe_summary_json=data.get("safe_summary_json"),
        created_at=datetime.utcnow(),
        metadata_json=data.get("metadata_json"),
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def submit_bot_action_for_approval(
    db: Session, bot_action_id: int, user: AuthenticatedUser,
) -> BotGovernanceAction:
    action = db.query(BotGovernanceAction).filter(BotGovernanceAction.id == bot_action_id).first()
    if not action:
        raise ValueError("Bot action not found")
    if action.status != "proposed":
        raise ValueError("Only proposed bot actions can be submitted")
    action.status = "pending_approval"
    db.commit()
    db.refresh(action)
    return action


def approve_bot_action(
    db: Session, bot_action_id: int, user: AuthenticatedUser,
) -> BotGovernanceAction:
    action = db.query(BotGovernanceAction).filter(BotGovernanceAction.id == bot_action_id).first()
    if not action:
        raise ValueError("Bot action not found")
    if action.status != "pending_approval":
        raise ValueError("Bot action is not pending approval")
    now = datetime.utcnow()
    action.status = "approved"
    action.reviewed_at = now
    action.reviewed_by_user_id = user.id
    action.reviewed_by_name = user.name
    db.commit()
    db.refresh(action)
    return action


def reject_bot_action(
    db: Session, bot_action_id: int, user: AuthenticatedUser, reason: Optional[str] = None,
) -> BotGovernanceAction:
    action = db.query(BotGovernanceAction).filter(BotGovernanceAction.id == bot_action_id).first()
    if not action:
        raise ValueError("Bot action not found")
    if action.status != "pending_approval":
        raise ValueError("Bot action is not pending approval")
    now = datetime.utcnow()
    action.status = "rejected"
    action.reviewed_at = now
    action.reviewed_by_user_id = user.id
    action.reviewed_by_name = user.name
    if reason:
        meta = dict(action.metadata_json or {})
        meta["rejection_reason"] = reason
        action.metadata_json = meta
    db.commit()
    db.refresh(action)
    return action


def list_bot_actions(
    db: Session, *, status_filter: Optional[str] = None, limit: int = 50, offset: int = 0,
) -> list[BotGovernanceAction]:
    query = db.query(BotGovernanceAction)
    if status_filter:
        query = query.filter(BotGovernanceAction.status == status_filter)
    return query.order_by(BotGovernanceAction.created_at.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0)).all()
