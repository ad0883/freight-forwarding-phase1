"""Phase 17 bot governance + learning system models."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text

from app.db.session import Base


class BotAgent(Base):
    __tablename__ = "bot_agents"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    bot_key = Column(String(120), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    bot_type = Column(String(60), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="active", index=True)
    owner_role = Column(String(30), nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner_name = Column(String(150), nullable=True)
    risk_level = Column(String(20), nullable=False, default="medium")
    current_prompt_version_id = Column(Integer, nullable=True)
    current_rule_version_id = Column(Integer, nullable=True)
    is_approval_required = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class BotActionRecord(Base):
    __tablename__ = "bot_action_records"

    id = Column(Integer, primary_key=True, index=True)
    bot_agent_id = Column(Integer, ForeignKey("bot_agents.id"), nullable=True, index=True)
    bot_key = Column(String(120), nullable=False, index=True)
    action_type = Column(String(60), nullable=False, index=True)
    source = Column(String(60), nullable=False, default="system")
    entity_type = Column(String(80), nullable=True)
    entity_id = Column(Integer, nullable=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    approval_request_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=True)
    exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=True)
    confidence = Column(Numeric(5, 2), nullable=True)
    risk_level = Column(String(20), nullable=False, default="medium")
    status = Column(String(30), nullable=False, default="observed", index=True)
    proposed_payload_json = Column(JSON, nullable=True)
    safe_summary_json = Column(JSON, nullable=True)
    input_summary_json = Column(JSON, nullable=True)
    output_summary_json = Column(JSON, nullable=True)
    prompt_version_id = Column(Integer, nullable=True)
    rule_version_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_name = Column(String(150), nullable=True)
    outcome_status = Column(String(30), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class BotFeedbackRecord(Base):
    __tablename__ = "bot_feedback_records"

    id = Column(Integer, primary_key=True, index=True)
    bot_action_record_id = Column(Integer, ForeignKey("bot_action_records.id"), nullable=True, index=True)
    bot_agent_id = Column(Integer, ForeignKey("bot_agents.id"), nullable=True, index=True)
    feedback_type = Column(String(40), nullable=False, index=True)
    rating = Column(Integer, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    human_decision = Column(String(30), nullable=True)
    feedback_text = Column(Text, nullable=True)
    correction_json = Column(JSON, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class BotPerformanceSnapshot(Base):
    __tablename__ = "bot_performance_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    bot_agent_id = Column(Integer, ForeignKey("bot_agents.id"), nullable=True, index=True)
    bot_key = Column(String(120), nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    total_actions = Column(Integer, nullable=False, default=0)
    proposed_count = Column(Integer, nullable=False, default=0)
    approved_count = Column(Integer, nullable=False, default=0)
    rejected_count = Column(Integer, nullable=False, default=0)
    applied_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    false_positive_count = Column(Integer, nullable=False, default=0)
    false_negative_count = Column(Integer, nullable=False, default=0)
    acceptance_rate = Column(Numeric(5, 2), nullable=True)
    rejection_rate = Column(Numeric(5, 2), nullable=True)
    average_confidence = Column(Numeric(5, 2), nullable=True)
    average_risk_score = Column(Numeric(5, 2), nullable=True)
    manual_review_rate = Column(Numeric(5, 2), nullable=True)
    approval_required_rate = Column(Numeric(5, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class BotPromptVersion(Base):
    __tablename__ = "bot_prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    bot_agent_id = Column(Integer, ForeignKey("bot_agents.id"), nullable=True, index=True)
    bot_key = Column(String(120), nullable=False, index=True)
    version = Column(String(30), nullable=False)
    name = Column(String(255), nullable=False)
    prompt_text = Column(Text, nullable=False)
    safe_summary = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="draft", index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, nullable=True)


class BotRuleVersion(Base):
    __tablename__ = "bot_rule_versions"

    id = Column(Integer, primary_key=True, index=True)
    bot_agent_id = Column(Integer, ForeignKey("bot_agents.id"), nullable=True, index=True)
    bot_key = Column(String(120), nullable=False, index=True)
    version = Column(String(30), nullable=False)
    name = Column(String(255), nullable=False)
    rule_config_json = Column(JSON, nullable=False)
    safe_summary = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="draft", index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, nullable=True)


class BotLearningCandidate(Base):
    __tablename__ = "bot_learning_candidates"

    id = Column(Integer, primary_key=True, index=True)
    bot_agent_id = Column(Integer, ForeignKey("bot_agents.id"), nullable=True, index=True)
    bot_key = Column(String(120), nullable=False, index=True)
    candidate_type = Column(String(60), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    source_type = Column(String(80), nullable=True)
    source_id = Column(Integer, nullable=True)
    evidence_json = Column(JSON, nullable=True)
    recommended_change_json = Column(JSON, nullable=True)
    risk_level = Column(String(20), nullable=False, default="medium")
    status = Column(String(40), nullable=False, default="open", index=True)
    approval_request_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class BotTrainingCase(Base):
    __tablename__ = "bot_training_cases"

    id = Column(Integer, primary_key=True, index=True)
    bot_agent_id = Column(Integer, ForeignKey("bot_agents.id"), nullable=True, index=True)
    bot_key = Column(String(120), nullable=False, index=True)
    case_type = Column(String(60), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    input_summary_json = Column(JSON, nullable=True)
    expected_output_json = Column(JSON, nullable=True)
    actual_output_json = Column(JSON, nullable=True)
    human_correction_json = Column(JSON, nullable=True)
    source_type = Column(String(80), nullable=True)
    source_id = Column(Integer, nullable=True)
    status = Column(String(30), nullable=False, default="candidate", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, nullable=True)


class BotEvaluationRun(Base):
    __tablename__ = "bot_evaluation_runs"

    id = Column(Integer, primary_key=True, index=True)
    bot_agent_id = Column(Integer, ForeignKey("bot_agents.id"), nullable=True, index=True)
    bot_key = Column(String(120), nullable=False, index=True)
    evaluation_name = Column(String(255), nullable=False)
    prompt_version_id = Column(Integer, nullable=True)
    rule_version_id = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="queued", index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_cases = Column(Integer, nullable=False, default=0)
    passed_cases = Column(Integer, nullable=False, default=0)
    failed_cases = Column(Integer, nullable=False, default=0)
    accuracy = Column(Numeric(5, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class BotEvaluationResult(Base):
    __tablename__ = "bot_evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_run_id = Column(Integer, ForeignKey("bot_evaluation_runs.id"), nullable=False, index=True)
    training_case_id = Column(Integer, ForeignKey("bot_training_cases.id"), nullable=True)
    status = Column(String(20), nullable=False, default="passed")
    score = Column(Numeric(5, 2), nullable=True)
    expected_summary_json = Column(JSON, nullable=True)
    actual_summary_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class BotGuardrailViolation(Base):
    __tablename__ = "bot_guardrail_violations"

    id = Column(Integer, primary_key=True, index=True)
    bot_agent_id = Column(Integer, ForeignKey("bot_agents.id"), nullable=True, index=True)
    bot_key = Column(String(120), nullable=False, index=True)
    action_record_id = Column(Integer, ForeignKey("bot_action_records.id"), nullable=True)
    violation_type = Column(String(80), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="medium")
    message = Column(Text, nullable=False)
    blocked_action = Column(String(255), nullable=True)
    entity_type = Column(String(80), nullable=True)
    entity_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class BotQualityReview(Base):
    __tablename__ = "bot_quality_reviews"

    id = Column(Integer, primary_key=True, index=True)
    bot_agent_id = Column(Integer, ForeignKey("bot_agents.id"), nullable=True, index=True)
    bot_key = Column(String(120), nullable=False, index=True)
    review_period_start = Column(DateTime, nullable=False)
    review_period_end = Column(DateTime, nullable=False)
    review_status = Column(String(30), nullable=False, default="open")
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_name = Column(String(150), nullable=True)
    summary = Column(Text, nullable=False)
    action_items_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, nullable=True)
