"""Phase 17 bot governance API routes."""
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.models.bot_governance import (
    BotActionRecord, BotAgent, BotEvaluationRun, BotFeedbackRecord,
    BotGuardrailViolation, BotLearningCandidate, BotPerformanceSnapshot,
    BotPromptVersion, BotQualityReview, BotRuleVersion, BotTrainingCase,
)
from app.services.audit_service import record_audit_log
from app.services.bot_governance.bot_core_service import (
    activate_prompt_version, activate_rule_version, create_bot_feedback,
    create_evaluation_run, create_learning_candidate, create_performance_snapshot,
    create_prompt_version, create_rule_version, create_training_case,
    get_governance_summary, list_bot_action_records, list_bot_feedback,
    list_learning_candidates, record_bot_action, record_guardrail_violation,
    review_learning_candidate, run_evaluation, update_bot_action_outcome,
)
from app.services.bot_governance.bot_registry_service import (
    list_bot_agents, pause_bot_agent, resume_bot_agent, update_bot_agent,
)

router = APIRouter(prefix="/bot-governance", tags=["bot-governance"])
AnyUser = Depends(require_roles("ADMIN", "STAFF", "VIEW_ONLY"))
OperationalUser = Depends(require_roles("ADMIN", "STAFF"))
AdminUser = Depends(require_roles("ADMIN"))


# --- Schemas (inline for brevity) ---
class BotAgentRead(BaseModel):
    id: int; bot_key: str; name: str; bot_type: str; status: str; risk_level: str
    is_approval_required: bool; created_at: datetime; updated_at: datetime
    class Config:
        from_attributes = True

class BotActionRecordRead(BaseModel):
    id: int; bot_key: str; action_type: str; source: str; status: str; risk_level: str
    confidence: Optional[Any] = None; outcome_status: Optional[str] = None
    entity_type: Optional[str] = None; entity_id: Optional[int] = None
    shipment_id: Optional[int] = None; created_at: datetime
    safe_summary_json: Optional[dict] = None
    class Config:
        from_attributes = True

class BotFeedbackRead(BaseModel):
    id: int; feedback_type: str; rating: Optional[int] = None; is_correct: Optional[bool] = None
    human_decision: Optional[str] = None; feedback_text: Optional[str] = None
    created_by_name: Optional[str] = None; created_at: datetime
    class Config:
        from_attributes = True

class LearningCandidateRead(BaseModel):
    id: int; bot_key: str; candidate_type: str; title: str; risk_level: str; status: str
    description: Optional[str] = None; created_at: datetime
    reviewed_by_name: Optional[str] = None; reviewed_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class PromptVersionRead(BaseModel):
    id: int; bot_key: str; version: str; name: str; status: str
    safe_summary: Optional[str] = None; created_by_name: Optional[str] = None
    approved_by_name: Optional[str] = None; created_at: datetime
    class Config:
        from_attributes = True

class RuleVersionRead(BaseModel):
    id: int; bot_key: str; version: str; name: str; status: str
    safe_summary: Optional[str] = None; created_by_name: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class EvalRunRead(BaseModel):
    id: int; bot_key: str; evaluation_name: str; status: str
    total_cases: int; passed_cases: int; failed_cases: int
    accuracy: Optional[Any] = None; created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class GuardrailViolationRead(BaseModel):
    id: int; bot_key: str; violation_type: str; severity: str; message: str
    blocked_action: Optional[str] = None; created_at: datetime
    class Config:
        from_attributes = True


# --- Summary ---
@router.get("/summary")
def summary(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return get_governance_summary(db, current_user)

# --- Agents ---
@router.get("/agents", response_model=list[BotAgentRead])
def agents_list(status: Optional[str] = None, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [BotAgentRead.model_validate(a) for a in list_bot_agents(db, status_filter=status)]

@router.get("/agents/{bot_agent_id}", response_model=BotAgentRead)
def agent_detail(bot_agent_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    a = db.query(BotAgent).filter(BotAgent.id == bot_agent_id).first()
    if not a: raise HTTPException(404, "Bot agent not found")
    return BotAgentRead.model_validate(a)

@router.patch("/agents/{bot_agent_id}", response_model=BotAgentRead)
def agent_update(bot_agent_id: int, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    import json
    body = {}  # simplified - accept any JSON body
    try: a = update_bot_agent(db, bot_agent_id, body, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    return BotAgentRead.model_validate(a)

@router.post("/agents/{bot_agent_id}/pause", response_model=BotAgentRead)
def agent_pause(bot_agent_id: int, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try: a = pause_bot_agent(db, bot_agent_id, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    record_audit_log(db, current_user, "bot.agent_pause", "bot_agent", entity_id=a.id, description=f"Bot {a.bot_key} paused.", request=request)
    return BotAgentRead.model_validate(a)

@router.post("/agents/{bot_agent_id}/resume", response_model=BotAgentRead)
def agent_resume(bot_agent_id: int, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try: a = resume_bot_agent(db, bot_agent_id, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    record_audit_log(db, current_user, "bot.agent_resume", "bot_agent", entity_id=a.id, description=f"Bot {a.bot_key} resumed.", request=request)
    return BotAgentRead.model_validate(a)

# --- Actions ---
@router.get("/actions", response_model=list[BotActionRecordRead])
def actions_list(bot_key: Optional[str] = None, status: Optional[str] = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [BotActionRecordRead.model_validate(a) for a in list_bot_action_records(db, bot_key=bot_key, status_filter=status, limit=limit, offset=offset)]

@router.patch("/actions/{action_id}/outcome")
def action_outcome(action_id: int, outcome: str = Query(...), db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try: rec = update_bot_action_outcome(db, action_id, outcome, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    return BotActionRecordRead.model_validate(rec)

# --- Feedback ---
@router.get("/feedback", response_model=list[BotFeedbackRead])
def feedback_list(bot_key: Optional[str] = None, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [BotFeedbackRead.model_validate(f) for f in list_bot_feedback(db, bot_key=bot_key, limit=limit)]

@router.post("/feedback", response_model=BotFeedbackRead, status_code=201)
def feedback_create(feedback_type: str = Query(...), feedback_text: Optional[str] = None, bot_action_record_id: Optional[int] = None, is_correct: Optional[bool] = None, human_decision: Optional[str] = None, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    data = {"feedback_type": feedback_type, "feedback_text": feedback_text, "bot_action_record_id": bot_action_record_id, "is_correct": is_correct, "human_decision": human_decision}
    fb = create_bot_feedback(db, data, current_user)
    return BotFeedbackRead.model_validate(fb)

# --- Performance ---
@router.get("/performance")
def performance_list(bot_key: Optional[str] = None, limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    q = db.query(BotPerformanceSnapshot)
    if bot_key: q = q.filter(BotPerformanceSnapshot.bot_key == bot_key)
    return q.order_by(BotPerformanceSnapshot.period_end.desc()).limit(limit).all()

@router.post("/performance/snapshot")
def performance_snapshot(bot_key: str = Query(...), period_start: str = Query(...), period_end: str = Query(...), db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    ps = datetime.fromisoformat(period_start)
    pe = datetime.fromisoformat(period_end)
    snap = create_performance_snapshot(db, bot_key, ps, pe)
    return {"id": snap.id, "total_actions": snap.total_actions, "acceptance_rate": float(snap.acceptance_rate) if snap.acceptance_rate else None}

# --- Learning Candidates ---
@router.get("/learning-candidates", response_model=list[LearningCandidateRead])
def lc_list(status: Optional[str] = None, bot_key: Optional[str] = None, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [LearningCandidateRead.model_validate(c) for c in list_learning_candidates(db, status_filter=status, bot_key=bot_key, limit=limit)]

@router.post("/learning-candidates", response_model=LearningCandidateRead, status_code=201)
def lc_create(bot_key: str = Query(...), candidate_type: str = Query(...), title: str = Query(...), db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    lc = create_learning_candidate(db, {"bot_key": bot_key, "candidate_type": candidate_type, "title": title}, current_user)
    return LearningCandidateRead.model_validate(lc)

@router.post("/learning-candidates/{candidate_id}/review", response_model=LearningCandidateRead)
def lc_review(candidate_id: int, decision: str = Query(...), request: Request = None, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try: lc = review_learning_candidate(db, candidate_id, decision, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    record_audit_log(db, current_user, "bot.learning_candidate_review", "bot_learning_candidate", entity_id=lc.id, description=f"Learning candidate reviewed: {decision}", request=request)
    return LearningCandidateRead.model_validate(lc)

# --- Prompt Versions ---
@router.get("/prompt-versions", response_model=list[PromptVersionRead])
def pv_list(bot_key: Optional[str] = None, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    q = db.query(BotPromptVersion)
    if bot_key: q = q.filter(BotPromptVersion.bot_key == bot_key)
    return [PromptVersionRead.model_validate(p) for p in q.order_by(BotPromptVersion.created_at.desc()).limit(50).all()]

@router.post("/prompt-versions", response_model=PromptVersionRead, status_code=201)
def pv_create(bot_key: str = Query(...), version: str = Query(...), name: str = Query(...), prompt_text: str = Query(...), db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    pv = create_prompt_version(db, {"bot_key": bot_key, "version": version, "name": name, "prompt_text": prompt_text}, current_user)
    return PromptVersionRead.model_validate(pv)

@router.post("/prompt-versions/{version_id}/activate", response_model=PromptVersionRead)
def pv_activate(version_id: int, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try: pv = activate_prompt_version(db, version_id, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    record_audit_log(db, current_user, "bot.prompt_version_activate", "bot_prompt_version", entity_id=pv.id, description=f"Prompt version {pv.version} activated for {pv.bot_key}.", request=request)
    return PromptVersionRead.model_validate(pv)

# --- Rule Versions ---
@router.get("/rule-versions", response_model=list[RuleVersionRead])
def rv_list(bot_key: Optional[str] = None, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    q = db.query(BotRuleVersion)
    if bot_key: q = q.filter(BotRuleVersion.bot_key == bot_key)
    return [RuleVersionRead.model_validate(r) for r in q.order_by(BotRuleVersion.created_at.desc()).limit(50).all()]

@router.post("/rule-versions/{version_id}/activate", response_model=RuleVersionRead)
def rv_activate(version_id: int, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try: rv = activate_rule_version(db, version_id, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    record_audit_log(db, current_user, "bot.rule_version_activate", "bot_rule_version", entity_id=rv.id, description=f"Rule version activated for {rv.bot_key}.", request=request)
    return RuleVersionRead.model_validate(rv)

# --- Evaluation Runs ---
@router.get("/evaluation-runs", response_model=list[EvalRunRead])
def eval_list(bot_key: Optional[str] = None, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    q = db.query(BotEvaluationRun)
    if bot_key: q = q.filter(BotEvaluationRun.bot_key == bot_key)
    return [EvalRunRead.model_validate(r) for r in q.order_by(BotEvaluationRun.id.desc()).limit(50).all()]

@router.post("/evaluation-runs", response_model=EvalRunRead, status_code=201)
def eval_create(bot_key: str = Query(...), evaluation_name: str = Query(...), db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    run = create_evaluation_run(db, {"bot_key": bot_key, "evaluation_name": evaluation_name}, current_user)
    return EvalRunRead.model_validate(run)

@router.post("/evaluation-runs/{run_id}/run", response_model=EvalRunRead)
def eval_run(run_id: int, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try: run = run_evaluation(db, run_id, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    record_audit_log(db, current_user, "bot.evaluation_run", "bot_evaluation_run", entity_id=run.id, description=f"Evaluation run completed: {run.passed_cases}/{run.total_cases} passed.", request=request)
    return EvalRunRead.model_validate(run)

# --- Guardrails ---
@router.get("/guardrail-violations", response_model=list[GuardrailViolationRead])
def guardrails_list(bot_key: Optional[str] = None, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    q = db.query(BotGuardrailViolation)
    if bot_key: q = q.filter(BotGuardrailViolation.bot_key == bot_key)
    return [GuardrailViolationRead.model_validate(v) for v in q.order_by(BotGuardrailViolation.created_at.desc()).limit(limit).all()]
