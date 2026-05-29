"""Phase 23 Predictive Intelligence.

Revision ID: phase23_predictive_intel
Revises: phase22_control_tower
Create Date: 2026-05-29
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "phase23_predictive_intel"
down_revision: Union[str, None] = "phase22_control_tower"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ci(n, t, c):
    op.execute(f"CREATE INDEX IF NOT EXISTS {n} ON {t} ({c})")


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())

    if "prediction_models" not in tables:
        op.create_table("prediction_models", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True), sa.Column("model_key", sa.String(60), nullable=False, unique=True), sa.Column("name", sa.String(150), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("model_type", sa.String(30), nullable=False, server_default="rule_based"), sa.Column("status", sa.String(20), nullable=False, server_default="active"), sa.Column("risk_domain", sa.String(40), nullable=False), sa.Column("version", sa.String(20), nullable=False, server_default="1.0"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "prediction_runs" not in tables:
        op.create_table("prediction_runs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True), sa.Column("run_number", sa.String(60), nullable=False), sa.Column("scope", sa.String(30), nullable=False, server_default="manual"), sa.Column("status", sa.String(20), nullable=False, server_default="running"), sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("completed_at", sa.DateTime(), nullable=True), sa.Column("models_run", sa.Integer(), nullable=False, server_default="0"), sa.Column("records_created", sa.Integer(), nullable=False, server_default="0"), sa.Column("high_risk_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("medium_risk_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("low_risk_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("error_message", sa.Text(), nullable=True), sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True), sa.Column("created_by_name", sa.String(150), nullable=True), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "prediction_records" not in tables:
        op.create_table("prediction_records", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("prediction_run_id", sa.Integer(), sa.ForeignKey("prediction_runs.id"), nullable=True), sa.Column("prediction_model_id", sa.Integer(), sa.ForeignKey("prediction_models.id"), nullable=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True), sa.Column("prediction_key", sa.String(80), nullable=False), sa.Column("risk_domain", sa.String(40), nullable=False), sa.Column("entity_type", sa.String(30), nullable=False), sa.Column("entity_id", sa.Integer(), nullable=True), sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True), sa.Column("container_id", sa.Integer(), sa.ForeignKey("containers.id"), nullable=True), sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=True), sa.Column("customs_case_id", sa.Integer(), sa.ForeignKey("customs_cases.id"), nullable=True), sa.Column("party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True), sa.Column("risk_score", sa.Float(), nullable=False, server_default="0"), sa.Column("risk_level", sa.String(20), nullable=False, server_default="low"), sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"), sa.Column("title", sa.String(500), nullable=False), sa.Column("summary", sa.Text(), nullable=True), sa.Column("predicted_event", sa.String(120), nullable=True), sa.Column("predicted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("prediction_window_start", sa.DateTime(), nullable=True), sa.Column("prediction_window_end", sa.DateTime(), nullable=True), sa.Column("status", sa.String(20), nullable=False, server_default="active"), sa.Column("linked_exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=True), sa.Column("linked_approval_request_id", sa.Integer(), sa.ForeignKey("approval_requests.id"), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "prediction_explanations" not in tables:
        op.create_table("prediction_explanations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("prediction_record_id", sa.Integer(), sa.ForeignKey("prediction_records.id"), nullable=False), sa.Column("factor_key", sa.String(80), nullable=False), sa.Column("factor_label", sa.String(255), nullable=False), sa.Column("factor_value", sa.String(255), nullable=True), sa.Column("impact", sa.String(20), nullable=False, server_default="medium"), sa.Column("weight", sa.Float(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "prediction_recommendations" not in tables:
        op.create_table("prediction_recommendations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("prediction_record_id", sa.Integer(), sa.ForeignKey("prediction_records.id"), nullable=False), sa.Column("recommendation_type", sa.String(40), nullable=False), sa.Column("title", sa.String(500), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("priority", sa.String(20), nullable=False, server_default="medium"), sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="false"), sa.Column("status", sa.String(20), nullable=False, server_default="pending"), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("reviewed_at", sa.DateTime(), nullable=True), sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True), sa.Column("reviewed_by_name", sa.String(150), nullable=True), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "prediction_outcomes" not in tables:
        op.create_table("prediction_outcomes", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("prediction_record_id", sa.Integer(), sa.ForeignKey("prediction_records.id"), nullable=False), sa.Column("outcome_status", sa.String(30), nullable=False), sa.Column("actual_event_occurred", sa.Boolean(), nullable=True), sa.Column("actual_event_at", sa.DateTime(), nullable=True), sa.Column("accuracy_label", sa.String(30), nullable=True), sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True), sa.Column("reviewed_by_name", sa.String(150), nullable=True), sa.Column("reviewed_at", sa.DateTime(), nullable=True), sa.Column("notes", sa.Text(), nullable=True), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "prediction_feedback" not in tables:
        op.create_table("prediction_feedback", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("prediction_record_id", sa.Integer(), sa.ForeignKey("prediction_records.id"), nullable=False), sa.Column("feedback_type", sa.String(30), nullable=False), sa.Column("rating", sa.Integer(), nullable=True), sa.Column("feedback_text", sa.Text(), nullable=True), sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True), sa.Column("created_by_name", sa.String(150), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    if "prediction_activity_logs" not in tables:
        op.create_table("prediction_activity_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("prediction_record_id", sa.Integer(), sa.ForeignKey("prediction_records.id"), nullable=True), sa.Column("prediction_run_id", sa.Integer(), sa.ForeignKey("prediction_runs.id"), nullable=True), sa.Column("activity_type", sa.String(60), nullable=False), sa.Column("safe_summary", sa.Text(), nullable=False), sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True), sa.Column("created_by_name", sa.String(150), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("metadata_json", sa.JSON(), nullable=True))

    _ci("ix_pred_models_key", "prediction_models", "model_key")
    _ci("ix_pred_models_domain", "prediction_models", "risk_domain")
    _ci("ix_pred_runs_status", "prediction_runs", "status")
    _ci("ix_pred_runs_number", "prediction_runs", "run_number")
    _ci("ix_pred_records_run", "prediction_records", "prediction_run_id")
    _ci("ix_pred_records_model", "prediction_records", "prediction_model_id")
    _ci("ix_pred_records_shipment", "prediction_records", "shipment_id")
    _ci("ix_pred_records_domain", "prediction_records", "risk_domain")
    _ci("ix_pred_records_level", "prediction_records", "risk_level")
    _ci("ix_pred_records_status", "prediction_records", "status")
    _ci("ix_pred_explanations_record", "prediction_explanations", "prediction_record_id")
    _ci("ix_pred_recommendations_record", "prediction_recommendations", "prediction_record_id")
    _ci("ix_pred_recommendations_status", "prediction_recommendations", "status")
    _ci("ix_pred_outcomes_record", "prediction_outcomes", "prediction_record_id")
    _ci("ix_pred_feedback_record", "prediction_feedback", "prediction_record_id")
    _ci("ix_pred_activity_record", "prediction_activity_logs", "prediction_record_id")


def downgrade() -> None:
    for t in ["prediction_activity_logs", "prediction_feedback", "prediction_outcomes", "prediction_recommendations", "prediction_explanations", "prediction_records", "prediction_runs", "prediction_models"]:
        op.drop_table(t)
