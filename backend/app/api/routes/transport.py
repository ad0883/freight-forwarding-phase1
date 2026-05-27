"""Phase 20 Transport + GPS layer API routes."""
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.models.transport import (
    TransportDocument,
    TransportDriver,
    TransportException,
    TransportJob,
    TransportJobContainer,
    TransportLocationUpdate,
    TransportMilestone,
    TransportVehicle,
)
from app.services.audit_service import record_audit_log
from app.services.transport_service import (
    add_location_update,
    assign_transporter,
    assign_vehicle_driver,
    build_customer_safe_transport_summary,
    close_transport_job,
    complete_transport_milestone,
    create_driver,
    create_transport_document,
    create_transport_exception,
    create_transport_job,
    get_latest_location,
    get_transport_job,
    get_transport_summary,
    list_drivers,
    list_location_updates,
    list_transport_documents,
    list_transport_exceptions,
    list_transport_jobs,
    list_transport_milestones,
    list_vehicles,
    create_vehicle,
    resolve_transport_exception,
    update_driver,
    update_transport_job,
    update_transport_status,
    update_vehicle,
)

router = APIRouter(prefix="/transport", tags=["transport"])
shipment_transport_router = APIRouter(prefix="/shipments", tags=["shipment-transport"])
portal_transport_router = APIRouter(prefix="/portal/shipments", tags=["portal-transport"])

AnyUser = Depends(require_roles("ADMIN", "STAFF", "VIEW_ONLY"))
OperationalUser = Depends(require_roles("ADMIN", "STAFF"))
AdminUser = Depends(require_roles("ADMIN"))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TransportJobRead(BaseModel):
    id: int
    shipment_id: int
    job_number: str
    job_type: str
    movement_type: str
    status: str
    priority: str
    transporter_party_id: Optional[int] = None
    transporter_name: Optional[str] = None
    pickup_location: Optional[str] = None
    delivery_location: Optional[str] = None
    planned_pickup_at: Optional[datetime] = None
    actual_pickup_at: Optional[datetime] = None
    planned_delivery_at: Optional[datetime] = None
    actual_delivery_at: Optional[datetime] = None
    planned_empty_return_at: Optional[datetime] = None
    actual_empty_return_at: Optional[datetime] = None
    eta: Optional[datetime] = None
    last_location_text: Optional[str] = None
    last_location_at: Optional[datetime] = None
    vehicle_id: Optional[int] = None
    driver_id: Optional[int] = None
    delay_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransportJobCreate(BaseModel):
    shipment_id: int
    job_type: str = "domestic_transfer"
    movement_type: str = "containerized"
    priority: str = "p3"
    pickup_location: Optional[str] = None
    delivery_location: Optional[str] = None
    origin_address: Optional[str] = None
    destination_address: Optional[str] = None
    planned_pickup_at: Optional[datetime] = None
    planned_delivery_at: Optional[datetime] = None
    planned_empty_return_at: Optional[datetime] = None


class TransportJobUpdate(BaseModel):
    pickup_location: Optional[str] = None
    delivery_location: Optional[str] = None
    origin_address: Optional[str] = None
    destination_address: Optional[str] = None
    planned_pickup_at: Optional[datetime] = None
    planned_delivery_at: Optional[datetime] = None
    planned_empty_return_at: Optional[datetime] = None
    eta: Optional[datetime] = None
    priority: Optional[str] = None
    movement_type: Optional[str] = None
    delay_reason: Optional[str] = None


class MilestoneRead(BaseModel):
    id: int
    transport_job_id: int
    milestone_key: str
    title: str
    status: str
    planned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completed_by_name: Optional[str] = None
    location_text: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class MilestoneCompleteData(BaseModel):
    location_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None


class LocationUpdateRead(BaseModel):
    id: int
    transport_job_id: int
    source: str
    location_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    recorded_at: datetime
    recorded_by_name: Optional[str] = None
    speed: Optional[float] = None

    class Config:
        from_attributes = True


class LocationUpdateCreate(BaseModel):
    source: str = "manual"
    location_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None


class VehicleRead(BaseModel):
    id: int
    vehicle_number: str
    vehicle_type: str
    capacity: Optional[str] = None
    status: str
    transporter_party_id: Optional[int] = None
    insurance_valid_until: Optional[datetime] = None
    fitness_valid_until: Optional[datetime] = None
    permit_valid_until: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VehicleCreate(BaseModel):
    vehicle_number: str = Field(min_length=1, max_length=30)
    vehicle_type: str = "trailer_20"
    capacity: Optional[str] = None
    status: str = "active"
    transporter_party_id: Optional[int] = None
    insurance_valid_until: Optional[datetime] = None
    fitness_valid_until: Optional[datetime] = None
    permit_valid_until: Optional[datetime] = None


class VehicleUpdate(BaseModel):
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    capacity: Optional[str] = None
    status: Optional[str] = None
    transporter_party_id: Optional[int] = None
    insurance_valid_until: Optional[datetime] = None
    fitness_valid_until: Optional[datetime] = None
    permit_valid_until: Optional[datetime] = None


class DriverRead(BaseModel):
    id: int
    driver_name: str
    phone: Optional[str] = None
    license_number: Optional[str] = None
    license_valid_until: Optional[datetime] = None
    status: str
    transporter_party_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DriverCreate(BaseModel):
    driver_name: str = Field(min_length=1, max_length=150)
    phone: Optional[str] = None
    license_number: Optional[str] = None
    license_valid_until: Optional[datetime] = None
    status: str = "active"
    transporter_party_id: Optional[int] = None


class DriverUpdate(BaseModel):
    driver_name: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None
    license_valid_until: Optional[datetime] = None
    status: Optional[str] = None
    transporter_party_id: Optional[int] = None


class TransportDocRead(BaseModel):
    id: int
    transport_job_id: int
    document_type: str
    status: str
    visible_to_customer: bool
    uploaded_by_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransportDocCreate(BaseModel):
    document_type: str = "other"
    document_version_id: Optional[int] = None
    status: str = "uploaded"
    visible_to_customer: bool = False


class TransportExceptionRead(BaseModel):
    id: int
    transport_job_id: int
    shipment_id: Optional[int] = None
    exception_type: str
    severity: str
    status: str
    title: str
    description: Optional[str] = None
    delay_minutes: Optional[int] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class TransportExceptionCreate(BaseModel):
    transport_job_id: int
    shipment_id: Optional[int] = None
    container_id: Optional[int] = None
    exception_type: str = "other"
    severity: str = "medium"
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    delay_minutes: Optional[int] = None


# ---------------------------------------------------------------------------
# Transport Job Routes
# ---------------------------------------------------------------------------

@router.get("/summary")
def transport_summary(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return get_transport_summary(db)


@router.get("", response_model=list[TransportJobRead])
def list_jobs(
    shipment_id: Optional[int] = None,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    delayed: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
):
    jobs = list_transport_jobs(
        db, shipment_id=shipment_id, status_filter=status,
        job_type=job_type, delayed_only=delayed, limit=limit, offset=offset,
    )
    return [TransportJobRead.model_validate(j) for j in jobs]


@router.post("", response_model=TransportJobRead, status_code=201)
def create_job(
    body: TransportJobCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    job = create_transport_job(db, body.model_dump(), current_user)
    record_audit_log(
        db, current_user, "transport.create", "transport_job",
        entity_id=job.id, entity_label=job.job_number,
        description=f"Transport job created for shipment {job.shipment_id}",
        request=request,
    )
    return TransportJobRead.model_validate(job)


@router.get("/exceptions", response_model=list[TransportExceptionRead])
def list_all_exceptions(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
):
    return [TransportExceptionRead.model_validate(e) for e in list_transport_exceptions(db, status_filter=status, limit=limit, offset=offset)]


@router.post("/exceptions", response_model=TransportExceptionRead, status_code=201)
def create_exception(
    body: TransportExceptionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    exc = create_transport_exception(db, body.model_dump(), current_user)
    record_audit_log(
        db, current_user, "transport.exception_create", "transport_exception",
        entity_id=exc.id, description=f"Transport exception: {exc.title[:100]}",
        request=request,
    )
    return TransportExceptionRead.model_validate(exc)


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

@router.get("/vehicles", response_model=list[VehicleRead])
def list_vehicles_route(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
):
    return [VehicleRead.model_validate(v) for v in list_vehicles(db, status_filter=status)]


@router.post("/vehicles", response_model=VehicleRead, status_code=201)
def create_vehicle_route(
    body: VehicleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    v = create_vehicle(db, body.model_dump(), current_user)
    record_audit_log(
        db, current_user, "transport.vehicle_create", "transport_vehicle",
        entity_id=v.id, entity_label=v.vehicle_number,
        description=f"Vehicle created: {v.vehicle_number}",
        request=request,
    )
    return VehicleRead.model_validate(v)


@router.patch("/vehicles/{vehicle_id}", response_model=VehicleRead)
def update_vehicle_route(
    vehicle_id: int,
    body: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        v = update_vehicle(db, vehicle_id, body.model_dump(exclude_unset=True), current_user)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return VehicleRead.model_validate(v)


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------

@router.get("/drivers", response_model=list[DriverRead])
def list_drivers_route(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = AnyUser,
):
    return [DriverRead.model_validate(d) for d in list_drivers(db, status_filter=status)]


@router.post("/drivers", response_model=DriverRead, status_code=201)
def create_driver_route(
    body: DriverCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    d = create_driver(db, body.model_dump(), current_user)
    record_audit_log(
        db, current_user, "transport.driver_create", "transport_driver",
        entity_id=d.id, entity_label=d.driver_name,
        description=f"Driver created: {d.driver_name}",
        request=request,
    )
    return DriverRead.model_validate(d)


@router.patch("/drivers/{driver_id}", response_model=DriverRead)
def update_driver_route(
    driver_id: int,
    body: DriverUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        d = update_driver(db, driver_id, body.model_dump(exclude_unset=True), current_user)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return DriverRead.model_validate(d)


# ---------------------------------------------------------------------------
# Job Detail Routes
# ---------------------------------------------------------------------------

@router.get("/{job_id}", response_model=TransportJobRead)
def get_job(job_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    job = get_transport_job(db, job_id)
    if not job:
        raise HTTPException(404, "Transport job not found")
    return TransportJobRead.model_validate(job)


@router.patch("/{job_id}", response_model=TransportJobRead)
def update_job(
    job_id: int,
    body: TransportJobUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        job = update_transport_job(db, job_id, body.model_dump(exclude_unset=True), current_user)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return TransportJobRead.model_validate(job)


@router.post("/{job_id}/assign-transporter", response_model=TransportJobRead)
def assign_transporter_route(
    job_id: int,
    transporter_party_id: int = Query(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        job = assign_transporter(db, job_id, transporter_party_id, current_user)
    except ValueError as e:
        raise HTTPException(400, str(e))
    record_audit_log(
        db, current_user, "transport.assign_transporter", "transport_job",
        entity_id=job.id, description=f"Transporter assigned: {job.transporter_name}",
        request=request,
    )
    return TransportJobRead.model_validate(job)


@router.post("/{job_id}/assign-vehicle-driver", response_model=TransportJobRead)
def assign_vehicle_driver_route(
    job_id: int,
    vehicle_id: Optional[int] = Query(None),
    driver_id: Optional[int] = Query(None),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        job = assign_vehicle_driver(db, job_id, current_user, vehicle_id=vehicle_id, driver_id=driver_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    record_audit_log(
        db, current_user, "transport.assign_vehicle_driver", "transport_job",
        entity_id=job.id, description="Vehicle/driver assigned",
        request=request,
    )
    return TransportJobRead.model_validate(job)


@router.post("/{job_id}/status", response_model=TransportJobRead)
def update_status_route(
    job_id: int,
    status: str = Query(...),
    notes: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        job = update_transport_status(db, job_id, status, current_user, notes)
    except ValueError as e:
        raise HTTPException(400, str(e))
    record_audit_log(
        db, current_user, "transport.status_update", "transport_job",
        entity_id=job.id, description=f"Status: {status}",
        request=request,
    )
    return TransportJobRead.model_validate(job)


@router.post("/{job_id}/close", response_model=TransportJobRead)
def close_job_route(
    job_id: int,
    notes: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        job = close_transport_job(db, job_id, current_user, notes)
    except ValueError as e:
        raise HTTPException(400, str(e))
    record_audit_log(
        db, current_user, "transport.close", "transport_job",
        entity_id=job.id, description="Transport job closed",
        request=request,
    )
    return TransportJobRead.model_validate(job)


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------

@router.get("/{job_id}/milestones", response_model=list[MilestoneRead])
def list_milestones(job_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [MilestoneRead.model_validate(m) for m in list_transport_milestones(db, job_id)]


@router.post("/milestones/{milestone_id}/complete", response_model=MilestoneRead)
def complete_milestone_route(
    milestone_id: int,
    body: Optional[MilestoneCompleteData] = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        m = complete_transport_milestone(db, milestone_id, current_user, body.model_dump() if body else None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return MilestoneRead.model_validate(m)


# ---------------------------------------------------------------------------
# Location Updates
# ---------------------------------------------------------------------------

@router.get("/{job_id}/locations", response_model=list[LocationUpdateRead])
def list_locations(job_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [LocationUpdateRead.model_validate(loc) for loc in list_location_updates(db, job_id)]


@router.post("/{job_id}/locations", response_model=LocationUpdateRead, status_code=201)
def add_location(
    job_id: int,
    body: LocationUpdateCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    loc = add_location_update(db, job_id, body.model_dump(), current_user)
    return LocationUpdateRead.model_validate(loc)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@router.get("/{job_id}/documents", response_model=list[TransportDocRead])
def list_docs(job_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [TransportDocRead.model_validate(d) for d in list_transport_documents(db, job_id)]


@router.post("/{job_id}/documents", response_model=TransportDocRead, status_code=201)
def create_doc(
    job_id: int,
    body: TransportDocCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    doc = create_transport_document(db, job_id, body.model_dump(), current_user)
    return TransportDocRead.model_validate(doc)


# ---------------------------------------------------------------------------
# Exceptions (detail)
# ---------------------------------------------------------------------------

@router.get("/exceptions/{exception_id}", response_model=TransportExceptionRead)
def get_exception(exception_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    exc = db.query(TransportException).filter(TransportException.id == exception_id).first()
    if not exc:
        raise HTTPException(404, "Transport exception not found")
    return TransportExceptionRead.model_validate(exc)


@router.post("/exceptions/{exception_id}/resolve", response_model=TransportExceptionRead)
def resolve_exception_route(
    exception_id: int,
    notes: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    try:
        exc = resolve_transport_exception(db, exception_id, current_user, notes)
    except ValueError as e:
        raise HTTPException(400, str(e))
    record_audit_log(
        db, current_user, "transport.exception_resolve", "transport_exception",
        entity_id=exc.id, description="Transport exception resolved",
        request=request,
    )
    return TransportExceptionRead.model_validate(exc)


# ---------------------------------------------------------------------------
# Shipment-specific routes
# ---------------------------------------------------------------------------

@shipment_transport_router.get("/{shipment_id}/transport", response_model=list[TransportJobRead])
def shipment_transport_list(shipment_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [TransportJobRead.model_validate(j) for j in list_transport_jobs(db, shipment_id=shipment_id)]


@shipment_transport_router.post("/{shipment_id}/transport", response_model=TransportJobRead, status_code=201)
def shipment_create_transport(
    shipment_id: int,
    body: TransportJobCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
):
    data = body.model_dump()
    data["shipment_id"] = shipment_id
    job = create_transport_job(db, data, current_user)
    return TransportJobRead.model_validate(job)


@shipment_transport_router.get("/{shipment_id}/transport-summary")
def shipment_transport_summary(shipment_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    jobs = list_transport_jobs(db, shipment_id=shipment_id)
    return {
        "shipment_id": shipment_id,
        "total_jobs": len(jobs),
        "jobs": [{
            "id": j.id, "job_number": j.job_number, "job_type": j.job_type,
            "status": j.status, "last_location_text": j.last_location_text,
            "eta": j.eta.isoformat() if j.eta else None,
        } for j in jobs],
    }


# ---------------------------------------------------------------------------
# Portal-safe routes
# ---------------------------------------------------------------------------

@portal_transport_router.get("/{shipment_id}/transport")
def portal_transport(shipment_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    """Customer-safe transport summary. Hides driver/cost/internal details."""
    return build_customer_safe_transport_summary(db, shipment_id)
