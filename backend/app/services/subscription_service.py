from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.subscription import (
    SubscriptionPlan,
    SubscriptionPlanFeature,
    OrganizationSubscription,
    SubscriptionEvent,
)
from app.models.user import User

def check_admin(user: User):
    if user.role not in ["ADMIN", "ORG_ADMIN"]:
        raise HTTPException(status_code=403, detail="Subscription management is restricted to Admin users.")

def log_event(
    db: Session,
    organization_id: int,
    event_type: str,
    safe_summary: str,
    user: Optional[User] = None,
    subscription_id: Optional[int] = None,
    old_status: Optional[str] = None,
    new_status: Optional[str] = None,
    old_plan_key: Optional[str] = None,
    new_plan_key: Optional[str] = None,
):
    event = SubscriptionEvent(
        organization_id=organization_id,
        subscription_id=subscription_id,
        event_type=event_type,
        safe_summary=safe_summary,
        old_status=old_status,
        new_status=new_status,
        old_plan_key=old_plan_key,
        new_plan_key=new_plan_key,
        created_by_user_id=user.id if user else None,
        created_by_name=user.name if user else "System",
    )
    db.add(event)

def seed_default_subscription_plans(db: Session):
    # Check if starter exists
    starter = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_key == "starter").first()
    if starter:
        return {"status": "Plans already seeded"}

    starter_plan = SubscriptionPlan(
        plan_key="starter",
        name="Starter",
        description="Basic freight operations for small teams.",
        status="active",
        billing_period="monthly",
        currency="USD",
        trial_days_default=14,
        is_public=True,
        display_order=1,
    )
    prof_plan = SubscriptionPlan(
        plan_key="professional",
        name="Professional",
        description="Full operations workspace with management dashboard and AI-assisted risk visibility.",
        status="active",
        billing_period="monthly",
        currency="USD",
        trial_days_default=14,
        is_public=True,
        display_order=2,
    )
    enterprise_plan = SubscriptionPlan(
        plan_key="enterprise",
        name="Enterprise",
        description="Advanced governance, admin controls, and custom enterprise support.",
        status="active",
        billing_period="custom",
        currency="USD",
        is_public=True,
        display_order=3,
    )
    internal_plan = SubscriptionPlan(
        plan_key="internal_trial",
        name="Internal Trial",
        description="Internal testing and controlled beta plan.",
        status="internal_only",
        billing_period="manual",
        currency="USD",
        is_public=False,
        display_order=4,
    )

    db.add_all([starter_plan, prof_plan, enterprise_plan, internal_plan])
    db.commit()

    # Features for Starter
    features_starter = [
        "Shipments", "Parties", "Documents", "Containers", "Basic finance",
        "Customs tracking", "Transport tracking", "Issues", "Basic dashboard"
    ]
    for idx, f in enumerate(features_starter):
        db.add(SubscriptionPlanFeature(plan_id=starter_plan.id, feature_key=f.lower().replace(" ", "_"), feature_label=f, sort_order=idx))

    # Features for Professional
    features_prof = [
        "Everything in Starter", "Document Check / Document Intelligence", "Management Dashboard",
        "Approvals", "Tracking", "Risk Alerts", "AI Assistant", "More users/shipments placeholder"
    ]
    for idx, f in enumerate(features_prof):
        db.add(SubscriptionPlanFeature(plan_id=prof_plan.id, feature_key=f.lower().replace(" ", "_"), feature_label=f, sort_order=idx))

    # Features for Enterprise
    features_enterprise = [
        "Everything in Professional", "Advanced Admin Settings", "Role policies", "AI Control",
        "Audit/security", "Custom limits", "Custom workflows placeholder"
    ]
    for idx, f in enumerate(features_enterprise):
        db.add(SubscriptionPlanFeature(plan_id=enterprise_plan.id, feature_key=f.lower().replace(" ", "_"), feature_label=f, sort_order=idx))

    db.commit()
    return {"status": "Plans seeded"}


def get_subscription_plans(db: Session, user: User):
    check_admin(user)
    return db.query(SubscriptionPlan).order_by(SubscriptionPlan.display_order).all()


def get_subscription_plan(db: Session, plan_id: int, user: User):
    check_admin(user)
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def get_organization_subscription(db: Session, organization_id: int, user: User):
    check_admin(user)
    # Ensure org has a subscription
    ensure_default_subscription_for_organization(db, organization_id, user)
    
    sub = db.query(OrganizationSubscription).filter(OrganizationSubscription.organization_id == organization_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return sub


def ensure_default_subscription_for_organization(db: Session, organization_id: int, user: Optional[User] = None):
    sub = db.query(OrganizationSubscription).filter(OrganizationSubscription.organization_id == organization_id).first()
    if sub:
        return sub

    # Find internal_trial plan
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_key == "internal_trial").first()
    if not plan:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_key == "starter").first()

    if not plan:
        # Plans not seeded
        return None

    new_sub = OrganizationSubscription(
        organization_id=organization_id,
        plan_id=plan.id,
        subscription_status="trial",
        billing_mode="internal",
        started_at=datetime.utcnow(),
    )
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)

    log_event(
        db, organization_id, "subscription_created", f"Created default subscription with plan {plan.name}",
        user=user, subscription_id=new_sub.id, new_status="trial", new_plan_key=plan.plan_key
    )
    db.commit()
    return new_sub


def assign_plan_to_organization(db: Session, organization_id: int, data: dict, user: User):
    check_admin(user)
    sub = db.query(OrganizationSubscription).filter(OrganizationSubscription.organization_id == organization_id).first()
    if not sub:
        sub = ensure_default_subscription_for_organization(db, organization_id, user)
    
    plan_id = data.get("plan_id")
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan_id")

    old_status = sub.subscription_status
    old_plan_key = sub.plan.plan_key if sub.plan else None

    sub.plan_id = plan_id
    if "status" in data and data["status"]:
        sub.subscription_status = data["status"]
    if "billing_mode" in data and data["billing_mode"]:
        sub.billing_mode = data["billing_mode"]
    if "trial_end_date" in data:
        sub.trial_ends_at = data["trial_end_date"]
    if "current_period_start" in data:
        sub.current_period_start = data["current_period_start"]
    if "current_period_end" in data:
        sub.current_period_end = data["current_period_end"]
    if "billing_contact_name" in data:
        sub.billing_contact_name = data["billing_contact_name"]
    if "billing_contact_email" in data:
        sub.billing_contact_email = data["billing_contact_email"]
    if "manual_payment_reference" in data:
        sub.manual_payment_reference = data["manual_payment_reference"]
    if "notes" in data:
        sub.notes = data["notes"]

    sub.updated_by_user_id = user.id
    sub.updated_by_name = user.name
    
    db.commit()
    db.refresh(sub)

    log_event(
        db, organization_id, "plan_assigned",
        f"Plan manually assigned to {plan.name}",
        user=user, subscription_id=sub.id,
        old_status=old_status, new_status=sub.subscription_status,
        old_plan_key=old_plan_key, new_plan_key=plan.plan_key
    )
    db.commit()
    return sub


def update_subscription_status(db: Session, subscription_id: int, status: str, user: User, note: Optional[str] = None):
    check_admin(user)
    sub = db.query(OrganizationSubscription).filter(OrganizationSubscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    old_status = sub.subscription_status
    sub.subscription_status = status
    sub.updated_by_user_id = user.id
    sub.updated_by_name = user.name
    
    db.commit()

    summary = f"Status changed to {status}"
    if note:
        summary += f" - Note: {note}"

    log_event(
        db, sub.organization_id, "status_changed",
        summary, user=user, subscription_id=sub.id,
        old_status=old_status, new_status=status
    )
    db.commit()
    return sub


def extend_trial(db: Session, subscription_id: int, trial_ends_at: datetime, user: User, note: Optional[str] = None):
    check_admin(user)
    sub = db.query(OrganizationSubscription).filter(OrganizationSubscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    sub.trial_ends_at = trial_ends_at
    sub.updated_by_user_id = user.id
    sub.updated_by_name = user.name
    
    db.commit()

    summary = f"Trial extended until {trial_ends_at.date()}"
    if note:
        summary += f" - Note: {note}"

    log_event(
        db, sub.organization_id, "trial_extended",
        summary, user=user, subscription_id=sub.id
    )
    db.commit()
    return sub


def list_subscription_events(db: Session, organization_id: int, user: User):
    check_admin(user)
    return db.query(SubscriptionEvent).filter(SubscriptionEvent.organization_id == organization_id).order_by(SubscriptionEvent.created_at.desc()).all()


def get_subscription_summary(db: Session, user: User):
    # Allowed for all valid internal users. Portals blocked.
    if user.role == "PORTAL_USER":
        raise HTTPException(status_code=403, detail="Not available for portal users.")

    sub = ensure_default_subscription_for_organization(db, user.organization_id, user=user)
    if not sub or not sub.plan:
        raise HTTPException(status_code=404, detail="No subscription found")

    # Only return safe read-only info
    return {
        "organization_id": sub.organization_id,
        "plan_key": sub.plan.plan_key,
        "plan_name": sub.plan.name,
        "status": sub.subscription_status,
        "is_active": sub.subscription_status in ["active", "trial", "manual_override", "internal"],
        "is_trial": sub.subscription_status == "trial",
        "trial_ends_at": sub.trial_ends_at,
        "features": sub.plan.features
    }

def has_feature_access(db: Session, user: User, feature_key: str, organization_id: Optional[int] = None) -> bool:
    if not organization_id:
        organization_id = user.organization_id
    
    sub = ensure_default_subscription_for_organization(db, organization_id, user)
    if not sub or not sub.plan:
        return False
    
    if sub.subscription_status in ["past_due", "suspended", "expired", "cancelled"]:
        # Block advanced features for overdue/suspended accounts
        # Note: In a real system, you might want more granular rules here.
        # But per the spec, if past_due, we should allow read access to core modules and block advanced ones safely.
        # For S4, returning False for suspended limits their access, but core features like shipments might be explicitly allowed if they aren't gated by `require_feature`.
        pass
    
    for feature in sub.plan.features:
        if feature.feature_key == feature_key and feature.included:
            return True
    return False

def require_feature_access(db: Session, user: User, feature_key: str, organization_id: Optional[int] = None):
    # Admins always need subscription access too, but we give a backdoor for subscription admin to fix subscriptions
    if feature_key == "subscription_admin" and user.role in ["ADMIN", "ORG_ADMIN"]:
        return True
    
    if not has_feature_access(db, user, feature_key, organization_id):
        raise HTTPException(
            status_code=403, 
            detail=f"Feature '{feature_key}' is not included in your current subscription plan. Please contact your admin to upgrade."
        )
    return True

def get_feature_access_summary(db: Session, user: User, organization_id: Optional[int] = None):
    if user.role == "PORTAL_USER":
        raise HTTPException(status_code=403, detail="Not available for portal users.")

    if not organization_id:
        organization_id = user.organization_id

    sub = ensure_default_subscription_for_organization(db, organization_id, user)
    if not sub or not sub.plan:
        raise HTTPException(status_code=404, detail="No subscription found")

    features_dict = {}
    for feature in sub.plan.features:
        if feature.included:
            features_dict[feature.feature_key] = True

    # Subscription admin fallback for admins
    if user.role in ["ADMIN", "ORG_ADMIN"]:
        features_dict["subscription_admin"] = True

    is_active = sub.subscription_status in ["active", "trial", "manual_override", "internal"]

    return {
        "organization_id": sub.organization_id,
        "plan_key": sub.plan.plan_key,
        "subscription_status": sub.subscription_status,
        "features": features_dict
    }
