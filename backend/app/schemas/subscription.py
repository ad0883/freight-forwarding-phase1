from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SubscriptionPlanFeatureRead(BaseModel):
    id: int
    plan_id: int
    feature_key: str
    feature_label: str
    feature_description: Optional[str] = None
    included: bool = True
    limit_value: Optional[int] = None
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlanRead(BaseModel):
    id: int
    plan_key: str
    name: str
    description: Optional[str] = None
    status: str
    billing_period: str
    currency: str
    base_price_amount: Optional[float] = None
    trial_days_default: Optional[int] = None
    is_public: bool
    is_active: bool
    display_order: int
    created_at: datetime
    updated_at: datetime
    metadata_json: Optional[Dict[str, Any]] = None
    features: List[SubscriptionPlanFeatureRead] = []

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlanCreate(BaseModel):
    plan_key: str
    name: str
    description: Optional[str] = None
    status: str = "active"
    billing_period: str = "monthly"
    currency: str = "USD"
    base_price_amount: Optional[float] = None
    trial_days_default: Optional[int] = None
    is_public: bool = True
    is_active: bool = True
    display_order: int = 0
    metadata_json: Optional[Dict[str, Any]] = None


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None
    metadata_json: Optional[Dict[str, Any]] = None


class OrganizationSubscriptionRead(BaseModel):
    id: int
    organization_id: int
    plan_id: int
    subscription_status: str
    billing_mode: str
    started_at: Optional[datetime] = None
    trial_started_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    reactivated_at: Optional[datetime] = None
    manual_payment_reference: Optional[str] = None
    billing_contact_name: Optional[str] = None
    billing_contact_email: Optional[str] = None
    notes: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_by_name: Optional[str] = None
    updated_by_user_id: Optional[int] = None
    updated_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata_json: Optional[Dict[str, Any]] = None

    plan: Optional[SubscriptionPlanRead] = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationSubscriptionCreate(BaseModel):
    organization_id: int
    plan_id: int
    subscription_status: str = "trial"
    billing_mode: str = "manual"
    started_at: Optional[datetime] = None
    trial_started_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    manual_payment_reference: Optional[str] = None
    billing_contact_name: Optional[str] = None
    billing_contact_email: Optional[str] = None
    notes: Optional[str] = None


class OrganizationSubscriptionUpdate(BaseModel):
    billing_contact_name: Optional[str] = None
    billing_contact_email: Optional[str] = None
    notes: Optional[str] = None


class SubscriptionStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


class SubscriptionPlanChangeRequest(BaseModel):
    plan_id: int
    status: Optional[str] = "active"
    billing_mode: Optional[str] = "manual"
    trial_end_date: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    billing_contact_name: Optional[str] = None
    billing_contact_email: Optional[str] = None
    manual_payment_reference: Optional[str] = None
    notes: Optional[str] = None


class ExtendTrialRequest(BaseModel):
    trial_ends_at: datetime
    note: Optional[str] = None


class SubscriptionEventRead(BaseModel):
    id: int
    organization_id: int
    subscription_id: Optional[int] = None
    event_type: str
    safe_summary: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    old_plan_key: Optional[str] = None
    new_plan_key: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class SubscriptionSummaryRead(BaseModel):
    organization_id: int
    plan_key: str
    plan_name: str
    status: str
    is_active: bool
    is_trial: bool
    trial_ends_at: Optional[datetime] = None
    features: List[SubscriptionPlanFeatureRead] = []

    model_config = ConfigDict(from_attributes=True)


class FeatureAccessSummaryRead(BaseModel):
    organization_id: int
    plan_key: str
    subscription_status: str
    features: Dict[str, bool]
    
    model_config = ConfigDict(from_attributes=True)
