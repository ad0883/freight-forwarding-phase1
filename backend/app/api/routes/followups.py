from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_write_access
from app.models.followup import FollowUpLog
from app.models.party import Party
from app.models.shipment import Shipment
from app.schemas.followup import FollowUpCreate, FollowUpRead, FollowUpUpdate


router = APIRouter(tags=["follow-ups"])


def _get_shipment(db: Session, shipment_id: int) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


def _validate_party(db: Session, party_id: Optional[int]) -> None:
    if party_id is None:
        return
    exists = db.query(Party.id).filter(Party.id == party_id, Party.is_active.is_(True)).first()
    if not exists:
        raise HTTPException(status_code=400, detail="Party does not exist or is inactive")


@router.get("/shipments/{shipment_id}/followups", response_model=list[FollowUpRead])
def list_followups(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[FollowUpLog]:
    _get_shipment(db, shipment_id)
    return (
        db.query(FollowUpLog)
        .options(joinedload(FollowUpLog.party), joinedload(FollowUpLog.logger))
        .filter(FollowUpLog.shipment_id == shipment_id)
        .order_by(FollowUpLog.date.desc(), FollowUpLog.id.desc())
        .all()
    )


@router.post("/shipments/{shipment_id}/followups", response_model=FollowUpRead, status_code=status.HTTP_201_CREATED)
def create_followup(
    shipment_id: int,
    followup_in: FollowUpCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> FollowUpLog:
    _get_shipment(db, shipment_id)
    _validate_party(db, followup_in.party_id)
    followup = FollowUpLog(
        **followup_in.model_dump(),
        shipment_id=shipment_id,
        logged_by=current_user.id,
    )
    db.add(followup)
    db.commit()
    db.refresh(followup)
    return followup


@router.patch("/followups/{followup_id}", response_model=FollowUpRead)
def update_followup(
    followup_id: int,
    followup_in: FollowUpUpdate,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_write_access),
) -> FollowUpLog:
    followup = db.query(FollowUpLog).filter(FollowUpLog.id == followup_id).first()
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    data = followup_in.model_dump(exclude_unset=True)
    _validate_party(db, data.get("party_id"))
    for field, value in data.items():
        setattr(followup, field, value)
    db.commit()
    db.refresh(followup)
    return followup


@router.delete("/followups/{followup_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_followup(
    followup_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_write_access),
) -> None:
    followup = db.query(FollowUpLog).filter(FollowUpLog.id == followup_id).first()
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    db.delete(followup)
    db.commit()
