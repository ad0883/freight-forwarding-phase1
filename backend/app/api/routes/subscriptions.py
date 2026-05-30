from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.subscription import (
    ExtendTrialRequest,
    OrganizationSubscriptionRead,
    SubscriptionEventRead,
    SubscriptionPlanChangeRequest,
    SubscriptionPlanRead,
    SubscriptionStatusUpdate,
    SubscriptionSummaryRead,
    FeatureAccessSummaryRead,
)
from app.services.subscription_service import (
    assign_plan_to_organization,
    extend_trial,
    get_organization_subscription,
    get_subscription_plan,
    get_subscription_plans,
    get_subscription_summary,
    get_feature_access_summary,
    list_subscription_events,
    seed_default_subscription_plans,
    update_subscription_status,
)

router = APIRouter()


@router.post("/seed-defaults", status_code=200)
def api_seed_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["ADMIN", "ORG_ADMIN"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Only Admins can seed plans")
    return seed_default_subscription_plans(db)


@router.get("/plans", response_model=List[SubscriptionPlanRead])
def api_get_subscription_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_subscription_plans(db, current_user)


@router.get("/summary", response_model=SubscriptionSummaryRead)
def api_get_subscription_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_subscription_summary(db, current_user)


@router.get("/features", response_model=FeatureAccessSummaryRead)
def api_get_feature_access_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_feature_access_summary(db, current_user)


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanRead)
def api_get_subscription_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_subscription_plan(db, plan_id, current_user)


@router.get("/organizations/{organization_id}", response_model=OrganizationSubscriptionRead)
def api_get_organization_subscription(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_organization_subscription(db, organization_id, current_user)


@router.post("/organizations/{organization_id}/assign-plan", response_model=OrganizationSubscriptionRead)
def api_assign_plan(
    organization_id: int,
    request: SubscriptionPlanChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return assign_plan_to_organization(db, organization_id, request.model_dump(exclude_unset=True), current_user)


@router.patch("/{subscription_id}/status", response_model=OrganizationSubscriptionRead)
def api_update_status(
    subscription_id: int,
    request: SubscriptionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_subscription_status(db, subscription_id, request.status, current_user, request.note)


@router.post("/{subscription_id}/extend-trial", response_model=OrganizationSubscriptionRead)
def api_extend_trial(
    subscription_id: int,
    request: ExtendTrialRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return extend_trial(db, subscription_id, request.trial_ends_at, current_user, request.note)


@router.get("/organizations/{organization_id}/events", response_model=List[SubscriptionEventRead])
def api_get_events(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_subscription_events(db, organization_id, current_user)
