"""Phase 14 credit control + party credit profiles + holds.

Tracks credit limit, credit days, party outstanding, and emits credit holds
when overdue/limit thresholds are exceeded. Holds are advisory inside the
app; they never trigger external action.
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.finance_control import (
    CreditHoldRecord,
    FinanceInvoice,
    FinancePayment,
    PartyCreditProfile,
)
from app.models.party import Party
from app.models.shipment import Shipment
from app.schemas.finance_control import (
    CreditHoldRead,
    PartyCreditProfileRead,
    PartyCreditProfileUpdate,
)
from app.services.organization_scope_service import get_user_organization_id


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Credit profile helpers
# ---------------------------------------------------------------------------


def _profile_to_read(
    db: Session, profile: PartyCreditProfile, party: Optional[Party] = None
) -> PartyCreditProfileRead:
    if party is None:
        party = db.query(Party).filter(Party.id == profile.party_id).first()
    outstanding = calculate_party_outstanding(db, profile.party_id, direction="receivable")
    overdue = calculate_party_outstanding(
        db, profile.party_id, direction="receivable", overdue_only=True
    )
    available = (
        Decimal(profile.credit_limit) - outstanding if profile.credit_limit else None
    )
    active_holds = (
        db.query(CreditHoldRecord)
        .filter(
            CreditHoldRecord.party_id == profile.party_id,
            CreditHoldRecord.status == "active",
        )
        .count()
    )
    return PartyCreditProfileRead(
        id=profile.id,
        organization_id=profile.organization_id,
        party_id=profile.party_id,
        party_name=party.name if party else None,
        credit_limit=profile.credit_limit,
        credit_currency=profile.credit_currency,
        credit_days=profile.credit_days,
        is_credit_allowed=bool(profile.is_credit_allowed),
        hold_on_overdue=bool(profile.hold_on_overdue),
        hold_on_limit_exceeded=bool(profile.hold_on_limit_exceeded),
        warning_threshold_percent=profile.warning_threshold_percent,
        status=profile.status,
        current_outstanding=outstanding,
        overdue_amount=overdue,
        available_credit=available,
        active_holds=active_holds,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def get_or_create_credit_profile(
    db: Session, party_id: int, user: Optional[AuthenticatedUser] = None
) -> PartyCreditProfile:
    profile = (
        db.query(PartyCreditProfile)
        .filter(PartyCreditProfile.party_id == party_id)
        .first()
    )
    if profile:
        return profile
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Party not found")
    profile = PartyCreditProfile(
        organization_id=get_user_organization_id(user) if user else None,
        party_id=party_id,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_credit_profile_read(
    db: Session, party_id: int, user: Optional[AuthenticatedUser] = None
) -> PartyCreditProfileRead:
    profile = get_or_create_credit_profile(db, party_id, user)
    return _profile_to_read(db, profile)


def list_credit_profiles(
    db: Session,
    *,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
) -> list[PartyCreditProfileRead]:
    query = db.query(PartyCreditProfile, Party).join(
        Party, Party.id == PartyCreditProfile.party_id
    )
    if status_filter:
        query = query.filter(PartyCreditProfile.status == status_filter)
    if search:
        pattern = f"%{search}%"
        query = query.filter(Party.name.ilike(pattern))
    rows = (
        query.order_by(Party.name.asc())
        .limit(min(max(limit, 1), 500))
        .all()
    )
    return [_profile_to_read(db, profile, party) for profile, party in rows]


def update_credit_profile(
    db: Session,
    party_id: int,
    payload: PartyCreditProfileUpdate,
    user: AuthenticatedUser,
) -> PartyCreditProfileRead:
    profile = get_or_create_credit_profile(db, party_id, user)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if value is None:
            continue
        if key == "credit_currency" and isinstance(value, str):
            value = value.upper()
        setattr(profile, key, value)
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return _profile_to_read(db, profile)


# ---------------------------------------------------------------------------
# Outstanding calculation
# ---------------------------------------------------------------------------


_OPEN_INVOICE_STATUSES = ("draft", "issued", "partially_paid", "overdue", "disputed", "on_hold")


def calculate_party_outstanding(
    db: Session,
    party_id: int,
    direction: str = "receivable",
    *,
    overdue_only: bool = False,
    as_of_date: Optional[date] = None,
) -> Decimal:
    today = as_of_date or date.today()
    query = db.query(FinanceInvoice).filter(
        FinanceInvoice.party_id == party_id,
        FinanceInvoice.direction == direction,
        FinanceInvoice.status.in_(_OPEN_INVOICE_STATUSES),
    )
    if overdue_only:
        query = query.filter(
            FinanceInvoice.due_date.isnot(None),
            FinanceInvoice.due_date < today,
        )
    total = Decimal("0")
    for invoice in query.all():
        outstanding = invoice.outstanding_amount or Decimal("0")
        total += Decimal(outstanding)
    return total


# ---------------------------------------------------------------------------
# Hold helpers
# ---------------------------------------------------------------------------


def _hold_to_read(db: Session, hold: CreditHoldRecord) -> CreditHoldRead:
    party_name = None
    shipment_code = None
    if hold.party_id:
        party = db.query(Party).filter(Party.id == hold.party_id).first()
        party_name = party.name if party else None
    if hold.shipment_id:
        shipment = db.query(Shipment).filter(Shipment.id == hold.shipment_id).first()
        shipment_code = shipment.shipment_code if shipment else None
    return CreditHoldRead(
        id=hold.id,
        party_id=hold.party_id,
        party_name=party_name,
        shipment_id=hold.shipment_id,
        shipment_code=shipment_code,
        hold_type=hold.hold_type,
        severity=hold.severity,
        status=hold.status,
        reason=hold.reason,
        trigger_source=hold.trigger_source,
        current_outstanding=hold.current_outstanding,
        credit_limit=hold.credit_limit,
        overdue_amount=hold.overdue_amount,
        blocked_action=hold.blocked_action,
        created_at=hold.created_at,
        created_by_user_id=hold.created_by_user_id,
        created_by_name=hold.created_by_name,
        resolved_at=hold.resolved_at,
        resolved_by_user_id=hold.resolved_by_user_id,
        resolved_by_name=hold.resolved_by_name,
        resolution_notes=hold.resolution_notes,
    )


def list_credit_holds(
    db: Session,
    *,
    status_filter: Optional[str] = None,
    party_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    hold_type: Optional[str] = None,
    blocked_action: Optional[str] = None,
    limit: int = 100,
) -> list[CreditHoldRead]:
    query = db.query(CreditHoldRecord)
    if status_filter:
        query = query.filter(CreditHoldRecord.status == status_filter)
    if party_id is not None:
        query = query.filter(CreditHoldRecord.party_id == party_id)
    if shipment_id is not None:
        query = query.filter(CreditHoldRecord.shipment_id == shipment_id)
    if hold_type:
        query = query.filter(CreditHoldRecord.hold_type == hold_type)
    if blocked_action:
        query = query.filter(CreditHoldRecord.blocked_action == blocked_action)
    rows = (
        query.order_by(CreditHoldRecord.created_at.desc(), CreditHoldRecord.id.desc())
        .limit(min(max(limit, 1), 500))
        .all()
    )
    return [_hold_to_read(db, row) for row in rows]


def get_active_holds_for_shipment(
    db: Session, shipment_id: int
) -> list[CreditHoldRecord]:
    return (
        db.query(CreditHoldRecord)
        .filter(
            CreditHoldRecord.shipment_id == shipment_id,
            CreditHoldRecord.status == "active",
        )
        .all()
    )


def get_active_holds_for_party(
    db: Session, party_id: int
) -> list[CreditHoldRecord]:
    return (
        db.query(CreditHoldRecord)
        .filter(
            CreditHoldRecord.party_id == party_id,
            CreditHoldRecord.status == "active",
        )
        .all()
    )


def create_or_refresh_credit_hold(
    db: Session,
    *,
    hold_type: str,
    reason: str,
    party_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    severity: str = "warning",
    trigger_source: str = "system",
    blocked_action: Optional[str] = None,
    current_outstanding: Optional[Decimal] = None,
    credit_limit: Optional[Decimal] = None,
    overdue_amount: Optional[Decimal] = None,
    user: Optional[AuthenticatedUser] = None,
) -> CreditHoldRecord:
    """Create a new active hold or refresh an existing matching one."""
    query = db.query(CreditHoldRecord).filter(
        CreditHoldRecord.hold_type == hold_type,
        CreditHoldRecord.status == "active",
    )
    if party_id is not None:
        query = query.filter(CreditHoldRecord.party_id == party_id)
    else:
        query = query.filter(CreditHoldRecord.party_id.is_(None))
    if shipment_id is not None:
        query = query.filter(CreditHoldRecord.shipment_id == shipment_id)
    else:
        query = query.filter(CreditHoldRecord.shipment_id.is_(None))
    if blocked_action is not None:
        query = query.filter(CreditHoldRecord.blocked_action == blocked_action)
    existing = query.first()
    if existing:
        existing.reason = reason
        existing.severity = severity
        existing.current_outstanding = current_outstanding
        existing.credit_limit = credit_limit
        existing.overdue_amount = overdue_amount
        db.commit()
        db.refresh(existing)
        return existing
    hold = CreditHoldRecord(
        party_id=party_id,
        shipment_id=shipment_id,
        hold_type=hold_type,
        severity=severity,
        status="active",
        reason=reason,
        trigger_source=trigger_source,
        blocked_action=blocked_action,
        current_outstanding=current_outstanding,
        credit_limit=credit_limit,
        overdue_amount=overdue_amount,
        created_by_user_id=user.id if user else None,
        created_by_name=user.name if user else None,
        created_at=datetime.utcnow(),
    )
    db.add(hold)
    db.commit()
    db.refresh(hold)
    return hold


def resolve_credit_hold(
    db: Session, hold_id: int, user: AuthenticatedUser, notes: Optional[str] = None
) -> CreditHoldRead:
    return _close_hold(db, hold_id, user, "resolved", notes)


def waive_credit_hold(
    db: Session, hold_id: int, user: AuthenticatedUser, notes: Optional[str] = None
) -> CreditHoldRead:
    return _close_hold(db, hold_id, user, "waived", notes)


def _close_hold(
    db: Session,
    hold_id: int,
    user: AuthenticatedUser,
    new_status: str,
    notes: Optional[str],
) -> CreditHoldRead:
    hold = db.query(CreditHoldRecord).filter(CreditHoldRecord.id == hold_id).first()
    if not hold:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit hold not found")
    hold.status = new_status
    hold.resolved_at = datetime.utcnow()
    hold.resolved_by_user_id = user.id
    hold.resolved_by_name = user.name
    if notes:
        hold.resolution_notes = notes
    db.commit()
    db.refresh(hold)
    return _hold_to_read(db, hold)


# ---------------------------------------------------------------------------
# Risk evaluation
# ---------------------------------------------------------------------------


def evaluate_credit_risk(
    db: Session,
    party_id: int,
    shipment_id: Optional[int] = None,
    user: Optional[AuthenticatedUser] = None,
) -> dict[str, object]:
    """Evaluate credit risk for a party and emit holds/risks if needed.

    Returns a summary dict.
    """
    from app.services.finance_risk_service import create_finance_risk

    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Party not found")
    profile = get_or_create_credit_profile(db, party_id, user)
    outstanding = calculate_party_outstanding(db, party_id, direction="receivable")
    overdue = calculate_party_outstanding(
        db, party_id, direction="receivable", overdue_only=True
    )

    holds_created: list[CreditHoldRecord] = []
    risks_created: list[str] = []

    party_label = party.name or f"Party #{party_id}"

    if profile.hold_on_limit_exceeded and profile.credit_limit and outstanding > Decimal(profile.credit_limit):
        hold = create_or_refresh_credit_hold(
            db,
            hold_type="credit_limit_exceeded",
            reason=(
                f"{party_label} outstanding {profile.credit_currency} {outstanding} "
                f"exceeds credit limit {profile.credit_currency} {profile.credit_limit}."
            ),
            party_id=party_id,
            shipment_id=shipment_id,
            severity="critical",
            current_outstanding=outstanding,
            credit_limit=profile.credit_limit,
            overdue_amount=overdue,
            user=user,
        )
        holds_created.append(hold)
        create_finance_risk(
            db,
            risk_type="credit_limit_exceeded",
            severity="critical",
            message=(
                f"{party_label} has exceeded credit limit "
                f"({profile.credit_currency} {outstanding} of {profile.credit_limit})."
            ),
            party_id=party_id,
            shipment_id=shipment_id,
            related_hold_id=hold.id,
            recommended_action="Review outstanding receivables and consider collection follow-up.",
            dedupe_key=f"finance_credit_limit_exceeded:{party_id}",
        )
        risks_created.append("credit_limit_exceeded")
    elif profile.credit_limit and profile.warning_threshold_percent:
        threshold = Decimal(profile.credit_limit) * Decimal(profile.warning_threshold_percent) / Decimal(100)
        if threshold and outstanding >= threshold:
            create_finance_risk(
                db,
                risk_type="credit_limit_warning",
                severity="warning",
                message=(
                    f"{party_label} outstanding {profile.credit_currency} {outstanding} is "
                    f"≥ {profile.warning_threshold_percent}% of credit limit "
                    f"{profile.credit_currency} {profile.credit_limit}."
                ),
                party_id=party_id,
                shipment_id=shipment_id,
                recommended_action="Monitor outstanding before extending more credit.",
                dedupe_key=f"finance_credit_limit_warning:{party_id}:{date.today().isoformat()}",
            )
            risks_created.append("credit_limit_warning")

    if profile.hold_on_overdue and overdue > Decimal("0"):
        hold = create_or_refresh_credit_hold(
            db,
            hold_type="overdue_payment",
            reason=(
                f"{party_label} has overdue receivables of "
                f"{profile.credit_currency} {overdue}."
            ),
            party_id=party_id,
            shipment_id=shipment_id,
            severity="warning",
            current_outstanding=outstanding,
            credit_limit=profile.credit_limit,
            overdue_amount=overdue,
            user=user,
        )
        holds_created.append(hold)
        create_finance_risk(
            db,
            risk_type="receivable_overdue",
            severity="warning",
            message=(
                f"{party_label} has overdue receivables totaling "
                f"{profile.credit_currency} {overdue}."
            ),
            party_id=party_id,
            shipment_id=shipment_id,
            related_hold_id=hold.id,
            recommended_action="Initiate collection follow-up.",
            dedupe_key=f"finance_receivable_overdue:{party_id}",
        )
        risks_created.append("receivable_overdue")

    return {
        "party_id": party_id,
        "outstanding": outstanding,
        "overdue": overdue,
        "credit_limit": profile.credit_limit,
        "currency": profile.credit_currency,
        "holds_created": [hold.id for hold in holds_created],
        "risks_created": risks_created,
    }


def refresh_party_finance_risks(
    db: Session, party_id: int, user: Optional[AuthenticatedUser] = None
) -> dict[str, object]:
    return evaluate_credit_risk(db, party_id, shipment_id=None, user=user)


def refresh_shipment_finance_risks(
    db: Session, shipment_id: int, user: Optional[AuthenticatedUser] = None
) -> dict[str, object]:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    party_id = shipment.exporter_id or shipment.importer_id
    summary: dict[str, object] = {
        "shipment_id": shipment_id,
        "party_id": party_id,
        "risks_created": [],
        "holds_created": [],
    }
    if party_id:
        evaluation = evaluate_credit_risk(db, party_id, shipment_id=shipment_id, user=user)
        summary.update(evaluation)
    # Negative margin signal
    try:
        from app.services.finance_service import calculate_shipment_pnl

        pnl = calculate_shipment_pnl(db, shipment_id)
        if pnl and pnl.net_profit is not None and Decimal(pnl.net_profit) < Decimal("0"):
            from app.services.finance_risk_service import create_finance_risk

            create_finance_risk(
                db,
                risk_type="margin_negative",
                severity="warning",
                message=(
                    f"Shipment {shipment.shipment_code} has negative P&L "
                    f"{pnl.currency} {pnl.net_profit}."
                ),
                shipment_id=shipment_id,
                recommended_action="Review charges and finalise expected receivables.",
                dedupe_key=f"finance_negative_margin:{shipment_id}",
            )
            summary.setdefault("risks_created", []).append("margin_negative")  # type: ignore[union-attr]
    except Exception:
        logger.exception("margin check failed for shipment %s", shipment_id)
    return summary


def expose_credit_hold_read(db: Session, hold: CreditHoldRecord) -> CreditHoldRead:
    return _hold_to_read(db, hold)
