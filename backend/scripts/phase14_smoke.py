"""Phase 14 smoke checks.

Runs a end-to-end light verification of finance invoice/payment/credit/aging
services. Cleans up after itself.

Run from backend/ with the project venv active:

    python scripts/phase14_smoke.py
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import Session  # noqa: E402

from app.api.deps import AuthenticatedUser  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.finance_control import (  # noqa: E402
    CreditHoldRecord,
    FinanceInvoice,
    FinancePayment,
    FinanceRiskRecord,
    PartyCreditProfile,
)
from app.models.party import Party  # noqa: E402
from app.models.shipment import Shipment  # noqa: E402
from app.models.user import User  # noqa: E402
from app.schemas.finance_control import (  # noqa: E402
    FinanceInvoiceCreate,
    FinanceInvoiceLineCreate,
    FinancePaymentAllocateRequest,
    FinancePaymentAllocationItem,
    FinancePaymentCreate,
    FxRateCreate,
    PartyCreditProfileUpdate,
)
from app.services import (  # noqa: E402
    credit_control_service,
    finance_aging_service,
    finance_invoice_service,
    finance_overview_service,
    fx_service,
    payment_service,
    release_control_service,
)


def admin_user(db: Session) -> AuthenticatedUser:
    user = (
        db.query(User)
        .filter(User.role == "ADMIN", User.is_active.is_(True))
        .order_by(User.id.asc())
        .first()
    )
    if not user:
        raise RuntimeError("No active admin user found")
    return AuthenticatedUser(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        organization_id=user.organization_id,
        organization_name=user.organization_name,
    )


def create_demo_party(db: Session) -> Party:
    name = "Phase14 Smoke Customer"
    party = db.query(Party).filter(Party.name == name).first()
    if party:
        return party
    party = Party(name=name, type="importer", is_active=True, country="IN")
    db.add(party)
    db.commit()
    db.refresh(party)
    return party


def create_demo_shipment(db: Session, party_id: int, user: AuthenticatedUser) -> Shipment:
    code = "FF-IMP-2099-9001"
    shipment = db.query(Shipment).filter(Shipment.shipment_code == code).first()
    if shipment:
        return shipment
    shipment = Shipment(
        shipment_code=code,
        type="import",
        status="active",
        importer_id=party_id,
        created_by=user.id,
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    return shipment


def cleanup(db: Session, party_id: int, shipment_id: int) -> None:
    from app.models.operational_event import OperationalEvent
    from app.models.validation_issue import ValidationIssue
    from app.models.notification import Notification

    db.query(FinanceRiskRecord).filter(
        (FinanceRiskRecord.party_id == party_id)
        | (FinanceRiskRecord.shipment_id == shipment_id)
    ).delete(synchronize_session=False)
    db.query(CreditHoldRecord).filter(
        (CreditHoldRecord.party_id == party_id)
        | (CreditHoldRecord.shipment_id == shipment_id)
    ).delete(synchronize_session=False)
    invoices = db.query(FinanceInvoice).filter(
        (FinanceInvoice.party_id == party_id)
        | (FinanceInvoice.shipment_id == shipment_id)
    ).all()
    for inv in invoices:
        for line in list(inv.lines):
            db.delete(line)
        db.delete(inv)
    payments = db.query(FinancePayment).filter(FinancePayment.party_id == party_id).all()
    for payment in payments:
        for allocation in list(payment.allocations):
            db.delete(allocation)
        db.delete(payment)
    db.query(PartyCreditProfile).filter(PartyCreditProfile.party_id == party_id).delete(
        synchronize_session=False
    )
    db.query(ValidationIssue).filter(
        ValidationIssue.shipment_id == shipment_id
    ).delete(synchronize_session=False)
    db.query(OperationalEvent).filter(
        OperationalEvent.shipment_id == shipment_id
    ).delete(synchronize_session=False)
    db.query(Notification).filter(
        Notification.entity_type == "finance_risk"
    ).delete(synchronize_session=False)
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if shipment and shipment.shipment_code.startswith("FF-IMP-2099"):
        db.delete(shipment)
    party = db.query(Party).filter(Party.id == party_id).first()
    if party and party.name.startswith("Phase14 Smoke"):
        db.delete(party)
    db.commit()


def run() -> None:
    db = SessionLocal()
    party = None
    shipment = None
    try:
        user = admin_user(db)
        party = create_demo_party(db)
        shipment = create_demo_shipment(db, party.id, user)

        # 1. Set up credit profile
        profile = credit_control_service.update_credit_profile(
            db,
            party.id,
            PartyCreditProfileUpdate(
                credit_limit=Decimal("5000"),
                credit_currency="INR",
                credit_days=15,
                warning_threshold_percent=80,
            ),
            user,
        )
        assert profile.credit_limit == Decimal("5000.00")
        print("[ok] credit profile created/updated")

        # 2. Create receivable invoice (overdue)
        invoice = finance_invoice_service.create_invoice(
            db,
            FinanceInvoiceCreate(
                shipment_id=shipment.id,
                party_id=party.id,
                invoice_number="SMOKE-INV-1",
                direction="receivable",
                status="issued",
                currency="INR",
                invoice_date=date.today() - timedelta(days=45),
                credit_days=15,
                lines=[
                    FinanceInvoiceLineCreate(
                        description="Smoke ocean freight",
                        quantity=Decimal("1"),
                        unit_price=Decimal("3000"),
                        amount=Decimal("3000"),
                    ),
                    FinanceInvoiceLineCreate(
                        description="Smoke handling",
                        quantity=Decimal("1"),
                        unit_price=Decimal("1000"),
                        amount=Decimal("1000"),
                    ),
                ],
            ),
            user,
        )
        assert invoice.total_amount == Decimal("4000.00")
        assert invoice.outstanding_amount == Decimal("4000.00")
        print(f"[ok] invoice created id={invoice.id} outstanding={invoice.outstanding_amount}")

        # 3. Mark overdue invoices
        invoice_db = db.query(FinanceInvoice).filter(FinanceInvoice.id == invoice.id).first()
        if invoice_db.due_date and invoice_db.due_date < date.today():
            invoice_db.status = "overdue"
            db.commit()

        # 4. Evaluate credit risk -> should produce overdue + maybe warning
        evaluation = credit_control_service.evaluate_credit_risk(
            db, party.id, shipment.id, user
        )
        print(f"[ok] credit risk evaluation: {evaluation['risks_created']}")
        assert "receivable_overdue" in evaluation["risks_created"]

        # 5. Create payment + allocate
        payment = payment_service.create_payment(
            db,
            FinancePaymentCreate(
                party_id=party.id,
                payment_type="receipt",
                currency="INR",
                amount=Decimal("1500"),
                payment_date=date.today(),
                reference_number="SMOKE-PAY-1",
            ),
            user,
        )
        assert payment.unallocated_amount == Decimal("1500.00")
        allocation_request = FinancePaymentAllocateRequest(
            allocations=[
                FinancePaymentAllocationItem(
                    invoice_id=invoice.id, allocated_amount=Decimal("1500")
                )
            ]
        )
        payment = payment_service.allocate_payment(db, payment.id, allocation_request, user)
        assert payment.unallocated_amount == Decimal("0.00")
        invoice_after = finance_invoice_service.get_invoice(db, invoice.id)
        assert invoice_after.paid_amount == Decimal("1500.00")
        assert invoice_after.outstanding_amount == Decimal("2500.00")
        print(
            f"[ok] payment allocated, invoice paid={invoice_after.paid_amount} "
            f"outstanding={invoice_after.outstanding_amount}"
        )

        # 6. Over-allocation should be blocked
        try:
            payment_service.allocate_payment(
                db,
                payment.id,
                FinancePaymentAllocateRequest(
                    allocations=[
                        FinancePaymentAllocationItem(
                            invoice_id=invoice.id, allocated_amount=Decimal("100")
                        )
                    ]
                ),
                user,
            )
            raise AssertionError("Over-allocation should have been blocked")
        except Exception as exc:  # noqa: BLE001
            assert "exceeds" in str(exc).lower(), exc
            print("[ok] over-allocation correctly blocked")

        # 7. Aging summary
        summary = finance_aging_service.calculate_aging_summary(db, direction="receivable")
        assert summary.buckets.total_outstanding > Decimal("0")
        print(
            f"[ok] aging summary: total={summary.buckets.total_outstanding} "
            f"overdue={summary.buckets.overdue_amount}"
        )

        # 8. FX rate snapshot
        fx = fx_service.create_fx_rate_snapshot(
            db,
            FxRateCreate(
                base_currency="USD",
                quote_currency="INR",
                rate=Decimal("83.5"),
                rate_date=date.today(),
            ),
            user,
        )
        assert fx.rate == Decimal("83.500000")
        converted = fx_service.convert_amount(db, Decimal("100"), "USD", "INR")
        assert converted == Decimal("8350.000")
        print(f"[ok] fx conversion 100 USD => INR {converted}")

        # 9. Release check should be blocked due to active hold
        release = release_control_service.check_release_allowed(
            db, shipment.id, "release_do", user
        )
        assert not release.allowed, "Release should be blocked while overdue hold is active"
        print(f"[ok] release blocked: {release.message}")

        # 10. Resolve hold and verify release allowed
        active_hold = (
            db.query(CreditHoldRecord)
            .filter(
                CreditHoldRecord.party_id == party.id,
                CreditHoldRecord.status == "active",
            )
            .first()
        )
        assert active_hold is not None
        credit_control_service.resolve_credit_hold(db, active_hold.id, user, notes="paid")
        release = release_control_service.check_release_allowed(
            db, shipment.id, "release_do", user
        )
        # Other holds may exist; resolve them all
        while not release.allowed:
            active_hold = (
                db.query(CreditHoldRecord)
                .filter(
                    CreditHoldRecord.party_id == party.id,
                    CreditHoldRecord.status == "active",
                )
                .first()
            )
            if not active_hold:
                break
            credit_control_service.resolve_credit_hold(db, active_hold.id, user)
            release = release_control_service.check_release_allowed(
                db, shipment.id, "release_do", user
            )
        assert release.allowed, "Release should be allowed after holds resolved"
        print("[ok] release allowed after holds resolved")

        # 11. Finance overview
        overview = finance_overview_service.build_finance_overview(db)
        print(
            f"[ok] overview: receivable_total={overview.receivable_total} "
            f"unallocated={overview.unallocated_payments}"
        )

        # 12. Shipment summary
        ship_summary = finance_overview_service.build_shipment_finance_summary(db, shipment.id)
        assert ship_summary.receivable_total == Decimal("4000.00")
        print(
            f"[ok] shipment finance summary: receivable_total="
            f"{ship_summary.receivable_total} payment_count={ship_summary.payment_count}"
        )

        print("\n=== Phase 14 smoke OK ===")
    finally:
        if party and shipment:
            try:
                cleanup(db, party.id, shipment.id)
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] cleanup failed: {exc}")
        db.close()


if __name__ == "__main__":
    run()
