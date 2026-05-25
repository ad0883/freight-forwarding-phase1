from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.bl_management import BLManagement
from app.models.demurrage import Demurrage
from app.models.email import EmailConnection, EmailMessageCache, EmailSuggestion
from app.models.notification import Notification
from app.models.shipment import Shipment
from app.models.task import Task
from app.schemas.notification import DailySummaryItem, DailySummaryRead, DailySummaryTotals
from app.services.demurrage_service import calculate_demurrage
from app.services.finance_service import calculate_dashboard_financials
from app.services.notification_service import get_unread_count, list_visible_notifications
from app.services.workflow_notification_service import IMPORT_DELIVERED_STATUSES, INACTIVE_SHIPMENT_STATUSES


def build_daily_summary(db: Session, user: AuthenticatedUser) -> DailySummaryRead:
    today = date.today()
    financials = calculate_dashboard_financials(db, today=today)
    open_tasks = _open_tasks_count(db)
    overdue_tasks = _overdue_tasks_count(db, today)
    demurrage_risks = _demurrage_risk_count(db, today)
    pending_bl = _pending_bl_count(db)
    shipments_attention = _shipments_needing_attention_count(db, today)
    pending_gmail = _pending_gmail_suggestion_count(db) if user.role in {"ADMIN", "STAFF"} else 0
    unread_notifications = get_unread_count(db, user)

    return DailySummaryRead(
        generated_at=datetime.utcnow(),
        totals=DailySummaryTotals(
            open_tasks=open_tasks,
            overdue_tasks=overdue_tasks,
            shipments_needing_attention=shipments_attention,
            demurrage_risks=demurrage_risks,
            pending_bl_approvals=pending_bl,
            pending_receivables_total=financials.pending_receivables,
            pending_payables_total=financials.pending_payables,
            pending_gmail_suggestions=pending_gmail,
            unread_notifications=unread_notifications,
            currency=financials.currency,
            multiple_currencies=financials.multiple_currencies,
        ),
        top_urgent_items=_top_urgent_items(db, user),
    )


def _open_tasks_count(db: Session) -> int:
    return (
        db.query(Task)
        .join(Shipment, Shipment.id == Task.shipment_id)
        .filter(Task.status == "open", Shipment.is_archived.is_(False))
        .count()
    )


def _overdue_tasks_count(db: Session, today: date) -> int:
    return (
        db.query(Task)
        .join(Shipment, Shipment.id == Task.shipment_id)
        .filter(
            Task.status == "open",
            Task.due_date.isnot(None),
            Task.due_date < today,
            Shipment.is_archived.is_(False),
        )
        .count()
    )


def _demurrage_risk_count(db: Session, today: date) -> int:
    rows = (
        db.query(Demurrage, Shipment)
        .join(Shipment, Shipment.id == Demurrage.shipment_id)
        .filter(Shipment.type == "import", Shipment.is_archived.is_(False))
        .all()
    )
    count = 0
    for demurrage, shipment in rows:
        if shipment.status in IMPORT_DELIVERED_STATUSES:
            continue
        read = calculate_demurrage(demurrage, today=today, persist_status=False)
        if read.is_demurrage_running or (
            read.days_remaining is not None and 0 < read.days_remaining <= demurrage.alert_at_days
        ):
            count += 1
    return count


def _pending_bl_count(db: Session) -> int:
    return (
        db.query(Shipment)
        .outerjoin(BLManagement, BLManagement.shipment_id == Shipment.id)
        .filter(
            Shipment.is_archived.is_(False),
            ~Shipment.status.in_(INACTIVE_SHIPMENT_STATUSES),
            BLManagement.approval_date.is_(None),
            (Shipment.status == "BL Draft Received") | BLManagement.draft_received.isnot(None),
        )
        .count()
    )


def _shipments_needing_attention_count(db: Session, today: date) -> int:
    tomorrow = today + timedelta(days=1)
    return (
        db.query(Shipment)
        .filter(
            Shipment.is_archived.is_(False),
            ~Shipment.status.in_(INACTIVE_SHIPMENT_STATUSES),
            Shipment.eta.isnot(None),
            Shipment.eta >= today,
            Shipment.eta <= tomorrow,
        )
        .count()
    )


def _pending_gmail_suggestion_count(db: Session) -> int:
    value = (
        db.query(func.count(EmailSuggestion.id))
        .join(EmailMessageCache, EmailMessageCache.id == EmailSuggestion.email_message_id)
        .join(EmailConnection, EmailConnection.id == EmailMessageCache.connection_id)
        .filter(EmailConnection.is_active.is_(True), EmailSuggestion.status == "pending")
        .scalar()
    )
    return int(value or 0)


def _top_urgent_items(db: Session, user: AuthenticatedUser) -> list[DailySummaryItem]:
    notifications = list_visible_notifications(db, user, limit=8)
    priority_rank = {"critical": 0, "warning": 1, "info": 2, "none": 3}
    active = [item for item in notifications if item.status != "dismissed"]
    active.sort(key=lambda item: (priority_rank.get(item.priority, 9), -item.created_at.timestamp()))
    return [
        DailySummaryItem(
            title=item.title,
            message=item.message,
            category=item.category,
            priority=item.priority,
            action_url=item.action_url,
            entity_label=item.entity_label,
        )
        for item in active[:5]
    ]
