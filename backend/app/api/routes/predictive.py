"""Phase 23 Predictive Intelligence API routes."""
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.services.audit_service import record_audit_log
from app.services.predictive.predictive_service import (
    add_feedback, dismiss_prediction, get_prediction, get_prediction_explanations,
    get_prediction_recommendations, get_predictive_summary, list_prediction_runs,
    list_predictions, record_outcome, review_recommendation, run_predictions,
    list_prediction_models,
)

router = APIRouter(prefix="/predictive", tags=["predictive"])
shipment_predictive_router = APIRouter(prefix="/shipments", tags=["shipment-predictive"])

AnyUser = Depends(require_roles("ADMIN", "STAFF", "VIEW_ONLY"))
OperationalUser = Depends(require_roles("ADMIN", "STAFF"))
AdminUser = Depends(require_roles("ADMIN"))


# --- Schemas ---
class PredictionRecordRead(BaseModel):
    id: int; prediction_key: str; risk_domain: str; entity_type: str
    shipment_id: Optional[int] = None; risk_score: float; risk_level: str
    confidence: float; title: str; summary: Optional[str] = None
    predicted_event: Optional[str] = None; status: str; created_at: datetime
    class Config:
        from_attributes = True

class RunRead(BaseModel):
    id: int; run_number: str; scope: str; status: str; started_at: datetime
    completed_at: Optional[datetime] = None; models_run: int; records_created: int
    high_risk_count: int; medium_risk_count: int; low_risk_count: int
    class Config:
        from_attributes = True

class ExplanationRead(BaseModel):
    id: int; factor_key: str; factor_label: str; factor_value: Optional[str] = None
    impact: str; weight: Optional[float] = None
    class Config:
        from_attributes = True

class RecommendationRead(BaseModel):
    id: int; recommendation_type: str; title: str; description: Optional[str] = None
    priority: str; requires_approval: bool; status: str
    reviewed_by_name: Optional[str] = None
    class Config:
        from_attributes = True

class ModelRead(BaseModel):
    id: int; model_key: str; name: str; model_type: str; risk_domain: str
    status: str; version: str; is_active: bool
    class Config:
        from_attributes = True

class OutcomeCreate(BaseModel):
    outcome_status: str = "reviewed"
    actual_event_occurred: Optional[bool] = None
    accuracy_label: Optional[str] = None
    notes: Optional[str] = None

class FeedbackCreate(BaseModel):
    feedback_type: str = "general"
    rating: Optional[int] = None
    feedback_text: Optional[str] = None


# --- Summary ---
@router.get("/summary")
def predictive_summary(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return get_predictive_summary(db, current_user)

# --- Models ---
@router.get("/models", response_model=list[ModelRead])
def list_models(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [ModelRead.model_validate(m) for m in list_prediction_models(db)]

# --- Runs ---
@router.get("/runs", response_model=list[RunRead])
def list_runs(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [RunRead.model_validate(r) for r in list_prediction_runs(db, limit=limit)]

@router.post("/run", response_model=RunRead, status_code=201)
def run_pred(request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    run = run_predictions(db, scope="all_active", user=current_user)
    record_audit_log(db, current_user, "predictive.run", "prediction_run", entity_id=run.id, description=f"Prediction run: {run.records_created} records", request=request)
    return RunRead.model_validate(run)

@router.post("/run/shipment/{shipment_id}", response_model=RunRead, status_code=201)
def run_pred_shipment(shipment_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    run = run_predictions(db, scope="shipment", user=current_user, shipment_id=shipment_id)
    return RunRead.model_validate(run)

# --- Predictions ---
@router.get("/predictions", response_model=list[PredictionRecordRead])
def list_preds(shipment_id: Optional[int] = None, risk_level: Optional[str] = None, status: Optional[str] = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [PredictionRecordRead.model_validate(p) for p in list_predictions(db, shipment_id=shipment_id, risk_level=risk_level, status=status, limit=limit, offset=offset)]

@router.get("/predictions/{prediction_id}", response_model=PredictionRecordRead)
def get_pred(prediction_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    p = get_prediction(db, prediction_id)
    if not p: raise HTTPException(404, "Prediction not found")
    return PredictionRecordRead.model_validate(p)

@router.post("/predictions/{prediction_id}/dismiss", response_model=PredictionRecordRead)
def dismiss_pred(prediction_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try: p = dismiss_prediction(db, prediction_id, current_user)
    except ValueError as e: raise HTTPException(404, str(e))
    return PredictionRecordRead.model_validate(p)

@router.post("/predictions/{prediction_id}/outcome", status_code=201)
def pred_outcome(prediction_id: int, body: OutcomeCreate, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    o = record_outcome(db, prediction_id, body.model_dump(), current_user)
    return {"id": o.id, "status": "recorded"}

@router.post("/predictions/{prediction_id}/feedback", status_code=201)
def pred_feedback(prediction_id: int, body: FeedbackCreate, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    fb = add_feedback(db, prediction_id, body.model_dump(), current_user)
    return {"id": fb.id, "status": "recorded"}

# --- Explanations / Recommendations ---
@router.get("/predictions/{prediction_id}/explanations", response_model=list[ExplanationRead])
def pred_explanations(prediction_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [ExplanationRead.model_validate(e) for e in get_prediction_explanations(db, prediction_id)]

@router.get("/predictions/{prediction_id}/recommendations", response_model=list[RecommendationRead])
def pred_recommendations(prediction_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [RecommendationRead.model_validate(r) for r in get_prediction_recommendations(db, prediction_id)]

@router.post("/recommendations/{recommendation_id}/review", response_model=RecommendationRead)
def review_rec(recommendation_id: int, decision: str = Query(...), db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try: r = review_recommendation(db, recommendation_id, decision, current_user)
    except ValueError as e: raise HTTPException(404, str(e))
    return RecommendationRead.model_validate(r)

# --- Shipment-specific ---
@shipment_predictive_router.get("/{shipment_id}/predictions", response_model=list[PredictionRecordRead])
def shipment_predictions(shipment_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [PredictionRecordRead.model_validate(p) for p in list_predictions(db, shipment_id=shipment_id)]

@shipment_predictive_router.post("/{shipment_id}/predictions/run", response_model=RunRead, status_code=201)
def shipment_run_pred(shipment_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    run = run_predictions(db, scope="shipment", user=current_user, shipment_id=shipment_id)
    return RunRead.model_validate(run)
