"""Phase 11 best-effort container backfill from legacy shipment fields."""
import logging
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.container import Container
from app.models.shipment import Shipment
from app.services.audit_service import record_audit_log
from app.services.container_service import (
    create_container,
    is_valid_container_number,
    normalize_container_number,
)
from app.services.event_service import record_operational_event


logger = logging.getLogger(__name__)


def backfill_containers_from_shipments(
    db: Session,
    *,
    dry_run: bool = True,
    user: Optional[AuthenticatedUser] = None,
    request=None,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    created_count = 0
    shipments = (
        db.query(Shipment)
        .filter(Shipment.is_archived.is_(False))
        .order_by(Shipment.id.asc())
        .all()
    )
    for shipment in shipments:
        existing_count = (
            db.query(Container).filter(Container.shipment_id == shipment.id).count()
        )
        if existing_count:
            continue
        raw_value = shipment.container_no or ""
        notes: list[str] = []
        numbers = _split_candidates(raw_value, notes)
        if not numbers:
            continue
        candidate = {
            "shipment_id": shipment.id,
            "shipment_code": shipment.shipment_code,
            "container_numbers": numbers,
            "container_size": _container_size_hint(shipment.container_type),
            "container_type": shipment.container_type,
            "notes": notes,
        }
        candidates.append(candidate)
        if dry_run or not user:
            continue
        for number in numbers:
            try:
                create_container(
                    db,
                    shipment,
                    {
                        "container_number": number,
                        "container_type": shipment.container_type,
                        "container_size": _container_size_hint(shipment.container_type),
                        "current_status": (
                            "EXPECTED_ON_VESSEL" if shipment.type == "import" else "CONTAINER_PLANNED"
                        ),
                    },
                    user,
                    request=request,
                    source="system",
                )
                created_count += 1
            except Exception:
                logger.exception(
                    "Container backfill failed for shipment_id=%s number=%s",
                    shipment.id,
                    number,
                )
    if user:
        record_audit_log(
            db,
            user,
            "container.backfill",
            "shipment",
            description="Container backfill from legacy shipment fields.",
            metadata={
                "dry_run": dry_run,
                "candidate_count": len(candidates),
                "created_count": created_count,
            },
            request=request,
        )
        record_operational_event(
            db,
            "container.backfill_dry_run" if dry_run else "container.backfill_applied",
            "shipment",
            actor_user=user,
            source="system",
            metadata={
                "candidate_count": len(candidates),
                "created_count": created_count,
            },
            request=request,
            run_validation=False,
        )
    return {
        "dry_run": dry_run,
        "candidates": candidates,
        "created_count": created_count,
    }


def _split_candidates(value: str, notes: list[str]) -> list[str]:
    raw = (value or "").strip()
    if not raw:
        return []
    pieces = [piece.strip() for piece in raw.replace(";", ",").split(",")]
    pieces = [normalize_container_number(piece) for piece in pieces if piece]
    valid: list[str] = []
    for piece in pieces:
        if is_valid_container_number(piece):
            valid.append(piece)
        else:
            notes.append(f"Skipped non-ISO value: {piece}")
    if not valid and pieces:
        notes.append("No valid ISO container numbers in the legacy field.")
    return valid


def _container_size_hint(container_type: Optional[str]) -> Optional[str]:
    if not container_type:
        return None
    upper = container_type.upper()
    if upper.startswith("20"):
        return "20"
    if upper.startswith("40"):
        return "40"
    if upper == "LCL":
        return "LCL"
    return None
