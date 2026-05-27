"""Bot action records, feedback, performance, learning, and guardrails."""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.bot_governance import (
    BotActionRecord, BotEvaluationResult, BotEvaluationRun,
    BotFeedbackRecord, BotGuardrailViolation, BotLearningCandidate,
    BotPerformanceSnapshot, BotPromptVersion, BotQualityReview,
    BotRuleVersion, BotTrainingCase,
)

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {"password", "jwt", "api_key", "gmail_token", "oauth_code", "database_url", "secret", "token"}


def _sanitize(d: Optional[dict]) -> Optional[dict]:
    if not d:
        return d
    return {k: v for k, v in d.items() if k.lower() not in SENSITIVE_KEYS}


# --- Action Records ---

def record_bot_action(db: Session, data: dict[str, Any]) -> BotActionRecord:
    rec = BotActionRecord(
        bot_agent_id=data.get("bot_agent_id"), bot_key=data["bot_key"],
        action_type=data["action_type"], source=data.get("source", "system"),
        entity_type=data.get("entity_type"), entity_id=data.get("entity_id"),
        shipment_id=data.get("shipment_id"), party_id=data.get("party_id"),
        confidence=data.get("confidence"), risk_level=data.get("risk_level", "medium"),
        status=data.get("status", "observed"),
        proposed_payload_json=_sanitize(data.get("proposed_payload_json")),
        safe_summary_json=data.get("safe_summary_json"),
        input_summary_json=_sanitize(data.get("input_summary_json")),
        output_summary_json=_sanitize(data.get("output_summary_json")),
        created_at=datetime.utcnow(), metadata_json=_sanitize(data.get("metadata_json")),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def update_bot_action_outcome(db: Session, action_id: int, outcome: str, user: Optional[AuthenticatedUser] = None) -> BotActionRecord:
    rec = db.query(BotActionRecord).filter(BotActionRecord.id == action_id).first()
    if not rec:
        raise ValueError("Bot action record not found")
    rec.outcome_status = outcome
    rec.reviewed_at = datetime.utcnow()
    if user:
        rec.reviewed_by_user_id = user.id
        rec.reviewed_by_name = user.name
    db.commit()
    db.refresh(rec)
    return rec


def list_bot_action_records(db: Session, *, bot_key: Optional[str] = None, status_filter: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[BotActionRecord]:
    q = db.query(BotActionRecord)
    if bot_key:
        q = q.filter(BotActionRecord.bot_key == bot_key)
    if status_filter:
        q = q.filter(BotActionRecord.status == status_filter)
    return q.order_by(BotActionRecord.created_at.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0)).all()


# --- Feedback ---

def create_bot_feedback(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> BotFeedbackRecord:
    fb = BotFeedbackRecord(
        bot_action_record_id=data.get("bot_action_record_id"),
        bot_agent_id=data.get("bot_agent_id"),
        feedback_type=data["feedback_type"],
        rating=data.get("rating"), is_correct=data.get("is_correct"),
        human_decision=data.get("human_decision"),
        feedback_text=data.get("feedback_text"),
        correction_json=_sanitize(data.get("correction_json")),
        created_by_user_id=user.id, created_by_name=user.name,
        created_at=datetime.utcnow(), metadata_json=_sanitize(data.get("metadata_json")),
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


def list_bot_feedback(db: Session, *, bot_key: Optional[str] = None, limit: int = 50) -> list[BotFeedbackRecord]:
    q = db.query(BotFeedbackRecord)
    if bot_key:
        q = q.join(BotActionRecord, BotFeedbackRecord.bot_action_record_id == BotActionRecord.id).filter(BotActionRecord.bot_key == bot_key)
    return q.order_by(BotFeedbackRecord.created_at.desc()).limit(limit).all()


# --- Performance ---

def create_performance_snapshot(db: Session, bot_key: str, period_start: datetime, period_end: datetime) -> BotPerformanceSnapshot:
    actions = db.query(BotActionRecord).filter(BotActionRecord.bot_key == bot_key, BotActionRecord.created_at >= period_start, BotActionRecord.created_at <= period_end).all()
    total = len(actions)
    proposed = sum(1 for a in actions if a.status in ("proposed", "pending_review", "pending_approval"))
    approved = sum(1 for a in actions if a.status == "approved" or a.outcome_status == "accepted")
    rejected = sum(1 for a in actions if a.status == "rejected" or a.outcome_status == "rejected")
    applied = sum(1 for a in actions if a.status == "applied")
    failed = sum(1 for a in actions if a.status == "failed")
    fp = sum(1 for a in actions if a.outcome_status == "false_positive")
    fn = sum(1 for a in actions if a.outcome_status == "false_negative")
    acc_rate = Decimal(str(round(approved / total * 100, 2))) if total > 0 else None
    rej_rate = Decimal(str(round(rejected / total * 100, 2))) if total > 0 else None
    confs = [float(a.confidence) for a in actions if a.confidence is not None]
    avg_conf = Decimal(str(round(sum(confs) / len(confs), 2))) if confs else None

    snap = BotPerformanceSnapshot(
        bot_key=bot_key, period_start=period_start, period_end=period_end,
        total_actions=total, proposed_count=proposed, approved_count=approved,
        rejected_count=rejected, applied_count=applied, failed_count=failed,
        false_positive_count=fp, false_negative_count=fn,
        acceptance_rate=acc_rate, rejection_rate=rej_rate, average_confidence=avg_conf,
        created_at=datetime.utcnow(),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


# --- Learning Candidates ---

def create_learning_candidate(db: Session, data: dict[str, Any], user: Optional[AuthenticatedUser] = None) -> BotLearningCandidate:
    lc = BotLearningCandidate(
        bot_agent_id=data.get("bot_agent_id"), bot_key=data["bot_key"],
        candidate_type=data["candidate_type"], title=data["title"],
        description=data.get("description"), source_type=data.get("source_type"),
        source_id=data.get("source_id"), evidence_json=_sanitize(data.get("evidence_json")),
        recommended_change_json=_sanitize(data.get("recommended_change_json")),
        risk_level=data.get("risk_level", "medium"), status="open",
        created_at=datetime.utcnow(), metadata_json=_sanitize(data.get("metadata_json")),
    )
    db.add(lc)
    db.commit()
    db.refresh(lc)
    return lc


def review_learning_candidate(db: Session, candidate_id: int, decision: str, user: AuthenticatedUser, notes: Optional[str] = None) -> BotLearningCandidate:
    lc = db.query(BotLearningCandidate).filter(BotLearningCandidate.id == candidate_id).first()
    if not lc:
        raise ValueError("Learning candidate not found")
    lc.status = decision
    lc.reviewed_at = datetime.utcnow()
    lc.reviewed_by_user_id = user.id
    lc.reviewed_by_name = user.name
    db.commit()
    db.refresh(lc)
    return lc


def list_learning_candidates(db: Session, *, status_filter: Optional[str] = None, bot_key: Optional[str] = None, limit: int = 50) -> list[BotLearningCandidate]:
    q = db.query(BotLearningCandidate)
    if status_filter:
        q = q.filter(BotLearningCandidate.status == status_filter)
    if bot_key:
        q = q.filter(BotLearningCandidate.bot_key == bot_key)
    return q.order_by(BotLearningCandidate.created_at.desc()).limit(limit).all()


# --- Training Cases ---

def create_training_case(db: Session, data: dict[str, Any]) -> BotTrainingCase:
    tc = BotTrainingCase(
        bot_agent_id=data.get("bot_agent_id"), bot_key=data["bot_key"],
        case_type=data["case_type"], title=data["title"],
        input_summary_json=_sanitize(data.get("input_summary_json")),
        expected_output_json=_sanitize(data.get("expected_output_json")),
        actual_output_json=_sanitize(data.get("actual_output_json")),
        human_correction_json=_sanitize(data.get("human_correction_json")),
        source_type=data.get("source_type"), source_id=data.get("source_id"),
        status="candidate", created_at=datetime.utcnow(),
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return tc


# --- Prompt/Rule Versions ---

def create_prompt_version(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> BotPromptVersion:
    pv = BotPromptVersion(
        bot_agent_id=data.get("bot_agent_id"), bot_key=data["bot_key"],
        version=data["version"], name=data["name"], prompt_text=data["prompt_text"],
        safe_summary=data.get("safe_summary"), status="draft",
        created_by_user_id=user.id, created_by_name=user.name, created_at=datetime.utcnow(),
    )
    db.add(pv)
    db.commit()
    db.refresh(pv)
    return pv


def activate_prompt_version(db: Session, version_id: int, user: AuthenticatedUser) -> BotPromptVersion:
    pv = db.query(BotPromptVersion).filter(BotPromptVersion.id == version_id).first()
    if not pv:
        raise ValueError("Prompt version not found")
    if pv.status not in ("approved", "draft"):
        raise ValueError("Only approved/draft versions can be activated")
    # Deactivate others
    db.query(BotPromptVersion).filter(BotPromptVersion.bot_key == pv.bot_key, BotPromptVersion.status == "active").update({"status": "deprecated"})
    pv.status = "active"
    pv.approved_by_user_id = user.id
    pv.approved_by_name = user.name
    pv.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(pv)
    return pv


def create_rule_version(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> BotRuleVersion:
    rv = BotRuleVersion(
        bot_agent_id=data.get("bot_agent_id"), bot_key=data["bot_key"],
        version=data["version"], name=data["name"], rule_config_json=data["rule_config_json"],
        safe_summary=data.get("safe_summary"), status="draft",
        created_by_user_id=user.id, created_by_name=user.name, created_at=datetime.utcnow(),
    )
    db.add(rv)
    db.commit()
    db.refresh(rv)
    return rv


def activate_rule_version(db: Session, version_id: int, user: AuthenticatedUser) -> BotRuleVersion:
    rv = db.query(BotRuleVersion).filter(BotRuleVersion.id == version_id).first()
    if not rv:
        raise ValueError("Rule version not found")
    db.query(BotRuleVersion).filter(BotRuleVersion.bot_key == rv.bot_key, BotRuleVersion.status == "active").update({"status": "deprecated"})
    rv.status = "active"
    rv.approved_by_user_id = user.id
    rv.approved_by_name = user.name
    rv.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(rv)
    return rv


# --- Evaluation ---

def create_evaluation_run(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> BotEvaluationRun:
    run = BotEvaluationRun(
        bot_agent_id=data.get("bot_agent_id"), bot_key=data["bot_key"],
        evaluation_name=data["evaluation_name"],
        prompt_version_id=data.get("prompt_version_id"), rule_version_id=data.get("rule_version_id"),
        status="queued", total_cases=0, passed_cases=0, failed_cases=0,
        created_by_user_id=user.id, created_by_name=user.name,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def run_evaluation(db: Session, run_id: int, user: AuthenticatedUser) -> BotEvaluationRun:
    run = db.query(BotEvaluationRun).filter(BotEvaluationRun.id == run_id).first()
    if not run:
        raise ValueError("Evaluation run not found")
    now = datetime.utcnow()
    run.status = "running"
    run.started_at = now
    # Get training cases for this bot
    cases = db.query(BotTrainingCase).filter(BotTrainingCase.bot_key == run.bot_key, BotTrainingCase.status == "approved").all()
    passed = 0
    failed = 0
    for case in cases:
        # Simple deterministic comparison
        match = case.expected_output_json == case.actual_output_json if case.expected_output_json and case.actual_output_json else None
        status = "passed" if match else ("failed" if match is False else "skipped")
        result = BotEvaluationResult(evaluation_run_id=run.id, training_case_id=case.id, status=status, created_at=now)
        db.add(result)
        if status == "passed":
            passed += 1
        elif status == "failed":
            failed += 1
    run.total_cases = len(cases)
    run.passed_cases = passed
    run.failed_cases = failed
    run.accuracy = Decimal(str(round(passed / len(cases) * 100, 2))) if cases else None
    run.status = "completed"
    run.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


# --- Guardrails ---

def record_guardrail_violation(db: Session, data: dict[str, Any]) -> BotGuardrailViolation:
    v = BotGuardrailViolation(
        bot_agent_id=data.get("bot_agent_id"), bot_key=data["bot_key"],
        action_record_id=data.get("action_record_id"),
        violation_type=data["violation_type"], severity=data.get("severity", "medium"),
        message=data["message"], blocked_action=data.get("blocked_action"),
        entity_type=data.get("entity_type"), entity_id=data.get("entity_id"),
        created_at=datetime.utcnow(), metadata_json=_sanitize(data.get("metadata_json")),
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


# --- Governance Summary ---

def get_governance_summary(db: Session, user: Optional[AuthenticatedUser] = None) -> dict[str, Any]:
    from app.models.bot_governance import BotAgent
    agents = db.query(BotAgent).filter(BotAgent.status == "active").count()
    needs_review = db.query(BotAgent).filter(BotAgent.status == "needs_review").count()
    violations = db.query(BotGuardrailViolation).count()
    open_candidates = db.query(BotLearningCandidate).filter(BotLearningCandidate.status == "open").count()
    pending_prompts = db.query(BotPromptVersion).filter(BotPromptVersion.status == "pending_approval").count()
    pending_rules = db.query(BotRuleVersion).filter(BotRuleVersion.status == "pending_approval").count()
    return {
        "active_agents": agents,
        "needs_review": needs_review,
        "guardrail_violations": violations,
        "open_learning_candidates": open_candidates,
        "pending_prompt_approvals": pending_prompts,
        "pending_rule_approvals": pending_rules,
    }
