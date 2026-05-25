from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.bl_management import BLManagement
from app.models.charge import Charge
from app.models.demurrage import Demurrage
from app.models.document import Document
from app.models.email import EmailConnection, EmailMessageCache, EmailSuggestion
from app.models.notification import NotificationRule
from app.models.shipment import Shipment
from app.models.task import Task
from app.services.demurrage_service import calculate_demurrage
from app.services.notification_service import create_notification, get_rules_by_key


INACTIVE_SHIPMENT_STATUSES = {"completed", "Completed", "cancelled", "Cancelled"}
IMPORT_DELIVERED_STATUSES = INACTIVE_SHIPMENT_STATUSES | {"Container Delivered", "Freight Collected"}


def run_notification_checks(db: Session, source: str = "scheduler") -> dict[str, Any]:
    today = date.today()
    rules = get_rules_by_key(db)
    created = 0
    checked_rules: list[str] = []
    skipped_rules: list[str] = []

    checks = [
        ("overdue_tasks", _notify_overdue_tasks),
        ("due_tasks_today", _notify_due_tasks_today),
        ("demurrage_running", _notify_demurrage_running),
        ("demurrage_expiring_soon", _notify_demurrage_expiring_soon),
        ("bl_approval_pending", _notify_bl_approval_pending),
        ("pending_document_review", _notify_pending_document_review),
        ("pending_receivables", _notify_pending_charges),
        ("pending_payables", _notify_pending_charges),
        ("gmail_suggestions_pending", _notify_gmail_suggestions_pending),
        ("shipments_eta_today", _notify_shipments_eta_today),
    ]

    for rule_key, handler in checks:
        rule = rules.get(rule_key)
        if not rule or not rule.is_enabled:
            skipped_rules.append(rule_key)
            continue
        checked_rules.append(rule_key)
        created += handler(db, rule, today, source)

    if created:
        db.commit()
    else:
        db.rollback()
    return {"created": created, "checked_rules": checked_rules, "skipped_rules": skipped_rules}


def _notify_overdue_tasks(db: Session, rule: NotificationRule, today: date, source: str) -> int:
    tasks = (
        db.query(Task)
        .join(Shipment, Shipment.id == Task.shipment_id)
        .filter(
            Task.status == "open",
            Task.due_date.isnot(None),
            Task.due_date < today,
            Shipment.is_archived.is_(False),
            ~Shipment.status.in_(INACTIVE_SHIPMENT_STATUSES),
        )
        .all()
    )
    created = 0
    for task in tasks:
        shipment_code = task.shipment.shipment_code if task.shipment else f"Shipment #{task.shipment_id}"
        created += _create(
            db,
            title="Overdue task",
            message=f'Task "{task.title}" is overdue for shipment {shipment_code}.',
            category=rule.category,
            priority=rule.priority,
            target_role=rule.target_role,
            entity_type="task",
            entity_id=task.id,
            entity_label=task.title,
            action_url=f"/shipments/{task.shipment_id}",
            dedupe_key=f"overdue_task:{task.id}",
            source=source,
            metadata={"shipment_id": task.shipment_id, "due_date": task.due_date.isoformat()},
        )
    return created


def _notify_due_tasks_today(db: Session, rule: NotificationRule, today: date, source: str) -> int:
    tasks = (
        db.query(Task)
        .join(Shipment, Shipment.id == Task.shipment_id)
        .filter(
            Task.status == "open",
            Task.due_date == today,
            Shipment.is_archived.is_(False),
            ~Shipment.status.in_(INACTIVE_SHIPMENT_STATUSES),
        )
        .all()
    )
    created = 0
    for task in tasks:
        shipment_code = task.shipment.shipment_code if task.shipment else f"Shipment #{task.shipment_id}"
        created += _create(
            db,
            title="Task due today",
            message=f'Task "{task.title}" is due today for shipment {shipment_code}.',
            category=rule.category,
            priority=rule.priority,
            target_role=rule.target_role,
            entity_type="task",
            entity_id=task.id,
            entity_label=task.title,
            action_url=f"/shipments/{task.shipment_id}",
            dedupe_key=f"task_due_today:{task.id}:{today.isoformat()}",
            source=source,
            metadata={"shipment_id": task.shipment_id, "due_date": today.isoformat()},
        )
    return created


def _notify_demurrage_running(db: Session, rule: NotificationRule, today: date, source: str) -> int:
    rows = (
        db.query(Demurrage, Shipment)
        .join(Shipment, Shipment.id == Demurrage.shipment_id)
        .filter(Shipment.type == "import", Shipment.is_archived.is_(False))
        .all()
    )
    created = 0
    for demurrage, shipment in rows:
        if shipment.status in IMPORT_DELIVERED_STATUSES:
            continue
        read = calculate_demurrage(demurrage, today=today, persist_status=False)
        if not read.is_demurrage_running:
            continue
        created += _create(
            db,
            title="Demurrage running",
            message=f"Demurrage is running for shipment {shipment.shipment_code}.",
            category=rule.category,
            priority=rule.priority,
            target_role=rule.target_role,
            entity_type="shipment",
            entity_id=shipment.id,
            entity_label=shipment.shipment_code,
            action_url=f"/shipments/{shipment.id}",
            dedupe_key=f"demurrage_running:{shipment.id}",
            source=source,
            metadata={"days_remaining": read.days_remaining, "currency": read.currency},
        )
    return created


def _notify_demurrage_expiring_soon(db: Session, rule: NotificationRule, today: date, source: str) -> int:
    threshold = rule.threshold_days if rule.threshold_days is not None else 2
    rows = (
        db.query(Demurrage, Shipment)
        .join(Shipment, Shipment.id == Demurrage.shipment_id)
        .filter(Shipment.type == "import", Shipment.is_archived.is_(False))
        .all()
    )
    created = 0
    for demurrage, shipment in rows:
        if shipment.status in IMPORT_DELIVERED_STATUSES:
            continue
        read = calculate_demurrage(demurrage, today=today, persist_status=False)
        if read.days_remaining is None or read.days_remaining <= 0 or read.days_remaining > threshold:
            continue
        created += _create(
            db,
            title="Free days expiring soon",
            message=f"Free days for shipment {shipment.shipment_code} expire in {read.days_remaining} day(s).",
            category=rule.category,
            priority=rule.priority,
            target_role=rule.target_role,
            entity_type="shipment",
            entity_id=shipment.id,
            entity_label=shipment.shipment_code,
            action_url=f"/shipments/{shipment.id}",
            dedupe_key=f"demurrage_expiring:{shipment.id}",
            source=source,
            metadata={"days_remaining": read.days_remaining, "threshold_days": threshold},
        )
    return created


def _notify_bl_approval_pending(db: Session, rule: NotificationRule, today: date, source: str) -> int:
    shipments = (
        db.query(Shipment)
        .outerjoin(BLManagement, BLManagement.shipment_id == Shipment.id)
        .filter(
            Shipment.is_archived.is_(False),
            ~Shipment.status.in_(INACTIVE_SHIPMENT_STATUSES),
            BLManagement.approval_date.is_(None),
            or_(Shipment.status == "BL Draft Received", BLManagement.draft_received.isnot(None)),
        )
        .all()
    )
    created = 0
    for shipment in shipments:
        created += _create(
            db,
            title="BL approval pending",
            message=f"BL approval is pending for shipment {shipment.shipment_code}.",
            category=rule.category,
            priority=rule.priority,
            target_role=rule.target_role,
            entity_type="shipment",
            entity_id=shipment.id,
            entity_label=shipment.shipment_code,
            action_url=f"/shipments/{shipment.id}",
            dedupe_key=f"bl_approval_pending:{shipment.id}",
            source=source,
        )
    return created


def _notify_pending_document_review(db: Session, rule: NotificationRule, today: date, source: str) -> int:
    threshold = rule.threshold_days if rule.threshold_days is not None else 3
    cutoff = datetime(today.year, today.month, today.day) - timedelta(days=threshold)
    docs = (
        db.query(Document, Shipment)
        .join(Shipment, Shipment.id == Document.shipment_id)
        .filter(
            Document.is_required.is_(True),
            Document.status == "pending",
            Document.created_at <= cutoff,
            Shipment.is_archived.is_(False),
            ~Shipment.status.in_(INACTIVE_SHIPMENT_STATUSES),
        )
        .all()
    )
    created = 0
    for document, shipment in docs:
        created += _create(
            db,
            title="Document review pending",
            message=f"{document.doc_type} is pending for shipment {shipment.shipment_code}.",
            category=rule.category,
            priority=rule.priority,
            target_role=rule.target_role,
            entity_type="document",
            entity_id=document.id,
            entity_label=f"{shipment.shipment_code} {document.doc_type}",
            action_url=f"/shipments/{shipment.id}",
            dedupe_key=f"pending_document:{document.id}",
            source=source,
            metadata={"shipment_id": shipment.id, "threshold_days": threshold},
        )
    return created


def _notify_pending_charges(db: Session, rule: NotificationRule, today: date, source: str) -> int:
    direction = "receivable" if rule.rule_key == "pending_receivables" else "payable"
    threshold = rule.threshold_days if rule.threshold_days is not None else 7
    cutoff = today - timedelta(days=threshold)
    rows = (
        db.query(Charge, Shipment)
        .join(Shipment, Shipment.id == Charge.shipment_id)
        .filter(
            Charge.direction == direction,
            Charge.status == "pending",
            Shipment.is_archived.is_(False),
            ~Shipment.status.in_(INACTIVE_SHIPMENT_STATUSES),
        )
        .all()
    )
    created = 0
    for charge, shipment in rows:
        charge_date = charge.date or charge.created_at.date()
        if charge_date > cutoff:
            continue
        title = "Pending receivable" if direction == "receivable" else "Pending payable"
        amount = _format_money(charge.amount, charge.currency)
        created += _create(
            db,
            title=title,
            message=f"{amount} is pending for shipment {shipment.shipment_code}.",
            category=rule.category,
            priority=rule.priority,
            target_role=rule.target_role,
            entity_type="charge",
            entity_id=charge.id,
            entity_label=charge.invoice_no or f"Charge #{charge.id}",
            action_url=f"/shipments/{shipment.id}",
            dedupe_key=f"pending_{direction}:{charge.id}",
            source=source,
            metadata={"shipment_id": shipment.id, "direction": direction, "threshold_days": threshold},
        )
    return created


def _notify_gmail_suggestions_pending(db: Session, rule: NotificationRule, today: date, source: str) -> int:
    rows = (
        db.query(EmailConnection.user_id, func.count(EmailSuggestion.id))
        .join(EmailMessageCache, EmailMessageCache.connection_id == EmailConnection.id)
        .join(EmailSuggestion, EmailSuggestion.email_message_id == EmailMessageCache.id)
        .filter(EmailConnection.is_active.is_(True), EmailSuggestion.status == "pending")
        .group_by(EmailConnection.user_id)
        .all()
    )
    created = 0
    for user_id, count in rows:
        created += _create(
            db,
            title="Gmail suggestions pending",
            message=f"{count} Gmail suggestion(s) need review.",
            category=rule.category,
            priority=rule.priority,
            target_user_id=user_id,
            entity_type="gmail_suggestion",
            action_url="/email",
            dedupe_key=f"gmail_suggestions_pending:{user_id}:{today.isoformat()}",
            source=source,
            metadata={"pending_count": int(count)},
        )
    return created


def _notify_shipments_eta_today(db: Session, rule: NotificationRule, today: date, source: str) -> int:
    threshold = rule.threshold_days if rule.threshold_days is not None else 1
    end_date = today + timedelta(days=threshold)
    shipments = (
        db.query(Shipment)
        .filter(
            Shipment.eta.isnot(None),
            Shipment.eta >= today,
            Shipment.eta <= end_date,
            Shipment.is_archived.is_(False),
            ~Shipment.status.in_(INACTIVE_SHIPMENT_STATUSES),
        )
        .all()
    )
    created = 0
    for shipment in shipments:
        when = "today" if shipment.eta == today else "tomorrow"
        created += _create(
            db,
            title="Shipment ETA approaching",
            message=f"Shipment {shipment.shipment_code} has ETA {when} ({shipment.eta}).",
            category=rule.category,
            priority=rule.priority,
            target_role=rule.target_role,
            entity_type="shipment",
            entity_id=shipment.id,
            entity_label=shipment.shipment_code,
            action_url=f"/shipments/{shipment.id}",
            dedupe_key=f"shipment_eta:{shipment.id}:{today.isoformat()}",
            source=source,
            metadata={"eta": shipment.eta.isoformat(), "threshold_days": threshold},
        )
    return created


def _create(db: Session, **kwargs) -> int:
    _, created = create_notification(db, **kwargs)
    return 1 if created else 0


def _format_money(amount: Decimal, currency: str) -> str:
    return f"{currency} {amount}"
