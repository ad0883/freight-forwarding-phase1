"""Phase 14 release control service.

Advisory in-app checks for sensitive shipment actions: release_final_bl,
release_do, dispatch_documents, mark_export_completed, mark_import_completed.
Active credit holds and severe finance risks raise blocks/warnings.
"""
import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.finance_control import CreditHoldRecord
from app.models.shipment import Shipment
from app.schemas.finance_control import CreditHoldRead, ReleaseCheckResult
from app.services.credit_control_service import (
    expose_credit_hold_read,
    get_active_holds_for_party,
    get_active_holds_for_shipment,
)
from app.services.finance_risk_service import create_finance_risk


logger = logging.getLogger(__name__)


SUPPORTED_RELEASE_ACTIONS = {
    "release_final_bl",
    "release_do",
    "dispatch_documents",
    "mark_export_completed",
    "mark_import_completed",
    "extend_credit",
}


def check_release_allowed(
    db: Session, shipment_id: int, action_key: str, user: Optional[AuthenticatedUser] = None
) -> ReleaseCheckResult:
    if action_key not in SUPPORTED_RELEASE_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported release action {action_key!r}. "
                f"Allowed: {', '.join(sorted(SUPPORTED_RELEASE_ACTIONS))}"
            ),
        )
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")

    blocking_holds: list[CreditHoldRecord] = list(get_active_holds_for_shipment(db, shipment_id))

    party_id = shipment.exporter_id or shipment.importer_id
    if party_id:
        for hold in get_active_holds_for_party(db, party_id):
            if hold not in blocking_holds:
                blocking_holds.append(hold)

    blocked_by = [
        expose_credit_hold_read(db, hold)
        for hold in blocking_holds
        if hold.blocked_action is None or hold.blocked_action == action_key
    ]

    warnings: list[str] = []
    allowed = True
    if blocked_by:
        allowed = False

    if not allowed:
        try:
            create_finance_risk(
                db,
                risk_type="release_blocked",
                severity="critical",
                message=(
                    f"Release action {action_key} blocked on shipment "
                    f"{shipment.shipment_code}: {len(blocked_by)} active hold(s)."
                ),
                shipment_id=shipment_id,
                party_id=party_id,
                related_hold_id=blocked_by[0].id,
                recommended_action="Resolve or waive the active credit holds before release.",
                dedupe_key=f"finance_release_blocked:{shipment_id}:{action_key}",
            )
        except Exception:
            logger.exception("Unable to record release-blocked finance risk")

    message = (
        f"Release allowed for {action_key} on {shipment.shipment_code}."
        if allowed
        else f"Release blocked for {action_key}: resolve {len(blocked_by)} active hold(s)."
    )
    return ReleaseCheckResult(
        action_key=action_key,
        allowed=allowed,
        blocked_by=blocked_by,
        warnings=warnings,
        message=message,
    )


def create_release_hold_if_needed(
    db: Session,
    shipment_id: int,
    action_key: str,
    reason: str,
    user: Optional[AuthenticatedUser] = None,
) -> Optional[CreditHoldRead]:
    """Create a manual release hold for a sensitive action when reasoned."""
    if action_key not in SUPPORTED_RELEASE_ACTIONS:
        return None
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        return None
    from app.services.credit_control_service import create_or_refresh_credit_hold

    hold_type = {
        "release_final_bl": "obl_release_hold",
        "release_do": "do_release_hold",
        "dispatch_documents": "document_release_hold",
        "mark_export_completed": "shipment_completion_hold",
        "mark_import_completed": "shipment_completion_hold",
        "extend_credit": "manual_finance_hold",
    }[action_key]
    party_id = shipment.exporter_id or shipment.importer_id
    hold = create_or_refresh_credit_hold(
        db,
        hold_type=hold_type,
        reason=reason,
        party_id=party_id,
        shipment_id=shipment_id,
        severity="warning",
        trigger_source="user",
        blocked_action=action_key,
        user=user,
    )
    return expose_credit_hold_read(db, hold)


def list_release_holds(
    db: Session,
    *,
    shipment_id: Optional[int] = None,
    status_filter: Optional[str] = "active",
    limit: int = 100,
) -> list[CreditHoldRead]:
    query = db.query(CreditHoldRecord).filter(
        CreditHoldRecord.blocked_action.isnot(None),
    )
    if shipment_id is not None:
        query = query.filter(CreditHoldRecord.shipment_id == shipment_id)
    if status_filter:
        query = query.filter(CreditHoldRecord.status == status_filter)
    rows = (
        query.order_by(CreditHoldRecord.created_at.desc())
        .limit(min(max(limit, 1), 500))
        .all()
    )
    return [expose_credit_hold_read(db, row) for row in rows]
