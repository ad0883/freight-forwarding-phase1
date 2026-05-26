from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.schemas.event import OperationalEventRead
from app.services.event_service import get_operational_event, list_operational_events


router = APIRouter(prefix="/events", tags=["events"])

OperationalUser = Depends(require_roles("ADMIN", "STAFF"))


@router.get("", response_model=list[OperationalEventRead])
def list_events(
    event_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    source: Optional[str] = None,
    validation_status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = OperationalUser,
) -> list[OperationalEventRead]:
    events = list_operational_events(
        db,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        shipment_id=shipment_id,
        source=source,
        validation_status=validation_status,
        date_from=datetime.combine(date_from, time.min) if date_from else None,
        date_to=datetime.combine(date_to, time.max) if date_to else None,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [OperationalEventRead.model_validate(event) for event in events]


@router.get("/{event_id}", response_model=OperationalEventRead)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = OperationalUser,
) -> OperationalEventRead:
    event = get_operational_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Operational event not found")
    return OperationalEventRead.model_validate(event)
