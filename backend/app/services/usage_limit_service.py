import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from fastapi import HTTPException

from app.models.usage_limit import SubscriptionUsageLimit, OrganizationUsageCounter, UsageEvent
from app.models.subscription import SubscriptionPlan, OrganizationSubscription
from app.models.organization import Organization
from app.models.user import User
from app.models.shipment import Shipment
from app.models.document import Document
from app.models.document_version import DocumentFile
from app.models.ai_log import AIInteractionLog
from app.models.tracking import TrackingSyncRun
from app.models.predictive import PredictionRun
from app.schemas.usage_limit import UsageCheckResult

logger = logging.getLogger(__name__)


def seed_default_usage_limits(db: Session):
    """Seed default usage limits for the main plans."""
    
    # We will fetch existing plans
    starter_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_key == "starter").first()
    pro_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_key == "professional").first()
    enterprise_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_key == "enterprise").first()
    internal_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_key == "internal_trial").first()

    def create_limits(plan, limits: dict):
        if not plan:
            return
        for key, value in limits.items():
            existing = db.query(SubscriptionUsageLimit).filter(
                SubscriptionUsageLimit.plan_id == plan.id,
                SubscriptionUsageLimit.usage_key == key
            ).first()
            if not existing:
                limit = SubscriptionUsageLimit(
                    plan_id=plan.id,
                    usage_key=key,
                    limit_value=value,
                    period="monthly" if "per_month" in key else "total",
                    enforcement_mode="hard",
                    warning_threshold_percent=80
                )
                db.add(limit)

    create_limits(starter_plan, {
        "users": 5,
        "shipments_per_month": 50,
        "documents_total": 500,
        "document_uploads_per_month": 100,
        "storage_mb": 1024,
        "ai_requests_per_month": 0,
        "tracking_syncs_per_month": 25,
        "prediction_runs_per_month": 0,
        "portal_users": 0,
        "api_requests_per_month": 5000,
    })

    create_limits(pro_plan, {
        "users": 20,
        "shipments_per_month": 500,
        "documents_total": 5000,
        "document_uploads_per_month": 1000,
        "storage_mb": 10240,
        "ai_requests_per_month": 1000,
        "tracking_syncs_per_month": 1000,
        "prediction_runs_per_month": 500,
        "portal_users": 25,
        "api_requests_per_month": 50000,
    })

    create_limits(enterprise_plan, {
        "users": None,
        "shipments_per_month": None,
        "documents_total": None,
        "document_uploads_per_month": None,
        "storage_mb": None,
        "ai_requests_per_month": None,
        "tracking_syncs_per_month": None,
        "prediction_runs_per_month": None,
        "portal_users": None,
        "api_requests_per_month": None,
    })

    create_limits(internal_plan, {
        "users": 20,
        "shipments_per_month": 200,
        "documents_total": 2000,
        "document_uploads_per_month": 500,
        "storage_mb": 5120,
        "ai_requests_per_month": 500,
        "tracking_syncs_per_month": 500,
        "prediction_runs_per_month": 250,
        "portal_users": 10,
        "api_requests_per_month": 25000,
    })

    db.commit()


def get_plan_usage_limits(db: Session, plan_id: int):
    return db.query(SubscriptionUsageLimit).filter(SubscriptionUsageLimit.plan_id == plan_id).all()


def _get_current_period_dates():
    now = datetime.utcnow()
    # For S5 we assume calendar months for simplicity, although it could be subscription based
    start = datetime(now.year, now.month, 1)
    if now.month == 12:
        end = datetime(now.year + 1, 1, 1)
    else:
        end = datetime(now.year, now.month + 1, 1)
    return start, end


def calculate_usage(db: Session, organization_id: int, usage_key: str, period_start: Optional[datetime] = None, period_end: Optional[datetime] = None) -> int:
    """Dynamically calculates the current usage based on the database."""
    used = 0
    
    if usage_key == "users":
        used = db.query(User).filter(
            User.organization_id == organization_id,
            User.is_active == True
        ).count()
        
    elif usage_key == "shipments_per_month":
        query = db.query(Shipment).filter(Shipment.organization_id == organization_id)
        if period_start and period_end:
            query = query.filter(Shipment.created_at >= period_start, Shipment.created_at < period_end)
        used = query.count()
        
    elif usage_key == "documents_total":
        # Document table has shipment_id. Getting docs for org shipments or org docs
        # Here we just count documents linked to shipments of this org as a proxy if org_id is not directly on Document
        # To be safe, let's query Shipment then Document
        shipment_ids = db.query(Shipment.id).filter(Shipment.organization_id == organization_id).subquery()
        used = db.query(Document).filter(Document.shipment_id.in_(shipment_ids)).count()
        
    elif usage_key == "document_uploads_per_month":
        shipment_ids = db.query(Shipment.id).filter(Shipment.organization_id == organization_id).subquery()
        query = db.query(Document).filter(Document.shipment_id.in_(shipment_ids))
        if period_start and period_end:
            query = query.filter(Document.created_at >= period_start, Document.created_at < period_end)
        used = query.count()
        
    elif usage_key == "storage_mb":
        shipment_ids = db.query(Shipment.id).filter(Shipment.organization_id == organization_id).subquery()
        doc_ids = db.query(Document.id).filter(Document.shipment_id.in_(shipment_ids)).subquery()
        total_bytes = db.query(func.sum(DocumentFile.file_size)).filter(DocumentFile.document_id.in_(doc_ids)).scalar() or 0
        used = int(total_bytes / (1024 * 1024))
        
    elif usage_key == "ai_requests_per_month":
        query = db.query(AIInteractionLog).filter(AIInteractionLog.organization_id == organization_id)
        if period_start and period_end:
            query = query.filter(AIInteractionLog.created_at >= period_start, AIInteractionLog.created_at < period_end)
        used = query.count()
        
    elif usage_key == "tracking_syncs_per_month":
        query = db.query(TrackingSyncRun).filter(TrackingSyncRun.organization_id == organization_id)
        if period_start and period_end:
            query = query.filter(TrackingSyncRun.started_at >= period_start, TrackingSyncRun.started_at < period_end)
        used = query.count()
        
    elif usage_key == "prediction_runs_per_month":
        query = db.query(PredictionRun).filter(PredictionRun.organization_id == organization_id)
        if period_start and period_end:
            query = query.filter(PredictionRun.started_at >= period_start, PredictionRun.started_at < period_end)
        used = query.count()
        
    # ... other keys could be zero by default
        
    return used


def recalculate_all_usage(db: Session, organization_id: int, user: Any = None) -> List[str]:
    keys_recounted = [
        "users", "shipments_per_month", "documents_total", 
        "document_uploads_per_month", "storage_mb", "ai_requests_per_month",
        "tracking_syncs_per_month", "prediction_runs_per_month"
    ]
    start, end = _get_current_period_dates()
    
    for key in keys_recounted:
        if "per_month" in key:
            p_start, p_end = start, end
        else:
            p_start, p_end = None, None
            
        used = calculate_usage(db, organization_id, key, p_start, p_end)
        
        counter = db.query(OrganizationUsageCounter).filter(
            OrganizationUsageCounter.organization_id == organization_id,
            OrganizationUsageCounter.usage_key == key,
            or_(OrganizationUsageCounter.period_start == p_start, OrganizationUsageCounter.period_start == None)
        ).first()
        
        if not counter:
            counter = OrganizationUsageCounter(
                organization_id=organization_id,
                usage_key=key,
                period_start=p_start,
                period_end=p_end,
                used_value=used,
                last_calculated_at=datetime.utcnow(),
                source="recalculated"
            )
            db.add(counter)
        else:
            counter.used_value = used
            counter.last_calculated_at = datetime.utcnow()
            counter.source = "recalculated"
            
    db.commit()
    return keys_recounted


def check_usage_limit(db: Session, organization_id: int, usage_key: str, increment: int = 0, user: Any = None) -> UsageCheckResult:
    """Checks the usage limit without raising an exception."""
    
    # 1. Get Plan ID
    sub = db.query(OrganizationSubscription).filter(OrganizationSubscription.organization_id == organization_id).first()
    plan_id = sub.plan_id if sub else None
    
    # 2. Get Limit
    limit_value = None
    warning_percent = 80
    if plan_id:
        limit_obj = db.query(SubscriptionUsageLimit).filter(
            SubscriptionUsageLimit.plan_id == plan_id,
            SubscriptionUsageLimit.usage_key == usage_key,
            SubscriptionUsageLimit.is_active == True
        ).first()
        if limit_obj:
            limit_value = limit_obj.limit_value
            warning_percent = limit_obj.warning_threshold_percent
            
    # 3. Get / Recalculate usage
    start, end = _get_current_period_dates()
    if "per_month" in usage_key:
        p_start, p_end = start, end
    else:
        p_start, p_end = None, None
        
    # We could recalculate on the fly for better accuracy
    used = calculate_usage(db, organization_id, usage_key, p_start, p_end)
    used += increment
    
    allowed = True
    blocked = False
    warning = False
    message = "OK"
    percent_used = 0
    remaining = None
    
    if limit_value is not None:
        remaining = max(0, limit_value - used)
        if limit_value > 0:
            percent_used = int((used / limit_value) * 100)
            
        if used >= limit_value:
            allowed = False
            blocked = True
            message = f"{usage_key.replace('_', ' ').capitalize()} limit reached for the current plan."
        elif percent_used >= warning_percent:
            warning = True
            message = f"You are approaching your limit. {remaining} remaining."
        else:
            message = f"{remaining} remaining."
            
    return UsageCheckResult(
        usage_key=usage_key,
        allowed=allowed,
        used=used,
        limit=limit_value,
        remaining=remaining,
        percent_used=percent_used,
        warning=warning,
        blocked=blocked,
        message=message
    )

def require_usage_available(db: Session, organization_id: int, usage_key: str, increment: int = 1, user: Any = None):
    """Checks usage and raises an exception if not allowed."""
    result = check_usage_limit(db, organization_id, usage_key, increment, user)
    
    if not result.allowed:
        # Record usage event
        record_usage_event(
            db=db,
            organization_id=organization_id,
            usage_key=usage_key,
            event_type="usage_blocked",
            used_value=result.used,
            limit_value=result.limit,
            user=user,
            safe_summary=result.message
        )
        raise HTTPException(status_code=403, detail={
            "code": "USAGE_LIMIT_REACHED",
            "usage_key": usage_key,
            "used": result.used,
            "limit": result.limit,
            "message": result.message
        })

def record_usage_event(db: Session, organization_id: int, usage_key: str, event_type: str, used_value: int, limit_value: Optional[int], user: Any = None, safe_summary: str = "", metadata: dict = None):
    sub = db.query(OrganizationSubscription).filter(OrganizationSubscription.organization_id == organization_id).first()
    
    start, end = _get_current_period_dates()
    if "per_month" in usage_key:
        p_start, p_end = start, end
    else:
        p_start, p_end = None, None
        
    event = UsageEvent(
        organization_id=organization_id,
        subscription_id=sub.id if sub else None,
        usage_key=usage_key,
        event_type=event_type,
        used_value=used_value,
        limit_value=limit_value,
        period_start=p_start,
        period_end=p_end,
        safe_summary=safe_summary,
        created_by_user_id=user.id if user else None,
        created_by_name=user.email if user else None,
        metadata_json=metadata
    )
    db.add(event)
    db.commit()

def get_organization_usage_summary(db: Session, organization_id: int, user: Any = None) -> Dict[str, UsageCheckResult]:
    keys = [
        "users", "shipments_per_month", "documents_total", 
        "document_uploads_per_month", "storage_mb", "ai_requests_per_month",
        "tracking_syncs_per_month", "prediction_runs_per_month", "portal_users"
    ]
    
    counters = {}
    for k in keys:
        counters[k] = check_usage_limit(db, organization_id, k, increment=0, user=user)
        
    return counters
