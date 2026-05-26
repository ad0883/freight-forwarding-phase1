"""Phase 14 finance payment service.

Internal payments and allocations only. No bank/payment-gateway integration.
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.charge import Charge
from app.models.finance_control import (
    FinanceInvoice,
    FinancePayment,
    FinancePaymentAllocation,
)
from app.models.party import Party
from app.models.shipment import Shipment
from app.schemas.finance_control import (
    FinancePaymentAllocateRequest,
    FinancePaymentAllocationItem,
    FinancePaymentAllocationRead,
    FinancePaymentCreate,
    FinancePaymentRead,
)
from app.services.audit_service import record_audit_log
from app.services.event_service import record_operational_event
from app.services.finance_invoice_service import recalculate_invoice_totals
from app.services.organization_scope_service import get_user_organization_id


logger = logging.getLogger(__name__)


_PAYMENT_TYPE_TO_DIRECTION = {
    "receipt": "inbound",
    "advance": "inbound",
    "vendor_payment": "outbound",
    "refund": "outbound",
    "adjustment": "inbound",
    "other": "inbound",
}


def _money(value: Optional[Decimal]) -> Decimal:
    return Decimal(value) if value is not None else Decimal("0")


def _allocation_to_read(allocation: FinancePaymentAllocation) -> FinancePaymentAllocationRead:
    return FinancePaymentAllocationRead(
        id=allocation.id,
        payment_id=allocation.payment_id,
        invoice_id=allocation.invoice_id,
        charge_id=allocation.charge_id,
        shipment_id=allocation.shipment_id,
        allocated_amount=_money(allocation.allocated_amount),
        currency=allocation.currency,
        allocated_at=allocation.allocated_at,
        allocated_by_user_id=allocation.allocated_by_user_id,
        allocated_by_name=allocation.allocated_by_name,
        notes=allocation.notes,
    )


def _payment_to_read(db: Session, payment: FinancePayment) -> FinancePaymentRead:
    party_name = None
    if payment.party_id:
        party = db.query(Party).filter(Party.id == payment.party_id).first()
        party_name = party.name if party else None
    allocations = [_allocation_to_read(allocation) for allocation in payment.allocations]
    return FinancePaymentRead(
        id=payment.id,
        organization_id=payment.organization_id,
        party_id=payment.party_id,
        party_name=party_name,
        payment_type=payment.payment_type,
        direction=payment.direction,
        status=payment.status,
        currency=payment.currency,
        amount=_money(payment.amount),
        unallocated_amount=_money(payment.unallocated_amount),
        payment_date=payment.payment_date,
        reference_number=payment.reference_number,
        method=payment.method,
        bank_name=payment.bank_name,
        notes=payment.notes,
        created_by_user_id=payment.created_by_user_id,
        created_by_name=payment.created_by_name,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
        allocations=allocations,
    )


def create_payment(
    db: Session, payload: FinancePaymentCreate, user: AuthenticatedUser
) -> FinancePaymentRead:
    if payload.party_id is not None:
        party = db.query(Party).filter(Party.id == payload.party_id).first()
        if not party:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Party not found")
    direction = payload.direction or _PAYMENT_TYPE_TO_DIRECTION.get(payload.payment_type, "inbound")
    payment = FinancePayment(
        organization_id=get_user_organization_id(user),
        party_id=payload.party_id,
        payment_type=payload.payment_type,
        direction=direction,
        status=payload.status or "posted",
        currency=payload.currency.upper(),
        amount=Decimal(payload.amount),
        unallocated_amount=Decimal(payload.amount),
        payment_date=payload.payment_date,
        reference_number=payload.reference_number,
        method=payload.method,
        bank_name=payload.bank_name,
        notes=payload.notes,
        created_by_user_id=user.id,
        created_by_name=user.name,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    record_audit_log(
        db,
        user,
        "finance.payment_create",
        "finance_payment",
        entity_id=payment.id,
        entity_label=payment.reference_number or f"Payment #{payment.id}",
        description="Finance payment created.",
        metadata={
            "party_id": payment.party_id,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "direction": payment.direction,
            "type": payment.payment_type,
        },
    )
    record_operational_event(
        db,
        "finance.payment_created",
        "finance_payment",
        entity_id=payment.id,
        entity_label=payment.reference_number or f"Payment #{payment.id}",
        actor_user=user,
        source="finance",
        new_state={
            "amount": str(payment.amount),
            "currency": payment.currency,
            "direction": payment.direction,
            "status": payment.status,
        },
    )
    return _payment_to_read(db, payment)


def allocate_payment(
    db: Session,
    payment_id: int,
    payload: FinancePaymentAllocateRequest,
    user: AuthenticatedUser,
) -> FinancePaymentRead:
    payment = _get_payment_or_404(db, payment_id)
    if payment.status in {"cancelled", "reversed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot allocate from a {payment.status} payment",
        )
    requested_total = sum(
        (Decimal(item.allocated_amount) for item in payload.allocations), Decimal("0")
    )
    if requested_total <= Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total allocated amount must be greater than zero",
        )
    if requested_total > _money(payment.unallocated_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Allocation {requested_total} exceeds unallocated amount "
                f"{payment.unallocated_amount}"
            ),
        )
    invoices_to_recalc: set[int] = set()
    for item in payload.allocations:
        invoice = _validate_allocation_target(db, payment, item)
        allocation = FinancePaymentAllocation(
            payment_id=payment.id,
            invoice_id=item.invoice_id,
            charge_id=item.charge_id,
            shipment_id=item.shipment_id or (invoice.shipment_id if invoice else None),
            allocated_amount=Decimal(item.allocated_amount),
            currency=payment.currency,
            allocated_at=datetime.utcnow(),
            allocated_by_user_id=user.id,
            allocated_by_name=user.name,
            notes=item.notes,
        )
        db.add(allocation)
        if item.invoice_id:
            invoices_to_recalc.add(item.invoice_id)
    payment.unallocated_amount = _money(payment.unallocated_amount) - requested_total
    if payment.unallocated_amount <= Decimal("0"):
        payment.unallocated_amount = Decimal("0")
        payment.status = "allocated"
    else:
        payment.status = "partially_allocated"
    payment.updated_at = datetime.utcnow()
    db.commit()
    for invoice_id in invoices_to_recalc:
        recalculate_invoice_totals(db, invoice_id)
    db.refresh(payment)
    record_audit_log(
        db,
        user,
        "finance.payment_allocate",
        "finance_payment",
        entity_id=payment.id,
        entity_label=payment.reference_number or f"Payment #{payment.id}",
        description="Payment allocated.",
        metadata={
            "allocation_count": len(payload.allocations),
            "allocated_amount": str(requested_total),
            "invoices": list(invoices_to_recalc),
        },
    )
    record_operational_event(
        db,
        "finance.payment_allocated",
        "finance_payment",
        entity_id=payment.id,
        entity_label=payment.reference_number or f"Payment #{payment.id}",
        actor_user=user,
        source="finance",
        metadata={
            "allocated_amount": str(requested_total),
            "invoice_ids": list(invoices_to_recalc),
        },
    )
    return _payment_to_read(db, payment)


def cancel_payment(
    db: Session,
    payment_id: int,
    user: AuthenticatedUser,
    reason: Optional[str] = None,
) -> FinancePaymentRead:
    payment = _get_payment_or_404(db, payment_id)
    if payment.status in {"cancelled", "reversed"}:
        return _payment_to_read(db, payment)
    affected_invoices = {
        allocation.invoice_id for allocation in payment.allocations if allocation.invoice_id
    }
    payment.status = "cancelled"
    payment.unallocated_amount = Decimal("0")
    metadata = dict(payment.notes or "")  # noqa: F841 - keep raw notes
    if reason:
        payment.notes = f"{(payment.notes or '').strip()}\nCancellation reason: {reason}".strip()
    payment.updated_at = datetime.utcnow()
    db.commit()
    for invoice_id in affected_invoices:
        try:
            recalculate_invoice_totals(db, invoice_id)
        except HTTPException:
            continue
    db.refresh(payment)
    record_audit_log(
        db,
        user,
        "finance.payment_cancel",
        "finance_payment",
        entity_id=payment.id,
        entity_label=payment.reference_number or f"Payment #{payment.id}",
        description="Payment cancelled.",
        metadata={"reason": reason, "invoice_ids": list(affected_invoices)},
    )
    record_operational_event(
        db,
        "finance.payment_cancelled",
        "finance_payment",
        entity_id=payment.id,
        entity_label=payment.reference_number or f"Payment #{payment.id}",
        actor_user=user,
        source="finance",
        metadata={"reason": reason},
    )
    return _payment_to_read(db, payment)


def list_payments(
    db: Session,
    *,
    direction: Optional[str] = None,
    status_filter: Optional[str] = None,
    party_id: Optional[int] = None,
    payment_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[FinancePaymentRead]:
    query = db.query(FinancePayment)
    if direction:
        query = query.filter(FinancePayment.direction == direction)
    if status_filter:
        query = query.filter(FinancePayment.status == status_filter)
    if party_id is not None:
        query = query.filter(FinancePayment.party_id == party_id)
    if payment_type:
        query = query.filter(FinancePayment.payment_type == payment_type)
    rows = (
        query.order_by(FinancePayment.created_at.desc(), FinancePayment.id.desc())
        .limit(min(max(limit, 1), 500))
        .offset(max(offset, 0))
        .all()
    )
    return [_payment_to_read(db, row) for row in rows]


def get_payment(db: Session, payment_id: int) -> FinancePaymentRead:
    payment = _get_payment_or_404(db, payment_id)
    return _payment_to_read(db, payment)


def _get_payment_or_404(db: Session, payment_id: int) -> FinancePayment:
    payment = db.query(FinancePayment).filter(FinancePayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


def _validate_allocation_target(
    db: Session, payment: FinancePayment, item: FinancePaymentAllocationItem
) -> Optional[FinanceInvoice]:
    invoice: Optional[FinanceInvoice] = None
    if item.invoice_id is not None:
        invoice = (
            db.query(FinanceInvoice)
            .filter(FinanceInvoice.id == item.invoice_id)
            .first()
        )
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invoice {item.invoice_id} not found",
            )
        if invoice.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot allocate to a cancelled invoice",
            )
        if invoice.currency != payment.currency:
            from app.services.finance_risk_service import create_finance_risk

            create_finance_risk(
                db,
                risk_type="missing_fx_rate",
                severity="warning",
                message=(
                    f"Payment {payment.id} currency {payment.currency} differs from "
                    f"invoice {invoice.id} currency {invoice.currency}."
                ),
                related_invoice_id=invoice.id,
                related_payment_id=payment.id,
                recommended_action="Record an FX rate before allocating in mixed currencies.",
                dedupe_key=f"finance_currency_mismatch:{payment.id}:{invoice.id}",
            )
        new_paid = _money(invoice.paid_amount) + Decimal(item.allocated_amount)
        if new_paid > _money(invoice.total_amount) + Decimal("0.01"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Allocation would exceed invoice total "
                    f"({new_paid} > {invoice.total_amount})"
                ),
            )
    if item.charge_id is not None:
        charge = db.query(Charge).filter(Charge.id == item.charge_id).first()
        if not charge:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Charge {item.charge_id} not found",
            )
    if item.shipment_id is not None:
        shipment = db.query(Shipment).filter(Shipment.id == item.shipment_id).first()
        if not shipment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Shipment {item.shipment_id} not found",
            )
    return invoice
