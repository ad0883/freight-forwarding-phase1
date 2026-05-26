from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_roles, require_write_access
from app.models.charge import Charge
from app.models.followup import FollowUpLog
from app.models.party import Party
from app.models.shipment import Shipment
from app.schemas.party import PartyCreate, PartyDeactivationRequest, PartyRead, PartyUpdate
from app.services.audit_service import changed_fields, record_audit_log
from app.services.event_service import OperationalEventType, diff_state, record_operational_event


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
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> Party:
    party = Party(**party_in.model_dump())
    db.add(party)
    db.commit()
    db.refresh(party)
    record_audit_log(
        db,
        current_user,
        "party.created",
        "party",
        entity_id=party.id,
        entity_label=party.name,
        description="Party created.",
        metadata={"type": party.type, "is_active": party.is_active},
        request=request,
    )
    record_operational_event(
        db,
        OperationalEventType.PARTY_CREATED.value,
        "party",
        entity_id=party.id,
        entity_label=party.name,
        actor_user=current_user,
        source="user",
        new_state={"name": party.name, "type": party.type, "is_active": party.is_active},
        request=request,
    )
    return party


@router.patch("/{party_id}/deactivate", response_model=PartyRead)
def deactivate_party(
    party_id: int,
    deactivate_in: PartyDeactivationRequest,
    request: Request,
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
    record_audit_log(
        db,
        current_user,
        "party.deactivated",
        "party",
        entity_id=party.id,
        entity_label=party.name,
        description="Party deactivated.",
        metadata={"reason_present": bool(deactivate_in.reason)},
        request=request,
    )
    record_operational_event(
        db,
        OperationalEventType.PARTY_DEACTIVATED.value,
        "party",
        entity_id=party.id,
        entity_label=party.name,
        actor_user=current_user,
        source="user",
        new_state={"is_active": False},
        metadata={"reason_present": bool(deactivate_in.reason)},
        request=request,
    )
    return party


@router.patch("/{party_id}/reactivate", response_model=PartyRead)
def reactivate_party(
    party_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
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
    record_audit_log(
        db,
        current_user,
        "party.reactivated",
        "party",
        entity_id=party.id,
        entity_label=party.name,
        description="Party reactivated.",
        metadata={"is_active": party.is_active},
        request=request,
    )
    record_operational_event(
        db,
        OperationalEventType.PARTY_REACTIVATED.value,
        "party",
        entity_id=party.id,
        entity_label=party.name,
        actor_user=current_user,
        source="user",
        new_state={"is_active": True},
        request=request,
    )
    return party


@router.delete("/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_party(
    party_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
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
    entity_label = party.name
    db.delete(party)
    db.commit()
    record_audit_log(
        db,
        current_user,
        "party.deleted",
        "party",
        entity_id=party_id,
        entity_label=entity_label,
        description="Party deleted.",
        metadata={"deleted": True},
        request=request,
    )
    record_operational_event(
        db,
        OperationalEventType.PARTY_DELETED.value,
        "party",
        entity_id=party_id,
        entity_label=entity_label,
        actor_user=current_user,
        source="user",
        metadata={"deleted": True},
        request=request,
    )


@router.patch("/{party_id}", response_model=PartyRead)
def update_party(
    party_id: int,
    party_in: PartyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> Party:
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    data = party_in.model_dump(exclude_unset=True)
    before = {field: getattr(party, field, None) for field in data}
    for field, value in data.items():
        setattr(party, field, value)
    db.commit()
    db.refresh(party)
    record_audit_log(
        db,
        current_user,
        "party.updated",
        "party",
        entity_id=party.id,
        entity_label=party.name,
        description="Party updated.",
        metadata={"fields_changed": changed_fields(before, {field: getattr(party, field, None) for field in data})},
        request=request,
    )
    after_state = {field: getattr(party, field, None) for field in data}
    record_operational_event(
        db,
        OperationalEventType.PARTY_UPDATED.value,
        "party",
        entity_id=party.id,
        entity_label=party.name,
        actor_user=current_user,
        source="user",
        previous_state=before,
        new_state=after_state,
        metadata={"fields_changed": diff_state(before, after_state)},
        request=request,
    )
    return party
