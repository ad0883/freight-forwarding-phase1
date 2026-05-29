"""Phase 23 Predictive Intelligence service."""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.predictive import (
    PredictionActivityLog, PredictionExplanation, PredictionFeedback,
    PredictionModel, PredictionOutcome, PredictionRecommendation,
    PredictionRecord, PredictionRun,
)

logger = logging.getLogger(__name__)

DEFAULT_MODELS = [
    {"model_key": "eta_delay_rule", "name": "ETA Delay Risk", "risk_domain": "eta_delay"},
    {"model_key": "demurrage_risk_rule", "name": "Demurrage Risk", "risk_domain": "demurrage"},
    {"model_key": "detention_risk_rule", "name": "Detention Risk", "risk_domain": "detention"},
    {"model_key": "customs_delay_rule", "name": "Customs Delay Risk", "risk_domain": "customs_delay"},
    {"model_key": "document_readiness_rule", "name": "Document Readiness Risk", "risk_domain": "document_readiness"},
    {"model_key": "finance_credit_risk_rule", "name": "Finance/Credit Risk", "risk_domain": "finance_credit"},
    {"model_key": "transport_delay_rule", "name": "Transport Delay Risk", "risk_domain": "transport_delay"},
    {"model_key": "tracking_reliability_rule", "name": "Tracking Reliability Risk", "risk_domain": "tracking_reliability"},
    {"model_key": "party_performance_rule", "name": "Party Performance Risk", "risk_domain": "party_performance"},
    {"model_key": "sla_breach_rule", "name": "SLA Breach Risk", "risk_domain": "sla_breach"},
    {"model_key": "overall_shipment_risk", "name": "Overall Shipment Risk", "risk_domain": "overall_shipment_risk"},
]


def seed_default_prediction_models(db: Session) -> None:
    for m in DEFAULT_MODELS:
        existing = db.query(PredictionModel).filter(PredictionModel.model_key == m["model_key"]).first()
        if not existing:
            db.add(PredictionModel(model_key=m["model_key"], name=m["name"], model_type="rule_based", risk_domain=m["risk_domain"], status="active", version="1.0", is_active=True, created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
    db.commit()


def list_prediction_models(db: Session) -> list[PredictionModel]:
    return db.query(PredictionModel).order_by(PredictionModel.model_key).all()


def run_predictions(db: Session, scope: str = "all_active", user: Optional[AuthenticatedUser] = None, shipment_id: Optional[int] = None) -> PredictionRun:
    """Run prediction engine. Creates prediction records based on rule-based scoring."""
    now = datetime.utcnow()
    run = PredictionRun(
        run_number=f"PRED-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        scope=scope, status="running", started_at=now,
        created_by_user_id=user.id if user else None,
        created_by_name=user.name if user else None,
    )
    db.add(run)
    db.flush()

    try:
        records = []
        models = db.query(PredictionModel).filter(PredictionModel.is_active.is_(True)).all()

        from app.models.shipment import Shipment
        q = db.query(Shipment).filter(Shipment.status != "Completed")
        if shipment_id:
            q = q.filter(Shipment.id == shipment_id)
        shipments = q.limit(50).all()

        for shipment in shipments:
            for model in models:
                score, factors = _score_shipment_for_model(db, shipment, model)
                if score > 20:  # Only create records for meaningful risk
                    level = "critical" if score >= 80 else "high" if score >= 60 else "medium" if score >= 40 else "low"
                    record = PredictionRecord(
                        prediction_run_id=run.id, prediction_model_id=model.id,
                        prediction_key=f"{model.model_key}_{shipment.id}",
                        risk_domain=model.risk_domain, entity_type="shipment",
                        entity_id=shipment.id, shipment_id=shipment.id,
                        risk_score=score, risk_level=level,
                        confidence=min(0.95, 0.5 + len(factors) * 0.1),
                        title=f"{model.name}: {shipment.shipment_code}",
                        summary=f"Risk score {score} for {model.risk_domain}",
                        predicted_event=model.risk_domain,
                        predicted_at=now,
                        prediction_window_start=now,
                        prediction_window_end=now + timedelta(days=7),
                        status="active", created_at=now, updated_at=now,
                    )
                    db.add(record)
                    db.flush()
                    # Add explanations
                    for f in factors:
                        db.add(PredictionExplanation(
                            prediction_record_id=record.id,
                            factor_key=f["key"], factor_label=f["label"],
                            factor_value=f.get("value"), impact=f.get("impact", "medium"),
                            weight=f.get("weight"), created_at=now,
                        ))
                    # Add recommendation if high risk
                    if level in ("high", "critical"):
                        db.add(PredictionRecommendation(
                            prediction_record_id=record.id,
                            recommendation_type="manual_review",
                            title=f"Review {model.risk_domain} risk for {shipment.shipment_code}",
                            priority=level, requires_approval=level == "critical",
                            status="pending", created_at=now,
                        ))
                    records.append(record)

        run.models_run = len(models)
        run.records_created = len(records)
        run.high_risk_count = sum(1 for r in records if r.risk_level in ("high", "critical"))
        run.medium_risk_count = sum(1 for r in records if r.risk_level == "medium")
        run.low_risk_count = sum(1 for r in records if r.risk_level == "low")
        run.status = "completed"
        run.completed_at = datetime.utcnow()
    except Exception as e:
        logger.error(f"Prediction run failed: {e}")
        run.status = "failed"
        run.error_message = str(e)[:500]
        run.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(run)
    return run


def _score_shipment_for_model(db: Session, shipment, model: PredictionModel) -> tuple:
    """Score a shipment for a specific model. Returns (score, factors)."""
    factors = []
    score = 0

    if model.risk_domain == "transport_delay":
        from app.models.transport import TransportJob
        delayed = db.query(TransportJob).filter(TransportJob.shipment_id == shipment.id, TransportJob.status == "delayed").count()
        if delayed:
            score += 40 * delayed
            factors.append({"key": "transport_delayed", "label": f"{delayed} transport job(s) delayed", "impact": "high", "weight": 40.0})

    elif model.risk_domain == "tracking_reliability":
        from app.models.tracking import TrackingWatchItem, TrackingMismatch
        stale = db.query(TrackingWatchItem).filter(TrackingWatchItem.shipment_id == shipment.id, TrackingWatchItem.status == "active", TrackingWatchItem.last_sync_at < datetime.utcnow() - timedelta(hours=24)).count()
        mismatches = db.query(TrackingMismatch).filter(TrackingMismatch.shipment_id == shipment.id, TrackingMismatch.status == "open").count()
        if stale:
            score += 30 * stale
            factors.append({"key": "tracking_stale", "label": f"{stale} stale tracking item(s)", "impact": "medium", "weight": 30.0})
        if mismatches:
            score += 25 * mismatches
            factors.append({"key": "tracking_mismatch", "label": f"{mismatches} open mismatch(es)", "impact": "high", "weight": 25.0})

    elif model.risk_domain == "customs_delay":
        from app.models.customs import CustomsCase, CustomsQuery
        open_queries = db.query(CustomsQuery).filter(CustomsQuery.shipment_id == shipment.id, CustomsQuery.status == "open").count()
        if open_queries:
            score += 35 * open_queries
            factors.append({"key": "customs_query_open", "label": f"{open_queries} open customs query(ies)", "impact": "high", "weight": 35.0})

    elif model.risk_domain == "finance_credit":
        from app.models.finance_control import CreditHoldRecord
        holds = db.query(CreditHoldRecord).filter(CreditHoldRecord.status == "active").count()
        if holds:
            score += 50
            factors.append({"key": "credit_hold_active", "label": "Active credit hold", "impact": "high", "weight": 50.0})

    elif model.risk_domain == "demurrage":
        from app.models.container import Container
        containers = db.query(Container).filter(Container.shipment_id == shipment.id, Container.is_active.is_(True)).all()
        for c in containers:
            if c.empty_return_deadline and c.empty_return_deadline < datetime.utcnow().date() and not c.empty_return_date:
                score += 60
                factors.append({"key": "empty_return_overdue", "label": f"Container {c.container_number} empty return overdue", "impact": "critical", "weight": 60.0})

    elif model.risk_domain == "overall_shipment_risk":
        # Aggregate: check exceptions, approvals, transport, tracking
        from app.models.exception_case import ExceptionCase
        from app.models.approval import ApprovalRequest
        exc = db.query(ExceptionCase).filter(ExceptionCase.shipment_id == shipment.id, ExceptionCase.status.in_(["open", "in_progress"])).count()
        if exc:
            score += 20 * exc
            factors.append({"key": "open_exceptions", "label": f"{exc} open exception(s)", "impact": "medium", "weight": 20.0})
        approvals = db.query(ApprovalRequest).filter(ApprovalRequest.shipment_id == shipment.id, ApprovalRequest.status == "pending").count()
        if approvals:
            score += 15 * approvals
            factors.append({"key": "pending_approvals", "label": f"{approvals} pending approval(s)", "impact": "medium", "weight": 15.0})

    return min(100, score), factors


def list_prediction_runs(db: Session, *, limit: int = 20) -> list[PredictionRun]:
    return db.query(PredictionRun).order_by(PredictionRun.started_at.desc()).limit(limit).all()


def list_predictions(db: Session, *, shipment_id: Optional[int] = None, risk_level: Optional[str] = None, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[PredictionRecord]:
    q = db.query(PredictionRecord)
    if shipment_id:
        q = q.filter(PredictionRecord.shipment_id == shipment_id)
    if risk_level:
        q = q.filter(PredictionRecord.risk_level == risk_level)
    if status:
        q = q.filter(PredictionRecord.status == status)
    return q.order_by(PredictionRecord.risk_score.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0)).all()


def get_prediction(db: Session, prediction_id: int) -> Optional[PredictionRecord]:
    return db.query(PredictionRecord).filter(PredictionRecord.id == prediction_id).first()


def get_prediction_explanations(db: Session, prediction_id: int) -> list[PredictionExplanation]:
    return db.query(PredictionExplanation).filter(PredictionExplanation.prediction_record_id == prediction_id).all()


def get_prediction_recommendations(db: Session, prediction_id: int) -> list[PredictionRecommendation]:
    return db.query(PredictionRecommendation).filter(PredictionRecommendation.prediction_record_id == prediction_id).all()


def dismiss_prediction(db: Session, prediction_id: int, user: AuthenticatedUser) -> PredictionRecord:
    p = get_prediction(db, prediction_id)
    if not p:
        raise ValueError("Prediction not found")
    p.status = "dismissed"
    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return p


def record_outcome(db: Session, prediction_id: int, data: dict[str, Any], user: AuthenticatedUser) -> PredictionOutcome:
    outcome = PredictionOutcome(
        prediction_record_id=prediction_id,
        outcome_status=data.get("outcome_status", "reviewed"),
        actual_event_occurred=data.get("actual_event_occurred"),
        actual_event_at=data.get("actual_event_at"),
        accuracy_label=data.get("accuracy_label"),
        reviewed_by_user_id=user.id, reviewed_by_name=user.name,
        reviewed_at=datetime.utcnow(), notes=data.get("notes"),
    )
    db.add(outcome)
    # Update prediction status
    pred = get_prediction(db, prediction_id)
    if pred and data.get("actual_event_occurred") is True:
        pred.status = "confirmed"
    elif pred and data.get("actual_event_occurred") is False:
        pred.status = "false_positive"
    db.commit()
    db.refresh(outcome)
    return outcome


def add_feedback(db: Session, prediction_id: int, data: dict[str, Any], user: AuthenticatedUser) -> PredictionFeedback:
    fb = PredictionFeedback(
        prediction_record_id=prediction_id,
        feedback_type=data.get("feedback_type", "general"),
        rating=data.get("rating"),
        feedback_text=data.get("feedback_text"),
        created_by_user_id=user.id, created_by_name=user.name,
        created_at=datetime.utcnow(),
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


def review_recommendation(db: Session, recommendation_id: int, decision: str, user: AuthenticatedUser) -> PredictionRecommendation:
    rec = db.query(PredictionRecommendation).filter(PredictionRecommendation.id == recommendation_id).first()
    if not rec:
        raise ValueError("Recommendation not found")
    rec.status = decision  # "accepted", "rejected", "deferred"
    rec.reviewed_at = datetime.utcnow()
    rec.reviewed_by_user_id = user.id
    rec.reviewed_by_name = user.name
    db.commit()
    db.refresh(rec)
    return rec


def get_predictive_summary(db: Session, user: AuthenticatedUser) -> dict[str, Any]:
    active = db.query(PredictionRecord).filter(PredictionRecord.status == "active").all()
    pending_recs = db.query(PredictionRecommendation).filter(PredictionRecommendation.status == "pending").count()
    return {
        "total_active": len(active),
        "critical": sum(1 for p in active if p.risk_level == "critical"),
        "high": sum(1 for p in active if p.risk_level == "high"),
        "medium": sum(1 for p in active if p.risk_level == "medium"),
        "low": sum(1 for p in active if p.risk_level == "low"),
        "pending_recommendations": pending_recs,
        "domains": _count_by_domain(active),
    }


def _count_by_domain(records) -> dict[str, int]:
    counts = {}
    for r in records:
        counts[r.risk_domain] = counts.get(r.risk_domain, 0) + 1
    return counts
