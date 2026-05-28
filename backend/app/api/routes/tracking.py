"""Phase 21 Tracking Adapters API routes."""
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.models.tracking import (
    TrackingEvent,
    TrackingMismatch,
    TrackingObservation,
    TrackingProvider,
    TrackingSuggestedUpdate,
    TrackingSyncRun,
    TrackingWatchItem,
)
from app.services.audit_service import record_audit_log
from app.services.tracking.tracking_provider_service import (
    create_adapter_config,
    create_tracking_provider,
    list_tracking_providers,
    update_tracking_provider,
)
from app.services.tracking.tracking_watch_service import (
    complete_watch_item,
    create_watch_item,
    list_watch_items,
    pause_watch_item,
    resume_watch_item,
)
from app.services.tracking.tracking_observation_service import (
    create_manual_observation,
    list_observations,
    list_tracking_events,
)
from app.services.tracking.tracking_suggestion_service import (
    approve_suggestion,
    create_mismatch,
    dismiss_suggestion,
    list_mismatches,
    list_suggestions,
    reject_suggestion,
    resolve_mismatch,
)
from app.services.tracking.tracking_sync_service import (
    build_customer_safe_tracking_summary,
    get_tracking_summary,
    list_sync_runs,
    run_tracking_sync,
)

router = APIRouter(prefix="/tracking", tags=["tracking"])
shipment_tracking_router = APIRouter(prefix="/shipments", tags=["shipment-tracking"])
portal_tracking_router = APIRouter(prefix="/portal/shipments", tags=["portal-tracking"])

AnyUser = Depends(require_roles("ADMIN", "STAFF", "VIEW_ONLY"))
OperationalUser = Depends(require_roles("ADMIN", "STAFF"))
AdminUser = Depends(require_roles("ADMIN"))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ProviderRead(BaseModel):
    id: int
    provider_key: str
    name: str
    provider_type: str
    status: str
    supports_container_tracking: bool
    supports_vessel_tracking: bool
    supports_transport_tracking: bool
    supports_terminal_tracking: bool
    requires_credentials: bool
    is_manual: bool
    is_mock: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProviderCreate(BaseModel):
    provider_key: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=150)
    provider_type: str = "other"
    status: str = "active"
    base_url: Optional[str] = None
    supports_container_tracking: bool = False
    supports_vessel_tracking: bool = False
    supports_transport_tracking: bool = False
    supports_terminal_tracking: bool = False
    requires_credentials: bool = False
    is_manual: bool = False
    is_mock: bool = False


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    base_url: Optional[str] = None
    supports_container_tracking: Optional[bool] = None
    supports_vessel_tracking: Optional[bool] = None
    supports_transport_tracking: Optional[bool] = None
    supports_terminal_tracking: Optional[bool] = None


class AdapterConfigCreate(BaseModel):
    config_name: str = "default"
    auth_type: str = "none"
    safe_config_json: Optional[dict] = None
    secret_ref: Optional[str] = None


class WatchItemRead(BaseModel):
    id: int
    tracking_provider_id: Optional[int] = None
    shipment_id: Optional[int] = None
    container_id: Optional[int] = None
    transport_job_id: Optional[int] = None
    watch_type: str
    tracking_identifier: str
    secondary_identifier: Optional[str] = None
    status: str
    last_sync_at: Optional[datetime] = None
    last_observation_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WatchItemCreate(BaseModel):
    tracking_provider_id: Optional[int] = None
    shipment_id: Optional[int] = None
    container_id: Optional[int] = None
    transport_job_id: Optional[int] = None
    customs_case_id: Optional[int] = None
    watch_type: str = "container"
    tracking_identifier: str = Field(min_length=1, max_length=120)
    secondary_identifier: Optional[str] = None


class ObservationRead(BaseModel):
    id: int
    tracking_watch_item_id: Optional[int] = None
    tracking_provider_id: Optional[int] = None
    shipment_id: Optional[int] = None
    container_id: Optional[int] = None
    observation_type: str
    source: str
    raw_status: Optional[str] = None
    normalized_status: str
    status_time: Optional[datetime] = None
    location_text: Optional[str] = None
    eta: Optional[datetime] = None
    etd: Optional[datetime] = None
    vessel_name: Optional[str] = None
    voyage_no: Optional[str] = None
    confidence: float
    is_customer_visible: bool
    observed_at: datetime
    received_at: datetime

    class Config:
        from_attributes = True


class ManualObservationCreate(BaseModel):
    tracking_watch_item_id: Optional[int] = None
    tracking_provider_id: Optional[int] = None
    shipment_id: Optional[int] = None
    container_id: Optional[int] = None
    transport_job_id: Optional[int] = None
    observation_type: str = "container_status"
    raw_status: str = Field(min_length=1, max_length=255)
    status_time: Optional[datetime] = None
    location_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    eta: Optional[datetime] = None
    etd: Optional[datetime] = None
    vessel_name: Optional[str] = None
    voyage_no: Optional[str] = None
    confidence: float = 0.8
    is_customer_visible: bool = False


class EventRead(BaseModel):
    id: int
    tracking_observation_id: Optional[int] = None
    shipment_id: Optional[int] = None
    container_id: Optional[int] = None
    event_key: str
    event_label: str
    event_time: Optional[datetime] = None
    location_text: Optional[str] = None
    confidence: float
    match_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SuggestionRead(BaseModel):
    id: int
    tracking_observation_id: Optional[int] = None
    shipment_id: Optional[int] = None
    container_id: Optional[int] = None
    suggestion_type: str
    target_entity_type: str
    target_field: str
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None
    confidence: float
    risk_level: str
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class MismatchRead(BaseModel):
    id: int
    tracking_observation_id: Optional[int] = None
    shipment_id: Optional[int] = None
    container_id: Optional[int] = None
    mismatch_type: str
    severity: str
    title: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class SyncRunRead(BaseModel):
    id: int
    tracking_provider_id: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    scope: str
    watch_items_processed: int
    observations_created: int
    suggestions_created: int
    mismatches_created: int
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@router.get("/summary")
def tracking_summary(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return get_tracking_summary(db)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

@router.get("/providers", response_model=list[ProviderRead])
def list_providers(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
):
    return [ProviderRead.model_validate(p) for p in list_tracking_providers(db, status_filter=status)]


@router.post("/providers", response_model=ProviderRead, status_code=201)
def create_provider(
    body: ProviderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AdminUser,
):
    p = create_tracking_provider(db, body.model_dump(), current_user)
    record_audit_log(db, current_user, "tracking.provider_create", "tracking_provider", entity_id=p.id, entity_label=p.provider_key, description=f"Provider created: {p.name}", request=request)
    return ProviderRead.model_validate(p)


@router.patch("/providers/{provider_id}", response_model=ProviderRead)
def update_provider(
    provider_id: int,
    body: ProviderUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AdminUser,
):
    try:
        p = update_tracking_provider(db, provider_id, body.model_dump(exclude_unset=True), current_user)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return ProviderRead.model_validate(p)


@router.post("/providers/{provider_id}/configs", status_code=201)
def create_config(
    provider_id: int,
    body: AdapterConfigCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AdminUser,
):
    config = create_adapter_config(db, provider_id, body.model_dump(), current_user)
    return {"id": config.id, "status": "created"}


# ---------------------------------------------------------------------------
# Watch Items
# ---------------------------------------------------------------------------

@router.get("/watch-items", response_model=list[WatchItemRead])
def list_watches(
    shipment_id: Optional[int] = None,
    status: Optional[str] = None,
    watch_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
):
    return [WatchItemRead.model_validate(w) for w in list_watch_items(db, shipment_id=shipment_id, status_filter=status, watch_type=watch_type, limit=limit, offset=offset)]


@router.post("/watch-items", response_model=WatchItemRead, status_code=201)
def create_watch(
    body: WatchItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    w = create_watch_item(db, body.model_dump(), current_user)
    record_audit_log(db, current_user, "tracking.watch_create", "tracking_watch_item", entity_id=w.id, entity_label=w.tracking_identifier, description=f"Watch item created: {w.tracking_identifier}", request=request)
    return WatchItemRead.model_validate(w)


@router.post("/watch-items/{watch_item_id}/pause", response_model=WatchItemRead)
def pause_watch(watch_item_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try:
        w = pause_watch_item(db, watch_item_id, current_user)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return WatchItemRead.model_validate(w)


@router.post("/watch-items/{watch_item_id}/resume", response_model=WatchItemRead)
def resume_watch(watch_item_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try:
        w = resume_watch_item(db, watch_item_id, current_user)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return WatchItemRead.model_validate(w)


@router.post("/watch-items/{watch_item_id}/complete", response_model=WatchItemRead)
def complete_watch(watch_item_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try:
        w = complete_watch_item(db, watch_item_id, current_user)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return WatchItemRead.model_validate(w)


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------

@router.get("/observations", response_model=list[ObservationRead])
def list_obs(
    shipment_id: Optional[int] = None,
    watch_item_id: Optional[int] = None,
    observation_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
):
    return [ObservationRead.model_validate(o) for o in list_observations(db, shipment_id=shipment_id, watch_item_id=watch_item_id, observation_type=observation_type, limit=limit, offset=offset)]


@router.post("/observations/manual", response_model=ObservationRead, status_code=201)
def create_manual_obs(
    body: ManualObservationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    obs = create_manual_observation(db, body.model_dump(), current_user)
    return ObservationRead.model_validate(obs)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@router.get("/events", response_model=list[EventRead])
def list_events(
    shipment_id: Optional[int] = None,
    container_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
):
    return [EventRead.model_validate(e) for e in list_tracking_events(db, shipment_id=shipment_id, container_id=container_id, limit=limit, offset=offset)]


# ---------------------------------------------------------------------------
# Mismatches
# ---------------------------------------------------------------------------

@router.get("/mismatches", response_model=list[MismatchRead])
def list_mm(
    status: Optional[str] = None,
    shipment_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
):
    return [MismatchRead.model_validate(m) for m in list_mismatches(db, status_filter=status, shipment_id=shipment_id, limit=limit, offset=offset)]


@router.post("/mismatches/{mismatch_id}/resolve", response_model=MismatchRead)
def resolve_mm(
    mismatch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        mm = resolve_mismatch(db, mismatch_id, current_user)
    except ValueError as e:
        raise HTTPException(404, str(e))
    record_audit_log(db, current_user, "tracking.mismatch_resolve", "tracking_mismatch", entity_id=mm.id, description="Tracking mismatch resolved", request=request)
    return MismatchRead.model_validate(mm)


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------

@router.get("/suggestions", response_model=list[SuggestionRead])
def list_sugg(
    status: Optional[str] = None,
    shipment_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
):
    return [SuggestionRead.model_validate(s) for s in list_suggestions(db, status_filter=status, shipment_id=shipment_id, limit=limit, offset=offset)]


@router.post("/suggestions/{suggestion_id}/approve", response_model=SuggestionRead)
def approve_sugg(
    suggestion_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        s = approve_suggestion(db, suggestion_id, current_user)
    except ValueError as e:
        raise HTTPException(404, str(e))
    record_audit_log(db, current_user, "tracking.suggestion_approve", "tracking_suggestion", entity_id=s.id, description="Tracking suggestion approved", request=request)
    return SuggestionRead.model_validate(s)


@router.post("/suggestions/{suggestion_id}/reject", response_model=SuggestionRead)
def reject_sugg(
    suggestion_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        s = reject_suggestion(db, suggestion_id, current_user, reason)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return SuggestionRead.model_validate(s)


@router.post("/suggestions/{suggestion_id}/dismiss", response_model=SuggestionRead)
def dismiss_sugg(
    suggestion_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        s = dismiss_suggestion(db, suggestion_id, current_user, reason)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return SuggestionRead.model_validate(s)


# ---------------------------------------------------------------------------
# Sync Runs
# ---------------------------------------------------------------------------

@router.get("/sync-runs", response_model=list[SyncRunRead])
def list_syncs(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
):
    return [SyncRunRead.model_validate(r) for r in list_sync_runs(db, status_filter=status, limit=limit)]


@router.post("/run-sync", response_model=SyncRunRead, status_code=201)
def run_sync(
    provider_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    sync = run_tracking_sync(db, scope="manual", user=current_user, provider_id=provider_id, shipment_id=shipment_id)
    record_audit_log(db, current_user, "tracking.sync_run", "tracking_sync_run", entity_id=sync.id, description=f"Tracking sync: {sync.status}, {sync.observations_created} observations", request=request)
    return SyncRunRead.model_validate(sync)


@router.post("/watch-items/{watch_item_id}/run-sync", response_model=SyncRunRead, status_code=201)
def run_watch_sync(
    watch_item_id: int,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    sync = run_tracking_sync(db, scope="single_watch_item", user=current_user, watch_item_id=watch_item_id)
    return SyncRunRead.model_validate(sync)


# ---------------------------------------------------------------------------
# Shipment-specific
# ---------------------------------------------------------------------------

@shipment_tracking_router.get("/{shipment_id}/tracking", response_model=list[ObservationRead])
def shipment_tracking(shipment_id: int, limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [ObservationRead.model_validate(o) for o in list_observations(db, shipment_id=shipment_id, limit=limit)]


@shipment_tracking_router.post("/{shipment_id}/tracking/watch-items", response_model=WatchItemRead, status_code=201)
def shipment_create_watch(
    shipment_id: int,
    body: WatchItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    data = body.model_dump()
    data["shipment_id"] = shipment_id
    w = create_watch_item(db, data, current_user)
    return WatchItemRead.model_validate(w)


@shipment_tracking_router.post("/{shipment_id}/tracking/run-sync", response_model=SyncRunRead, status_code=201)
def shipment_run_sync(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    sync = run_tracking_sync(db, scope="shipment", user=current_user, shipment_id=shipment_id)
    return SyncRunRead.model_validate(sync)


# ---------------------------------------------------------------------------
# Portal-safe
# ---------------------------------------------------------------------------

@portal_tracking_router.get("/{shipment_id}/tracking")
def portal_tracking(shipment_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    """Customer-safe tracking summary. Hides provider/internal details."""
    return build_customer_safe_tracking_summary(db, shipment_id)
