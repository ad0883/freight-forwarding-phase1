"""Phase 14 finance risk service.

Creates and resolves finance risk records, with deduplication based on a
caller-supplied ``dedupe_key``. Critical risks also fan out to notifications
and validation issues, but writes never break the original business action.
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.finance_control import FinanceRiskRecord
from app.models.party import Party
from app.models.shipment import Shipment
from app.models.validation_issue import ValidationIssue
from app.schemas.finance_control import FinanceRiskRead


logger = logging.getLogger(__name__)


SEVERITY_TO_PRIORITY = {
    "critical": "critical",
    "warning": "warning",
    "info": "info",
}

RISK_TO_RULE_KEY = {
    "receivable_overdue": "finance_receivable_overdue",
    "payable_overdue": "finance_payable_overdue",
    "credit_limit_warning": "finance_credit_limit_warning",
    "credit_limit_exceeded": "finance_credit_limit_exceeded",
    "unallocated_payment": "finance_payment_overallocated",
    "missing_fx_rate": "finance_missing_fx_rate",
    "release_blocked": "finance_release_blocked_credit_hold",
    "margin_negative": "finance_negative_margin_warning",
    "invoice_dispute": "finance_invoice_overdue",
}


def _to_read(db: Session, risk: FinanceRiskRecord) -> FinanceRiskRead:
    party_name = None
    shipment_code = None
    if risk.party_id:
        party = db.query(Party).filter(Party.id == risk.party_id).first()
        party_name = party.name if party else None
    if risk.shipment_id:
        shipment = db.query(Shipment).filter(Shipment.id == risk.shipment_id).first()
        shipment_code = shipment.shipment_code if shipment else None
    return FinanceRiskRead(
        id=risk.id,
        party_id=risk.party_id,
        party_name=party_name,
        shipment_id=risk.shipment_id,
        shipment_code=shipment_code,
        risk_type=risk.risk_type,
        severity=risk.severity,
        status=risk.status,
        message=risk.message,
        recommended_action=risk.recommended_action,
        related_invoice_id=risk.related_invoice_id,
        related_payment_id=risk.related_payment_id,
        related_hold_id=risk.related_hold_id,
        created_at=risk.created_at,
        resolved_at=risk.resolved_at,
        resolved_by_user_id=risk.resolved_by_user_id,
        resolved_by_name=risk.resolved_by_name,
    )


def create_finance_risk(
    db: Session,
    *,
    risk_type: str,
    message: str,
    severity: str = "warning",
    party_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    related_invoice_id: Optional[int] = None,
    related_payment_id: Optional[int] = None,
    related_hold_id: Optional[int] = None,
    recommended_action: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    dedupe_key: Optional[str] = None,
    user: Optional[AuthenticatedUser] = None,
) -> Optional[FinanceRiskRecord]:
    """Create a finance risk record. Deduplicates on ``dedupe_key`` when supplied."""
    try:
        if dedupe_key:
            existing = (
                db.query(FinanceRiskRecord)
                .filter(
                    FinanceRiskRecord.dedupe_key == dedupe_key,
                    FinanceRiskRecord.status.in_(["open", "acknowledged"]),
                )
                .first()
            )
            if existing:
                # Refresh fields to keep the most recent context
                existing.message = message
                existing.severity = severity
                existing.recommended_action = recommended_action
                if metadata is not None:
                    existing.metadata_json = metadata
                db.commit()
                db.refresh(existing)
                return existing
        risk = FinanceRiskRecord(
            party_id=party_id,
            shipment_id=shipment_id,
            risk_type=risk_type,
            severity=severity,
            status="open",
            message=message,
            recommended_action=recommended_action,
            related_invoice_id=related_invoice_id,
            related_payment_id=related_payment_id,
            related_hold_id=related_hold_id,
            dedupe_key=dedupe_key,
            metadata_json=metadata,
            created_at=datetime.utcnow(),
        )
        db.add(risk)
        db.commit()
        db.refresh(risk)
    except Exception:
        logger.exception("Unable to create finance risk type=%s", risk_type)
        try:
            db.rollback()
        except Exception:
            pass
        return None

    _emit_notification(db, risk)
    _emit_validation_issue(db, risk)
    return risk


def list_finance_risks(
    db: Session,
    *,
    risk_type: Optional[str] = None,
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    party_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[FinanceRiskRead]:
    query = db.query(FinanceRiskRecord)
    if risk_type:
        query = query.filter(FinanceRiskRecord.risk_type == risk_type)
    if severity:
        query = query.filter(FinanceRiskRecord.severity == severity)
    if status_filter:
        query = query.filter(FinanceRiskRecord.status == status_filter)
    if party_id is not None:
        query = query.filter(FinanceRiskRecord.party_id == party_id)
    if shipment_id is not None:
        query = query.filter(FinanceRiskRecord.shipment_id == shipment_id)
    rows = (
        query.order_by(FinanceRiskRecord.created_at.desc(), FinanceRiskRecord.id.desc())
        .limit(min(max(limit, 1), 500))
        .offset(max(offset, 0))
        .all()
    )
    return [_to_read(db, row) for row in rows]


def resolve_finance_risk(
    db: Session, risk_id: int, user: AuthenticatedUser, notes: Optional[str] = None
) -> FinanceRiskRead:
    risk = db.query(FinanceRiskRecord).filter(FinanceRiskRecord.id == risk_id).first()
    if not risk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finance risk not found")
    risk.status = "resolved"
    risk.resolved_at = datetime.utcnow()
    risk.resolved_by_user_id = user.id
    risk.resolved_by_name = user.name
    if notes:
        metadata = dict(risk.metadata_json or {})
        metadata["resolution_notes"] = notes
        risk.metadata_json = metadata
    db.commit()
    db.refresh(risk)
    return _to_read(db, risk)


def get_open_risks_for_shipment(
    db: Session, shipment_id: int
) -> list[FinanceRiskRecord]:
    return (
        db.query(FinanceRiskRecord)
        .filter(
            FinanceRiskRecord.shipment_id == shipment_id,
            FinanceRiskRecord.status.in_(["open", "acknowledged"]),
        )
        .order_by(FinanceRiskRecord.created_at.desc())
        .all()
    )


def get_open_risks_for_party(
    db: Session, party_id: int
) -> list[FinanceRiskRecord]:
    return (
        db.query(FinanceRiskRecord)
        .filter(
            FinanceRiskRecord.party_id == party_id,
            FinanceRiskRecord.status.in_(["open", "acknowledged"]),
        )
        .order_by(FinanceRiskRecord.created_at.desc())
        .all()
    )


def _emit_notification(db: Session, risk: FinanceRiskRecord) -> None:
    try:
        from app.services.notification_service import create_notification

        priority = SEVERITY_TO_PRIORITY.get(risk.severity, "warning")
        target_role = "ADMIN" if risk.severity == "critical" else "STAFF"
        title = f"Finance: {risk.risk_type.replace('_', ' ').title()}"
        action_url = "/finance"
        if risk.shipment_id:
            action_url = f"/shipments/{risk.shipment_id}"
        create_notification(
            db,
            title=title,
            message=risk.message,
            category="finance",
            priority=priority,
            target_role=target_role,
            entity_type="finance_risk",
            entity_id=risk.id,
            entity_label=risk.message[:120],
            action_url=action_url,
            dedupe_key=risk.dedupe_key,
            source="system",
            metadata={
                "risk_type": risk.risk_type,
                "shipment_id": risk.shipment_id,
                "party_id": risk.party_id,
                "related_invoice_id": risk.related_invoice_id,
                "related_payment_id": risk.related_payment_id,
                "related_hold_id": risk.related_hold_id,
                "date": date.today().isoformat(),
            },
        )
        db.commit()
    except Exception:
        logger.exception(
            "Unable to emit finance notification for risk_type=%s", risk.risk_type
        )
        try:
            db.rollback()
        except Exception:
            pass


def _emit_validation_issue(db: Session, risk: FinanceRiskRecord) -> None:
    rule_key = RISK_TO_RULE_KEY.get(risk.risk_type)
    if not rule_key:
        return
    try:
        existing = (
            db.query(ValidationIssue)
            .filter(
                ValidationIssue.rule_key == rule_key,
                ValidationIssue.entity_type == "finance_risk",
                ValidationIssue.entity_id == risk.id,
                ValidationIssue.status.in_(["open", "acknowledged"]),
            )
            .first()
        )
        if existing:
            return
        issue = ValidationIssue(
            rule_key=rule_key,
            severity=risk.severity,
            status="open",
            message=risk.message,
            entity_type="finance_risk",
            entity_id=risk.id,
            entity_label=risk.message[:120],
            shipment_id=risk.shipment_id,
            metadata_json={
                "risk_type": risk.risk_type,
                "party_id": risk.party_id,
                "related_invoice_id": risk.related_invoice_id,
                "related_payment_id": risk.related_payment_id,
                "related_hold_id": risk.related_hold_id,
            },
            created_at=datetime.utcnow(),
        )
        db.add(issue)
        db.commit()
    except Exception:
        logger.exception(
            "Unable to emit validation issue for finance risk type=%s", risk.risk_type
        )
        try:
            db.rollback()
        except Exception:
            pass
