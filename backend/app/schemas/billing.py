from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class BillingProfileBase(BaseModel):
    billing_contact_name: Optional[str] = None
    billing_contact_email: Optional[str] = None
    billing_contact_phone: Optional[str] = None
    billing_address: Optional[str] = None
    billing_country: Optional[str] = None
    billing_currency: str = "USD"
    tax_id: Optional[str] = None
    gst_number: Optional[str] = None
    billing_cycle: str = "monthly"
    payment_terms_days: int = 30
    manual_payment_method: Optional[str] = None
    billing_notes: Optional[str] = None

class BillingProfileCreate(BillingProfileBase):
    pass

class BillingProfileUpdate(BillingProfileBase):
    pass

class BillingProfileRead(BillingProfileBase):
    id: int
    organization_id: int
    is_billing_enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ManualBillingRecordBase(BaseModel):
    record_type: str
    invoice_reference: Optional[str] = None
    external_invoice_url: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    due_date: Optional[datetime] = None
    amount_due: Optional[float] = None
    amount_paid: Optional[float] = None
    currency: str = "USD"
    payment_status: str = "draft"
    payment_received_at: Optional[datetime] = None
    payment_reference: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None

class ManualBillingRecordCreate(ManualBillingRecordBase):
    subscription_id: Optional[int] = None
    billing_profile_id: Optional[int] = None

class ManualBillingRecordUpdate(BaseModel):
    record_type: Optional[str] = None
    invoice_reference: Optional[str] = None
    external_invoice_url: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    due_date: Optional[datetime] = None
    amount_due: Optional[float] = None
    amount_paid: Optional[float] = None
    currency: Optional[str] = None
    payment_status: Optional[str] = None
    payment_received_at: Optional[datetime] = None
    payment_reference: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None

class BillingStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None

class ManualBillingRecordRead(ManualBillingRecordBase):
    id: int
    organization_id: int
    subscription_id: Optional[int] = None
    billing_profile_id: Optional[int] = None
    created_by_name: Optional[str] = None
    updated_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BillingEventRead(BaseModel):
    id: int
    organization_id: int
    billing_record_id: Optional[int] = None
    subscription_id: Optional[int] = None
    event_type: str
    safe_summary: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    invoice_reference: Optional[str] = None
    created_by_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class BillingSummaryRead(BaseModel):
    organization_id: int
    total_outstanding: float
    paid_this_month: float
    overdue_records_count: int
    has_billing_profile: bool

class BillingDashboardRead(BaseModel):
    total_outstanding_platform: float
    total_paid_this_month_platform: float
    overdue_records_count: int
    suspended_organizations_count: int
    manual_review_records_count: int
