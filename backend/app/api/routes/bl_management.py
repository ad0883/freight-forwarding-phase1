from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_write_access
from app.models.bl_management import BLManagement
from app.models.shipment import Shipment
from app.schemas.bl_management import BLManagementRead, BLManagementUpdate


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
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_write_access),
) -> BLManagement:
    record = _get_or_create_bl(db, shipment_id)
    for field, value in bl_in.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record
