from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_roles
from app.models.notification import NotificationRule
from app.schemas.notification import (
    DailySummaryRead,
    NotificationActionResponse,
    NotificationBulkActionResponse,
    NotificationRead,
    NotificationRuleRead,
    NotificationRuleUpdate,
    NotificationRunChecksResponse,
    NotificationUnreadCount,
)
from app.services.audit_service import changed_fields, record_audit_log
from app.services.daily_summary_service import build_daily_summary
from app.services.event_service import OperationalEventType, record_operational_event
from app.services.notification_service import (
    dismiss,
    get_unread_count,
    list_visible_notifications,
    mark_all_read,
    mark_read,
    mark_unread,
)
from app.services.workflow_notification_service import run_notification_checks


router = APIRouter(prefix="/notifications", tags=["notifications"])

OperationalUser = Depends(require_roles("ADMIN", "STAFF"))
AdminUser = Depends(require_roles("ADMIN"))


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    category: Optional[str] = None,
    priority: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[NotificationRead]:
    return list_visible_notifications(
        db,
        current_user,
        status_filter=status_filter,
        category=category,
        priority=priority,
        date_from=datetime.combine(date_from, time.min) if date_from else None,
        date_to=datetime.combine(date_to, time.max) if date_to else None,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/unread-count", response_model=NotificationUnreadCount)
def unread_count(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> NotificationUnreadCount:
    return NotificationUnreadCount(unread_count=get_unread_count(db, current_user))


@router.patch("/{notification_id}/read", response_model=NotificationActionResponse)
def read_notification(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> NotificationActionResponse:
    notification = mark_read(db, notification_id, current_user)
    record_audit_log(
        db,
        current_user,
        "notification.mark_read",
        "notification",
        entity_id=notification.id,
        entity_label=notification.title,
        description="Notification marked read.",
        request=request,
    )
    return NotificationActionResponse(notification=notification)


@router.patch("/{notification_id}/unread", response_model=NotificationActionResponse)
def unread_notification(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> NotificationActionResponse:
    notification = mark_unread(db, notification_id, current_user)
    record_audit_log(
        db,
        current_user,
        "notification.mark_unread",
        "notification",
        entity_id=notification.id,
        entity_label=notification.title,
        description="Notification marked unread.",
        request=request,
    )
    return NotificationActionResponse(notification=notification)


@router.patch("/{notification_id}/dismiss", response_model=NotificationActionResponse)
def dismiss_notification(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> NotificationActionResponse:
    notification = dismiss(db, notification_id, current_user)
    record_audit_log(
        db,
        current_user,
        "notification.dismiss",
        "notification",
        entity_id=notification.id,
        entity_label=notification.title,
        description="Notification dismissed.",
        request=request,
    )
    return NotificationActionResponse(notification=notification)


@router.post("/mark-all-read", response_model=NotificationBulkActionResponse)
def mark_all_notifications_read(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> NotificationBulkActionResponse:
    updated = mark_all_read(db, current_user)
    record_audit_log(
        db,
        current_user,
        "notification.mark_all_read",
        "notification",
        description="All visible notifications marked read.",
        metadata={"updated": updated},
        request=request,
    )
    return NotificationBulkActionResponse(updated=updated)


@router.post("/run-checks", response_model=NotificationRunChecksResponse)
def run_checks(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> NotificationRunChecksResponse:
    result = run_notification_checks(db, source="manual")
    record_audit_log(
        db,
        current_user,
        "notification.run_checks",
        "notification",
        description="Notification checks manually run.",
        metadata=result,
        request=request,
    )
    record_operational_event(
        db,
        OperationalEventType.NOTIFICATION_CHECKS_RUN.value,
        "notification",
        actor_user=current_user,
        source="notification",
        metadata={
            "created": result.get("created"),
            "checked_rules_count": len(result.get("checked_rules", [])),
            "skipped_rules_count": len(result.get("skipped_rules", [])),
        },
        request=request,
        run_validation=False,
    )
    return NotificationRunChecksResponse(**result)


@router.get("/daily-summary", response_model=DailySummaryRead)
def daily_summary(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DailySummaryRead:
    return build_daily_summary(db, current_user)


@router.get("/rules", response_model=list[NotificationRuleRead])
def list_rules(
    db: Session = Depends(get_db),
    _: AuthenticatedUser = AdminUser,
) -> list[NotificationRule]:
    return db.query(NotificationRule).order_by(NotificationRule.category.asc(), NotificationRule.name.asc()).all()


@router.patch("/rules/{rule_id}", response_model=NotificationRuleRead)
def update_rule(
    rule_id: int,
    payload: NotificationRuleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AdminUser,
) -> NotificationRule:
    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification rule not found")
    data = payload.model_dump(exclude_unset=True)
    before = {field: getattr(rule, field, None) for field in data}
    for field, value in data.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    record_audit_log(
        db,
        current_user,
        "notification.rule_update",
        "notification_rule",
        entity_id=rule.id,
        entity_label=rule.rule_key,
        description="Notification rule updated.",
        metadata={"fields_changed": changed_fields(before, {field: getattr(rule, field, None) for field in data})},
        request=request,
    )
    return rule
