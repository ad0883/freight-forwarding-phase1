import csv
import json
from io import StringIO

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.models.audit import AuditLog
from app.models.charge import Charge
from app.models.party import Party
from app.models.shipment import Shipment
from app.models.task import Task
from app.services.audit_service import record_audit_log


router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/shipments.csv")
def export_shipments(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> Response:
    rows = [
        {
            "id": shipment.id,
            "shipment_code": shipment.shipment_code,
            "type": shipment.type,
            "status": shipment.status,
            "exporter": shipment.exporter.name if shipment.exporter else "",
            "importer": shipment.importer.name if shipment.importer else "",
            "shipping_line": shipment.shipping_line,
            "vessel_name": shipment.vessel_name,
            "voyage_no": shipment.voyage_no,
            "origin_port": shipment.origin_port,
            "dest_port": shipment.dest_port,
            "container_no": shipment.container_no,
            "container_type": shipment.container_type,
            "etd": shipment.etd,
            "eta": shipment.eta,
            "booking_ref": shipment.booking_ref,
            "bl_number": shipment.bl_number,
            "commodity": shipment.commodity,
            "is_archived": shipment.is_archived,
            "created_at": shipment.created_at,
        }
        for shipment in db.query(Shipment)
        .options(joinedload(Shipment.exporter), joinedload(Shipment.importer))
        .order_by(Shipment.created_at.desc())
        .all()
    ]
    record_audit_log(
        db,
        current_user,
        "export.shipments",
        "export",
        description="Admin exported shipments CSV.",
        metadata={"row_count": len(rows)},
        request=request,
    )
    return _csv_response("shipments.csv", rows)


@router.get("/parties.csv")
def export_parties(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> Response:
    rows = [
        {
            "id": party.id,
            "name": party.name,
            "type": party.type,
            "contact_person": party.contact_person,
            "email": party.email,
            "phone": party.phone,
            "country": party.country,
            "gstin": party.gstin,
            "is_active": party.is_active,
            "created_at": party.created_at,
        }
        for party in db.query(Party).order_by(Party.name.asc()).all()
    ]
    record_audit_log(
        db,
        current_user,
        "export.parties",
        "export",
        description="Admin exported parties CSV.",
        metadata={"row_count": len(rows)},
        request=request,
    )
    return _csv_response("parties.csv", rows)


@router.get("/charges.csv")
def export_charges(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> Response:
    rows = [
        {
            "id": charge.id,
            "shipment_id": charge.shipment_id,
            "shipment_code": charge.shipment.shipment_code if charge.shipment else "",
            "charge_type": charge.charge_type,
            "direction": charge.direction,
            "amount": charge.amount,
            "currency": charge.currency,
            "party": charge.party.name if charge.party else "",
            "status": charge.status,
            "invoice_no": charge.invoice_no,
            "date": charge.date,
            "notes": charge.notes,
            "created_at": charge.created_at,
            "updated_at": charge.updated_at,
        }
        for charge in db.query(Charge)
        .options(joinedload(Charge.shipment), joinedload(Charge.party))
        .order_by(Charge.created_at.desc())
        .all()
    ]
    record_audit_log(
        db,
        current_user,
        "export.charges",
        "export",
        description="Admin exported charges CSV.",
        metadata={"row_count": len(rows)},
        request=request,
    )
    return _csv_response("charges.csv", rows)


@router.get("/tasks.csv")
def export_tasks(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> Response:
    rows = [
        {
            "id": task.id,
            "shipment_id": task.shipment_id,
            "shipment_code": task.shipment.shipment_code if task.shipment else "",
            "title": task.title,
            "description": task.description,
            "assigned_to": task.assigned_to,
            "due_date": task.due_date,
            "priority": task.priority,
            "status": task.status,
            "auto_generated": task.auto_generated,
            "created_at": task.created_at,
        }
        for task in db.query(Task)
        .options(joinedload(Task.shipment))
        .order_by(Task.created_at.desc())
        .all()
    ]
    record_audit_log(
        db,
        current_user,
        "export.tasks",
        "export",
        description="Admin exported tasks CSV.",
        metadata={"row_count": len(rows)},
        request=request,
    )
    return _csv_response("tasks.csv", rows)


@router.get("/audit-logs.csv")
def export_audit_logs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> Response:
    rows = [
        {
            "id": audit_log.id,
            "created_at": audit_log.created_at,
            "actor_user_id": audit_log.actor_user_id,
            "actor_name": audit_log.actor_name,
            "actor_email": audit_log.actor_email,
            "actor_role": audit_log.actor_role,
            "action": audit_log.action,
            "entity_type": audit_log.entity_type,
            "entity_id": audit_log.entity_id,
            "entity_label": audit_log.entity_label,
            "description": audit_log.description,
            "metadata_json": json.dumps(audit_log.metadata_json or {}, default=str),
            "ip_address": audit_log.ip_address,
        }
        for audit_log in db.query(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).all()
    ]
    record_audit_log(
        db,
        current_user,
        "export.audit_logs",
        "export",
        description="Admin exported audit logs CSV.",
        metadata={"row_count": len(rows)},
        request=request,
    )
    return _csv_response("audit-logs.csv", rows)


def _csv_response(filename: str, rows: list[dict[str, object]]) -> Response:
    output = StringIO()
    fieldnames = list(rows[0].keys()) if rows else ["id"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
