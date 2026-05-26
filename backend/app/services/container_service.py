"""Phase 11 container lifecycle service.

Container records track each physical container as a first-class operational
entity. Container events are append-only. Status transitions trigger Phase 9
operational events and Phase 11 validation issues without forcing changes to
the shipment-level workflow state machine.
"""
import logging
import re
from datetime import date, datetime
from typing import Any, Iterable, Optional

from fastapi import HTTPException, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.container import Container, ContainerEvent
from app.models.shipment import Shipment
from app.services.audit_service import record_audit_log
from app.services.event_service import record_operational_event


logger = logging.getLogger(__name__)


CONTAINER_NUMBER_RE = re.compile(r"^[A-Z]{4}\d{7}$")
EXPORT_STATUSES = [
    "CONTAINER_PLANNED",
    "EMPTY_RELEASED",
    "EMPTY_PICKUP_SCHEDULED",
    "EMPTY_PICKED_UP",
    "ARRIVED_AT_FACTORY",
    "STUFFING_STARTED",
    "STUFFING_COMPLETED",
    "SEALED",
    "DISPATCHED_TO_PORT",
    "GATE_IN",
    "LOADED_ON_VESSEL",
    "DEPARTED",
    "CLOSED",
]
IMPORT_STATUSES = [
    "EXPECTED_ON_VESSEL",
    "ARRIVED_AT_PORT",
    "DISCHARGED",
    "DO_RECEIVED",
    "CLEARED_FOR_DELIVERY",
    "GATE_OUT",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "DE_STUFFED_IF_APPLICABLE",
    "EMPTY_RETURN_PENDING",
    "EMPTY_RETURNED",
    "CLOSED",
]
ALL_STATUSES = sorted({*EXPORT_STATUSES, *IMPORT_STATUSES})

STATUS_TO_DATE_FIELD = {
    "CONTAINER_PLANNED": "planned_date",
    "EMPTY_RELEASED": "empty_release_date",
    "EMPTY_PICKED_UP": "empty_pickup_date",
    "ARRIVED_AT_FACTORY": "factory_arrival_date",
    "STUFFING_STARTED": "stuffing_start_date",
    "STUFFING_COMPLETED": "stuffing_completed_date",
    "SEALED": "sealed_date",
    "GATE_IN": "gate_in_date",
    "LOADED_ON_VESSEL": "loaded_on_vessel_date",
    "DEPARTED": "departed_date",
    "ARRIVED_AT_PORT": "expected_arrival_date",
    "DISCHARGED": "discharge_date",
    "DO_RECEIVED": "do_received_date",
    "GATE_OUT": "gate_out_date",
    "DELIVERED": "delivery_date",
    "EMPTY_RETURNED": "empty_return_date",
}

STATUS_TO_EVENT_TYPE = {
    "CONTAINER_PLANNED": "CONTAINER_PLANNED",
    "EMPTY_RELEASED": "EMPTY_RELEASED",
    "EMPTY_PICKUP_SCHEDULED": "EMPTY_PICKUP_SCHEDULED",
    "EMPTY_PICKED_UP": "EMPTY_PICKED_UP",
    "ARRIVED_AT_FACTORY": "ARRIVED_AT_FACTORY",
    "STUFFING_STARTED": "STUFFING_STARTED",
    "STUFFING_COMPLETED": "STUFFING_COMPLETED",
    "SEALED": "SEALED",
    "DISPATCHED_TO_PORT": "DISPATCHED_TO_PORT",
    "GATE_IN": "GATE_IN",
    "LOADED_ON_VESSEL": "LOADED_ON_VESSEL",
    "DEPARTED": "DEPARTED",
    "EXPECTED_ON_VESSEL": "EXPECTED_ON_VESSEL",
    "ARRIVED_AT_PORT": "ARRIVED_AT_PORT",
    "DISCHARGED": "DISCHARGED",
    "DO_RECEIVED": "DO_RECEIVED",
    "CLEARED_FOR_DELIVERY": "CLEARED_FOR_DELIVERY",
    "GATE_OUT": "GATE_OUT",
    "OUT_FOR_DELIVERY": "OUT_FOR_DELIVERY",
    "DELIVERED": "DELIVERED",
    "DE_STUFFED_IF_APPLICABLE": "DE_STUFFED_IF_APPLICABLE",
    "EMPTY_RETURN_PENDING": "EMPTY_RETURN_PENDING",
    "EMPTY_RETURNED": "EMPTY_RETURNED",
    "CLOSED": "CLOSED",
}


def is_valid_container_number(value: Optional[str]) -> bool:
    if not value:
        return False
    return bool(CONTAINER_NUMBER_RE.match(value.strip().upper()))


def normalize_container_number(value: str) -> str:
    return value.strip().upper()


def get_shipment(db: Session, shipment_id: int) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    return shipment


def list_containers(
    db: Session,
    *,
    shipment_id: Optional[int] = None,
    include_inactive: bool = False,
    risk_level: Optional[str] = None,
) -> list[Container]:
    query = db.query(Container)
    if shipment_id is not None:
        query = query.filter(Container.shipment_id == shipment_id)
    if not include_inactive:
        query = query.filter(Container.is_active.is_(True))
    return query.order_by(Container.shipment_id.asc(), Container.id.asc()).all()


def get_container(db: Session, container_id: int) -> Container:
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")
    return container


def create_container(
    db: Session,
    shipment: Shipment,
    data: dict[str, Any],
    user: AuthenticatedUser,
    *,
    request: Optional[Request] = None,
    source: str = "user",
) -> Container:
    payload = dict(data)
    container_number = payload.get("container_number")
    if not container_number:
        raise HTTPException(status_code=400, detail="container_number is required")
    payload["container_number"] = normalize_container_number(container_number)
    if not payload.get("current_status"):
        payload["current_status"] = (
            "CONTAINER_PLANNED" if shipment.type == "export" else "EXPECTED_ON_VESSEL"
        )
    container = Container(shipment_id=shipment.id, **payload)
    db.add(container)
    db.flush()
    record_container_event(
        db,
        container,
        event_type="CONTAINER_CREATED",
        event_date=date.today(),
        user=user,
        source=source,
        description="Container record created.",
        commit=False,
    )
    db.commit()
    db.refresh(container)

    record_audit_log(
        db,
        user,
        "container.create",
        "container",
        entity_id=container.id,
        entity_label=container.container_number,
        description="Container created.",
        metadata={"shipment_id": shipment.id, "container_status": container.current_status},
        request=request,
    )
    record_operational_event(
        db,
        "container.created",
        "container",
        entity_id=container.id,
        entity_label=container.container_number,
        shipment_id=shipment.id,
        actor_user=user,
        source=source if source in {"user", "system", "gmail", "ai", "scheduler", "workflow", "finance", "notification"} else "system",
        new_state={
            "container_number": container.container_number,
            "current_status": container.current_status,
            "container_size": container.container_size,
            "container_type": container.container_type,
        },
        metadata={"shipment_id": shipment.id},
        request=request,
        run_validation=False,
    )
    _run_container_validation(db, container, shipment, user=user, request=request)
    return container


def update_container(
    db: Session,
    container: Container,
    data: dict[str, Any],
    user: AuthenticatedUser,
    *,
    request: Optional[Request] = None,
) -> Container:
    payload = dict(data)
    if "container_number" in payload and payload["container_number"]:
        payload["container_number"] = normalize_container_number(payload["container_number"])
    before = {field: getattr(container, field, None) for field in payload.keys()}
    for field, value in payload.items():
        setattr(container, field, value)
    db.commit()
    db.refresh(container)
    record_audit_log(
        db,
        user,
        "container.update",
        "container",
        entity_id=container.id,
        entity_label=container.container_number,
        description="Container updated.",
        metadata={
            "shipment_id": container.shipment_id,
            "fields_changed": sorted(payload.keys()),
        },
        request=request,
    )
    record_operational_event(
        db,
        "container.updated",
        "container",
        entity_id=container.id,
        entity_label=container.container_number,
        shipment_id=container.shipment_id,
        actor_user=user,
        source="user",
        previous_state=before,
        new_state={
            "container_number": container.container_number,
            "current_status": container.current_status,
            **{key: getattr(container, key, None) for key in payload.keys()},
        },
        metadata={"fields_changed": sorted(payload.keys())},
        request=request,
        run_validation=False,
    )
    shipment = get_shipment(db, container.shipment_id)
    _run_container_validation(db, container, shipment, user=user, request=request)
    return container


def delete_container(db: Session, container: Container, user: AuthenticatedUser, *, request: Optional[Request] = None) -> None:
    if (
        db.query(ContainerEvent.id)
        .filter(ContainerEvent.container_id == container.id)
        .first()
    ):
        # Soft delete to preserve append-only events.
        container.is_active = False
        container.closed_at = datetime.utcnow()
        db.commit()
        record_audit_log(
            db,
            user,
            "container.update",
            "container",
            entity_id=container.id,
            entity_label=container.container_number,
            description="Container deactivated (soft delete).",
            metadata={"shipment_id": container.shipment_id, "soft_delete": True},
            request=request,
        )
        return
    container_id = container.id
    container_number = container.container_number
    shipment_id = container.shipment_id
    db.delete(container)
    db.commit()
    record_audit_log(
        db,
        user,
        "container.update",
        "container",
        entity_id=container_id,
        entity_label=container_number,
        description="Container hard-deleted (no events recorded).",
        metadata={"shipment_id": shipment_id, "hard_delete": True},
        request=request,
    )


def record_container_event(
    db: Session,
    container: Container,
    *,
    event_type: str,
    event_date: Optional[date] = None,
    user: Optional[AuthenticatedUser] = None,
    source: str = "user",
    description: Optional[str] = None,
    location: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    commit: bool = True,
    request: Optional[Request] = None,
) -> ContainerEvent:
    event = ContainerEvent(
        container_id=container.id,
        shipment_id=container.shipment_id,
        event_type=event_type,
        event_date=event_date or date.today(),
        location=location,
        source=source,
        description=description,
        actor_user_id=getattr(user, "id", None) if user else None,
        actor_name=getattr(user, "name", None) if user else None,
        metadata_json=metadata or None,
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.flush()
    if commit:
        db.commit()
        db.refresh(event)
        if user:
            record_audit_log(
                db,
                user,
                "container.event_add",
                "container",
                entity_id=container.id,
                entity_label=container.container_number,
                description=f"Container event {event_type} recorded.",
                metadata={
                    "shipment_id": container.shipment_id,
                    "event_type": event_type,
                    "event_date": event_date.isoformat() if event_date else None,
                    "source": source,
                },
                request=request,
            )
        record_operational_event(
            db,
            "container.event_added",
            "container",
            entity_id=container.id,
            entity_label=container.container_number,
            shipment_id=container.shipment_id,
            actor_user=user,
            source=source if source in {"user", "system", "gmail", "ai", "scheduler", "workflow", "finance", "notification"} else "system",
            new_state={"event_type": event_type},
            metadata={"event_date": event_date.isoformat() if event_date else None},
            request=request,
            run_validation=False,
        )
    return event


def transition_container_status(
    db: Session,
    container: Container,
    new_status: str,
    user: AuthenticatedUser,
    *,
    reason: Optional[str] = None,
    event_date: Optional[date] = None,
    request: Optional[Request] = None,
) -> Container:
    new_status = (new_status or "").strip().upper()
    if new_status not in ALL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Unknown container status: {new_status}")
    previous_status = container.current_status
    container.current_status = new_status
    date_field = STATUS_TO_DATE_FIELD.get(new_status)
    if date_field and not getattr(container, date_field):
        setattr(container, date_field, event_date or date.today())
    if new_status == "CLOSED":
        container.closed_at = datetime.utcnow()
        container.is_active = False
    db.flush()
    event_type = STATUS_TO_EVENT_TYPE.get(new_status, new_status)
    record_container_event(
        db,
        container,
        event_type=event_type,
        event_date=event_date or date.today(),
        user=user,
        source="user",
        description=reason,
        commit=False,
    )
    db.commit()
    db.refresh(container)
    record_audit_log(
        db,
        user,
        "container.status_change",
        "container",
        entity_id=container.id,
        entity_label=container.container_number,
        description=f"Container status {previous_status} -> {new_status}",
        metadata={
            "shipment_id": container.shipment_id,
            "previous_status": previous_status,
            "new_status": new_status,
            "reason_present": bool(reason),
        },
        request=request,
    )
    record_operational_event(
        db,
        "container.status_changed",
        "container",
        entity_id=container.id,
        entity_label=container.container_number,
        shipment_id=container.shipment_id,
        actor_user=user,
        source="user",
        previous_state={"current_status": previous_status},
        new_state={"current_status": new_status},
        metadata={"reason_present": bool(reason)},
        request=request,
        run_validation=False,
    )
    shipment = get_shipment(db, container.shipment_id)
    _run_container_validation(db, container, shipment, user=user, request=request)
    return container


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run_container_validation(
    db: Session,
    container: Container,
    shipment: Shipment,
    *,
    user: Optional[AuthenticatedUser] = None,
    request: Optional[Request] = None,
) -> None:
    try:
        from app.services.container_validation_service import (
            evaluate_container_validation,
        )

        evaluate_container_validation(db, container, shipment, request=request, user=user)
    except Exception:
        logger.exception(
            "container validation failed container_id=%s", getattr(container, "id", None)
        )
