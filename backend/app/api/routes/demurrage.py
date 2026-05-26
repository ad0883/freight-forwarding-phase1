from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_write_access
from app.models.shipment import Shipment
from app.schemas.demurrage import DemurrageRead, DemurrageUpdate
from app.services.audit_service import changed_fields, record_audit_log
from app.services.dashboard_service import invalidate_dashboard_cache
from app.services.demurrage_service import calculate_demurrage, get_or_create_demurrage
from app.services.event_service import OperationalEventType, diff_state, record_operational_event


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
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> DemurrageRead:
    shipment = _get_shipment(db, shipment_id)
    record = get_or_create_demurrage(db, shipment)
    data = demurrage_in.model_dump(exclude_unset=True)
    before = {field: getattr(record, field, None) for field in data}
    for field, value in data.items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    invalidate_dashboard_cache()
    record_audit_log(
        db,
        current_user,
        "demurrage.updated",
        "demurrage",
        entity_id=record.id,
        entity_label=f"Shipment {shipment.shipment_code}",
        description="Demurrage updated.",
        metadata={"shipment_id": shipment.id, "fields_changed": changed_fields(before, {field: getattr(record, field, None) for field in data})},
        request=request,
    )
    after_state = {field: getattr(record, field, None) for field in data}
    record_operational_event(
        db,
        OperationalEventType.DEMURRAGE_UPDATED.value,
        "demurrage",
        entity_id=record.id,
        entity_label=f"Shipment {shipment.shipment_code}",
        shipment_id=shipment.id,
        actor_user=current_user,
        source="user",
        previous_state=before,
        new_state=after_state,
        metadata={"shipment_id": shipment.id, "fields_changed": diff_state(before, after_state)},
        request=request,
    )
    return calculate_demurrage(record)
