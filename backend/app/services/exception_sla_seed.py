"""Seed default SLA policies for the exception engine."""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.exception_case import ExceptionCaseSlaPolicy

logger = logging.getLogger(__name__)

DEFAULT_SLA_POLICIES = [
    {"category": "all", "severity": "critical", "priority": "p0", "response_minutes": 30, "resolution_minutes": 240},
    {"category": "all", "severity": "high", "priority": "p1", "response_minutes": 60, "resolution_minutes": 480},
    {"category": "all", "severity": "medium", "priority": "p2", "response_minutes": 240, "resolution_minutes": 1440},
    {"category": "all", "severity": "low", "priority": "p3", "response_minutes": 480, "resolution_minutes": 2880},
    {"category": "all", "severity": "info", "priority": "p4", "response_minutes": 1440, "resolution_minutes": 10080},
]


def seed_default_sla_policies(db: Session) -> None:
    """Seed default SLA policies if none exist."""
    existing_count = db.query(ExceptionCaseSlaPolicy).count()
    if existing_count > 0:
        return

    now = datetime.utcnow()
    for policy_data in DEFAULT_SLA_POLICIES:
        policy = ExceptionCaseSlaPolicy(
            category=policy_data["category"],
            severity=policy_data["severity"],
            priority=policy_data["priority"],
            response_minutes=policy_data["response_minutes"],
            resolution_minutes=policy_data["resolution_minutes"],
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(policy)

    db.commit()
    logger.info("Seeded %d default SLA policies", len(DEFAULT_SLA_POLICIES))
