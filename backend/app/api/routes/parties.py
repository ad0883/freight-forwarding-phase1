from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_write_access
from app.models.party import Party
from app.models.user import User
from app.schemas.party import PartyCreate, PartyRead, PartyUpdate


router = APIRouter(prefix="/parties", tags=["parties"])


@router.get("", response_model=list[PartyRead])
def list_parties(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[Party]:
    return db.query(Party).order_by(Party.name.asc()).all()


@router.post("", response_model=PartyRead, status_code=status.HTTP_201_CREATED)
def create_party(
    party_in: PartyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_write_access),
) -> Party:
    party = Party(**party_in.model_dump())
    db.add(party)
    db.commit()
    db.refresh(party)
    return party


@router.patch("/{party_id}", response_model=PartyRead)
def update_party(
    party_id: int,
    party_in: PartyUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_write_access),
) -> Party:
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    for field, value in party_in.model_dump(exclude_unset=True).items():
        setattr(party, field, value)
    db.commit()
    db.refresh(party)
    return party
