from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.notification import Notification, NotificationRule, NotificationUserState
from app.schemas.notification import NotificationRead


SENSITIVE_METADATA_FRAGMENTS = {
    "access_token",
    "api_key",
    "authorization",
    "body",
    "client_secret",
    "cookie",
    "database_url",
    "gmail_token",
    "jwt",
    "oauth",
    "password",
    "refresh_token",
    "secret",
    "token",
}

DEFAULT_RULES = [
    {
        "rule_key": "overdue_tasks",
        "name": "Overdue tasks",
        "description": "Open tasks with due dates before today.",
        "category": "task",
        "priority": "warning",
        "threshold_days": None,
        "target_role": "STAFF",
    },
    {
        "rule_key": "due_tasks_today",
        "name": "Tasks due today",
        "description": "Open tasks due today.",
        "category": "task",
        "priority": "info",
        "threshold_days": None,
        "target_role": "STAFF",
    },
    {
        "rule_key": "demurrage_running",
        "name": "Demurrage running",
        "description": "Import shipments currently accruing demurrage.",
        "category": "demurrage",
        "priority": "critical",
        "threshold_days": None,
        "target_role": "STAFF",
    },
    {
        "rule_key": "demurrage_expiring_soon",
        "name": "Free days expiring soon",
        "description": "Import shipments with free days ending soon.",
        "category": "demurrage",
        "priority": "warning",
        "threshold_days": 2,
        "target_role": "STAFF",
    },
    {
        "rule_key": "bl_approval_pending",
        "name": "BL approval pending",
        "description": "BL draft received or workflow is waiting for approval.",
        "category": "bl",
        "priority": "warning",
        "threshold_days": None,
        "target_role": "STAFF",
    },
    {
        "rule_key": "pending_document_review",
        "name": "Pending document review",
        "description": "Required documents pending longer than the configured threshold.",
        "category": "document",
        "priority": "warning",
        "threshold_days": 3,
        "target_role": "STAFF",
    },
    {
        "rule_key": "pending_receivables",
        "name": "Pending receivables",
        "description": "Receivable charges pending longer than the configured threshold.",
        "category": "finance",
        "priority": "warning",
        "threshold_days": 7,
        "target_role": "STAFF",
    },
    {
        "rule_key": "pending_payables",
        "name": "Pending payables",
        "description": "Payable charges pending longer than the configured threshold.",
        "category": "finance",
        "priority": "info",
        "threshold_days": 7,
        "target_role": "STAFF",
    },
    {
        "rule_key": "gmail_suggestions_pending",
        "name": "Gmail suggestions pending",
        "description": "Reviewable Gmail suggestions are waiting for a user.",
        "category": "gmail",
        "priority": "info",
        "threshold_days": None,
        "target_role": None,
    },
    {
        "rule_key": "shipments_eta_today",
        "name": "Shipments ETA today or tomorrow",
        "description": "Active import shipments with ETA today or tomorrow.",
        "category": "shipment",
        "priority": "info",
        "threshold_days": 1,
        "target_role": "STAFF",
    },
    {
        "rule_key": "finance_overview",
        "name": "Finance overview",
        "description": "Phase 14 finance summary widget visibility.",
        "category": "finance",
        "priority": "info",
        "threshold_days": None,
        "target_role": "STAFF",
    },
]


def seed_default_notification_rules(db: Session) -> None:
    existing = {
        row.rule_key
        for row in db.query(NotificationRule.rule_key)
        .filter(NotificationRule.rule_key.in_([rule["rule_key"] for rule in DEFAULT_RULES]))
        .all()
    }
    created = False
    for rule in DEFAULT_RULES:
        if rule["rule_key"] in existing:
            continue
        db.add(NotificationRule(**rule))
        created = True
    if created:
        db.commit()


def get_rules_by_key(db: Session) -> dict[str, NotificationRule]:
    return {rule.rule_key: rule for rule in db.query(NotificationRule).all()}


def active_rule_keys(db: Session) -> set[str]:
    return {
        rule.rule_key
        for rule in db.query(NotificationRule.rule_key).filter(NotificationRule.is_enabled.is_(True)).all()
    }


def create_notification(
    db: Session,
    title: str,
    message: str,
    category: str,
    priority: str,
    target_role: Optional[str] = None,
    target_user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    entity_label: Optional[str] = None,
    action_url: Optional[str] = None,
    dedupe_key: Optional[str] = None,
    source: str = "system",
    metadata: Optional[dict[str, Any]] = None,
    expires_at: Optional[datetime] = None,
) -> tuple[Notification, bool]:
    if dedupe_key:
        existing = (
            db.query(Notification)
            .filter(
                Notification.dedupe_key == dedupe_key,
                or_(Notification.expires_at.is_(None), Notification.expires_at > datetime.utcnow()),
            )
            .first()
        )
        if existing:
            return existing, False
    notification = Notification(
        title=title,
        message=message,
        category=category,
        priority=priority,
        target_role=target_role,
        target_user_id=target_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label,
        action_url=action_url,
        dedupe_key=dedupe_key,
        source=source,
        metadata_json=_sanitize_metadata(metadata or {}),
        expires_at=expires_at,
    )
    db.add(notification)
    db.flush()
    return notification, True


def list_visible_notifications(
    db: Session,
    user: AuthenticatedUser,
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[NotificationRead]:
    query = _visible_query(db, user).filter(
        or_(Notification.expires_at.is_(None), Notification.expires_at > datetime.utcnow())
    )
    if category:
        query = query.filter(Notification.category == category)
    if priority:
        query = query.filter(Notification.priority == priority)
    if date_from:
        query = query.filter(Notification.created_at >= date_from)
    if date_to:
        query = query.filter(Notification.created_at <= date_to)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Notification.title.ilike(pattern),
                Notification.message.ilike(pattern),
                Notification.entity_label.ilike(pattern),
            )
        )
    rows = query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(500).all()
    items = [_notification_read(db, row, user) for row in rows]
    if status_filter:
        items = [item for item in items if item.status == status_filter]
    return items[offset : offset + limit]


def get_unread_count(db: Session, user: AuthenticatedUser) -> int:
    rows = (
        _visible_query(db, user)
        .outerjoin(
            NotificationUserState,
            and_(
                NotificationUserState.notification_id == Notification.id,
                NotificationUserState.user_id == user.id,
            ),
        )
        .filter(
            or_(Notification.expires_at.is_(None), Notification.expires_at > datetime.utcnow()),
            NotificationUserState.dismissed_at.is_(None),
            NotificationUserState.read_at.is_(None),
        )
        .count()
    )
    return int(rows)


def mark_read(db: Session, notification_id: int, user: AuthenticatedUser) -> NotificationRead:
    notification = get_visible_notification(db, notification_id, user)
    state = _get_or_create_state(db, notification.id, user.id)
    state.read_at = datetime.utcnow()
    state.dismissed_at = None
    db.commit()
    return _notification_read(db, notification, user)


def mark_unread(db: Session, notification_id: int, user: AuthenticatedUser) -> NotificationRead:
    notification = get_visible_notification(db, notification_id, user)
    state = _get_or_create_state(db, notification.id, user.id)
    state.read_at = None
    state.dismissed_at = None
    db.commit()
    return _notification_read(db, notification, user)


def dismiss(db: Session, notification_id: int, user: AuthenticatedUser) -> NotificationRead:
    notification = get_visible_notification(db, notification_id, user)
    state = _get_or_create_state(db, notification.id, user.id)
    now = datetime.utcnow()
    state.read_at = state.read_at or now
    state.dismissed_at = now
    db.commit()
    return _notification_read(db, notification, user)


def mark_all_read(db: Session, user: AuthenticatedUser) -> int:
    notifications = _visible_query(db, user).filter(
        or_(Notification.expires_at.is_(None), Notification.expires_at > datetime.utcnow())
    ).all()
    updated = 0
    now = datetime.utcnow()
    for notification in notifications:
        state = _get_or_create_state(db, notification.id, user.id)
        if state.dismissed_at is None and state.read_at is None:
            state.read_at = now
            updated += 1
    db.commit()
    return updated


def get_visible_notification(db: Session, notification_id: int, user: AuthenticatedUser) -> Notification:
    notification = _visible_query(db, user).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


def _visible_query(db: Session, user: AuthenticatedUser):
    query = db.query(Notification)
    if user.role == "ADMIN":
        return query
    return query.filter(
        or_(
            Notification.target_user_id == user.id,
            and_(
                Notification.target_user_id.is_(None),
                or_(Notification.target_role.is_(None), Notification.target_role == user.role),
            ),
        )
    )


def _get_or_create_state(db: Session, notification_id: int, user_id: int) -> NotificationUserState:
    state = (
        db.query(NotificationUserState)
        .filter(
            NotificationUserState.notification_id == notification_id,
            NotificationUserState.user_id == user_id,
        )
        .first()
    )
    if state:
        return state
    state = NotificationUserState(notification_id=notification_id, user_id=user_id)
    db.add(state)
    db.flush()
    return state


def _notification_read(db: Session, notification: Notification, user: AuthenticatedUser) -> NotificationRead:
    state = (
        db.query(NotificationUserState)
        .filter(
            NotificationUserState.notification_id == notification.id,
            NotificationUserState.user_id == user.id,
        )
        .first()
    )
    status_value = "unread"
    read_at = None
    dismissed_at = None
    if state:
        read_at = state.read_at
        dismissed_at = state.dismissed_at
        if dismissed_at:
            status_value = "dismissed"
        elif read_at:
            status_value = "read"
    return NotificationRead(
        id=notification.id,
        title=notification.title,
        message=notification.message,
        category=notification.category,
        priority=notification.priority,
        status=status_value,
        target_role=notification.target_role,
        target_user_id=notification.target_user_id,
        entity_type=notification.entity_type,
        entity_id=notification.entity_id,
        entity_label=notification.entity_label,
        action_url=notification.action_url,
        dedupe_key=notification.dedupe_key,
        source=notification.source,
        created_at=notification.created_at,
        read_at=read_at,
        dismissed_at=dismissed_at,
        expires_at=notification.expires_at,
        metadata_json=notification.metadata_json,
    )


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        safe_key = str(key)
        if any(fragment in safe_key.lower() for fragment in SENSITIVE_METADATA_FRAGMENTS):
            sanitized[safe_key] = "[redacted]"
            continue
        if isinstance(value, dict):
            sanitized[safe_key] = _sanitize_metadata(value)
        elif isinstance(value, list):
            sanitized[safe_key] = value[:20]
        elif isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[safe_key] = value if not isinstance(value, str) or len(value) <= 500 else f"{value[:500]}..."
        else:
            sanitized[safe_key] = str(value)
    return sanitized
