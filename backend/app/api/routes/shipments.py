from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db, require_write_access
from app.models.party import Party
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas.shipment import DashboardSummary, ShipmentCreate, ShipmentRead, ShipmentUpdate
from app.services.dashboard_service import get_dashboard_summary, invalidate_dashboard_cache
from app.services.shipment_service import create_shipment_with_defaults


router = APIRouter(prefix="/shipments", tags=["shipments"])


def _validate_party_ids(db: Session, exporter_id: Optional[int], importer_id: Optional[int]) -> None:
    for party_id in [exporter_id, importer_id]:
        if party_id is None:
            continue
        exists = db.query(Party.id).filter(Party.id == party_id).first()
        if not exists:
            raise HTTPException(status_code=400, detail=f"Party {party_id} does not exist")


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> DashboardSummary:
    return get_dashboard_summary(db)


@router.get("", response_model=list[ShipmentRead])
def list_shipments(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Shipment]:
    query = db.query(Shipment).options(joinedload(Shipment.exporter), joinedload(Shipment.importer))
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_access),
) -> Shipment:
    _validate_party_ids(db, shipment_in.exporter_id, shipment_in.importer_id)
    shipment = create_shipment_with_defaults(db, shipment_in, current_user.id)
    invalidate_dashboard_cache()
    return shipment


@router.get("/{shipment_id}", response_model=ShipmentRead)
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
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
    db: Session = Depends(get_db),
    _: User = Depends(require_write_access),
) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    data = shipment_in.model_dump(exclude_unset=True)
    _validate_party_ids(db, data.get("exporter_id"), data.get("importer_id"))
    for field, value in data.items():
        setattr(shipment, field, value)
    db.commit()
    db.refresh(shipment)
    invalidate_dashboard_cache()
    return shipment
