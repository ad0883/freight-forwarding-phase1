from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.billing import OrganizationBillingProfile, ManualBillingRecord, BillingEvent
from app.models.subscription import OrganizationSubscription
from app.models.user import User

def check_admin(user: User):
    if user.role not in ["ADMIN", "ORG_ADMIN"]:
        raise HTTPException(status_code=403, detail="Billing management is restricted.")

def check_platform_admin(user: User):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only platform admins can perform this action.")

def check_org_access(user: User, organization_id: int):
    if user.role != "ADMIN" and user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization's billing data.")

def record_billing_event(
    db: Session,
    organization_id: int,
    event_type: str,
    safe_summary: str,
    user: Optional[User] = None,
    billing_record_id: Optional[int] = None,
    subscription_id: Optional[int] = None,
    old_status: Optional[str] = None,
    new_status: Optional[str] = None,
    invoice_reference: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    event = BillingEvent(
        organization_id=organization_id,
        billing_record_id=billing_record_id,
        subscription_id=subscription_id,
        event_type=event_type,
        safe_summary=safe_summary,
        old_status=old_status,
        new_status=new_status,
        invoice_reference=invoice_reference,
        created_by_user_id=user.id if user else None,
        created_by_name=user.name if user else "System",
        metadata_json=metadata
    )
    db.add(event)

def ensure_billing_profile(db: Session, organization_id: int, user: Optional[User] = None) -> OrganizationBillingProfile:
    profile = db.query(OrganizationBillingProfile).filter(OrganizationBillingProfile.organization_id == organization_id).first()
    if not profile:
        profile = OrganizationBillingProfile(organization_id=organization_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        record_billing_event(
            db, organization_id, "billing_profile_created",
            "Auto-created default billing profile", user=user
        )
        db.commit()
    return profile

def get_billing_profile(db: Session, organization_id: int, user: User) -> OrganizationBillingProfile:
    check_org_access(user, organization_id)
    return ensure_billing_profile(db, organization_id, user)

def update_billing_profile(db: Session, organization_id: int, data: dict, user: User) -> OrganizationBillingProfile:
    check_org_access(user, organization_id)
    profile = ensure_billing_profile(db, organization_id, user)
    
    for key, value in data.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
            
    db.commit()
    db.refresh(profile)
    record_billing_event(db, organization_id, "billing_profile_updated", "Updated billing profile", user=user)
    db.commit()
    return profile

def create_manual_billing_record(db: Session, organization_id: int, data: dict, user: User) -> ManualBillingRecord:
    check_platform_admin(user)
    ensure_billing_profile(db, organization_id, user)
    
    record = ManualBillingRecord(
        organization_id=organization_id,
        **data,
        created_by_user_id=user.id,
        created_by_name=user.name
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    
    record_billing_event(
        db, organization_id, "invoice_created",
        f"Created {record.record_type} record: {record.invoice_reference or 'No ref'}",
        user=user,
        billing_record_id=record.id,
        new_status=record.payment_status,
        invoice_reference=record.invoice_reference
    )
    db.commit()
    return record

def update_billing_status(db: Session, record_id: int, payment_status: str, user: User, note: Optional[str] = None) -> ManualBillingRecord:
    check_platform_admin(user)
    record = db.query(ManualBillingRecord).filter(ManualBillingRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Billing record not found")
        
    old_status = record.payment_status
    record.payment_status = payment_status
    if note:
        record.notes = (record.notes + "\n" + note) if record.notes else note
        
    record.updated_by_user_id = user.id
    record.updated_by_name = user.name
    
    db.commit()
    db.refresh(record)
    
    record_billing_event(
        db, record.organization_id, "invoice_status_changed",
        f"Status changed to {payment_status}" + (f" - Note: {note}" if note else ""),
        user=user,
        billing_record_id=record.id,
        old_status=old_status,
        new_status=payment_status,
        invoice_reference=record.invoice_reference
    )
    db.commit()
    return record

def mark_invoice_paid(db: Session, record_id: int, payment_reference: str, payment_received_at: datetime, user: User, note: Optional[str] = None) -> ManualBillingRecord:
    check_platform_admin(user)
    record = db.query(ManualBillingRecord).filter(ManualBillingRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Billing record not found")
        
    old_status = record.payment_status
    record.payment_status = "paid"
    record.payment_reference = payment_reference
    record.payment_received_at = payment_received_at
    if record.amount_due is not None:
        record.amount_paid = record.amount_due
        
    if note:
        record.notes = (record.notes + "\n" + note) if record.notes else note
        
    record.updated_by_user_id = user.id
    record.updated_by_name = user.name
    
    db.commit()
    db.refresh(record)
    
    record_billing_event(
        db, record.organization_id, "payment_marked_paid",
        f"Marked paid with ref: {payment_reference}",
        user=user,
        billing_record_id=record.id,
        old_status=old_status,
        new_status="paid",
        invoice_reference=record.invoice_reference
    )
    db.commit()
    return record

def mark_invoice_overdue(db: Session, record_id: int, user: User, note: Optional[str] = None) -> ManualBillingRecord:
    return update_billing_status(db, record_id, "overdue", user, note)

def list_billing_records(db: Session, organization_id: int, user: User) -> List[ManualBillingRecord]:
    check_org_access(user, organization_id)
    return db.query(ManualBillingRecord).filter(ManualBillingRecord.organization_id == organization_id).order_by(ManualBillingRecord.created_at.desc()).all()

def list_billing_events(db: Session, organization_id: int, user: User) -> List[BillingEvent]:
    check_org_access(user, organization_id)
    return db.query(BillingEvent).filter(BillingEvent.organization_id == organization_id).order_by(BillingEvent.created_at.desc()).all()

def get_billing_summary(db: Session, organization_id: int, user: User) -> dict:
    check_org_access(user, organization_id)
    
    records = db.query(ManualBillingRecord).filter(ManualBillingRecord.organization_id == organization_id).all()
    
    total_outstanding = sum(float(r.amount_due or 0) - float(r.amount_paid or 0) for r in records if r.payment_status in ["issued", "pending", "overdue", "partially_paid"])
    
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    paid_this_month = sum(float(r.amount_paid or 0) for r in records if r.payment_status == "paid" and r.payment_received_at and r.payment_received_at >= current_month)
    
    overdue_count = sum(1 for r in records if r.payment_status == "overdue")
    
    profile = db.query(OrganizationBillingProfile).filter(OrganizationBillingProfile.organization_id == organization_id).first()
    has_profile = profile is not None
    
    return {
        "organization_id": organization_id,
        "total_outstanding": total_outstanding,
        "paid_this_month": paid_this_month,
        "overdue_records_count": overdue_count,
        "has_billing_profile": has_profile
    }

def get_billing_dashboard(db: Session, user: User) -> dict:
    check_platform_admin(user)
    
    all_records = db.query(ManualBillingRecord).all()
    
    total_outstanding = sum(float(r.amount_due or 0) - float(r.amount_paid or 0) for r in all_records if r.payment_status in ["issued", "pending", "overdue", "partially_paid"])
    
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    paid_this_month = sum(float(r.amount_paid or 0) for r in all_records if r.payment_status == "paid" and r.payment_received_at and r.payment_received_at >= current_month)
    
    overdue_count = sum(1 for r in all_records if r.payment_status == "overdue")
    manual_review_count = sum(1 for r in all_records if r.payment_status == "manual_review")
    
    suspended_orgs = db.query(OrganizationSubscription).filter(OrganizationSubscription.subscription_status == "suspended").count()
    
    return {
        "total_outstanding_platform": total_outstanding,
        "total_paid_this_month_platform": paid_this_month,
        "overdue_records_count": overdue_count,
        "suspended_organizations_count": suspended_orgs,
        "manual_review_records_count": manual_review_count
    }
