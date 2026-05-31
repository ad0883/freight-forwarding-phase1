from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.billing import (
    BillingProfileRead,
    BillingProfileUpdate,
    ManualBillingRecordRead,
    ManualBillingRecordCreate,
    ManualBillingRecordUpdate,
    BillingStatusUpdate,
    BillingEventRead,
    BillingSummaryRead,
    BillingDashboardRead
)
from app.services.billing_service import (
    get_billing_profile,
    update_billing_profile,
    create_manual_billing_record,
    update_billing_status,
    mark_invoice_paid,
    mark_invoice_overdue,
    list_billing_records,
    list_billing_events,
    get_billing_summary,
    get_billing_dashboard
)

router = APIRouter()

@router.get("/summary", response_model=BillingSummaryRead)
def api_get_billing_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    return get_billing_summary(db, current_user.organization_id, current_user)

@router.get("/dashboard", response_model=BillingDashboardRead)
def api_get_billing_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_billing_dashboard(db, current_user)

@router.get("/organizations/{organization_id}/profile", response_model=BillingProfileRead)
def api_get_billing_profile(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_billing_profile(db, organization_id, current_user)

@router.patch("/organizations/{organization_id}/profile", response_model=BillingProfileRead)
def api_update_billing_profile(
    organization_id: int,
    request: BillingProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_billing_profile(db, organization_id, request.dict(exclude_unset=True), current_user)

@router.get("/organizations/{organization_id}/records", response_model=List[ManualBillingRecordRead])
def api_list_billing_records(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_billing_records(db, organization_id, current_user)

@router.post("/organizations/{organization_id}/records", response_model=ManualBillingRecordRead)
def api_create_billing_record(
    organization_id: int,
    request: ManualBillingRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_manual_billing_record(db, organization_id, request.dict(exclude_unset=True), current_user)

@router.patch("/records/{record_id}/status", response_model=ManualBillingRecordRead)
def api_update_billing_status(
    record_id: int,
    request: BillingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_billing_status(db, record_id, request.status, current_user, request.note)

@router.post("/records/{record_id}/mark-paid", response_model=ManualBillingRecordRead)
def api_mark_invoice_paid(
    record_id: int,
    payment_reference: str = Body(..., embed=True),
    payment_received_at: datetime = Body(default_factory=datetime.utcnow, embed=True),
    note: str = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return mark_invoice_paid(db, record_id, payment_reference, payment_received_at, current_user, note)

@router.post("/records/{record_id}/mark-overdue", response_model=ManualBillingRecordRead)
def api_mark_invoice_overdue(
    record_id: int,
    note: str = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return mark_invoice_overdue(db, record_id, current_user, note)

@router.get("/organizations/{organization_id}/events", response_model=List[BillingEventRead])
def api_list_billing_events(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_billing_events(db, organization_id, current_user)
