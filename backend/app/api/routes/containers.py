"""Phase 11 container API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_roles, require_write_access
from app.models.container import Container, ContainerEvent
from app.models.shipment import Shipment
from app.schemas.container import (
    ContainerBackfillCandidate,
    ContainerBackfillRequest,
    ContainerBackfillResponse,
    ContainerCreate,
    ContainerEventCreate,
    ContainerEventRead,
    ContainerExposureRead,
    ContainerRead,
    ContainerRiskRow,
    ContainerTransitionRequest,
    ContainerUpdate,
    ShipmentExposureSummary,
)
from app.services.container_backfill_service import backfill_containers_from_shipments
from app.services.container_service import (
    ALL_STATUSES,
    create_container,
    delete_container,
    get_container,
    get_shipment,
    list_containers,
    record_container_event,
    transition_container_status,
    update_container,
)
from app.services.demurrage_detention_service import (
    list_recent_container_risk,
    refresh_container_exposure,
    refresh_shipment_container_exposure,
)


container_router = APIRouter(prefix="/containers", tags=["containers"])
shipment_container_router = APIRouter(prefix="/shipments", tags=["containers"])

AdminUser = Depends(require_roles("ADMIN"))


def _container_to_read(container: Container, *, exposure: Optional[dict] = None) -> ContainerRead:
    base = ContainerRead.model_validate(container)
    base.shipment_code = container.shipment.shipment_code if container.shipment else None
    if exposure is not None:
        base.exposure = ContainerExposureRead(**exposure)
    return base


def _exposure_dict(snapshot) -> dict:
    return {
        "container_id": snapshot.container_id,
        "shipment_id": snapshot.shipment_id,
        "currency": snapshot.currency,
        "demurrage_days_used": snapshot.demurrage_days_used,
        "demurrage_chargeable_days": snapshot.demurrage_chargeable_days,
        "demurrage_estimated_amount": snapshot.demurrage_estimated_amount,
        "demurrage_status": snapshot.demurrage_status,
        "demurrage_start_date": snapshot.demurrage_start_date,
        "demurrage_end_date": snapshot.demurrage_end_date,
        "detention_days_used": snapshot.detention_days_used,
        "detention_chargeable_days": snapshot.detention_chargeable_days,
        "detention_estimated_amount": snapshot.detention_estimated_amount,
        "detention_status": snapshot.detention_status,
        "detention_start_date": snapshot.detention_start_date,
        "detention_end_date": snapshot.detention_end_date,
        "risk_level": snapshot.risk_level,
    }


# ---------------------------------------------------------------------------
# Container endpoints
# ---------------------------------------------------------------------------


@container_router.get("", response_model=list[ContainerRead])
def list_containers_route(
    shipment_id: Optional[int] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[ContainerRead]:
    rows = list_containers(db, shipment_id=shipment_id, include_inactive=include_inactive)
    return [_container_to_read(container) for container in rows]


@container_router.post("/backfill-from-shipments", response_model=ContainerBackfillResponse)
def backfill_route(
    payload: ContainerBackfillRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AdminUser,
) -> ContainerBackfillResponse:
    summary = backfill_containers_from_shipments(
        db,
        dry_run=payload.dry_run,
        user=current_user,
        request=request,
    )
    return ContainerBackfillResponse(
        dry_run=summary["dry_run"],
        candidates=[ContainerBackfillCandidate(**candidate) for candidate in summary["candidates"]],
        created_count=summary["created_count"],
    )


@container_router.get("/risk", response_model=list[ContainerRiskRow])
def list_risk_route(
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[ContainerRiskRow]:
    rows = list_recent_container_risk(db, limit=limit)
    return [ContainerRiskRow(**row) for row in rows]


@container_router.get("/statuses", response_model=list[str])
def list_statuses_route(_: AuthenticatedUser = Depends(get_current_user)) -> list[str]:
    return ALL_STATUSES


@container_router.get("/{container_id}", response_model=ContainerRead)
def get_container_route(
    container_id: int,
    include_exposure: bool = True,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> ContainerRead:
    container = get_container(db, container_id)
    exposure = None
    if include_exposure:
        snapshot = refresh_container_exposure(db, container)
        exposure = _exposure_dict(snapshot)
    return _container_to_read(container, exposure=exposure)


@container_router.patch("/{container_id}", response_model=ContainerRead)
def update_container_route(
    container_id: int,
    payload: ContainerUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> ContainerRead:
    container = get_container(db, container_id)
    update_container(
        db,
        container,
        payload.model_dump(exclude_unset=True),
        current_user,
        request=request,
    )
    return _container_to_read(container)


@container_router.delete("/{container_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_container_route(
    container_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AdminUser,
) -> None:
    container = get_container(db, container_id)
    delete_container(db, container, current_user, request=request)


@container_router.get("/{container_id}/events", response_model=list[ContainerEventRead])
def list_container_events_route(
    container_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[ContainerEventRead]:
    container = get_container(db, container_id)
    events = (
        db.query(ContainerEvent)
        .filter(ContainerEvent.container_id == container.id)
        .order_by(ContainerEvent.event_date.asc().nullslast(), ContainerEvent.id.asc())
        .all()
    )
    return [ContainerEventRead.model_validate(event) for event in events]


@container_router.post("/{container_id}/events", response_model=ContainerEventRead)
def create_container_event_route(
    container_id: int,
    payload: ContainerEventCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> ContainerEventRead:
    container = get_container(db, container_id)
    event = record_container_event(
        db,
        container,
        event_type=payload.event_type,
        event_date=payload.event_date,
        user=current_user,
        source=payload.source,
        description=payload.description,
        location=payload.location,
        metadata=payload.metadata_json,
        request=request,
    )
    return ContainerEventRead.model_validate(event)


@container_router.post("/{container_id}/transition", response_model=ContainerRead)
def transition_container_route(
    container_id: int,
    payload: ContainerTransitionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> ContainerRead:
    container = get_container(db, container_id)
    transition_container_status(
        db,
        container,
        payload.new_status,
        current_user,
        reason=payload.reason,
        event_date=payload.event_date,
        request=request,
    )
    return _container_to_read(container)


@container_router.get("/{container_id}/exposure", response_model=ContainerExposureRead)
def container_exposure_route(
    container_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> ContainerExposureRead:
    container = get_container(db, container_id)
    snapshot = refresh_container_exposure(db, container)
    return ContainerExposureRead(**_exposure_dict(snapshot))


@container_router.post("/{container_id}/refresh-exposure", response_model=ContainerExposureRead)
def container_refresh_exposure_route(
    container_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> ContainerExposureRead:
    container = get_container(db, container_id)
    snapshot = refresh_container_exposure(db, container, user=current_user, request=request)
    return ContainerExposureRead(**_exposure_dict(snapshot))


# ---------------------------------------------------------------------------
# Shipment-scoped routes
# ---------------------------------------------------------------------------


@shipment_container_router.get(
    "/{shipment_id}/containers", response_model=list[ContainerRead]
)
def list_shipment_containers_route(
    shipment_id: int,
    include_inactive: bool = False,
    include_exposure: bool = True,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[ContainerRead]:
    get_shipment(db, shipment_id)
    rows = list_containers(db, shipment_id=shipment_id, include_inactive=include_inactive)
    out: list[ContainerRead] = []
    for container in rows:
        exposure = None
        if include_exposure:
            snapshot = refresh_container_exposure(db, container)
            exposure = _exposure_dict(snapshot)
        out.append(_container_to_read(container, exposure=exposure))
    return out


@shipment_container_router.post(
    "/{shipment_id}/containers", response_model=ContainerRead, status_code=status.HTTP_201_CREATED
)
def create_shipment_container_route(
    shipment_id: int,
    payload: ContainerCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> ContainerRead:
    shipment = get_shipment(db, shipment_id)
    container = create_container(
        db,
        shipment,
        payload.model_dump(exclude_unset=True),
        current_user,
        request=request,
    )
    snapshot = refresh_container_exposure(db, container, user=current_user, request=request)
    return _container_to_read(container, exposure=_exposure_dict(snapshot))


@shipment_container_router.get(
    "/{shipment_id}/container-exposure", response_model=ShipmentExposureSummary
)
def shipment_container_exposure_route(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> ShipmentExposureSummary:
    snapshots = refresh_shipment_container_exposure(db, shipment_id)
    summary = _summarize_shipment(shipment_id, snapshots)
    return summary


@shipment_container_router.post(
    "/{shipment_id}/refresh-container-exposure", response_model=ShipmentExposureSummary
)
def shipment_refresh_container_exposure_route(
    shipment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> ShipmentExposureSummary:
    snapshots = refresh_shipment_container_exposure(db, shipment_id, user=current_user, request=request)
    return _summarize_shipment(shipment_id, snapshots)


def _summarize_shipment(
    shipment_id: int, snapshots: list
) -> ShipmentExposureSummary:
    container_count = len(snapshots)
    currency = snapshots[0].currency if snapshots else "INR"
    demurrage_total = sum((s.demurrage_estimated_amount for s in snapshots), 0)
    detention_total = sum((s.detention_estimated_amount for s in snapshots), 0)
    demurrage_running = sum(1 for s in snapshots if s.demurrage_status == "running")
    detention_running = sum(1 for s in snapshots if s.detention_status == "running")
    overdue = sum(1 for s in snapshots if s.risk_level == "critical")
    if any(s.risk_level == "critical" for s in snapshots):
        risk = "critical"
    elif any(s.risk_level == "running" for s in snapshots):
        risk = "running"
    elif any(s.risk_level == "warning" for s in snapshots):
        risk = "warning"
    elif any(s.risk_level == "info" for s in snapshots):
        risk = "info"
    else:
        risk = "none"
    exposures = [ContainerExposureRead(**_exposure_dict(s)) for s in snapshots]
    return ShipmentExposureSummary(
        shipment_id=shipment_id,
        container_count=container_count,
        currency=currency,
        demurrage_estimated_amount=demurrage_total,
        detention_estimated_amount=detention_total,
        demurrage_running=demurrage_running,
        detention_running=detention_running,
        empty_return_overdue=overdue,
        risk_level=risk,
        containers=exposures,
    )
