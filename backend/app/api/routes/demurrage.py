from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_write_access
from app.models.shipment import Shipment
from app.schemas.demurrage import DemurrageRead, DemurrageUpdate
from app.services.dashboard_service import invalidate_dashboard_cache
from app.services.demurrage_service import calculate_demurrage, get_or_create_demurrage


router = APIRouter(prefix="/shipments/{shipment_id}/demurrage", tags=["demurrage"])


def _get_shipment(db: Session, shipment_id: int) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


@router.get("", response_model=DemurrageRead)
def get_demurrage(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> DemurrageRead:
    shipment = _get_shipment(db, shipment_id)
    record = get_or_create_demurrage(db, shipment)
    read = calculate_demurrage(record)
    db.commit()
    return read


@router.patch("", response_model=DemurrageRead)
def update_demurrage(
    shipment_id: int,
    demurrage_in: DemurrageUpdate,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_write_access),
) -> DemurrageRead:
    shipment = _get_shipment(db, shipment_id)
    record = get_or_create_demurrage(db, shipment)
    for field, value in demurrage_in.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    invalidate_dashboard_cache()
    return calculate_demurrage(record)
