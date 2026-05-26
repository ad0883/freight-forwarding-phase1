"""Phase 14 finance + credit-control API routes."""
from datetime import date as Date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    AuthenticatedUser,
    get_current_user,
    get_db,
    require_roles,
    require_write_access,
)
from app.schemas.finance_control import (
    CreditHoldRead,
    CreditHoldResolutionRequest,
    FinanceAgingSnapshotRead,
    FinanceAgingSummary,
    FinanceInvoiceCancel,
    FinanceInvoiceCreate,
    FinanceInvoiceRead,
    FinanceInvoiceUpdate,
    FinanceOverviewSummary,
    FinancePaymentAllocateRequest,
    FinancePaymentCancel,
    FinancePaymentCreate,
    FinancePaymentRead,
    FinanceRiskRead,
    FinanceRiskResolutionRequest,
    FxRateCreate,
    FxRateRead,
    PartyCreditProfileRead,
    PartyCreditProfileUpdate,
    ReleaseCheckResult,
    ShipmentFinanceSummary,
)
from app.services import (
    credit_control_service,
    finance_aging_service,
    finance_invoice_service,
    finance_overview_service,
    finance_risk_service,
    fx_service,
    payment_service,
    release_control_service,
)


router = APIRouter(prefix="/finance", tags=["finance"])
shipment_finance_router = APIRouter(tags=["finance"])


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


@router.get("/overview", response_model=FinanceOverviewSummary)
def finance_overview(
    currency: str = Query("INR", min_length=1, max_length=10),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> FinanceOverviewSummary:
    return finance_overview_service.build_finance_overview(db, currency=currency)


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


@router.get("/invoices", response_model=list[FinanceInvoiceRead])
def list_invoices(
    direction: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    party_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    overdue_only: bool = False,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[FinanceInvoiceRead]:
    return finance_invoice_service.list_invoices(
        db,
        direction=direction,
        status_filter=status_filter,
        party_id=party_id,
        shipment_id=shipment_id,
        overdue_only=overdue_only,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("/invoices", response_model=FinanceInvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: FinanceInvoiceCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_write_access),
) -> FinanceInvoiceRead:
    return finance_invoice_service.create_invoice(db, payload, user)


@router.get("/invoices/{invoice_id}", response_model=FinanceInvoiceRead)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> FinanceInvoiceRead:
    return finance_invoice_service.get_invoice(db, invoice_id)


@router.patch("/invoices/{invoice_id}", response_model=FinanceInvoiceRead)
def update_invoice(
    invoice_id: int,
    payload: FinanceInvoiceUpdate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_write_access),
) -> FinanceInvoiceRead:
    return finance_invoice_service.update_invoice(db, invoice_id, payload, user)


@router.post("/invoices/{invoice_id}/cancel", response_model=FinanceInvoiceRead)
def cancel_invoice(
    invoice_id: int,
    payload: FinanceInvoiceCancel = FinanceInvoiceCancel(),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> FinanceInvoiceRead:
    return finance_invoice_service.cancel_invoice(db, invoice_id, user, reason=payload.reason)


@router.post(
    "/invoices/from-charge/{charge_id}",
    response_model=FinanceInvoiceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice_from_charge(
    charge_id: int,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_write_access),
) -> FinanceInvoiceRead:
    return finance_invoice_service.create_invoice_from_charge(db, charge_id, user)


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


@router.get("/payments", response_model=list[FinancePaymentRead])
def list_payments(
    direction: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    party_id: Optional[int] = None,
    payment_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[FinancePaymentRead]:
    return payment_service.list_payments(
        db,
        direction=direction,
        status_filter=status_filter,
        party_id=party_id,
        payment_type=payment_type,
        limit=limit,
        offset=offset,
    )


@router.post("/payments", response_model=FinancePaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: FinancePaymentCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_write_access),
) -> FinancePaymentRead:
    return payment_service.create_payment(db, payload, user)


@router.get("/payments/{payment_id}", response_model=FinancePaymentRead)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> FinancePaymentRead:
    return payment_service.get_payment(db, payment_id)


@router.post("/payments/{payment_id}/allocate", response_model=FinancePaymentRead)
def allocate_payment(
    payment_id: int,
    payload: FinancePaymentAllocateRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_write_access),
) -> FinancePaymentRead:
    return payment_service.allocate_payment(db, payment_id, payload, user)


@router.post("/payments/{payment_id}/cancel", response_model=FinancePaymentRead)
def cancel_payment(
    payment_id: int,
    payload: FinancePaymentCancel = FinancePaymentCancel(),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> FinancePaymentRead:
    return payment_service.cancel_payment(db, payment_id, user, reason=payload.reason)


# ---------------------------------------------------------------------------
# Credit profiles
# ---------------------------------------------------------------------------


@router.get("/credit-profiles", response_model=list[PartyCreditProfileRead])
def list_credit_profiles(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[PartyCreditProfileRead]:
    return credit_control_service.list_credit_profiles(
        db, status_filter=status_filter, search=search, limit=limit
    )


@router.get("/parties/{party_id}/credit-profile", response_model=PartyCreditProfileRead)
def get_credit_profile(
    party_id: int,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> PartyCreditProfileRead:
    return credit_control_service.get_credit_profile_read(db, party_id, user)


@router.patch("/parties/{party_id}/credit-profile", response_model=PartyCreditProfileRead)
def update_credit_profile(
    party_id: int,
    payload: PartyCreditProfileUpdate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> PartyCreditProfileRead:
    return credit_control_service.update_credit_profile(db, party_id, payload, user)


# ---------------------------------------------------------------------------
# Holds
# ---------------------------------------------------------------------------


@router.get("/holds", response_model=list[CreditHoldRead])
def list_holds(
    status_filter: Optional[str] = Query("active", alias="status"),
    party_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    hold_type: Optional[str] = None,
    blocked_action: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[CreditHoldRead]:
    return credit_control_service.list_credit_holds(
        db,
        status_filter=status_filter,
        party_id=party_id,
        shipment_id=shipment_id,
        hold_type=hold_type,
        blocked_action=blocked_action,
        limit=limit,
    )


@router.post("/holds/{hold_id}/resolve", response_model=CreditHoldRead)
def resolve_hold(
    hold_id: int,
    payload: CreditHoldResolutionRequest = CreditHoldResolutionRequest(),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_write_access),
) -> CreditHoldRead:
    return credit_control_service.resolve_credit_hold(db, hold_id, user, notes=payload.notes)


@router.post("/holds/{hold_id}/waive", response_model=CreditHoldRead)
def waive_hold(
    hold_id: int,
    payload: CreditHoldResolutionRequest = CreditHoldResolutionRequest(),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> CreditHoldRead:
    return credit_control_service.waive_credit_hold(db, hold_id, user, notes=payload.notes)


# ---------------------------------------------------------------------------
# Aging
# ---------------------------------------------------------------------------


@router.get("/aging", response_model=FinanceAgingSummary)
def aging_summary(
    direction: str = Query("receivable"),
    currency: Optional[str] = None,
    as_of_date: Optional[Date] = None,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> FinanceAgingSummary:
    return finance_aging_service.calculate_aging_summary(
        db, direction=direction, as_of_date=as_of_date, currency=currency
    )


@router.get("/parties/{party_id}/aging", response_model=FinanceAgingSummary)
def party_aging(
    party_id: int,
    direction: str = Query("receivable"),
    currency: Optional[str] = None,
    as_of_date: Optional[Date] = None,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> FinanceAgingSummary:
    buckets = finance_aging_service.calculate_aging_for_party(
        db, party_id, direction=direction, as_of_date=as_of_date, currency=currency
    )
    return FinanceAgingSummary(
        direction=direction,
        currency=(currency or "INR").upper(),
        snapshot_date=as_of_date or Date.today(),
        buckets=buckets,
        parties=[],
    )


@router.post("/aging/snapshot", response_model=FinanceAgingSnapshotRead)
def aging_snapshot(
    direction: str = Query("receivable"),
    currency: str = Query("INR"),
    party_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_write_access),
) -> FinanceAgingSnapshotRead:
    return finance_aging_service.create_aging_snapshot(
        db,
        party_id=party_id,
        shipment_id=shipment_id,
        direction=direction,
        currency=currency,
    )


# ---------------------------------------------------------------------------
# FX
# ---------------------------------------------------------------------------


@router.get("/fx-rates", response_model=list[FxRateRead])
def list_fx_rates(
    base_currency: Optional[str] = None,
    quote_currency: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[FxRateRead]:
    return fx_service.list_fx_rates(
        db,
        base_currency=base_currency,
        quote_currency=quote_currency,
        limit=limit,
    )


@router.post("/fx-rates", response_model=FxRateRead, status_code=status.HTTP_201_CREATED)
def create_fx_rate(
    payload: FxRateCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_write_access),
) -> FxRateRead:
    return fx_service.create_fx_rate_snapshot(db, payload, user)


# ---------------------------------------------------------------------------
# Risks
# ---------------------------------------------------------------------------


@router.get("/risks", response_model=list[FinanceRiskRead])
def list_finance_risks(
    risk_type: Optional[str] = None,
    severity: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    party_id: Optional[int] = None,
    shipment_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[FinanceRiskRead]:
    return finance_risk_service.list_finance_risks(
        db,
        risk_type=risk_type,
        severity=severity,
        status_filter=status_filter,
        party_id=party_id,
        shipment_id=shipment_id,
        limit=limit,
        offset=offset,
    )


@router.post("/risks/{risk_id}/resolve", response_model=FinanceRiskRead)
def resolve_finance_risk(
    risk_id: int,
    payload: FinanceRiskResolutionRequest = FinanceRiskResolutionRequest(),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_write_access),
) -> FinanceRiskRead:
    return finance_risk_service.resolve_finance_risk(db, risk_id, user, notes=payload.notes)


@router.post("/refresh-party/{party_id}")
def refresh_party_finance_risks(
    party_id: int,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, object]:
    return credit_control_service.refresh_party_finance_risks(db, party_id, user)


@router.post("/refresh-shipment/{shipment_id}")
def refresh_shipment_finance_risks(
    shipment_id: int,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, object]:
    return credit_control_service.refresh_shipment_finance_risks(db, shipment_id, user)


# ---------------------------------------------------------------------------
# Shipment-specific routes
# ---------------------------------------------------------------------------


@shipment_finance_router.get(
    "/shipments/{shipment_id}/finance-summary", response_model=ShipmentFinanceSummary
)
def shipment_finance_summary(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> ShipmentFinanceSummary:
    return finance_overview_service.build_shipment_finance_summary(db, shipment_id)


@shipment_finance_router.get(
    "/shipments/{shipment_id}/release-checks", response_model=list[ReleaseCheckResult]
)
def shipment_release_checks(
    shipment_id: int,
    actions: Optional[str] = Query(None, description="Comma-separated action keys"),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[ReleaseCheckResult]:
    if actions:
        keys = [item.strip() for item in actions.split(",") if item.strip()]
    else:
        keys = sorted(release_control_service.SUPPORTED_RELEASE_ACTIONS)
    results: list[ReleaseCheckResult] = []
    for key in keys:
        try:
            results.append(release_control_service.check_release_allowed(db, shipment_id, key))
        except HTTPException as exc:
            if exc.status_code == status.HTTP_400_BAD_REQUEST:
                continue
            raise
    return results


@shipment_finance_router.post("/shipments/{shipment_id}/finance-refresh")
def shipment_finance_refresh(
    shipment_id: int,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, object]:
    return credit_control_service.refresh_shipment_finance_risks(db, shipment_id, user)
