from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_write_access
from app.models.bl_management import BLManagement
from app.models.shipment import Shipment
from app.schemas.bl_management import BLManagementRead, BLManagementUpdate
from app.services.audit_service import changed_fields, record_audit_log


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
    return record
