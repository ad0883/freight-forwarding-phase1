from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Numeric, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_key = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active")  # active, inactive, deprecated, internal_only
    billing_period = Column(String(50), nullable=False, default="monthly")  # monthly, yearly, custom, manual
    currency = Column(String(10), nullable=False, default="USD")
    base_price_amount = Column(Numeric(10, 2), nullable=True)
    trial_days_default = Column(Integer, nullable=True)
    is_public = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    features = relationship("SubscriptionPlanFeature", back_populates="plan", cascade="all, delete-orphan")


class SubscriptionPlanFeature(Base):
    __tablename__ = "subscription_plan_features"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    feature_key = Column(String(100), nullable=False)
    feature_label = Column(String(255), nullable=False)
    feature_description = Column(Text, nullable=True)
    included = Column(Boolean, nullable=False, default=True)
    limit_value = Column(Integer, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    plan = relationship("SubscriptionPlan", back_populates="features")


class OrganizationSubscription(Base):
    __tablename__ = "organization_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, unique=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    subscription_status = Column(String(50), nullable=False, default="trial")  # trial, active, suspended, cancelled...
    billing_mode = Column(String(50), nullable=False, default="manual")
    
    started_at = Column(DateTime, nullable=True)
    trial_started_at = Column(DateTime, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    suspended_at = Column(DateTime, nullable=True)
    reactivated_at = Column(DateTime, nullable=True)
    
    manual_payment_reference = Column(String(255), nullable=True)
    billing_contact_name = Column(String(255), nullable=True)
    billing_contact_email = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    created_by_user_id = Column(Integer, nullable=True)
    created_by_name = Column(String(255), nullable=True)
    updated_by_user_id = Column(Integer, nullable=True)
    updated_by_name = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    plan = relationship("SubscriptionPlan")
    organization = relationship("Organization")


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("organization_subscriptions.id"), nullable=True)
    event_type = Column(String(100), nullable=False)
    safe_summary = Column(Text, nullable=False)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    old_plan_key = Column(String(100), nullable=True)
    new_plan_key = Column(String(100), nullable=True)
    
    created_by_user_id = Column(Integer, nullable=True)
    created_by_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)
