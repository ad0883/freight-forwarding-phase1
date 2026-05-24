from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.demurrage import Demurrage
from app.models.document import Document
from app.models.shipment import Shipment
from app.models.task import Task
from app.services.dashboard_service import invalidate_dashboard_cache
from app.services.demurrage_service import calculate_demurrage


INACTIVE_SHIPMENT_STATUSES = {"completed", "Completed", "cancelled", "Cancelled"}
IMPORT_DELIVERED_STATUSES = INACTIVE_SHIPMENT_STATUSES | {"Container Delivered", "Freight Collected"}


def create_overdue_task_alerts(db: Session) -> int:
    today = date.today()
    created = 0
    created += _create_task_overdue_alerts(db, today)
    created += _create_export_deadline_alerts(db, today)
    created += _create_import_demurrage_alerts(db, today)
    created += _create_import_document_alerts(db, today)
    if created:
        db.commit()
        invalidate_dashboard_cache()
    return created


def _alert_exists(db: Session, shipment_id: int, title: str, priority: str) -> bool:
    return (
        db.query(Alert.id)
        .filter(
            Alert.shipment_id == shipment_id,
            Alert.title == title,
            Alert.priority == priority,
            Alert.is_read.is_(False),
        )
        .first()
        is not None
    )


def _add_alert(
    db: Session,
    shipment_id: int,
    title: str,
    message: str,
    priority: str,
    task_id: Optional[int] = None,
) -> int:
    if _alert_exists(db, shipment_id, title, priority):
        return 0
    db.add(
        Alert(
            shipment_id=shipment_id,
            task_id=task_id,
            title=title,
            message=message,
            priority=priority,
        )
    )
    return 1


def _create_task_overdue_alerts(db: Session, today: date) -> int:
    overdue_tasks = (
        db.query(Task)
        .join(Shipment, Shipment.id == Task.shipment_id)
        .filter(
            Task.status == "open",
            Task.due_date.isnot(None),
            Task.due_date < today,
            Shipment.is_archived.is_(False),
        )
        .all()
    )
    created = 0
    for task in overdue_tasks:
        created += _add_alert(
            db,
            shipment_id=task.shipment_id,
            task_id=task.id,
            title=f"Overdue task: {task.title}",
            message=f"Task '{task.title}' is overdue.",
            priority="warning",
        )
    return created


def _document_incomplete(db: Session, shipment_id: int, doc_type: str) -> bool:
    document = (
        db.query(Document)
        .filter(Document.shipment_id == shipment_id, Document.doc_type == doc_type)
        .first()
    )
    if not document:
        return True
    return document.status not in ["received", "approved", "not_required"]


def _within_days(target: Optional[date], today: date, days: int) -> bool:
    return target is not None and today <= target <= today + timedelta(days=days)


def _create_export_deadline_alerts(db: Session, today: date) -> int:
    shipments = db.query(Shipment).filter(Shipment.type == "export", Shipment.is_archived.is_(False)).all()
    created = 0
    for shipment in shipments:
        if shipment.status in INACTIVE_SHIPMENT_STATUSES:
            continue
        if _within_days(shipment.vgm_cutoff_date, today, 2) and _document_incomplete(db, shipment.id, "VGM"):
            created += _add_alert(
                db,
                shipment.id,
                "VGM cutoff approaching",
                f"VGM cutoff for {shipment.shipment_code} is within 2 days.",
                "warning",
            )
        if _within_days(shipment.si_cutoff_date, today, 2) and _document_incomplete(db, shipment.id, "SI"):
            created += _add_alert(
                db,
                shipment.id,
                "SI cutoff approaching",
                f"SI cutoff for {shipment.shipment_code} is within 2 days.",
                "warning",
            )
        if _within_days(shipment.bl_cutoff_date, today, 2) and _document_incomplete(db, shipment.id, "BL_DRAFT"):
            created += _add_alert(
                db,
                shipment.id,
                "BL cutoff approaching",
                f"BL cutoff for {shipment.shipment_code} is within 2 days.",
                "warning",
            )
    return created


def _create_import_demurrage_alerts(db: Session, today: date) -> int:
    records = (
        db.query(Demurrage, Shipment)
        .join(Shipment, Shipment.id == Demurrage.shipment_id)
        .filter(Shipment.type == "import", Shipment.is_archived.is_(False))
        .all()
    )
    created = 0
    for demurrage, shipment in records:
        if shipment.status in IMPORT_DELIVERED_STATUSES:
            continue
        read = calculate_demurrage(demurrage, today=today)
        if read.days_remaining is None:
            continue
        if 0 < read.days_remaining <= demurrage.alert_at_days:
            created += _add_alert(
                db,
                shipment.id,
                "Free days expiring",
                f"Free days for {shipment.shipment_code} expire in {read.days_remaining} day(s).",
                "critical",
            )
        elif read.days_remaining <= 0:
            demurrage.status = "running"
            created += _add_alert(
                db,
                shipment.id,
                "Demurrage started",
                f"Demurrage is running for {shipment.shipment_code}.",
                "critical",
            )
    return created


def _create_import_document_alerts(db: Session, today: date) -> int:
    shipments = db.query(Shipment).filter(Shipment.type == "import", Shipment.is_archived.is_(False)).all()
    created = 0
    for shipment in shipments:
        if shipment.status in IMPORT_DELIVERED_STATUSES:
            continue
        if shipment.eta and shipment.eta < today - timedelta(days=2) and _document_incomplete(db, shipment.id, "DO"):
            created += _add_alert(
                db,
                shipment.id,
                "DO not collected",
                f"DO is not marked received for {shipment.shipment_code}.",
                "critical",
            )
        if shipment.eta and today <= shipment.eta <= today + timedelta(days=3) and _document_incomplete(db, shipment.id, "FREIGHT_INVOICE"):
            created += _add_alert(
                db,
                shipment.id,
                "Freight invoice pending",
                f"Freight invoice is pending for {shipment.shipment_code}.",
                "warning",
            )
    return created
