from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_roles, require_write_access
from app.models.party import Party
from app.models.shipment import Shipment
from app.schemas.shipment import (
    DashboardSummary,
    ShipmentArchiveRequest,
    ShipmentCreate,
    ShipmentRead,
    ShipmentUpdate,
    WorkflowStatusUpdate,
)
from app.services.dashboard_service import get_dashboard_summary, invalidate_dashboard_cache
from app.services.event_service import OperationalEventType, diff_state, record_operational_event
from app.services.shipment_service import create_shipment_with_defaults
from app.services.audit_service import changed_fields, record_audit_log
from app.services.workflow_service import update_workflow_status


router = APIRouter(prefix="/shipments", tags=["shipments"])


def _validate_party_ids(db: Session, exporter_id: Optional[int], importer_id: Optional[int]) -> None:
    for party_id in [exporter_id, importer_id]:
        if party_id is None:
            continue
        exists = db.query(Party.id).filter(Party.id == party_id, Party.is_active.is_(True)).first()
        if not exists:
            raise HTTPException(status_code=400, detail=f"Party {party_id} does not exist or is inactive")


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(
    db: Session = Depends(get_db), _: AuthenticatedUser = Depends(get_current_user)
) -> DashboardSummary:
    return get_dashboard_summary(db)


@router.get("", response_model=list[ShipmentRead])
def list_shipments(
    search: Optional[str] = None,
    include_archived: bool = False,
    archived_only: bool = False,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[Shipment]:
    query = db.query(Shipment).options(joinedload(Shipment.exporter), joinedload(Shipment.importer))
    if archived_only:
        query = query.filter(Shipment.is_archived.is_(True))
    elif not include_archived:
        query = query.filter(Shipment.is_archived.is_(False))
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Shipment.shipment_code.ilike(pattern),
                Shipment.shipping_line.ilike(pattern),
                Shipment.origin_port.ilike(pattern),
                Shipment.dest_port.ilike(pattern),
                Shipment.commodity.ilike(pattern),
            )
        )
    return query.order_by(Shipment.created_at.desc()).all()


@router.post("", response_model=ShipmentRead, status_code=status.HTTP_201_CREATED)
def create_shipment(
    shipment_in: ShipmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> Shipment:
    _validate_party_ids(db, shipment_in.exporter_id, shipment_in.importer_id)
    shipment = create_shipment_with_defaults(db, shipment_in, current_user.id)
    invalidate_dashboard_cache()
    record_audit_log(
        db,
        current_user,
        "shipment.created",
        "shipment",
        entity_id=shipment.id,
        entity_label=shipment.shipment_code,
        description="Shipment created.",
        metadata={"type": shipment.type, "status": shipment.status},
        request=request,
    )
    record_operational_event(
        db,
        OperationalEventType.SHIPMENT_CREATED.value,
        "shipment",
        entity_id=shipment.id,
        entity_label=shipment.shipment_code,
        shipment_id=shipment.id,
        actor_user=current_user,
        source="user",
        new_state={
            "shipment_code": shipment.shipment_code,
            "type": shipment.type,
            "status": shipment.status,
            "is_archived": shipment.is_archived,
        },
        metadata={"created": True},
        request=request,
    )
    return shipment


@router.get("/{shipment_id}", response_model=ShipmentRead)
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> Shipment:
    shipment = (
        db.query(Shipment)
        .options(joinedload(Shipment.exporter), joinedload(Shipment.importer))
        .filter(Shipment.id == shipment_id)
        .first()
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


@router.patch("/{shipment_id}", response_model=ShipmentRead)
def update_shipment(
    shipment_id: int,
    shipment_in: ShipmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    data = shipment_in.model_dump(exclude_unset=True)
    _validate_party_ids(db, data.get("exporter_id"), data.get("importer_id"))
    before = {field: getattr(shipment, field, None) for field in data}
    for field, value in data.items():
        setattr(shipment, field, value)
    db.commit()
    db.refresh(shipment)
    invalidate_dashboard_cache()
    record_audit_log(
        db,
        current_user,
        "shipment.updated",
        "shipment",
        entity_id=shipment.id,
        entity_label=shipment.shipment_code,
        description="Shipment updated.",
        metadata={"fields_changed": changed_fields(before, {field: getattr(shipment, field, None) for field in data})},
        request=request,
    )
    record_operational_event(
        db,
        OperationalEventType.SHIPMENT_UPDATED.value,
        "shipment",
        entity_id=shipment.id,
        entity_label=shipment.shipment_code,
        shipment_id=shipment.id,
        actor_user=current_user,
        source="user",
        previous_state=before,
        new_state={
            "shipment_code": shipment.shipment_code,
            "type": shipment.type,
            "status": shipment.status,
            "is_archived": shipment.is_archived,
            **{field: getattr(shipment, field, None) for field in data},
        },
        metadata={"fields_changed": diff_state(before, {field: getattr(shipment, field, None) for field in data})},
        request=request,
    )
    return shipment


@router.patch("/{shipment_id}/archive", response_model=ShipmentRead)
def archive_shipment(
    shipment_id: int,
    archive_in: ShipmentArchiveRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    shipment.is_archived = True
    shipment.archived_at = datetime.utcnow()
    shipment.archived_by = current_user.id
    shipment.archive_reason = archive_in.reason
    db.commit()
    db.refresh(shipment)
    invalidate_dashboard_cache()
    record_audit_log(
        db,
        current_user,
        "shipment.archived",
        "shipment",
        entity_id=shipment.id,
        entity_label=shipment.shipment_code,
        description="Shipment archived.",
        metadata={"reason_present": bool(archive_in.reason)},
        request=request,
    )
    record_operational_event(
        db,
        OperationalEventType.SHIPMENT_ARCHIVED.value,
        "shipment",
        entity_id=shipment.id,
        entity_label=shipment.shipment_code,
        shipment_id=shipment.id,
        actor_user=current_user,
        source="user",
        new_state={
            "shipment_code": shipment.shipment_code,
            "type": shipment.type,
            "status": shipment.status,
            "is_archived": True,
        },
        metadata={"reason_present": bool(archive_in.reason)},
        request=request,
    )
    return shipment


@router.patch("/{shipment_id}/restore", response_model=ShipmentRead)
def restore_shipment(
    shipment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    shipment.is_archived = False
    shipment.archived_at = None
    shipment.archived_by = None
    shipment.archive_reason = None
    db.commit()
    db.refresh(shipment)
    invalidate_dashboard_cache()
    record_audit_log(
        db,
        current_user,
        "shipment.restored",
        "shipment",
        entity_id=shipment.id,
        entity_label=shipment.shipment_code,
        description="Shipment restored from archive.",
        metadata={"restored": True},
        request=request,
    )
    record_operational_event(
        db,
        OperationalEventType.SHIPMENT_RESTORED.value,
        "shipment",
        entity_id=shipment.id,
        entity_label=shipment.shipment_code,
        shipment_id=shipment.id,
        actor_user=current_user,
        source="user",
        new_state={
            "shipment_code": shipment.shipment_code,
            "type": shipment.type,
            "status": shipment.status,
            "is_archived": False,
        },
        metadata={"restored": True},
        request=request,
    )
    return shipment


@router.patch("/{shipment_id}/workflow-status", response_model=ShipmentRead)
def update_shipment_workflow_status(
    shipment_id: int,
    workflow_in: WorkflowStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    previous_status = shipment.status
    updated = update_workflow_status(db, shipment, workflow_in)
    invalidate_dashboard_cache()
    record_audit_log(
        db,
        current_user,
        "shipment.workflow_status_updated",
        "shipment",
        entity_id=updated.id,
        entity_label=updated.shipment_code,
        description="Shipment workflow status updated.",
        metadata={"from_status": previous_status, "to_status": updated.status},
        request=request,
    )
    record_operational_event(
        db,
        OperationalEventType.SHIPMENT_WORKFLOW_STATUS_UPDATED.value,
        "shipment",
        entity_id=updated.id,
        entity_label=updated.shipment_code,
        shipment_id=updated.id,
        actor_user=current_user,
        source="workflow",
        previous_state={"status": previous_status},
        new_state={
            "shipment_code": updated.shipment_code,
            "type": updated.type,
            "status": updated.status,
            "is_archived": updated.is_archived,
        },
        metadata={"from_status": previous_status, "to_status": updated.status},
        request=request,
    )
    return updated
