from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_write_access
from app.models.bl_management import BLManagement
from app.models.shipment import Shipment
from app.schemas.bl_management import BLManagementRead, BLManagementUpdate
from app.services.audit_service import changed_fields, record_audit_log
from app.services.event_service import OperationalEventType, diff_state, record_operational_event


router = APIRouter(prefix="/shipments/{shipment_id}/bl", tags=["bl-management"])


def _get_shipment(db: Session, shipment_id: int) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


def _get_or_create_bl(db: Session, shipment_id: int) -> BLManagement:
    _get_shipment(db, shipment_id)
    record = db.query(BLManagement).filter(BLManagement.shipment_id == shipment_id).first()
    if record:
        return record
    record = BLManagement(shipment_id=shipment_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=BLManagementRead)
def get_bl_management(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> BLManagement:
    return _get_or_create_bl(db, shipment_id)


@router.patch("", response_model=BLManagementRead)
def update_bl_management(
    shipment_id: int,
    bl_in: BLManagementUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> BLManagement:
    record = _get_or_create_bl(db, shipment_id)
    data = bl_in.model_dump(exclude_unset=True)
    before = {field: getattr(record, field, None) for field in data}
    for field, value in data.items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    record_audit_log(
        db,
        current_user,
        "bl_management.updated",
        "bl_management",
        entity_id=record.id,
        entity_label=f"Shipment #{shipment_id} BL",
        description="BL management updated.",
        metadata={"shipment_id": shipment_id, "fields_changed": changed_fields(before, {field: getattr(record, field, None) for field in data})},
        request=request,
    )
    after_state = {field: getattr(record, field, None) for field in data}
    record_operational_event(
        db,
        OperationalEventType.BL_MANAGEMENT_UPDATED.value,
        "bl_management",
        entity_id=record.id,
        entity_label=f"Shipment #{shipment_id} BL",
        shipment_id=shipment_id,
        actor_user=current_user,
        source="user",
        previous_state=before,
        new_state={
            "draft_received": getattr(record, "draft_received", None),
            "approval_date": getattr(record, "approval_date", None),
            "final_received": getattr(record, "final_received", None),
            "bl_number": getattr(record, "bl_number", None),
            **after_state,
        },
        metadata={"shipment_id": shipment_id, "fields_changed": diff_state(before, after_state)},
        request=request,
    )
    return record
