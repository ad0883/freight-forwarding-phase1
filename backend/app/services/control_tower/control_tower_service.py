"""Phase 22 + 22.1 Control Tower service — unified operational intelligence."""
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser

logger = logging.getLogger(__name__)

# Stale data thresholds (Phase 22.1)
STALE_THRESHOLDS = {
    "shipment_update_days": 7,
    "container_update_days": 5,
    "tracking_sync_hours": 24,
    "transport_location_hours": 12,
    "customs_update_days": 3,
    "document_review_days": 2,
    "exception_open_days": 2,
    "approval_pending_days": 2,
}


def get_control_tower_summary(db: Session, user: AuthenticatedUser) -> dict[str, Any]:
    """Unified control tower summary combining all modules."""
    return {
        "operations": _get_operations(db),
        "containers": _get_containers(db),
        "documents": _get_documents(db),
        "finance": _get_finance(db, user),
        "exceptions_approvals": _get_exceptions_approvals(db),
        "customs": _get_customs(db),
        "transport": _get_transport(db),
        "tracking": _get_tracking(db),
        "portal": _get_portal(db),
        "bot_governance": _get_bot_governance(db, user),
    }


def get_operations_overview(db: Session, user: AuthenticatedUser) -> dict[str, Any]:
    """Operations health overview."""
    return _get_operations(db)


def get_risk_heatmap(db: Session, user: AuthenticatedUser) -> dict[str, Any]:
    """Real-data risk heatmap (Phase 22.1 — no hardcoded values)."""
    from app.models.exception_case import ExceptionCase
    from app.models.approval import ApprovalRequest
    from app.models.finance_control import CreditHoldRecord
    from app.models.tracking import TrackingMismatch, TrackingSuggestedUpdate
    from app.models.transport import TransportException

    critical_exceptions = db.query(ExceptionCase).filter(
        ExceptionCase.status.in_(["open", "in_progress"]),
        ExceptionCase.severity == "critical"
    ).count()

    pending_approvals = db.query(ApprovalRequest).filter(
        ApprovalRequest.status == "pending"
    ).count()

    high_risk_approvals = db.query(ApprovalRequest).filter(
        ApprovalRequest.status == "pending",
        ApprovalRequest.risk_level == "high"
    ).count()

    finance_holds = db.query(CreditHoldRecord).filter(
        CreditHoldRecord.status == "active"
    ).count()

    tracking_mismatches = db.query(TrackingMismatch).filter(
        TrackingMismatch.status == "open"
    ).count()

    transport_exceptions = db.query(TransportException).filter(
        TransportException.status == "open"
    ).count()

    # Calculate overall risk score (0-100)
    risk_score = min(100, (
        critical_exceptions * 15 +
        high_risk_approvals * 10 +
        finance_holds * 8 +
        tracking_mismatches * 5 +
        transport_exceptions * 5 +
        pending_approvals * 2
    ))

    return {
        "risk_score": risk_score,
        "risk_level": "critical" if risk_score >= 70 else "high" if risk_score >= 40 else "medium" if risk_score >= 20 else "low",
        "inputs": {
            "critical_exceptions": critical_exceptions,
            "pending_approvals": pending_approvals,
            "high_risk_approvals": high_risk_approvals,
            "finance_holds": finance_holds,
            "tracking_mismatches": tracking_mismatches,
            "transport_exceptions": transport_exceptions,
        },
    }


def get_top_risks(db: Session, user: AuthenticatedUser) -> list[dict[str, Any]]:
    """Top risk items across modules."""
    risks = []

    from app.models.exception_case import ExceptionCase
    critical = db.query(ExceptionCase).filter(
        ExceptionCase.status.in_(["open", "in_progress"]),
        ExceptionCase.severity == "critical"
    ).order_by(ExceptionCase.created_at.desc()).limit(5).all()
    for e in critical:
        risks.append({"type": "exception", "severity": "critical", "title": e.title[:100] if e.title else "Critical exception", "entity_id": e.id, "link": "/manual-review"})

    from app.models.approval import ApprovalRequest
    high_approvals = db.query(ApprovalRequest).filter(
        ApprovalRequest.status == "pending", ApprovalRequest.risk_level == "high"
    ).limit(5).all()
    for a in high_approvals:
        risks.append({"type": "approval", "severity": "high", "title": f"High-risk approval #{a.id}", "entity_id": a.id, "link": "/approvals"})

    from app.models.transport import TransportJob
    delayed = db.query(TransportJob).filter(TransportJob.status == "delayed").limit(5).all()
    for j in delayed:
        risks.append({"type": "transport_delay", "severity": "high", "title": f"Transport delayed: {j.job_number}", "entity_id": j.id, "link": "/transport"})

    return sorted(risks, key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r["severity"], 4))[:10]


def get_sla_overdue(db: Session, user: AuthenticatedUser) -> list[dict[str, Any]]:
    """SLA overdue items."""
    overdue = []
    now = datetime.utcnow()

    from app.models.exception_case import ExceptionCase
    old_exceptions = db.query(ExceptionCase).filter(
        ExceptionCase.status.in_(["open", "in_progress"]),
        ExceptionCase.created_at < now - timedelta(days=2)
    ).limit(10).all()
    for e in old_exceptions:
        overdue.append({"type": "exception", "title": e.title[:80] if e.title else "Exception overdue", "entity_id": e.id, "days_overdue": (now - e.created_at).days, "link": "/manual-review"})

    from app.models.approval import ApprovalRequest
    old_approvals = db.query(ApprovalRequest).filter(
        ApprovalRequest.status == "pending",
        ApprovalRequest.created_at < now - timedelta(days=2)
    ).limit(10).all()
    for a in old_approvals:
        overdue.append({"type": "approval", "title": f"Approval #{a.id} pending", "entity_id": a.id, "days_overdue": (now - a.created_at).days, "link": "/approvals"})

    return sorted(overdue, key=lambda x: -x["days_overdue"])[:15]


# --- Phase 22.1 additions ---

def get_map_readiness(db: Session, user: AuthenticatedUser) -> dict[str, Any]:
    """Map-ready placeholders (Phase 22.1)."""
    from app.models.tracking import TrackingObservation
    from app.models.transport import TransportJob

    obs_with_coords = db.query(TrackingObservation).filter(
        TrackingObservation.latitude.isnot(None)
    ).count()
    transport_with_loc = db.query(TransportJob).filter(
        TransportJob.last_latitude.isnot(None)
    ).count()

    return {
        "ocean_visibility": {"enabled": False, "source": "placeholder", "items_count": obs_with_coords, "message": "Map provider integration will be added later."},
        "domestic_movement": {"enabled": False, "source": "placeholder", "items_count": transport_with_loc, "message": "Map provider integration will be added later."},
        "vessel_container_map": {"enabled": False, "source": "placeholder", "items_count": obs_with_coords, "message": "Map provider integration will be added later."},
        "transport_gps_map": {"enabled": False, "source": "placeholder", "items_count": transport_with_loc, "message": "Map provider integration will be added later."},
    }


def get_eta_etd_changes(db: Session, user: AuthenticatedUser) -> list[dict[str, Any]]:
    """ETA/ETD changes from tracking observations (Phase 22.1)."""
    from app.models.tracking import TrackingObservation

    obs_with_eta = db.query(TrackingObservation).filter(
        TrackingObservation.eta.isnot(None)
    ).order_by(TrackingObservation.received_at.desc()).limit(20).all()

    changes = []
    for o in obs_with_eta:
        changes.append({
            "shipment_id": o.shipment_id,
            "observation_id": o.id,
            "latest_eta": o.eta.isoformat() if o.eta else None,
            "latest_etd": o.etd.isoformat() if o.etd else None,
            "source": o.source,
            "confidence": o.confidence,
            "location": o.location_text,
            "vessel_name": o.vessel_name,
            "received_at": o.received_at.isoformat(),
            "link": f"/shipments/{o.shipment_id}" if o.shipment_id else None,
        })
    return changes


def get_tracking_source_health(db: Session, user: AuthenticatedUser) -> list[dict[str, Any]]:
    """Tracking adapter health (Phase 22.1)."""
    from app.models.tracking import TrackingProvider, TrackingSyncRun, TrackingWatchItem

    providers = db.query(TrackingProvider).order_by(TrackingProvider.created_at).all()
    now = datetime.utcnow()
    result = []

    for p in providers:
        failed_syncs = db.query(TrackingSyncRun).filter(
            TrackingSyncRun.tracking_provider_id == p.id,
            TrackingSyncRun.status == "failed"
        ).count()

        stale_cutoff = now - timedelta(hours=24)
        stale_watches = db.query(TrackingWatchItem).filter(
            TrackingWatchItem.tracking_provider_id == p.id,
            TrackingWatchItem.status == "active",
            (TrackingWatchItem.last_sync_at < stale_cutoff) | (TrackingWatchItem.last_sync_at.is_(None))
        ).count()

        last_sync = db.query(TrackingSyncRun).filter(
            TrackingSyncRun.tracking_provider_id == p.id,
            TrackingSyncRun.status == "completed"
        ).order_by(TrackingSyncRun.completed_at.desc()).first()

        result.append({
            "provider_id": p.id,
            "name": p.name,
            "provider_type": p.provider_type,
            "status": p.status,
            "is_manual": p.is_manual,
            "is_mock": p.is_mock,
            "requires_credentials": p.requires_credentials,
            "last_sync_at": last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else None,
            "failed_sync_count": failed_syncs,
            "stale_watch_items": stale_watches,
        })
    return result


def get_stale_data_warnings(db: Session, user: AuthenticatedUser) -> dict[str, Any]:
    """Stale data monitor (Phase 22.1)."""
    now = datetime.utcnow()
    warnings_list = []

    from app.models.shipment import Shipment
    stale_shipments = db.query(Shipment).filter(
        Shipment.created_at < now - timedelta(days=STALE_THRESHOLDS["shipment_update_days"]),
        Shipment.status != "Completed"
    ).count()
    if stale_shipments:
        warnings_list.append({"category": "shipments", "count": stale_shipments, "threshold": f"{STALE_THRESHOLDS['shipment_update_days']} days", "link": "/shipments"})

    from app.models.container import Container
    stale_containers = db.query(Container).filter(
        Container.updated_at < now - timedelta(days=STALE_THRESHOLDS["container_update_days"]),
        Container.is_active.is_(True)
    ).count()
    if stale_containers:
        warnings_list.append({"category": "containers", "count": stale_containers, "threshold": f"{STALE_THRESHOLDS['container_update_days']} days", "link": "/shipments"})

    from app.models.tracking import TrackingWatchItem
    stale_tracking = db.query(TrackingWatchItem).filter(
        TrackingWatchItem.status == "active",
        (TrackingWatchItem.last_sync_at < now - timedelta(hours=STALE_THRESHOLDS["tracking_sync_hours"])) | (TrackingWatchItem.last_sync_at.is_(None))
    ).count()
    if stale_tracking:
        warnings_list.append({"category": "tracking", "count": stale_tracking, "threshold": f"{STALE_THRESHOLDS['tracking_sync_hours']} hours", "link": "/tracking"})

    from app.models.transport import TransportJob
    stale_transport = db.query(TransportJob).filter(
        TransportJob.status == "in_transit",
        TransportJob.last_location_at < now - timedelta(hours=STALE_THRESHOLDS["transport_location_hours"])
    ).count()
    if stale_transport:
        warnings_list.append({"category": "transport", "count": stale_transport, "threshold": f"{STALE_THRESHOLDS['transport_location_hours']} hours", "link": "/transport"})

    from app.models.exception_case import ExceptionCase
    stale_exceptions = db.query(ExceptionCase).filter(
        ExceptionCase.status.in_(["open", "in_progress"]),
        ExceptionCase.created_at < now - timedelta(days=STALE_THRESHOLDS["exception_open_days"])
    ).count()
    if stale_exceptions:
        warnings_list.append({"category": "exceptions", "count": stale_exceptions, "threshold": f"{STALE_THRESHOLDS['exception_open_days']} days", "link": "/manual-review"})

    from app.models.approval import ApprovalRequest
    stale_approvals = db.query(ApprovalRequest).filter(
        ApprovalRequest.status == "pending",
        ApprovalRequest.created_at < now - timedelta(days=STALE_THRESHOLDS["approval_pending_days"])
    ).count()
    if stale_approvals:
        warnings_list.append({"category": "approvals", "count": stale_approvals, "threshold": f"{STALE_THRESHOLDS['approval_pending_days']} days", "link": "/approvals"})

    return {"warnings": warnings_list, "total_stale": sum(w["count"] for w in warnings_list), "thresholds": STALE_THRESHOLDS}


def get_party_performance(db: Session, user: AuthenticatedUser) -> dict[str, Any]:
    """Basic party performance snapshot (Phase 22.1)."""
    from app.models.customs import CustomsCase, CustomsQuery
    from app.models.transport import TransportJob
    from app.models.portal import PortalRequest

    cha_open_queries = db.query(CustomsQuery).filter(CustomsQuery.status == "open").count()
    cha_delayed = db.query(CustomsCase).filter(CustomsCase.status == "delayed").count()
    transporter_delayed = db.query(TransportJob).filter(TransportJob.status == "delayed").count()
    transporter_empty_pending = db.query(TransportJob).filter(TransportJob.status == "empty_return_pending").count()
    customer_open_requests = db.query(PortalRequest).filter(PortalRequest.status.in_(["open", "in_progress"])).count()

    return {
        "cha": {"open_queries": cha_open_queries, "delayed_cases": cha_delayed},
        "transporter": {"delayed_jobs": transporter_delayed, "empty_return_pending": transporter_empty_pending},
        "customer": {"open_requests": customer_open_requests},
    }


# --- Internal helpers ---

def _get_operations(db: Session) -> dict[str, Any]:
    from app.models.shipment import Shipment
    from app.models.task import Task
    total = db.query(Shipment).filter(Shipment.status != "Completed").count()
    exports = db.query(Shipment).filter(Shipment.type == "export", Shipment.status != "Completed").count()
    imports = db.query(Shipment).filter(Shipment.type == "import", Shipment.status != "Completed").count()
    open_tasks = db.query(Task).filter(Task.status == "open").count()
    return {"active_shipments": total, "exports": exports, "imports": imports, "open_tasks": open_tasks}


def _get_containers(db: Session) -> dict[str, Any]:
    from app.models.container import Container
    active = db.query(Container).filter(Container.is_active.is_(True)).count()
    return {"active": active}


def _get_documents(db: Session) -> dict[str, Any]:
    from app.models.document import Document
    pending = db.query(Document).filter(Document.status == "pending").count()
    return {"pending_review": pending}


def _get_finance(db: Session, user: AuthenticatedUser) -> dict[str, Any]:
    from app.models.finance_control import CreditHoldRecord
    holds = db.query(CreditHoldRecord).filter(CreditHoldRecord.status == "active").count()
    if user.role == "ADMIN":
        return {"credit_holds": holds}
    return {"credit_holds": holds}


def _get_exceptions_approvals(db: Session) -> dict[str, Any]:
    from app.models.exception_case import ExceptionCase
    from app.models.approval import ApprovalRequest
    open_exc = db.query(ExceptionCase).filter(ExceptionCase.status.in_(["open", "in_progress"])).count()
    critical = db.query(ExceptionCase).filter(ExceptionCase.status.in_(["open", "in_progress"]), ExceptionCase.severity == "critical").count()
    pending_app = db.query(ApprovalRequest).filter(ApprovalRequest.status == "pending").count()
    return {"open_exceptions": open_exc, "critical_exceptions": critical, "pending_approvals": pending_app}


def _get_customs(db: Session) -> dict[str, Any]:
    from app.models.customs import CustomsCase, CustomsQuery
    active = db.query(CustomsCase).filter(CustomsCase.status.notin_(["closed", "cancelled"])).count()
    queries = db.query(CustomsQuery).filter(CustomsQuery.status == "open").count()
    return {"active_cases": active, "open_queries": queries}


def _get_transport(db: Session) -> dict[str, Any]:
    from app.models.transport import TransportJob, TransportException
    active = db.query(TransportJob).filter(TransportJob.status.notin_(["closed", "cancelled"])).count()
    delayed = db.query(TransportJob).filter(TransportJob.status == "delayed").count()
    in_transit = db.query(TransportJob).filter(TransportJob.status == "in_transit").count()
    exceptions = db.query(TransportException).filter(TransportException.status == "open").count()
    return {"active_jobs": active, "in_transit": in_transit, "delayed": delayed, "open_exceptions": exceptions}


def _get_tracking(db: Session) -> dict[str, Any]:
    from app.models.tracking import TrackingWatchItem, TrackingMismatch, TrackingSuggestedUpdate
    active_watches = db.query(TrackingWatchItem).filter(TrackingWatchItem.status == "active").count()
    mismatches = db.query(TrackingMismatch).filter(TrackingMismatch.status == "open").count()
    pending_sugg = db.query(TrackingSuggestedUpdate).filter(TrackingSuggestedUpdate.status == "pending_review").count()
    return {"active_watches": active_watches, "open_mismatches": mismatches, "pending_suggestions": pending_sugg}


def _get_portal(db: Session) -> dict[str, Any]:
    from app.models.portal import PortalAccount, PortalRequest
    accounts = db.query(PortalAccount).filter(PortalAccount.status == "active").count()
    requests = db.query(PortalRequest).filter(PortalRequest.status.in_(["open", "in_progress"])).count()
    return {"active_accounts": accounts, "open_requests": requests}


def _get_bot_governance(db: Session, user: AuthenticatedUser) -> dict[str, Any]:
    from app.models.bot_governance import BotGuardrailViolation, BotLearningCandidate
    violations = db.query(BotGuardrailViolation).count()
    learning = db.query(BotLearningCandidate).filter(BotLearningCandidate.status == "pending").count()
    if user.role != "ADMIN":
        return {"guardrail_violations": violations}
    return {"guardrail_violations": violations, "learning_candidates_pending": learning}
