"""Phase 17 bot governance + learning system.

Revision ID: phase17_bot_learning
Revises: phase16_approval_engine
Create Date: 2026-05-28
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "phase17_bot_learning"
down_revision: Union[str, None] = "phase16_approval_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _ci(n, t, c): op.execute(f"CREATE INDEX IF NOT EXISTS {n} ON {t} ({c})")

def upgrade() -> None:
    conn = op.get_bind()
    tables = set(inspect(conn).get_table_names())

    if "bot_agents" not in tables:
        op.create_table("bot_agents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("bot_key", sa.String(120), nullable=False, unique=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("bot_type", sa.String(60), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="active"),
            sa.Column("owner_role", sa.String(30), nullable=True),
            sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("owner_name", sa.String(150), nullable=True),
            sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("current_prompt_version_id", sa.Integer(), nullable=True),
            sa.Column("current_rule_version_id", sa.Integer(), nullable=True),
            sa.Column("is_approval_required", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "bot_action_records" not in tables:
        op.create_table("bot_action_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bot_agent_id", sa.Integer(), sa.ForeignKey("bot_agents.id"), nullable=True),
            sa.Column("bot_key", sa.String(120), nullable=False),
            sa.Column("action_type", sa.String(60), nullable=False),
            sa.Column("source", sa.String(60), nullable=False, server_default="system"),
            sa.Column("entity_type", sa.String(80), nullable=True),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
            sa.Column("approval_request_id", sa.Integer(), sa.ForeignKey("approval_requests.id"), nullable=True),
            sa.Column("exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=True),
            sa.Column("confidence", sa.Numeric(5,2), nullable=True),
            sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(30), nullable=False, server_default="observed"),
            sa.Column("proposed_payload_json", sa.JSON(), nullable=True),
            sa.Column("safe_summary_json", sa.JSON(), nullable=True),
            sa.Column("input_summary_json", sa.JSON(), nullable=True),
            sa.Column("output_summary_json", sa.JSON(), nullable=True),
            sa.Column("prompt_version_id", sa.Integer(), nullable=True),
            sa.Column("rule_version_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_by_name", sa.String(150), nullable=True),
            sa.Column("outcome_status", sa.String(30), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "bot_feedback_records" not in tables:
        op.create_table("bot_feedback_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bot_action_record_id", sa.Integer(), sa.ForeignKey("bot_action_records.id"), nullable=True),
            sa.Column("bot_agent_id", sa.Integer(), sa.ForeignKey("bot_agents.id"), nullable=True),
            sa.Column("feedback_type", sa.String(40), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=True),
            sa.Column("is_correct", sa.Boolean(), nullable=True),
            sa.Column("human_decision", sa.String(30), nullable=True),
            sa.Column("feedback_text", sa.Text(), nullable=True),
            sa.Column("correction_json", sa.JSON(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_name", sa.String(150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "bot_performance_snapshots" not in tables:
        op.create_table("bot_performance_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bot_agent_id", sa.Integer(), sa.ForeignKey("bot_agents.id"), nullable=True),
            sa.Column("bot_key", sa.String(120), nullable=False),
            sa.Column("period_start", sa.DateTime(), nullable=False),
            sa.Column("period_end", sa.DateTime(), nullable=False),
            sa.Column("total_actions", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("proposed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("approved_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("applied_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("false_positive_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("false_negative_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("acceptance_rate", sa.Numeric(5,2), nullable=True),
            sa.Column("rejection_rate", sa.Numeric(5,2), nullable=True),
            sa.Column("average_confidence", sa.Numeric(5,2), nullable=True),
            sa.Column("average_risk_score", sa.Numeric(5,2), nullable=True),
            sa.Column("manual_review_rate", sa.Numeric(5,2), nullable=True),
            sa.Column("approval_required_rate", sa.Numeric(5,2), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    for tbl_name, cols in [
        ("bot_prompt_versions", [("bot_agent_id", "Integer", "bot_agents.id"), ("bot_key", "String(120)", None), ("version", "String(30)", None), ("name", "String(255)", None), ("prompt_text", "Text", None), ("safe_summary", "Text", None), ("status", "String(30)", None), ("created_by_user_id", "Integer", "users.id"), ("created_by_name", "String(150)", None), ("approved_by_user_id", "Integer", "users.id"), ("approved_by_name", "String(150)", None), ("created_at", "DateTime", None), ("approved_at", "DateTime", None), ("metadata_json", "JSON", None)]),
        ("bot_rule_versions", [("bot_agent_id", "Integer", "bot_agents.id"), ("bot_key", "String(120)", None), ("version", "String(30)", None), ("name", "String(255)", None), ("rule_config_json", "JSON", None), ("safe_summary", "Text", None), ("status", "String(30)", None), ("created_by_user_id", "Integer", "users.id"), ("created_by_name", "String(150)", None), ("approved_by_user_id", "Integer", "users.id"), ("approved_by_name", "String(150)", None), ("created_at", "DateTime", None), ("approved_at", "DateTime", None), ("metadata_json", "JSON", None)]),
    ]:
        if tbl_name not in tables:
            columns = [sa.Column("id", sa.Integer(), primary_key=True)]
            for col_name, col_type, fk in cols:
                kwargs = {"nullable": True}
                if col_type == "Integer" and fk: columns.append(sa.Column(col_name, sa.Integer(), sa.ForeignKey(fk), **kwargs))
                elif col_type.startswith("String"): columns.append(sa.Column(col_name, sa.String(int(col_type.split("(")[1].rstrip(")"))), **kwargs))
                elif col_type == "Text": columns.append(sa.Column(col_name, sa.Text(), **kwargs))
                elif col_type == "DateTime": columns.append(sa.Column(col_name, sa.DateTime(), **kwargs))
                elif col_type == "JSON": columns.append(sa.Column(col_name, sa.JSON(), **kwargs))
                elif col_type == "Integer": columns.append(sa.Column(col_name, sa.Integer(), **kwargs))
            op.create_table(tbl_name, *columns)

    if "bot_learning_candidates" not in tables:
        op.create_table("bot_learning_candidates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bot_agent_id", sa.Integer(), sa.ForeignKey("bot_agents.id"), nullable=True),
            sa.Column("bot_key", sa.String(120), nullable=False),
            sa.Column("candidate_type", sa.String(60), nullable=False),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("source_type", sa.String(80), nullable=True),
            sa.Column("source_id", sa.Integer(), nullable=True),
            sa.Column("evidence_json", sa.JSON(), nullable=True),
            sa.Column("recommended_change_json", sa.JSON(), nullable=True),
            sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(40), nullable=False, server_default="open"),
            sa.Column("approval_request_id", sa.Integer(), sa.ForeignKey("approval_requests.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_by_name", sa.String(150), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "bot_training_cases" not in tables:
        op.create_table("bot_training_cases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bot_agent_id", sa.Integer(), sa.ForeignKey("bot_agents.id"), nullable=True),
            sa.Column("bot_key", sa.String(120), nullable=False),
            sa.Column("case_type", sa.String(60), nullable=False),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("input_summary_json", sa.JSON(), nullable=True),
            sa.Column("expected_output_json", sa.JSON(), nullable=True),
            sa.Column("actual_output_json", sa.JSON(), nullable=True),
            sa.Column("human_correction_json", sa.JSON(), nullable=True),
            sa.Column("source_type", sa.String(80), nullable=True),
            sa.Column("source_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="candidate"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "bot_evaluation_runs" not in tables:
        op.create_table("bot_evaluation_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bot_agent_id", sa.Integer(), sa.ForeignKey("bot_agents.id"), nullable=True),
            sa.Column("bot_key", sa.String(120), nullable=False),
            sa.Column("evaluation_name", sa.String(255), nullable=False),
            sa.Column("prompt_version_id", sa.Integer(), nullable=True),
            sa.Column("rule_version_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("total_cases", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("passed_cases", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_cases", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("accuracy", sa.Numeric(5,2), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_name", sa.String(150), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "bot_evaluation_results" not in tables:
        op.create_table("bot_evaluation_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("evaluation_run_id", sa.Integer(), sa.ForeignKey("bot_evaluation_runs.id"), nullable=False),
            sa.Column("training_case_id", sa.Integer(), sa.ForeignKey("bot_training_cases.id"), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="passed"),
            sa.Column("score", sa.Numeric(5,2), nullable=True),
            sa.Column("expected_summary_json", sa.JSON(), nullable=True),
            sa.Column("actual_summary_json", sa.JSON(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "bot_guardrail_violations" not in tables:
        op.create_table("bot_guardrail_violations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bot_agent_id", sa.Integer(), sa.ForeignKey("bot_agents.id"), nullable=True),
            sa.Column("bot_key", sa.String(120), nullable=False),
            sa.Column("action_record_id", sa.Integer(), sa.ForeignKey("bot_action_records.id"), nullable=True),
            sa.Column("violation_type", sa.String(80), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("blocked_action", sa.String(255), nullable=True),
            sa.Column("entity_type", sa.String(80), nullable=True),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )
    if "bot_quality_reviews" not in tables:
        op.create_table("bot_quality_reviews",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("bot_agent_id", sa.Integer(), sa.ForeignKey("bot_agents.id"), nullable=True),
            sa.Column("bot_key", sa.String(120), nullable=False),
            sa.Column("review_period_start", sa.DateTime(), nullable=False),
            sa.Column("review_period_end", sa.DateTime(), nullable=False),
            sa.Column("review_status", sa.String(30), nullable=False, server_default="open"),
            sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_by_name", sa.String(150), nullable=True),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("action_items_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    # Indexes
    _ci("ix_bot_agents_key", "bot_agents", "bot_key")
    _ci("ix_bot_agents_status", "bot_agents", "status")
    _ci("ix_bot_action_records_key", "bot_action_records", "bot_key")
    _ci("ix_bot_action_records_status", "bot_action_records", "status")
    _ci("ix_bot_action_records_created", "bot_action_records", "created_at")
    _ci("ix_bot_feedback_records_action", "bot_feedback_records", "bot_action_record_id")
    _ci("ix_bot_performance_key", "bot_performance_snapshots", "bot_key")
    _ci("ix_bot_prompt_versions_key", "bot_prompt_versions", "bot_key")
    _ci("ix_bot_rule_versions_key", "bot_rule_versions", "bot_key")
    _ci("ix_bot_learning_candidates_key", "bot_learning_candidates", "bot_key")
    _ci("ix_bot_learning_candidates_status", "bot_learning_candidates", "status")
    _ci("ix_bot_training_cases_key", "bot_training_cases", "bot_key")
    _ci("ix_bot_evaluation_runs_key", "bot_evaluation_runs", "bot_key")
    _ci("ix_bot_evaluation_results_run", "bot_evaluation_results", "evaluation_run_id")
    _ci("ix_bot_guardrail_violations_key", "bot_guardrail_violations", "bot_key")
    _ci("ix_bot_quality_reviews_key", "bot_quality_reviews", "bot_key")

def downgrade() -> None:
    for t in ["bot_quality_reviews", "bot_guardrail_violations", "bot_evaluation_results", "bot_evaluation_runs", "bot_training_cases", "bot_learning_candidates", "bot_rule_versions", "bot_prompt_versions", "bot_performance_snapshots", "bot_feedback_records", "bot_action_records", "bot_agents"]:
        op.drop_table(t)
