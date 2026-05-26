"""Phase 11 demurrage / detention exposure service.

Demurrage and detention are intentionally separated. Estimates here are
advisory and never automatically create payable/receivable charges.
"""
import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.container import (
    Container,
    ContainerDemurrageRecord,
    ContainerDetentionRecord,
    DemurrageDetentionRule,
)
from app.models.demurrage import Demurrage as ShipmentDemurrage
from app.models.shipment import Shipment
from app.services.audit_service import record_audit_log
from app.services.event_service import record_operational_event
from app.services.notification_service import create_notification


logger = logging.getLogger(__name__)


DEFAULT_DEMURRAGE_FREE_DAYS = 7
DEFAULT_DETENTION_FREE_DAYS = 7
DEFAULT_RATE_PER_DAY = Decimal("50")
DEFAULT_CURRENCY = "INR"


@dataclass
class ExposureSnapshot:
    container_id: int
    shipment_id: int
    currency: str
    demurrage_days_used: int
    demurrage_chargeable_days: int
    demurrage_estimated_amount: Decimal
    demurrage_status: str
    demurrage_start_date: Optional[date]
    demurrage_end_date: Optional[date]
    detention_days_used: int
    detention_chargeable_days: int
    detention_estimated_amount: Decimal
    detention_status: str
    detention_start_date: Optional[date]
    detention_end_date: Optional[date]
    risk_level: str


def calculate_demurrage_for_container(
    db: Session, container: Container
) -> dict[str, Any]:
    today = date.today()
    free_days = _resolve_free_days(
        db,
        rule_type="demurrage",
        shipment=_safe_shipment(db, container.shipment_id),
        container=container,
        override=container.demurrage_free_days,
    )
    rate_per_day, currency = _resolve_rate(
        db, rule_type="demurrage", container=container, shipment=_safe_shipment(db, container.shipment_id)
    )
    start_date = container.demurrage_start_date or container.discharge_date or container.expected_arrival_date
    end_date = container.demurrage_end_date or container.delivery_date or container.gate_out_date
    open_window = end_date is None
    effective_end = end_date or today
    days_used = _date_diff(start_date, effective_end)
    chargeable_days = max(0, days_used - free_days)
    estimated_amount = (rate_per_day * chargeable_days) if chargeable_days > 0 else Decimal("0")
    if start_date is None:
        result_status = "not_applicable"
    elif open_window and chargeable_days > 0:
        result_status = "running"
    else:
        result_status = "estimated"
    return {
        "free_days": free_days,
        "days_used": int(days_used),
        "chargeable_days": int(chargeable_days),
        "currency": currency,
        "estimated_amount": estimated_amount.quantize(Decimal("0.01")),
        "status": result_status,
        "start_date": start_date,
        "end_date": end_date,
        "rate_per_day": rate_per_day,
    }


def calculate_detention_for_container(
    db: Session, container: Container
) -> dict[str, Any]:
    today = date.today()
    free_days = _resolve_free_days(
        db,
        rule_type="detention",
        shipment=_safe_shipment(db, container.shipment_id),
        container=container,
        override=container.detention_free_days,
    )
    rate_per_day, currency = _resolve_rate(
        db, rule_type="detention", container=container, shipment=_safe_shipment(db, container.shipment_id)
    )
    start_date = (
        container.detention_start_date
        or container.delivery_date
        or container.gate_out_date
    )
    end_date = container.detention_end_date or container.empty_return_date
    open_window = end_date is None
    effective_end = end_date or today
    days_used = _date_diff(start_date, effective_end)
    chargeable_days = max(0, days_used - free_days)
    estimated_amount = (rate_per_day * chargeable_days) if chargeable_days > 0 else Decimal("0")
    if start_date is None:
        result_status = "not_applicable"
    elif open_window and chargeable_days > 0:
        result_status = "running"
    else:
        result_status = "estimated"
    return {
        "free_days": free_days,
        "days_used": int(days_used),
        "chargeable_days": int(chargeable_days),
        "currency": currency,
        "estimated_amount": estimated_amount.quantize(Decimal("0.01")),
        "status": result_status,
        "start_date": start_date,
        "end_date": end_date,
        "rate_per_day": rate_per_day,
    }


def refresh_container_exposure(
    db: Session,
    container: Container,
    *,
    user: Optional[AuthenticatedUser] = None,
    request=None,
) -> ExposureSnapshot:
    demurrage = calculate_demurrage_for_container(db, container)
    detention = calculate_detention_for_container(db, container)

    demurrage_record = _upsert_record(
        db,
        ContainerDemurrageRecord,
        container=container,
        result=demurrage,
        record_source="phase11_engine",
    )
    detention_record = _upsert_record(
        db,
        ContainerDetentionRecord,
        container=container,
        result=detention,
        record_source="phase11_engine",
    )
    db.commit()

    snapshot = ExposureSnapshot(
        container_id=container.id,
        shipment_id=container.shipment_id,
        currency=demurrage["currency"],
        demurrage_days_used=demurrage["days_used"],
        demurrage_chargeable_days=demurrage["chargeable_days"],
        demurrage_estimated_amount=Decimal(str(demurrage["estimated_amount"])),
        demurrage_status=demurrage["status"],
        demurrage_start_date=demurrage["start_date"],
        demurrage_end_date=demurrage["end_date"],
        detention_days_used=detention["days_used"],
        detention_chargeable_days=detention["chargeable_days"],
        detention_estimated_amount=Decimal(str(detention["estimated_amount"])),
        detention_status=detention["status"],
        detention_start_date=detention["start_date"],
        detention_end_date=detention["end_date"],
        risk_level=_risk_level(container, demurrage, detention),
    )

    record_operational_event(
        db,
        "container.exposure_refreshed",
        "container",
        entity_id=container.id,
        entity_label=container.container_number,
        shipment_id=container.shipment_id,
        actor_user=user,
        source="finance",
        new_state={
            "demurrage_status": snapshot.demurrage_status,
            "detention_status": snapshot.detention_status,
            "risk_level": snapshot.risk_level,
        },
        metadata={
            "demurrage_chargeable_days": snapshot.demurrage_chargeable_days,
            "detention_chargeable_days": snapshot.detention_chargeable_days,
            "demurrage_estimated_amount": str(snapshot.demurrage_estimated_amount),
            "detention_estimated_amount": str(snapshot.detention_estimated_amount),
        },
        request=request,
        run_validation=False,
    )
    if user:
        record_audit_log(
            db,
            user,
            "container.exposure_refresh",
            "container",
            entity_id=container.id,
            entity_label=container.container_number,
            description="Container exposure refreshed.",
            metadata={
                "shipment_id": container.shipment_id,
                "risk_level": snapshot.risk_level,
            },
            request=request,
        )
    _emit_risk_notifications(db, container, snapshot)
    return snapshot


def refresh_shipment_container_exposure(
    db: Session,
    shipment_id: int,
    *,
    user: Optional[AuthenticatedUser] = None,
    request=None,
) -> list[ExposureSnapshot]:
    containers = (
        db.query(Container)
        .filter(Container.shipment_id == shipment_id, Container.is_active.is_(True))
        .all()
    )
    return [refresh_container_exposure(db, container, user=user, request=request) for container in containers]


def list_recent_container_risk(db: Session, *, limit: int = 25) -> list[dict[str, Any]]:
    rows = (
        db.query(Container, Shipment)
        .join(Shipment, Shipment.id == Container.shipment_id)
        .filter(Container.is_active.is_(True), Shipment.is_archived.is_(False))
        .order_by(Container.updated_at.desc())
        .limit(200)
        .all()
    )
    out: list[dict[str, Any]] = []
    for container, shipment in rows:
        snapshot = refresh_container_exposure(db, container)
        if snapshot.risk_level in {"none"}:
            continue
        out.append(
            {
                "shipment_id": shipment.id,
                "shipment_code": shipment.shipment_code,
                "container_id": container.id,
                "container_number": container.container_number,
                "current_status": container.current_status,
                "demurrage_status": snapshot.demurrage_status,
                "demurrage_estimated_amount": snapshot.demurrage_estimated_amount,
                "detention_status": snapshot.detention_status,
                "detention_estimated_amount": snapshot.detention_estimated_amount,
                "empty_return_deadline": container.empty_return_deadline,
                "risk_level": snapshot.risk_level,
            }
        )
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_shipment(db: Session, shipment_id: int) -> Optional[Shipment]:
    return db.query(Shipment).filter(Shipment.id == shipment_id).first()


def _resolve_free_days(
    db: Session,
    *,
    rule_type: str,
    shipment: Optional[Shipment],
    container: Container,
    override: Optional[int],
) -> int:
    if override is not None:
        return int(override)
    if rule_type == "demurrage" and shipment and shipment.id:
        existing = (
            db.query(ShipmentDemurrage.free_days)
            .filter(ShipmentDemurrage.shipment_id == shipment.id)
            .first()
        )
        if existing and existing.free_days is not None:
            return int(existing.free_days)
    rule = (
        db.query(DemurrageDetentionRule)
        .filter(
            DemurrageDetentionRule.is_active.is_(True),
            DemurrageDetentionRule.rule_type == rule_type,
        )
        .filter(
            (DemurrageDetentionRule.shipment_direction.is_(None))
            | (DemurrageDetentionRule.shipment_direction == (shipment.type if shipment else None))
        )
        .filter(
            (DemurrageDetentionRule.container_size.is_(None))
            | (DemurrageDetentionRule.container_size == container.container_size)
        )
        .order_by(DemurrageDetentionRule.created_at.asc())
        .first()
    )
    if rule and rule.free_days is not None:
        return int(rule.free_days)
    return DEFAULT_DEMURRAGE_FREE_DAYS if rule_type == "demurrage" else DEFAULT_DETENTION_FREE_DAYS


def _resolve_rate(
    db: Session,
    *,
    rule_type: str,
    container: Container,
    shipment: Optional[Shipment],
) -> tuple[Decimal, str]:
    rule = (
        db.query(DemurrageDetentionRule)
        .filter(
            DemurrageDetentionRule.is_active.is_(True),
            DemurrageDetentionRule.rule_type == rule_type,
        )
        .filter(
            (DemurrageDetentionRule.shipment_direction.is_(None))
            | (DemurrageDetentionRule.shipment_direction == (shipment.type if shipment else None))
        )
        .filter(
            (DemurrageDetentionRule.container_size.is_(None))
            | (DemurrageDetentionRule.container_size == container.container_size)
        )
        .order_by(DemurrageDetentionRule.created_at.asc())
        .first()
    )
    if rule and rule.rate_per_day is not None:
        return Decimal(str(rule.rate_per_day)), rule.currency or DEFAULT_CURRENCY
    return DEFAULT_RATE_PER_DAY, DEFAULT_CURRENCY


def _date_diff(start: Optional[date], end: Optional[date]) -> int:
    if not start or not end:
        return 0
    diff = (end - start).days
    return max(0, diff)


def _upsert_record(
    db: Session,
    model,
    *,
    container: Container,
    result: dict[str, Any],
    record_source: str,
):
    record = (
        db.query(model)
        .filter(model.container_id == container.id)
        .order_by(model.id.desc())
        .first()
    )
    if not record:
        record = model(
            container_id=container.id,
            shipment_id=container.shipment_id,
        )
        db.add(record)
    record.start_date = result["start_date"]
    record.end_date = result["end_date"]
    record.free_days = result["free_days"]
    record.days_used = result["days_used"]
    record.chargeable_days = result["chargeable_days"]
    record.currency = result["currency"]
    record.estimated_amount = result["estimated_amount"]
    record.status = result["status"]
    record.source = record_source
    db.flush()
    return record


def _risk_level(
    container: Container,
    demurrage: dict[str, Any],
    detention: dict[str, Any],
) -> str:
    today = date.today()
    if (
        container.empty_return_deadline
        and not container.empty_return_date
        and container.empty_return_deadline < today
    ):
        return "critical"
    if demurrage["status"] == "running" or detention["status"] == "running":
        return "running"
    if (
        container.empty_return_deadline
        and not container.empty_return_date
        and (container.empty_return_deadline - today).days <= 1
    ):
        return "critical"
    if (
        container.empty_return_deadline
        and not container.empty_return_date
        and (container.empty_return_deadline - today).days <= 3
    ):
        return "warning"
    if demurrage["chargeable_days"] > 0 or detention["chargeable_days"] > 0:
        return "warning"
    return "none"


def _emit_risk_notifications(
    db: Session, container: Container, snapshot: ExposureSnapshot
) -> None:
    today = date.today()
    base_metadata = {
        "shipment_id": container.shipment_id,
        "container_id": container.id,
        "container_number": container.container_number,
    }
    try:
        if snapshot.demurrage_status == "running":
            _create(
                db,
                title="Demurrage running",
                message=(
                    f"Container {container.container_number} demurrage is running with "
                    f"{snapshot.demurrage_chargeable_days} chargeable day(s)."
                ),
                category="demurrage",
                priority="critical",
                entity_type="container",
                entity_id=container.id,
                entity_label=container.container_number,
                dedupe_key=f"container_demurrage_running:{container.id}",
                metadata=base_metadata,
            )
        if snapshot.detention_status == "running":
            _create(
                db,
                title="Detention running",
                message=(
                    f"Container {container.container_number} detention is running with "
                    f"{snapshot.detention_chargeable_days} chargeable day(s)."
                ),
                category="demurrage",
                priority="critical",
                entity_type="container",
                entity_id=container.id,
                entity_label=container.container_number,
                dedupe_key=f"container_detention_running:{container.id}",
                metadata=base_metadata,
            )
        if container.empty_return_deadline and not container.empty_return_date:
            days_remaining = (container.empty_return_deadline - today).days
            if days_remaining < 0:
                _create(
                    db,
                    title="Empty return overdue",
                    message=(
                        f"Empty return for container {container.container_number} is "
                        f"overdue by {abs(days_remaining)} day(s)."
                    ),
                    category="demurrage",
                    priority="critical",
                    entity_type="container",
                    entity_id=container.id,
                    entity_label=container.container_number,
                    dedupe_key=f"container_empty_return_overdue:{container.id}",
                    metadata=base_metadata,
                )
            elif days_remaining <= 1:
                _create(
                    db,
                    title="Empty return due tomorrow",
                    message=(
                        f"Empty return deadline for container {container.container_number} "
                        f"is in {days_remaining} day(s)."
                    ),
                    category="demurrage",
                    priority="warning",
                    entity_type="container",
                    entity_id=container.id,
                    entity_label=container.container_number,
                    dedupe_key=f"container_detention_warning:{container.id}:{today.isoformat()}",
                    metadata=base_metadata,
                )
            elif days_remaining <= 3:
                _create(
                    db,
                    title="Empty return approaching",
                    message=(
                        f"Empty return deadline for container {container.container_number} "
                        f"is in {days_remaining} day(s)."
                    ),
                    category="demurrage",
                    priority="info",
                    entity_type="container",
                    entity_id=container.id,
                    entity_label=container.container_number,
                    dedupe_key=f"container_detention_warning:{container.id}:{today.isoformat()}",
                    metadata=base_metadata,
                )
    except Exception:
        logger.exception(
            "container risk notification failed container_id=%s", container.id
        )


def _create(db: Session, **kwargs) -> None:
    create_notification(db, source="workflow", target_role="STAFF", **kwargs)
