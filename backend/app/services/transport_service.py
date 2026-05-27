"""Phase 20 Transport + GPS layer service."""
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.transport import (
    TransportActivityLog,
    TransportChargeRef,
    TransportDocument,
    TransportDriver,
    TransportException,
    TransportJob,
    TransportJobContainer,
    TransportLocationUpdate,
    TransportMilestone,
    TransportVehicle,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Job number generation
# ---------------------------------------------------------------------------

def _gen_job_number() -> str:
    return f"TRN-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


# ---------------------------------------------------------------------------
# Milestone templates
# ---------------------------------------------------------------------------

MILESTONE_TEMPLATES: dict[str, list[str]] = {
    "export_pickup": [
        "transporter_assigned", "vehicle_assigned", "pickup_scheduled",
        "vehicle_reached_factory", "cargo_loaded", "container_picked_up",
        "gate_in_completed", "job_closed",
    ],
    "import_delivery": [
        "transporter_assigned", "vehicle_assigned", "gate_out_completed",
        "in_transit", "reached_delivery", "cargo_delivered",
        "pod_received", "empty_return_pending", "empty_returned", "job_closed",
    ],
    "empty_container_pickup": [
        "vehicle_assigned", "empty_pickup_confirmed", "in_transit",
        "delivered_to_factory", "job_closed",
    ],
    "empty_container_return": [
        "vehicle_assigned", "empty_pickup_confirmed", "in_transit",
        "empty_returned_to_yard", "return_slip_received", "job_closed",
    ],
    "factory_stuffing": [
        "transporter_assigned", "vehicle_assigned", "reached_factory",
        "stuffing_started", "stuffing_completed", "sealed", "job_closed",
    ],
    "port_gate_in": [
        "transporter_assigned", "vehicle_assigned", "in_transit",
        "at_gate", "gate_in_completed", "job_closed",
    ],
    "port_gate_out": [
        "transporter_assigned", "vehicle_assigned", "gate_out_completed",
        "in_transit", "job_closed",
    ],
    "domestic_transfer": [
        "transporter_assigned", "vehicle_assigned", "pickup_scheduled",
        "picked_up", "in_transit", "delivered", "pod_received", "job_closed",
    ],
}

DEFAULT_MILESTONES = [
    "transporter_assigned", "vehicle_assigned", "pickup_scheduled",
    "picked_up", "in_transit", "delivered", "job_closed",
]


# ---------------------------------------------------------------------------
# Transport Job CRUD
# ---------------------------------------------------------------------------

def create_transport_job(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> TransportJob:
    now = datetime.utcnow()
    job = TransportJob(
        shipment_id=data["shipment_id"],
        job_number=_gen_job_number(),
        job_type=data.get("job_type", "domestic_transfer"),
        movement_type=data.get("movement_type", "containerized"),
        status="planned",
        priority=data.get("priority", "p3"),
        pickup_location=data.get("pickup_location"),
        delivery_location=data.get("delivery_location"),
        origin_address=data.get("origin_address"),
        destination_address=data.get("destination_address"),
        planned_pickup_at=data.get("planned_pickup_at"),
        planned_delivery_at=data.get("planned_delivery_at"),
        planned_empty_return_at=data.get("planned_empty_return_at"),
        created_by_user_id=user.id,
        created_by_name=user.name,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.flush()
    _seed_milestones(db, job)
    _log_activity(db, job, "job_created", f"Transport job created: {job.job_number}", user)
    db.commit()
    db.refresh(job)
    return job


def get_transport_job(db: Session, job_id: int) -> Optional[TransportJob]:
    return db.query(TransportJob).filter(TransportJob.id == job_id).first()


def list_transport_jobs(
    db: Session,
    *,
    shipment_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    job_type: Optional[str] = None,
    transporter_party_id: Optional[int] = None,
    delayed_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[TransportJob]:
    q = db.query(TransportJob)
    if shipment_id:
        q = q.filter(TransportJob.shipment_id == shipment_id)
    if status_filter:
        q = q.filter(TransportJob.status == status_filter)
    if job_type:
        q = q.filter(TransportJob.job_type == job_type)
    if transporter_party_id:
        q = q.filter(TransportJob.transporter_party_id == transporter_party_id)
    if delayed_only:
        q = q.filter(TransportJob.status == "delayed")
    return q.order_by(TransportJob.created_at.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0)).all()


def update_transport_job(db: Session, job_id: int, data: dict[str, Any], user: AuthenticatedUser) -> TransportJob:
    job = get_transport_job(db, job_id)
    if not job:
        raise ValueError("Transport job not found")
    updatable = [
        "pickup_location", "delivery_location", "origin_address", "destination_address",
        "planned_pickup_at", "planned_delivery_at", "planned_empty_return_at",
        "eta", "priority", "movement_type", "delay_reason",
    ]
    for field in updatable:
        if field in data and data[field] is not None:
            setattr(job, field, data[field])
    job.updated_at = datetime.utcnow()
    _log_activity(db, job, "job_updated", "Transport job updated", user)
    db.commit()
    db.refresh(job)
    return job


def assign_transporter(db: Session, job_id: int, transporter_party_id: int, user: AuthenticatedUser) -> TransportJob:
    job = get_transport_job(db, job_id)
    if not job:
        raise ValueError("Transport job not found")
    from app.models.party import Party
    party = db.query(Party).filter(Party.id == transporter_party_id).first()
    job.transporter_party_id = transporter_party_id
    job.transporter_name = party.name if party else None
    if job.status == "planned":
        job.status = "transporter_assigned"
    job.updated_at = datetime.utcnow()
    _log_activity(db, job, "transporter_assigned", f"Transporter assigned: {job.transporter_name}", user)
    db.commit()
    db.refresh(job)
    return job


def assign_vehicle_driver(
    db: Session, job_id: int, user: AuthenticatedUser,
    vehicle_id: Optional[int] = None, driver_id: Optional[int] = None,
) -> TransportJob:
    job = get_transport_job(db, job_id)
    if not job:
        raise ValueError("Transport job not found")
    if vehicle_id:
        vehicle = db.query(TransportVehicle).filter(TransportVehicle.id == vehicle_id).first()
        if not vehicle:
            raise ValueError("Vehicle not found")
        job.vehicle_id = vehicle_id
        if job.status in ("planned", "transporter_assigned"):
            job.status = "vehicle_assigned"
    if driver_id:
        driver = db.query(TransportDriver).filter(TransportDriver.id == driver_id).first()
        if not driver:
            raise ValueError("Driver not found")
        job.driver_id = driver_id
        if job.status in ("planned", "transporter_assigned", "vehicle_assigned"):
            job.status = "driver_assigned"
    job.updated_at = datetime.utcnow()
    _log_activity(db, job, "vehicle_driver_assigned", "Vehicle/driver assigned", user)
    db.commit()
    db.refresh(job)
    return job


def update_transport_status(db: Session, job_id: int, status: str, user: AuthenticatedUser, notes: Optional[str] = None) -> TransportJob:
    job = get_transport_job(db, job_id)
    if not job:
        raise ValueError("Transport job not found")
    now = datetime.utcnow()
    old_status = job.status
    job.status = status
    job.updated_at = now
    # Update timestamp fields based on status
    if status == "picked_up" or status == "at_pickup":
        job.actual_pickup_at = now
    elif status == "delivered" or status == "at_delivery":
        job.actual_delivery_at = now
    elif status == "empty_returned":
        job.actual_empty_return_at = now
    if notes:
        job.delay_reason = notes if status == "delayed" else job.delay_reason
    _log_activity(db, job, f"status_{old_status}_to_{status}", f"Status: {old_status} → {status}" + (f" ({notes})" if notes else ""), user)
    db.commit()
    db.refresh(job)
    return job


def close_transport_job(db: Session, job_id: int, user: AuthenticatedUser, notes: Optional[str] = None) -> TransportJob:
    return update_transport_status(db, job_id, "closed", user, notes)


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------

def _seed_milestones(db: Session, job: TransportJob) -> None:
    keys = MILESTONE_TEMPLATES.get(job.job_type, DEFAULT_MILESTONES)
    for key in keys:
        db.add(TransportMilestone(
            transport_job_id=job.id,
            milestone_key=key,
            title=key.replace("_", " ").title(),
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))


def list_transport_milestones(db: Session, job_id: int) -> list[TransportMilestone]:
    return db.query(TransportMilestone).filter(
        TransportMilestone.transport_job_id == job_id
    ).order_by(TransportMilestone.id).all()


def complete_transport_milestone(db: Session, milestone_id: int, user: AuthenticatedUser, data: Optional[dict] = None) -> TransportMilestone:
    m = db.query(TransportMilestone).filter(TransportMilestone.id == milestone_id).first()
    if not m:
        raise ValueError("Milestone not found")
    now = datetime.utcnow()
    m.status = "completed"
    m.completed_at = now
    m.completed_by_user_id = user.id
    m.completed_by_name = user.name
    m.updated_at = now
    if data:
        m.location_text = data.get("location_text", m.location_text)
        m.latitude = data.get("latitude", m.latitude)
        m.longitude = data.get("longitude", m.longitude)
        m.notes = data.get("notes", m.notes)
    db.commit()
    db.refresh(m)
    return m


# ---------------------------------------------------------------------------
# Location Updates
# ---------------------------------------------------------------------------

def add_location_update(db: Session, job_id: int, data: dict[str, Any], user: AuthenticatedUser) -> TransportLocationUpdate:
    now = datetime.utcnow()
    loc = TransportLocationUpdate(
        transport_job_id=job_id,
        source=data.get("source", "manual"),
        location_text=data.get("location_text"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        recorded_at=now,
        recorded_by_user_id=user.id,
        recorded_by_name=user.name,
        accuracy_meters=data.get("accuracy_meters"),
        speed=data.get("speed"),
        heading=data.get("heading"),
        created_at=now,
    )
    db.add(loc)
    # Update job's last location
    job = get_transport_job(db, job_id)
    if job:
        job.last_location_text = loc.location_text
        job.last_latitude = loc.latitude
        job.last_longitude = loc.longitude
        job.last_location_at = now
        job.updated_at = now
    db.commit()
    db.refresh(loc)
    return loc


def list_location_updates(db: Session, job_id: int) -> list[TransportLocationUpdate]:
    return db.query(TransportLocationUpdate).filter(
        TransportLocationUpdate.transport_job_id == job_id
    ).order_by(TransportLocationUpdate.recorded_at.desc()).all()


def get_latest_location(db: Session, job_id: int) -> Optional[TransportLocationUpdate]:
    return db.query(TransportLocationUpdate).filter(
        TransportLocationUpdate.transport_job_id == job_id
    ).order_by(TransportLocationUpdate.recorded_at.desc()).first()


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

def create_vehicle(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> TransportVehicle:
    now = datetime.utcnow()
    v = TransportVehicle(
        vehicle_number=data["vehicle_number"],
        vehicle_type=data.get("vehicle_type", "trailer_20"),
        capacity=data.get("capacity"),
        status=data.get("status", "active"),
        transporter_party_id=data.get("transporter_party_id"),
        insurance_valid_until=data.get("insurance_valid_until"),
        fitness_valid_until=data.get("fitness_valid_until"),
        permit_valid_until=data.get("permit_valid_until"),
        created_at=now,
        updated_at=now,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def list_vehicles(db: Session, *, status_filter: Optional[str] = None, limit: int = 100) -> list[TransportVehicle]:
    q = db.query(TransportVehicle)
    if status_filter:
        q = q.filter(TransportVehicle.status == status_filter)
    return q.order_by(TransportVehicle.created_at.desc()).limit(limit).all()


def update_vehicle(db: Session, vehicle_id: int, data: dict[str, Any], user: AuthenticatedUser) -> TransportVehicle:
    v = db.query(TransportVehicle).filter(TransportVehicle.id == vehicle_id).first()
    if not v:
        raise ValueError("Vehicle not found")
    updatable = ["vehicle_number", "vehicle_type", "capacity", "status",
                 "transporter_party_id", "insurance_valid_until", "fitness_valid_until", "permit_valid_until"]
    for field in updatable:
        if field in data and data[field] is not None:
            setattr(v, field, data[field])
    v.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(v)
    return v


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------

def create_driver(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> TransportDriver:
    now = datetime.utcnow()
    d = TransportDriver(
        driver_name=data["driver_name"],
        phone=data.get("phone"),
        license_number=data.get("license_number"),
        license_valid_until=data.get("license_valid_until"),
        status=data.get("status", "active"),
        transporter_party_id=data.get("transporter_party_id"),
        created_at=now,
        updated_at=now,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def list_drivers(db: Session, *, status_filter: Optional[str] = None, limit: int = 100) -> list[TransportDriver]:
    q = db.query(TransportDriver)
    if status_filter:
        q = q.filter(TransportDriver.status == status_filter)
    return q.order_by(TransportDriver.created_at.desc()).limit(limit).all()


def update_driver(db: Session, driver_id: int, data: dict[str, Any], user: AuthenticatedUser) -> TransportDriver:
    d = db.query(TransportDriver).filter(TransportDriver.id == driver_id).first()
    if not d:
        raise ValueError("Driver not found")
    updatable = ["driver_name", "phone", "license_number", "license_valid_until", "status", "transporter_party_id"]
    for field in updatable:
        if field in data and data[field] is not None:
            setattr(d, field, data[field])
    d.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(d)
    return d


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def create_transport_document(db: Session, job_id: int, data: dict[str, Any], user: AuthenticatedUser) -> TransportDocument:
    doc = TransportDocument(
        transport_job_id=job_id,
        shipment_id=data.get("shipment_id"),
        document_version_id=data.get("document_version_id"),
        document_type=data.get("document_type", "other"),
        status=data.get("status", "uploaded"),
        visible_to_customer=data.get("visible_to_customer", False),
        uploaded_by_user_id=user.id,
        uploaded_by_name=user.name,
        created_at=datetime.utcnow(),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def list_transport_documents(db: Session, job_id: int) -> list[TransportDocument]:
    return db.query(TransportDocument).filter(
        TransportDocument.transport_job_id == job_id
    ).order_by(TransportDocument.created_at.desc()).all()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

def create_transport_exception(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> TransportException:
    exc = TransportException(
        transport_job_id=data["transport_job_id"],
        shipment_id=data.get("shipment_id"),
        container_id=data.get("container_id"),
        exception_type=data.get("exception_type", "other"),
        severity=data.get("severity", "medium"),
        status="open",
        title=data["title"],
        description=data.get("description"),
        delay_minutes=data.get("delay_minutes"),
        created_at=datetime.utcnow(),
    )
    db.add(exc)
    # Log activity
    job = get_transport_job(db, data["transport_job_id"])
    if job:
        _log_activity(db, job, "exception_created", f"Exception: {exc.title[:100]}", user)
    db.commit()
    db.refresh(exc)
    return exc


def list_transport_exceptions(
    db: Session,
    *,
    transport_job_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TransportException]:
    q = db.query(TransportException)
    if transport_job_id:
        q = q.filter(TransportException.transport_job_id == transport_job_id)
    if status_filter:
        q = q.filter(TransportException.status == status_filter)
    return q.order_by(TransportException.created_at.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0)).all()


def resolve_transport_exception(db: Session, exception_id: int, user: AuthenticatedUser, notes: Optional[str] = None) -> TransportException:
    exc = db.query(TransportException).filter(TransportException.id == exception_id).first()
    if not exc:
        raise ValueError("Transport exception not found")
    exc.status = "resolved"
    exc.resolved_at = datetime.utcnow()
    exc.resolved_by_user_id = user.id
    exc.resolved_by_name = user.name
    job = get_transport_job(db, exc.transport_job_id)
    if job:
        _log_activity(db, job, "exception_resolved", f"Exception resolved: {exc.title[:100]}", user)
    db.commit()
    db.refresh(exc)
    return exc


# ---------------------------------------------------------------------------
# Summary / Visibility
# ---------------------------------------------------------------------------

def get_transport_summary(db: Session) -> dict[str, Any]:
    active = db.query(TransportJob).filter(TransportJob.status.notin_(["closed", "cancelled"])).all()
    open_exceptions = db.query(TransportException).filter(TransportException.status == "open").count()
    return {
        "total_active": len(active),
        "in_transit": sum(1 for j in active if j.status == "in_transit"),
        "delayed": sum(1 for j in active if j.status == "delayed"),
        "empty_return_pending": sum(1 for j in active if j.status == "empty_return_pending"),
        "pod_pending": sum(1 for j in active if j.status == "delivered" and not j.actual_empty_return_at),
        "unassigned": sum(1 for j in active if j.status == "planned"),
        "exceptions_open": open_exceptions,
    }


def build_customer_safe_transport_summary(db: Session, shipment_id: int) -> list[dict[str, Any]]:
    """Build portal-safe transport summary. Hides driver/cost/internal details."""
    jobs = db.query(TransportJob).filter(TransportJob.shipment_id == shipment_id).order_by(TransportJob.created_at.desc()).all()
    result = []
    for job in jobs:
        result.append({
            "job_number": job.job_number,
            "job_type": job.job_type,
            "status": job.status,
            "pickup_location": job.pickup_location,
            "delivery_location": job.delivery_location,
            "planned_pickup_at": job.planned_pickup_at.isoformat() if job.planned_pickup_at else None,
            "actual_pickup_at": job.actual_pickup_at.isoformat() if job.actual_pickup_at else None,
            "planned_delivery_at": job.planned_delivery_at.isoformat() if job.planned_delivery_at else None,
            "actual_delivery_at": job.actual_delivery_at.isoformat() if job.actual_delivery_at else None,
            "last_location_text": job.last_location_text,
            "last_location_at": job.last_location_at.isoformat() if job.last_location_at else None,
            "eta": job.eta.isoformat() if job.eta else None,
            "empty_return_status": "returned" if job.actual_empty_return_at else ("pending" if job.status == "empty_return_pending" else None),
            # Intentionally omit: driver phone, license, transporter cost, internal notes
        })
    return result


# ---------------------------------------------------------------------------
# Activity Log
# ---------------------------------------------------------------------------

def _log_activity(db: Session, job: TransportJob, activity_type: str, summary: str, user: Optional[AuthenticatedUser] = None) -> None:
    db.add(TransportActivityLog(
        transport_job_id=job.id,
        shipment_id=job.shipment_id,
        activity_type=activity_type,
        safe_summary=summary,
        created_by_user_id=user.id if user else None,
        created_by_name=user.name if user else None,
        created_at=datetime.utcnow(),
    ))
