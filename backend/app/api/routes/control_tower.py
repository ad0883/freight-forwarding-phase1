"""Phase 22 + 22.1 Control Tower Dashboard API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.services.control_tower.control_tower_service import (
    get_control_tower_summary,
    get_eta_etd_changes,
    get_map_readiness,
    get_operations_overview,
    get_party_performance,
    get_risk_heatmap,
    get_sla_overdue,
    get_stale_data_warnings,
    get_top_risks,
    get_tracking_source_health,
)

router = APIRouter(prefix="/control-tower", tags=["control-tower"])

AnyUser = Depends(require_roles("ADMIN", "STAFF", "VIEW_ONLY"))
OperationalUser = Depends(require_roles("ADMIN", "STAFF"))
AdminUser = Depends(require_roles("ADMIN"))


@router.get("/summary")
def control_tower_summary(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    """Unified control tower summary."""
    return get_control_tower_summary(db, current_user)


@router.get("/operations")
def operations(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return get_operations_overview(db, current_user)


@router.get("/risk-heatmap")
def risk_heatmap(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    """Real-data risk heatmap."""
    return get_risk_heatmap(db, current_user)


@router.get("/top-risks")
def top_risks(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return get_top_risks(db, current_user)


@router.get("/sla-overdue")
def sla_overdue(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return get_sla_overdue(db, current_user)


@router.get("/map-readiness")
def map_readiness(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    """Map-ready placeholders (Phase 22.1)."""
    return get_map_readiness(db, current_user)


@router.get("/eta-etd-changes")
def eta_etd_changes(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    """ETA/ETD change panel (Phase 22.1)."""
    return get_eta_etd_changes(db, current_user)


@router.get("/tracking-source-health")
def tracking_source_health(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    """Tracking adapter health (Phase 22.1)."""
    return get_tracking_source_health(db, current_user)


@router.get("/stale-data")
def stale_data(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    """Stale data monitor (Phase 22.1)."""
    return get_stale_data_warnings(db, current_user)


@router.get("/party-performance")
def party_performance(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    """Party performance snapshot (Phase 22.1)."""
    return get_party_performance(db, current_user)
