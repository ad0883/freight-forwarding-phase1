from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.models.user import User
from app.schemas.usage_limit import UsageSummaryRead, UsageRecountRequest, UsageRecountResult, UsageLimitRead
from app.services.usage_limit_service import (
    get_organization_usage_summary,
    recalculate_all_usage,
    get_plan_usage_limits,
)

router = APIRouter(prefix="/usage-limits", tags=["usage_limits"])


@router.get("/summary", response_model=UsageSummaryRead)
def get_usage_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the usage summary for the current user's organization."""
    org_id = current_user.organization_id
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    counters = get_organization_usage_summary(db, org_id, current_user)
    return {"organization_id": org_id, "counters": counters}


@router.get("/plans/{plan_id}", response_model=List[UsageLimitRead])
def get_plan_limits(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    """Get usage limits for a specific plan."""
    return get_plan_usage_limits(db, plan_id)


@router.get("/organizations/{organization_id}", response_model=UsageSummaryRead)
def get_org_usage(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "STAFF")),
):
    """Get the usage summary for a specific organization."""
    # Org admin can view their own, platform admin can view any.
    if current_user.role != "admin" and current_user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this organization's usage")
        
    counters = get_organization_usage_summary(db, organization_id, current_user)
    return {"organization_id": organization_id, "counters": counters}


@router.post("/organizations/{organization_id}/recount", response_model=UsageRecountResult)
def recount_org_usage(
    organization_id: int,
    request: UsageRecountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    """Recalculate usage counters for an organization."""
    # This should be admin-only due to potential DB load
    keys = recalculate_all_usage(db, organization_id, current_user)
    return {
        "organization_id": organization_id,
        "keys_recounted": keys,
        "message": "Usage successfully recalculated"
    }


@router.get("/organizations/{organization_id}/events")
def get_org_usage_events(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    """Get usage events (audit logs) for an organization."""
    from app.models.usage_limit import UsageEvent
    events = db.query(UsageEvent).filter(UsageEvent.organization_id == organization_id).order_by(UsageEvent.created_at.desc()).limit(100).all()
    return events
