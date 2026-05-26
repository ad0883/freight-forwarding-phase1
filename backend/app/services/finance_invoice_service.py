"""Phase 14 finance invoice service.

Manages finance_invoice and finance_invoice_line records. Existing charges
remain the source of Phase 3 P&L; invoices created here are an additional
finance-control layer and do not mutate charges.
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.charge import Charge
from app.models.finance_control import (
    FinanceInvoice,
    FinanceInvoiceLine,
    FinancePaymentAllocation,
)
from app.models.party import Party
from app.models.shipment import Shipment
from app.schemas.finance_control import (
    FinanceInvoiceCreate,
    FinanceInvoiceLineRead,
    FinanceInvoiceRead,
    FinanceInvoiceUpdate,
)
from app.services.audit_service import record_audit_log
from app.services.event_service import record_operational_event
from app.services.organization_scope_service import get_user_organization_id
from app.services.validation_issue_service import (
    create_critical_notifications_for_issues,
)


logger = logging.getLogger(__name__)


_OPEN_STATUSES = {"draft", "issued", "partially_paid", "overdue", "disputed", "on_hold"}
_CLOSED_STATUSES = {"paid", "cancelled"}


def _money(value: Optional[Decimal]) -> Decimal:
    return Decimal(value) if value is not None else Decimal("0")


def _line_to_read(line: FinanceInvoiceLine) -> FinanceInvoiceLineRead:
    return FinanceInvoiceLineRead(
        id=line.id,
        invoice_id=line.invoice_id,
        charge_id=line.charge_id,
        description=line.description,
        quantity=line.quantity,
        unit_price=line.unit_price,
        amount=line.amount,
        currency=line.currency,
        tax_code=line.tax_code,
        tax_amount=line.tax_amount,
        created_at=line.created_at,
    )


def _invoice_to_read(db: Session, invoice: FinanceInvoice) -> FinanceInvoiceRead:
    party_name = None
    shipment_code = None
    if invoice.party_id:
        party = db.query(Party).filter(Party.id == invoice.party_id).first()
        party_name = party.name if party else None
    if invoice.shipment_id:
        shipment = db.query(Shipment).filter(Shipment.id == invoice.shipment_id).first()
        shipment_code = shipment.shipment_code if shipment else None
    lines = [_line_to_read(line) for line in invoice.lines]
    return FinanceInvoiceRead(
        id=invoice.id,
        organization_id=invoice.organization_id,
        shipment_id=invoice.shipment_id,
        shipment_code=shipment_code,
        party_id=invoice.party_id,
        party_name=party_name,
        invoice_number=invoice.invoice_number,
        invoice_type=invoice.invoice_type,
        direction=invoice.direction,
        status=invoice.status,
        currency=invoice.currency,
        subtotal_amount=_money(invoice.subtotal_amount),
        tax_amount=_money(invoice.tax_amount),
        total_amount=_money(invoice.total_amount),
        paid_amount=_money(invoice.paid_amount),
        outstanding_amount=_money(invoice.outstanding_amount),
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        credit_days=invoice.credit_days,
        source=invoice.source,
        linked_charge_id=invoice.linked_charge_id,
        created_by_user_id=invoice.created_by_user_id,
        created_by_name=invoice.created_by_name,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
        lines=lines,
        metadata_json=invoice.metadata_json,
    )


def _validate_invoice_payload(payload: FinanceInvoiceCreate) -> None:
    if not payload.lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice must include at least one line",
        )
    for line in payload.lines:
        if line.amount is None:
            line.amount = (Decimal(line.quantity) * Decimal(line.unit_price)).quantize(Decimal("0.01"))
        if Decimal(line.amount) < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice line amount cannot be negative",
            )


def _ensure_party(db: Session, party_id: Optional[int]) -> Optional[Party]:
    if party_id is None:
        return None
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Party not found")
    return party


def _ensure_shipment(db: Session, shipment_id: Optional[int]) -> Optional[Shipment]:
    if shipment_id is None:
        return None
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shipment not found")
    return shipment


def _ensure_charge(db: Session, charge_id: Optional[int]) -> Optional[Charge]:
    if charge_id is None:
        return None
    charge = db.query(Charge).filter(Charge.id == charge_id).first()
    if not charge:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Charge not found")
    return charge


def _compute_due_date(
    invoice_date: Optional[date], credit_days: Optional[int], explicit_due: Optional[date]
) -> Optional[date]:
    if explicit_due:
        return explicit_due
    if invoice_date and credit_days is not None:
        return invoice_date + timedelta(days=int(credit_days))
    return None


def create_invoice(
    db: Session, payload: FinanceInvoiceCreate, user: AuthenticatedUser
) -> FinanceInvoiceRead:
    _validate_invoice_payload(payload)
    _ensure_party(db, payload.party_id)
    _ensure_shipment(db, payload.shipment_id)
    linked_charge = _ensure_charge(db, payload.linked_charge_id)

    currency = payload.currency.upper()
    subtotal = sum((Decimal(line.amount or 0) for line in payload.lines), Decimal("0"))
    tax_total = Decimal("0")
    if payload.tax_amount is not None:
        tax_total = Decimal(payload.tax_amount)
    else:
        tax_total = sum(
            (Decimal(line.tax_amount or 0) for line in payload.lines), Decimal("0")
        )
    total = subtotal + tax_total
    invoice = FinanceInvoice(
        organization_id=get_user_organization_id(user),
        shipment_id=payload.shipment_id,
        party_id=payload.party_id,
        invoice_number=payload.invoice_number,
        invoice_type=payload.invoice_type,
        direction=payload.direction,
        status=payload.status or "draft",
        currency=currency,
        subtotal_amount=subtotal,
        tax_amount=tax_total,
        total_amount=total,
        paid_amount=Decimal("0"),
        outstanding_amount=total,
        invoice_date=payload.invoice_date,
        due_date=_compute_due_date(payload.invoice_date, payload.credit_days, payload.due_date),
        credit_days=payload.credit_days,
        source=payload.source or "manual",
        linked_charge_id=linked_charge.id if linked_charge else None,
        created_by_user_id=user.id,
        created_by_name=user.name,
        metadata_json={"notes": payload.notes} if payload.notes else None,
    )
    db.add(invoice)
    db.flush()
    for line in payload.lines:
        line_amount = Decimal(line.amount or 0)
        db_line = FinanceInvoiceLine(
            invoice_id=invoice.id,
            charge_id=line.charge_id,
            description=line.description,
            quantity=Decimal(line.quantity or 1),
            unit_price=Decimal(line.unit_price or 0),
            amount=line_amount,
            currency=(line.currency or currency).upper(),
            tax_code=line.tax_code,
            tax_amount=Decimal(line.tax_amount) if line.tax_amount is not None else None,
        )
        db.add(db_line)
    db.commit()
    db.refresh(invoice)

    record_audit_log(
        db,
        user,
        "finance.invoice_create",
        "finance_invoice",
        entity_id=invoice.id,
        entity_label=invoice.invoice_number or f"Invoice #{invoice.id}",
        description="Finance invoice created.",
        metadata={
            "shipment_id": invoice.shipment_id,
            "party_id": invoice.party_id,
            "direction": invoice.direction,
            "total_amount": str(invoice.total_amount),
            "currency": invoice.currency,
        },
    )
    record_operational_event(
        db,
        "finance.invoice_created",
        "finance_invoice",
        entity_id=invoice.id,
        entity_label=invoice.invoice_number or f"Invoice #{invoice.id}",
        shipment_id=invoice.shipment_id,
        actor_user=user,
        source="finance",
        new_state={
            "direction": invoice.direction,
            "status": invoice.status,
            "currency": invoice.currency,
            "total_amount": str(invoice.total_amount),
        },
    )
    _check_invoice_validation(db, invoice)
    return _invoice_to_read(db, invoice)


def create_invoice_from_charge(
    db: Session,
    charge_id: int,
    user: AuthenticatedUser,
    *,
    invoice_data: Optional[dict[str, Any]] = None,
) -> FinanceInvoiceRead:
    charge = db.query(Charge).filter(Charge.id == charge_id).first()
    if not charge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Charge not found")
    invoice_data = invoice_data or {}
    direction = "receivable" if charge.direction == "receivable" else "payable"
    invoice_type = (
        "freight_invoice" if charge.charge_type == "ocean_freight" else "customer_invoice"
    )
    if direction == "payable":
        invoice_type = "vendor_invoice"
    payload = FinanceInvoiceCreate(
        shipment_id=charge.shipment_id,
        party_id=charge.party_id,
        invoice_number=invoice_data.get("invoice_number") or charge.invoice_no,
        invoice_type=invoice_data.get("invoice_type") or invoice_type,
        direction=direction,
        status="issued",
        currency=charge.currency,
        invoice_date=invoice_data.get("invoice_date") or charge.date or date.today(),
        due_date=invoice_data.get("due_date"),
        credit_days=invoice_data.get("credit_days"),
        source="charge",
        linked_charge_id=charge.id,
        lines=[
            {
                "description": invoice_data.get("description")
                or f"{charge.charge_type.replace('_', ' ').title()}",
                "quantity": 1,
                "unit_price": Decimal(charge.amount),
                "amount": Decimal(charge.amount),
                "currency": charge.currency,
                "charge_id": charge.id,
            }
        ],
        notes=invoice_data.get("notes") or charge.notes,
    )
    return create_invoice(db, payload, user)


def update_invoice(
    db: Session,
    invoice_id: int,
    payload: FinanceInvoiceUpdate,
    user: AuthenticatedUser,
) -> FinanceInvoiceRead:
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancelled invoices cannot be updated",
        )
    data = payload.model_dump(exclude_unset=True)
    if "currency" in data and data["currency"]:
        data["currency"] = data["currency"].upper()
    notes = data.pop("notes", None)
    for key, value in data.items():
        if value is None and key not in {"due_date", "credit_days", "tax_amount", "party_id"}:
            continue
        if key == "tax_amount" and value is not None:
            invoice.tax_amount = Decimal(value)
            invoice.total_amount = _money(invoice.subtotal_amount) + _money(invoice.tax_amount)
            invoice.outstanding_amount = (
                _money(invoice.total_amount) - _money(invoice.paid_amount)
            )
            continue
        setattr(invoice, key, value)
    if invoice.invoice_date and invoice.credit_days is not None and not data.get("due_date"):
        invoice.due_date = invoice.invoice_date + timedelta(days=int(invoice.credit_days))
    if notes is not None:
        metadata = dict(invoice.metadata_json or {})
        metadata["notes"] = notes
        invoice.metadata_json = metadata
    invoice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(invoice)
    record_audit_log(
        db,
        user,
        "finance.invoice_update",
        "finance_invoice",
        entity_id=invoice.id,
        entity_label=invoice.invoice_number or f"Invoice #{invoice.id}",
        description="Finance invoice updated.",
        metadata={"fields_changed": sorted(data.keys())},
    )
    record_operational_event(
        db,
        "finance.invoice_updated",
        "finance_invoice",
        entity_id=invoice.id,
        entity_label=invoice.invoice_number or f"Invoice #{invoice.id}",
        shipment_id=invoice.shipment_id,
        actor_user=user,
        source="finance",
    )
    return _invoice_to_read(db, invoice)


def cancel_invoice(
    db: Session, invoice_id: int, user: AuthenticatedUser, reason: Optional[str] = None
) -> FinanceInvoiceRead:
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status == "cancelled":
        return _invoice_to_read(db, invoice)
    invoice.status = "cancelled"
    invoice.outstanding_amount = Decimal("0")
    metadata = dict(invoice.metadata_json or {})
    if reason:
        metadata["cancel_reason"] = reason
    invoice.metadata_json = metadata
    invoice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(invoice)
    record_audit_log(
        db,
        user,
        "finance.invoice_cancel",
        "finance_invoice",
        entity_id=invoice.id,
        entity_label=invoice.invoice_number or f"Invoice #{invoice.id}",
        description="Finance invoice cancelled.",
        metadata={"reason": reason},
    )
    record_operational_event(
        db,
        "finance.invoice_cancelled",
        "finance_invoice",
        entity_id=invoice.id,
        entity_label=invoice.invoice_number or f"Invoice #{invoice.id}",
        shipment_id=invoice.shipment_id,
        actor_user=user,
        source="finance",
        metadata={"reason": reason},
    )
    return _invoice_to_read(db, invoice)


def list_invoices(
    db: Session,
    *,
    direction: Optional[str] = None,
    status_filter: Optional[str] = None,
    party_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    overdue_only: bool = False,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[FinanceInvoiceRead]:
    query = db.query(FinanceInvoice)
    if direction:
        query = query.filter(FinanceInvoice.direction == direction)
    if status_filter:
        query = query.filter(FinanceInvoice.status == status_filter)
    if party_id is not None:
        query = query.filter(FinanceInvoice.party_id == party_id)
    if shipment_id is not None:
        query = query.filter(FinanceInvoice.shipment_id == shipment_id)
    if overdue_only:
        query = query.filter(
            FinanceInvoice.due_date.isnot(None),
            FinanceInvoice.due_date < date.today(),
            FinanceInvoice.status.in_(list(_OPEN_STATUSES)),
        )
    if search:
        pattern = f"%{search}%"
        query = query.filter(FinanceInvoice.invoice_number.ilike(pattern))
    rows = (
        query.order_by(FinanceInvoice.created_at.desc(), FinanceInvoice.id.desc())
        .limit(min(max(limit, 1), 500))
        .offset(max(offset, 0))
        .all()
    )
    return [_invoice_to_read(db, row) for row in rows]


def get_invoice(db: Session, invoice_id: int) -> FinanceInvoiceRead:
    invoice = _get_invoice_or_404(db, invoice_id)
    return _invoice_to_read(db, invoice)


def recalculate_invoice_totals(db: Session, invoice_id: int) -> FinanceInvoice:
    """Recompute paid/outstanding from active allocations."""
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status == "cancelled":
        invoice.outstanding_amount = Decimal("0")
        db.commit()
        return invoice
    paid = (
        db.query(FinancePaymentAllocation)
        .filter(FinancePaymentAllocation.invoice_id == invoice_id)
        .all()
    )
    paid_amount = Decimal("0")
    for allocation in paid:
        # Allocations from cancelled/reversed payments are excluded via service rules
        if allocation.payment and allocation.payment.status in {"cancelled", "reversed"}:
            continue
        paid_amount += Decimal(allocation.allocated_amount or 0)
    invoice.paid_amount = paid_amount
    total = _money(invoice.total_amount)
    outstanding = total - paid_amount
    if outstanding < Decimal("0"):
        outstanding = Decimal("0")
    invoice.outstanding_amount = outstanding
    if invoice.status not in {"cancelled", "disputed", "on_hold"}:
        if outstanding == Decimal("0") and total > Decimal("0"):
            invoice.status = "paid"
        elif paid_amount > Decimal("0"):
            invoice.status = "partially_paid"
        elif (
            invoice.due_date
            and invoice.due_date < date.today()
            and invoice.status in {"issued", "draft"}
        ):
            invoice.status = "overdue"
    invoice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(invoice)
    return invoice


def mark_overdue_invoices(db: Session) -> int:
    """Flip due-but-unpaid invoices to overdue. Caller commits."""
    today = date.today()
    rows = (
        db.query(FinanceInvoice)
        .filter(
            FinanceInvoice.status.in_(["issued", "partially_paid"]),
            FinanceInvoice.due_date.isnot(None),
            FinanceInvoice.due_date < today,
        )
        .all()
    )
    updated = 0
    for invoice in rows:
        invoice.status = "overdue"
        invoice.updated_at = datetime.utcnow()
        updated += 1
    if updated:
        db.commit()
    return updated


def _get_invoice_or_404(db: Session, invoice_id: int) -> FinanceInvoice:
    invoice = db.query(FinanceInvoice).filter(FinanceInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def _check_invoice_validation(db: Session, invoice: FinanceInvoice) -> None:
    """Emit validation issues for risky invoice signals (best effort)."""
    try:
        from app.models.validation_issue import ValidationIssue

        issues: list[ValidationIssue] = []
        if invoice.party_id is None:
            issues.append(
                ValidationIssue(
                    rule_key="finance_invoice_missing_party",
                    severity="warning",
                    status="open",
                    message=f"Invoice {invoice.invoice_number or invoice.id} created without a party.",
                    entity_type="finance_invoice",
                    entity_id=invoice.id,
                    entity_label=invoice.invoice_number,
                    shipment_id=invoice.shipment_id,
                    metadata_json={"direction": invoice.direction},
                    created_at=datetime.utcnow(),
                )
            )
        if invoice.total_amount is not None and Decimal(invoice.total_amount) < 0:
            issues.append(
                ValidationIssue(
                    rule_key="finance_invoice_negative_amount",
                    severity="warning",
                    status="open",
                    message=f"Invoice {invoice.invoice_number or invoice.id} has negative total.",
                    entity_type="finance_invoice",
                    entity_id=invoice.id,
                    entity_label=invoice.invoice_number,
                    shipment_id=invoice.shipment_id,
                    created_at=datetime.utcnow(),
                )
            )
        for issue in issues:
            db.add(issue)
        if issues:
            db.commit()
            create_critical_notifications_for_issues(db, issues)
    except Exception:
        logger.exception("Unable to emit invoice validation issues")
        try:
            db.rollback()
        except Exception:
            pass
