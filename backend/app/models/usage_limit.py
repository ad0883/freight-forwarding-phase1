from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.types import PortableJSON


class SubscriptionUsageLimit(Base):
    __tablename__ = "subscription_usage_limits"
    __table_args__ = (
        UniqueConstraint("plan_id", "usage_key", name="uq_subscription_usage_limits_plan_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False, index=True)
    usage_key = Column(String, nullable=False)
    limit_value = Column(Integer, nullable=True) # null = unlimited
    period = Column(String, nullable=False, default="monthly")
    enforcement_mode = Column(String, nullable=False, default="hard")
    warning_threshold_percent = Column(Integer, nullable=False, default=80)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    metadata_json = Column(PortableJSON, nullable=True)

    plan = relationship("SubscriptionPlan", foreign_keys=[plan_id])


class OrganizationUsageCounter(Base):
    __tablename__ = "organization_usage_counters"
    __table_args__ = (
        UniqueConstraint("organization_id", "usage_key", "period_start", name="uq_org_usage_counters_org_key_period"),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    usage_key = Column(String, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    used_value = Column(Integer, nullable=False, default=0)
    last_calculated_at = Column(DateTime(timezone=True), nullable=True)
    source = Column(String, nullable=False, default="calculated")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    metadata_json = Column(PortableJSON, nullable=True)

    organization = relationship("Organization", foreign_keys=[organization_id])


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("organization_subscriptions.id"), nullable=True)
    usage_key = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    used_value = Column(Integer, nullable=False)
    limit_value = Column(Integer, nullable=True)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    safe_summary = Column(String, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    metadata_json = Column(PortableJSON, nullable=True)

    organization = relationship("Organization", foreign_keys=[organization_id])
    subscription = relationship("OrganizationSubscription", foreign_keys=[subscription_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
