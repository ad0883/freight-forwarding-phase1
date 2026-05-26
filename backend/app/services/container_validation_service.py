"""Phase 11 deterministic container validation checks.

These checks emit Phase 9 ValidationIssue rows when broken container
states are detected. Issues are advisory (non-blocking) by default.
"""
import logging
from datetime import date, datetime
from typing import Any, Optional

from fastapi import Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.container import Container
from app.models.shipment import Shipment
from app.models.validation_issue import ValidationIssue
from app.services.container_service import (
    CONTAINER_NUMBER_RE,
    is_valid_container_number,
)
from app.services.rule_engine import is_rule_enabled


logger = logging.getLogger(__name__)


def evaluate_container_validation(
    db: Session,
    container: Container,
    shipment: Shipment,
    *,
    user: Optional[AuthenticatedUser] = None,
    request: Optional[Request] = None,
) -> list[ValidationIssue]:
    """Run all Phase 11 validation rules for a container."""
    issues: list[ValidationIssue] = []
    try:
        if is_rule_enabled(db, "container_number_format_warning") and not is_valid_container_number(
            container.container_number
        ):
            issues.append(
                _emit_issue(
                    db,
                    rule_key="container_number_format_warning",
                    severity="warning",
                    container=container,
                    message=(
                        f"Container number {container.container_number} does not match the "
                        "ISO format ABCD1234567."
                    ),
                    recommended_action="Correct the container number to four uppercase letters and seven digits.",
                )
            )

        if is_rule_enabled(db, "container_duplicate_active_warning"):
            duplicates = (
                db.query(Container.id)
                .filter(
                    Container.container_number == container.container_number,
                    Container.is_active.is_(True),
                    Container.id != container.id,
                )
                .all()
            )
            if duplicates:
                issues.append(
                    _emit_issue(
                        db,
                        rule_key="container_duplicate_active_warning",
                        severity="warning",
                        container=container,
                        message=(
                            f"Container number {container.container_number} is active in "
                            f"{len(duplicates)} other shipment(s)."
                        ),
                        recommended_action=(
                            "Verify this container is not double-booked. Deactivate the duplicate if needed."
                        ),
                    )
                )

        if (
            is_rule_enabled(db, "container_loaded_before_gate_in_warning")
            and container.loaded_on_vessel_date
            and container.gate_in_date
            and container.loaded_on_vessel_date < container.gate_in_date
        ):
            issues.append(
                _emit_issue(
                    db,
                    rule_key="container_loaded_before_gate_in_warning",
                    severity="warning",
                    container=container,
                    message=(
                        "Loaded-on-vessel date is earlier than gate-in date. Check the dates."
                    ),
                    recommended_action="Correct the gate-in or loaded-on-vessel date.",
                )
            )

        if (
            is_rule_enabled(db, "import_container_delivered_before_do_warning")
            and shipment.type == "import"
            and container.delivery_date
            and container.do_received_date
            and container.delivery_date < container.do_received_date
        ):
            issues.append(
                _emit_issue(
                    db,
                    rule_key="import_container_delivered_before_do_warning",
                    severity="warning",
                    container=container,
                    message=(
                        "Container delivery date is before DO received date. Investigate."
                    ),
                    recommended_action="Correct the DO or delivery dates.",
                )
            )

        if (
            is_rule_enabled(db, "empty_return_before_delivery_warning")
            and container.empty_return_date
            and container.delivery_date
            and container.empty_return_date < container.delivery_date
        ):
            issues.append(
                _emit_issue(
                    db,
                    rule_key="empty_return_before_delivery_warning",
                    severity="warning",
                    container=container,
                    message=(
                        "Empty return date is before delivery date. Check the lifecycle."
                    ),
                    recommended_action="Correct the empty return or delivery date.",
                )
            )

        if (
            is_rule_enabled(db, "gate_in_after_cutoff_warning")
            and container.gate_in_date
            and getattr(shipment, "vgm_cutoff_date", None)
            and container.gate_in_date > shipment.vgm_cutoff_date
        ):
            issues.append(
                _emit_issue(
                    db,
                    rule_key="gate_in_after_cutoff_warning",
                    severity="warning",
                    container=container,
                    message=(
                        "Container gate-in is after the shipment VGM cutoff. Validate with the line."
                    ),
                    recommended_action="Confirm the cutoff or update the gate-in date.",
                )
            )

        # Informational rule for reporting only.
        if is_rule_enabled(db, "partial_delivery_supported_info") and (
            container.delivery_date and not container.empty_return_date
        ):
            issues.append(
                _emit_issue(
                    db,
                    rule_key="partial_delivery_supported_info",
                    severity="info",
                    container=container,
                    message=(
                        "Container delivered but empty return is still pending."
                    ),
                    recommended_action="Track empty return to avoid detention.",
                )
            )

        if issues:
            db.commit()
    except Exception:
        logger.exception(
            "container validation pipeline failed container_id=%s", container.id
        )
        try:
            db.rollback()
        except Exception:
            pass
    return issues


def _emit_issue(
    db: Session,
    *,
    rule_key: str,
    severity: str,
    container: Container,
    message: str,
    recommended_action: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> ValidationIssue:
    """Create or refresh an open validation issue for the container."""
    existing = (
        db.query(ValidationIssue)
        .filter(
            ValidationIssue.rule_key == rule_key,
            ValidationIssue.entity_type == "container",
            ValidationIssue.entity_id == container.id,
            ValidationIssue.status == "open",
        )
        .first()
    )
    if existing:
        existing.message = message
        existing.recommended_action = recommended_action
        existing.metadata_json = metadata or existing.metadata_json
        existing.severity = severity
        return existing
    issue = ValidationIssue(
        rule_key=rule_key,
        entity_type="container",
        entity_id=container.id,
        entity_label=container.container_number,
        shipment_id=container.shipment_id,
        severity=severity,
        status="open",
        message=message,
        recommended_action=recommended_action,
        metadata_json=metadata or None,
        created_at=datetime.utcnow(),
    )
    db.add(issue)
    db.flush()
    return issue
