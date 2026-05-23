from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.bl_management import BLManagement
from app.models.demurrage import Demurrage
from app.models.document import Document
from app.models.shipment import Shipment
from app.models.task import Task
from app.schemas.shipment import WorkflowStatusUpdate


EXPORT_STATUSES = [
    "Booking Received",
    "Container Booked",
    "SI Submitted",
    "VGM Filed",
    "BL Draft Received",
    "BL Approved",
    "Final BL Received",
    "Docs Collected",
    "Docs Dispatched",
    "Overseas Coordinated",
    "Freight Invoiced",
    "Vessel Sailed",
    "Completed",
]

IMPORT_STATUSES = [
    "Pre-Alert Received",
    "ETA Tracking Active",
    "IGM Filed",
    "Freight Invoice Received",
    "BL Surrender Confirmed",
    "DO Received",
    "DO Handed to CHA",
    "Clearance In Progress",
    "Container Delivered",
    "Freight Collected",
    "Completed",
]

EXPORT_NEXT_TASKS = {
    "Booking Received": "Book container with line",
    "Container Booked": "Send Shipping Instruction",
    "SI Submitted": "Follow up VGM",
    "VGM Filed": "Check BL draft from line",
    "BL Draft Received": "Get BL approval from exporter",
    "BL Approved": "Request final BL from line",
    "Final BL Received": "Collect Invoice and Packing List",
    "Docs Collected": "Dispatch documents via courier",
    "Docs Dispatched": "Coordinate with overseas FF",
    "Overseas Coordinated": "Raise freight invoice to client",
    "Freight Invoiced": "Confirm vessel sailing",
    "Vessel Sailed": "Monitor until shipment completion",
}

IMPORT_NEXT_TASKS = {
    "Pre-Alert Received": "Track ETA updates from line",
    "ETA Tracking Active": "File IGM with shipping line",
    "IGM Filed": "Follow up line for freight invoice",
    "Freight Invoice Received": "Confirm BL surrender or telex",
    "BL Surrender Confirmed": "Pay freight and get DO",
    "DO Received": "Hand DO to CHA",
    "DO Handed to CHA": "Track clearance status",
    "Clearance In Progress": "Track container delivery",
    "Container Delivered": "Collect freight from importer",
    "Freight Collected": "Mark shipment completed",
}


def default_workflow_status(shipment_type: str) -> str:
    return "Booking Received" if shipment_type == "export" else "Pre-Alert Received"


def workflow_statuses_for(shipment_type: str) -> list[str]:
    return EXPORT_STATUSES if shipment_type == "export" else IMPORT_STATUSES


def next_task_for(shipment: Shipment, status: str) -> Optional[str]:
    mapping = EXPORT_NEXT_TASKS if shipment.type == "export" else IMPORT_NEXT_TASKS
    return mapping.get(status)


def update_workflow_status(
    db: Session, shipment: Shipment, update: WorkflowStatusUpdate
) -> Shipment:
    valid_statuses = workflow_statuses_for(shipment.type)
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid workflow status for shipment type")
    shipment.status = update.status
    _create_next_task(db, shipment, update.status)
    _apply_workflow_side_effects(db, shipment, update.status)
    db.commit()
    db.refresh(shipment)
    return shipment


def _create_next_task(db: Session, shipment: Shipment, status: str) -> None:
    title = next_task_for(shipment, status)
    if not title:
        return
    existing = (
        db.query(Task)
        .filter(Task.shipment_id == shipment.id, Task.title == title, Task.auto_generated.is_(True))
        .first()
    )
    if existing:
        return
    db.add(
        Task(
            shipment_id=shipment.id,
            title=title,
            description=f"Auto-generated when workflow moved to {status}.",
            priority="info",
            status="open",
            auto_generated=True,
        )
    )


def _get_or_create_bl(db: Session, shipment: Shipment) -> BLManagement:
    record = db.query(BLManagement).filter(BLManagement.shipment_id == shipment.id).first()
    if record:
        return record
    record = BLManagement(shipment_id=shipment.id)
    db.add(record)
    db.flush()
    return record


def _get_or_create_demurrage(db: Session, shipment: Shipment) -> Demurrage:
    record = db.query(Demurrage).filter(Demurrage.shipment_id == shipment.id).first()
    if record:
        return record
    record = Demurrage(shipment_id=shipment.id)
    db.add(record)
    db.flush()
    return record


def _set_document_status_if_pending(
    db: Session, shipment: Shipment, doc_type: str, status: str
) -> None:
    document = (
        db.query(Document)
        .filter(Document.shipment_id == shipment.id, Document.doc_type == doc_type)
        .first()
    )
    if document and document.status == "pending":
        document.status = status


def _apply_workflow_side_effects(db: Session, shipment: Shipment, status: str) -> None:
    today = date.today()
    if shipment.type == "export":
        if status == "SI Submitted":
            _set_document_status_if_pending(db, shipment, "SI", "sent")
        elif status == "VGM Filed":
            _set_document_status_if_pending(db, shipment, "VGM", "received")
        elif status == "BL Draft Received":
            _set_document_status_if_pending(db, shipment, "BL_DRAFT", "received")
            bl = _get_or_create_bl(db, shipment)
            if not bl.draft_received:
                bl.draft_received = today
        elif status == "BL Approved":
            _set_document_status_if_pending(db, shipment, "BL_DRAFT", "approved")
            bl = _get_or_create_bl(db, shipment)
            if not bl.approval_date:
                bl.approval_date = today
        elif status == "Final BL Received":
            _set_document_status_if_pending(db, shipment, "FINAL_BL", "received")
            bl = _get_or_create_bl(db, shipment)
            if not bl.final_bl_date:
                bl.final_bl_date = today
        elif status == "Docs Collected":
            _set_document_status_if_pending(db, shipment, "INVOICE", "received")
            _set_document_status_if_pending(db, shipment, "PACKING_LIST", "received")
        return

    if status == "Freight Invoice Received":
        _set_document_status_if_pending(db, shipment, "FREIGHT_INVOICE", "received")
    elif status == "BL Surrender Confirmed":
        _set_document_status_if_pending(db, shipment, "TELEX_RELEASE", "received")
    elif status == "DO Received":
        _set_document_status_if_pending(db, shipment, "DO", "received")
        if not shipment.do_received_date:
            shipment.do_received_date = today
        demurrage = _get_or_create_demurrage(db, shipment)
        if not demurrage.start_date:
            demurrage.start_date = today
    elif status == "Container Delivered":
        if not shipment.container_delivered_date:
            shipment.container_delivered_date = today
        demurrage = _get_or_create_demurrage(db, shipment)
        demurrage.status = "within_free_days"
