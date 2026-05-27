"""Phase 15 manual review queue service."""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.exception_case import ExceptionCase
from app.services.exception_service import ACTIVE_STATUSES


def get_manual_review_queue(
    db: Session,
    *,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ExceptionCase]:
    """Get the manual review queue (all active exceptions needing attention)."""
    query = (
        db.query(ExceptionCase)
        .filter(ExceptionCase.status.in_(ACTIVE_STATUSES))
    )
    if category:
        query = query.filter(ExceptionCase.category == category)
    if severity:
        query = query.filter(ExceptionCase.severity == severity)
    if priority:
        query = query.filter(ExceptionCase.priority == priority)

    return (
        query.order_by(
            ExceptionCase.priority.asc(),
            ExceptionCase.risk_score.desc(),
            ExceptionCase.created_at.desc(),
        )
        .limit(min(max(limit, 1), 200))
        .offset(max(offset, 0))
        .all()
    )


def get_manual_review_summary(
    db: Session,
    user: Optional[AuthenticatedUser] = None,
) -> dict[str, Any]:
    """Get summary for the manual review dashboard."""
    from app.services.exception_service import get_exception_summary
    return get_exception_summary(db, user)


def get_my_review_items(
    db: Session,
    user: AuthenticatedUser,
    limit: int = 50,
) -> list[ExceptionCase]:
    """Get exceptions assigned to the current user."""
    return (
        db.query(ExceptionCase)
        .filter(
            ExceptionCase.assigned_to_user_id == user.id,
            ExceptionCase.status.in_(ACTIVE_STATUSES),
        )
        .order_by(ExceptionCase.priority.asc(), ExceptionCase.due_at.asc())
        .limit(min(max(limit, 1), 200))
        .all()
    )


def get_role_review_items(
    db: Session,
    role: str,
    limit: int = 50,
) -> list[ExceptionCase]:
    """Get exceptions assigned to a specific role."""
    return (
        db.query(ExceptionCase)
        .filter(
            ExceptionCase.assigned_to_role == role,
            ExceptionCase.status.in_(ACTIVE_STATUSES),
        )
        .order_by(ExceptionCase.priority.asc(), ExceptionCase.due_at.asc())
        .limit(min(max(limit, 1), 200))
        .all()
    )
