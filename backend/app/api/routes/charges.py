from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_write_access
from app.models.charge import Charge
from app.models.party import Party
from app.models.shipment import Shipment
from app.schemas.charge import ChargeCreate, ChargeRead, ChargeUpdate, ShipmentPLSummary, is_valid_charge_status
from app.services.audit_service import changed_fields, record_audit_log
from app.services.dashboard_service import invalidate_dashboard_cache
from app.services.finance_service import calculate_shipment_pnl


router = APIRouter(tags=["charges"])


def _get_shipment(db: Session, shipment_id: int) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


def _get_charge(db: Session, charge_id: int) -> Charge:
    charge = (
        db.query(Charge)
        .options(joinedload(Charge.shipment), joinedload(Charge.party))
        .filter(Charge.id == charge_id)
        .first()
    )
    if not charge:
        raise HTTPException(status_code=404, detail="Charge not found")
    return charge


def _validate_party(db: Session, party_id: Optional[int]) -> None:
    if party_id is None:
        return
    exists = db.query(Party.id).filter(Party.id == party_id, Party.is_active.is_(True)).first()
    if not exists:
        raise HTTPException(status_code=400, detail="Party does not exist or is inactive")


def _validate_direction_status(direction: str, status_value: str) -> None:
    if not is_valid_charge_status(direction, status_value):
        raise HTTPException(
            status_code=400,
            detail=f"{status_value} is not valid for {direction} charges",
        )


def _charge_read(charge: Charge) -> ChargeRead:
    return ChargeRead(
        id=charge.id,
        shipment_id=charge.shipment_id,
        shipment_code=charge.shipment.shipment_code if charge.shipment else None,
        charge_type=charge.charge_type,
        direction=charge.direction,
        amount=charge.amount,
        currency=charge.currency,
        party_id=charge.party_id,
        party_name=charge.party.name if charge.party else None,
        status=charge.status,
        invoice_no=charge.invoice_no,
        date=charge.date,
        notes=charge.notes,
        created_at=charge.created_at,
        updated_at=charge.updated_at,
    )


@router.get("/shipments/{shipment_id}/charges", response_model=list[ChargeRead])
def list_charges_for_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[ChargeRead]:
    _get_shipment(db, shipment_id)
    charges = (
        db.query(Charge)
        .options(joinedload(Charge.shipment), joinedload(Charge.party))
        .filter(Charge.shipment_id == shipment_id)
        .order_by(Charge.date.desc().nullslast(), Charge.created_at.desc(), Charge.id.desc())
        .all()
    )
    return [_charge_read(charge) for charge in charges]


@router.post("/shipments/{shipment_id}/charges", response_model=ChargeRead, status_code=status.HTTP_201_CREATED)
def create_charge(
    shipment_id: int,
    charge_in: ChargeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> ChargeRead:
    _get_shipment(db, shipment_id)
    if charge_in.shipment_id is not None and charge_in.shipment_id != shipment_id:
        raise HTTPException(status_code=400, detail="Shipment ID does not match path")
    _validate_party(db, charge_in.party_id)
    _validate_direction_status(charge_in.direction, charge_in.status)
    data = charge_in.model_dump(exclude={"shipment_id"})
    data["currency"] = data["currency"].upper()
    charge = Charge(**data, shipment_id=shipment_id)
    db.add(charge)
    db.commit()
    db.refresh(charge)
    invalidate_dashboard_cache()
    charge = _get_charge(db, charge.id)
    record_audit_log(
        db,
        current_user,
        "charge.created",
        "charge",
        entity_id=charge.id,
        entity_label=charge.invoice_no or f"Charge #{charge.id}",
        description="Charge created.",
        metadata={
            "shipment_id": charge.shipment_id,
            "direction": charge.direction,
            "status": charge.status,
            "amount": charge.amount,
            "currency": charge.currency,
        },
        request=request,
    )
    return _charge_read(charge)


@router.patch("/charges/{charge_id}", response_model=ChargeRead)
def update_charge(
    charge_id: int,
    charge_in: ChargeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> ChargeRead:
    charge = _get_charge(db, charge_id)
    data = charge_in.model_dump(exclude_unset=True)
    _validate_party(db, data.get("party_id"))
    direction = data.get("direction", charge.direction)
    status_value = data.get("status", charge.status)
    _validate_direction_status(direction, status_value)
    before = {field: getattr(charge, field, None) for field in data}
    previous_status = charge.status
    for field, value in data.items():
        setattr(charge, field, value)
    db.commit()
    db.refresh(charge)
    invalidate_dashboard_cache()
    charge = _get_charge(db, charge.id)
    action = "charge.updated"
    if previous_status != charge.status and charge.status == "paid":
        action = "charge.marked_paid"
    elif previous_status != charge.status and charge.status == "received":
        action = "charge.marked_received"
    record_audit_log(
        db,
        current_user,
        action,
        "charge",
        entity_id=charge.id,
        entity_label=charge.invoice_no or f"Charge #{charge.id}",
        description="Charge updated.",
        metadata={
            "shipment_id": charge.shipment_id,
            "fields_changed": changed_fields(before, {field: getattr(charge, field, None) for field in data}),
            "previous_status": previous_status,
            "status": charge.status,
        },
        request=request,
    )
    return _charge_read(charge)


@router.delete("/charges/{charge_id}", response_model=ChargeRead)
def cancel_charge(
    charge_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> ChargeRead:
    charge = _get_charge(db, charge_id)
    charge.status = "cancelled"
    db.commit()
    db.refresh(charge)
    invalidate_dashboard_cache()
    charge = _get_charge(db, charge.id)
    record_audit_log(
        db,
        current_user,
        "charge.cancelled",
        "charge",
        entity_id=charge.id,
        entity_label=charge.invoice_no or f"Charge #{charge.id}",
        description="Charge cancelled.",
        metadata={"shipment_id": charge.shipment_id, "status": charge.status},
        request=request,
    )
    return _charge_read(charge)


@router.get("/shipments/{shipment_id}/pnl", response_model=ShipmentPLSummary)
def get_shipment_pnl(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> ShipmentPLSummary:
    summary = calculate_shipment_pnl(db, shipment_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return summary
