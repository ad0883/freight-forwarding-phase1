from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_roles, require_write_access
from app.models.charge import Charge
from app.models.followup import FollowUpLog
from app.models.party import Party
from app.models.shipment import Shipment
from app.schemas.party import PartyCreate, PartyDeactivationRequest, PartyRead, PartyUpdate


router = APIRouter(prefix="/parties", tags=["parties"])


@router.get("", response_model=list[PartyRead])
def list_parties(
    include_inactive: bool = False,
    inactive_only: bool = False,
    db: Session = Depends(get_db), _: AuthenticatedUser = Depends(get_current_user)
) -> list[Party]:
    query = db.query(Party)
    if inactive_only:
        query = query.filter(Party.is_active.is_(False))
    elif not include_inactive:
        query = query.filter(Party.is_active.is_(True))
    return query.order_by(Party.name.asc()).all()


@router.post("", response_model=PartyRead, status_code=status.HTTP_201_CREATED)
def create_party(
    party_in: PartyCreate,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_write_access),
) -> Party:
    party = Party(**party_in.model_dump())
    db.add(party)
    db.commit()
    db.refresh(party)
    return party


@router.patch("/{party_id}/deactivate", response_model=PartyRead)
def deactivate_party(
    party_id: int,
    deactivate_in: PartyDeactivationRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> Party:
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    party.is_active = False
    party.deactivated_at = datetime.utcnow()
    party.deactivated_by = current_user.id
    party.deactivation_reason = deactivate_in.reason
    db.commit()
    db.refresh(party)
    return party


@router.patch("/{party_id}/reactivate", response_model=PartyRead)
def reactivate_party(
    party_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> Party:
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    party.is_active = True
    party.deactivated_at = None
    party.deactivated_by = None
    party.deactivation_reason = None
    db.commit()
    db.refresh(party)
    return party


@router.delete("/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_party(
    party_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> None:
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    is_used = any(
        [
            db.query(Shipment.id)
            .filter((Shipment.exporter_id == party_id) | (Shipment.importer_id == party_id))
            .first(),
            db.query(Charge.id).filter(Charge.party_id == party_id).first(),
            db.query(FollowUpLog.id).filter(FollowUpLog.party_id == party_id).first(),
        ]
    )
    if is_used:
        raise HTTPException(
            status_code=400,
            detail="Party is used in existing records. Deactivate it instead.",
        )
    db.delete(party)
    db.commit()


@router.patch("/{party_id}", response_model=PartyRead)
def update_party(
    party_id: int,
    party_in: PartyUpdate,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_write_access),
) -> Party:
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    for field, value in party_in.model_dump(exclude_unset=True).items():
        setattr(party, field, value)
    db.commit()
    db.refresh(party)
    return party
