"""Bot agent registry service."""
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.bot_governance import BotAgent

logger = logging.getLogger(__name__)

DEFAULT_AGENTS = [
    {"bot_key": "ai_assistant", "name": "AI Assistant", "bot_type": "ai_assistant", "risk_level": "low"},
    {"bot_key": "gmail_parser", "name": "Gmail Parser", "bot_type": "gmail_parser", "risk_level": "medium"},
    {"bot_key": "document_intelligence", "name": "Document Intelligence", "bot_type": "document_extractor", "risk_level": "medium"},
    {"bot_key": "workflow_exception_detector", "name": "Workflow Exception Detector", "bot_type": "workflow_detector", "risk_level": "medium"},
    {"bot_key": "container_risk_checker", "name": "Container Risk Checker", "bot_type": "container_risk_checker", "risk_level": "medium"},
    {"bot_key": "finance_credit_checker", "name": "Finance Credit Checker", "bot_type": "finance_checker", "risk_level": "high"},
    {"bot_key": "notification_checker", "name": "Notification Checker", "bot_type": "notification_checker", "risk_level": "low"},
    {"bot_key": "exception_detector", "name": "Exception Detector", "bot_type": "exception_detector", "risk_level": "medium"},
    {"bot_key": "approval_router", "name": "Approval Router", "bot_type": "approval_router", "risk_level": "high"},
]


def seed_default_bot_agents(db: Session) -> None:
    existing = db.query(BotAgent).count()
    if existing > 0:
        return
    now = datetime.utcnow()
    for a in DEFAULT_AGENTS:
        agent = BotAgent(bot_key=a["bot_key"], name=a["name"], bot_type=a["bot_type"], status="active", risk_level=a["risk_level"], is_approval_required=a["risk_level"] in ("high", "critical"), created_at=now, updated_at=now)
        db.add(agent)
    db.commit()
    logger.info("Seeded %d default bot agents", len(DEFAULT_AGENTS))


def get_or_create_bot_agent(db: Session, bot_key: str, defaults: Optional[dict] = None) -> BotAgent:
    agent = db.query(BotAgent).filter(BotAgent.bot_key == bot_key).first()
    if agent:
        return agent
    now = datetime.utcnow()
    d = defaults or {}
    agent = BotAgent(bot_key=bot_key, name=d.get("name", bot_key), bot_type=d.get("bot_type", "other"), status="active", risk_level=d.get("risk_level", "medium"), is_approval_required=True, created_at=now, updated_at=now)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def list_bot_agents(db: Session, *, status_filter: Optional[str] = None, limit: int = 50) -> list[BotAgent]:
    q = db.query(BotAgent)
    if status_filter:
        q = q.filter(BotAgent.status == status_filter)
    return q.order_by(BotAgent.bot_key).limit(limit).all()


def update_bot_agent(db: Session, bot_agent_id: int, data: dict[str, Any], user: AuthenticatedUser) -> BotAgent:
    agent = db.query(BotAgent).filter(BotAgent.id == bot_agent_id).first()
    if not agent:
        raise ValueError("Bot agent not found")
    for k, v in data.items():
        if hasattr(agent, k) and k not in ("id", "bot_key", "created_at"):
            setattr(agent, k, v)
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent


def pause_bot_agent(db: Session, bot_agent_id: int, user: AuthenticatedUser, reason: Optional[str] = None) -> BotAgent:
    agent = db.query(BotAgent).filter(BotAgent.id == bot_agent_id).first()
    if not agent:
        raise ValueError("Bot agent not found")
    agent.status = "paused"
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent


def resume_bot_agent(db: Session, bot_agent_id: int, user: AuthenticatedUser, reason: Optional[str] = None) -> BotAgent:
    agent = db.query(BotAgent).filter(BotAgent.id == bot_agent_id).first()
    if not agent:
        raise ValueError("Bot agent not found")
    agent.status = "active"
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent
