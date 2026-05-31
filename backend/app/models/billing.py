from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class OrganizationBillingProfile(Base):
    __tablename__ = "organization_billing_profiles"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, unique=True)
    billing_contact_name = Column(String(255), nullable=True)
    billing_contact_email = Column(String(255), nullable=True)
    billing_contact_phone = Column(String(50), nullable=True)
    billing_address = Column(Text, nullable=True)
    billing_country = Column(String(100), nullable=True)
    billing_currency = Column(String(10), nullable=False, default="USD")
    tax_id = Column(String(100), nullable=True)
    gst_number = Column(String(100), nullable=True)
    billing_cycle = Column(String(50), nullable=False, default="monthly")
    payment_terms_days = Column(Integer, nullable=False, default=30)
    manual_payment_method = Column(String(100), nullable=True)
    billing_notes = Column(Text, nullable=True)
    is_billing_enabled = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    metadata_json = Column(JSONB, nullable=True)

    organization = relationship("Organization")


class ManualBillingRecord(Base):
    __tablename__ = "manual_billing_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("organization_subscriptions.id"), nullable=True)
    billing_profile_id = Column(Integer, ForeignKey("organization_billing_profiles.id"), nullable=True)
    
    record_type = Column(String(50), nullable=False) # invoice, payment, credit_note, manual_adjustment, billing_note
    invoice_reference = Column(String(100), nullable=True, index=True)
    external_invoice_url = Column(String(1024), nullable=True)
    
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    
    amount_due = Column(Numeric(12, 2), nullable=True)
    amount_paid = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(10), nullable=False, default="USD")
    
    payment_status = Column(String(50), nullable=False, default="draft")
    payment_received_at = Column(DateTime(timezone=True), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    payment_method = Column(String(100), nullable=True)
    
    notes = Column(Text, nullable=True)
    
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(255), nullable=True)
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_name = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    metadata_json = Column(JSONB, nullable=True)

    organization = relationship("Organization")
    subscription = relationship("OrganizationSubscription")
    billing_profile = relationship("OrganizationBillingProfile")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    updated_by = relationship("User", foreign_keys=[updated_by_user_id])


class BillingEvent(Base):
    __tablename__ = "billing_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    billing_record_id = Column(Integer, ForeignKey("manual_billing_records.id"), nullable=True)
    subscription_id = Column(Integer, ForeignKey("organization_subscriptions.id"), nullable=True)
    
    event_type = Column(String(100), nullable=False)
    safe_summary = Column(Text, nullable=False)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    invoice_reference = Column(String(100), nullable=True)
    
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    metadata_json = Column(JSONB, nullable=True)

    organization = relationship("Organization")
    billing_record = relationship("ManualBillingRecord")
    subscription = relationship("OrganizationSubscription")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
