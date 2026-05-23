from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db
from app.schemas.charge import (
    DashboardFinancialSummary,
    MonthlyReportSummary,
    PendingChargeReportRow,
    ShipmentPLReportRow,
)
from app.services.finance_service import (
    calculate_dashboard_financials,
    calculate_monthly_report,
    list_pending_payables,
    list_pending_receivables,
    list_shipment_pnl,
)


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard-financials", response_model=DashboardFinancialSummary)
def dashboard_financials(
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> DashboardFinancialSummary:
    return calculate_dashboard_financials(db)


@router.get("/monthly", response_model=MonthlyReportSummary)
def monthly_report(
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> MonthlyReportSummary:
    today = date.today()
    return calculate_monthly_report(db, year=year or today.year, month=month or today.month)


@router.get("/pending-receivables", response_model=list[PendingChargeReportRow])
def pending_receivables(
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[PendingChargeReportRow]:
    return list_pending_receivables(db)


@router.get("/pending-payables", response_model=list[PendingChargeReportRow])
def pending_payables(
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[PendingChargeReportRow]:
    return list_pending_payables(db)


@router.get("/shipment-pnl", response_model=list[ShipmentPLReportRow])
def shipment_pnl_report(
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[ShipmentPLReportRow]:
    return list_shipment_pnl(db)
