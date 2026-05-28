"""Phase 21 Tracking Adapters.

Revision ID: phase21_tracking_adapters
Revises: phase20_transport_gps
Create Date: 2026-05-28
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "phase21_tracking_adapters"
down_revision: Union[str, None] = "phase20_transport_gps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ci(n, t, c):
    op.execute(f"CREATE INDEX IF NOT EXISTS {n} ON {t} ({c})")


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())

    if "tracking_providers" not in tables:
        op.create_table(
            "tracking_providers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("provider_key", sa.String(60), nullable=False, unique=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("provider_type", sa.String(40), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("base_url", sa.String(500), nullable=True),
            sa.Column("supports_container_tracking", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("supports_vessel_tracking", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("supports_transport_tracking", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("supports_terminal_tracking", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("requires_credentials", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("is_manual", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("is_mock", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "tracking_adapter_configs" not in tables:
        op.create_table(
            "tracking_adapter_configs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tracking_provider_id", sa.Integer(), sa.ForeignKey("tracking_providers.id"), nullable=False),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("config_name", sa.String(150), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("auth_type", sa.String(20), nullable=False, server_default="none"),
            sa.Column("safe_config_json", sa.JSON(), nullable=True),
            sa.Column("secret_ref", sa.String(255), nullable=True),
            sa.Column("last_verified_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_name", sa.String(150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "tracking_watch_items" not in tables:
        op.create_table(
            "tracking_watch_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("tracking_provider_id", sa.Integer(), sa.ForeignKey("tracking_providers.id"), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("container_id", sa.Integer(), sa.ForeignKey("containers.id"), nullable=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=True),
            sa.Column("customs_case_id", sa.Integer(), sa.ForeignKey("customs_cases.id"), nullable=True),
            sa.Column("watch_type", sa.String(30), nullable=False),
            sa.Column("tracking_identifier", sa.String(120), nullable=False),
            sa.Column("secondary_identifier", sa.String(120), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("last_sync_at", sa.DateTime(), nullable=True),
            sa.Column("last_observation_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_name", sa.String(150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "tracking_observations" not in tables:
        op.create_table(
            "tracking_observations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tracking_watch_item_id", sa.Integer(), sa.ForeignKey("tracking_watch_items.id"), nullable=True),
            sa.Column("tracking_provider_id", sa.Integer(), sa.ForeignKey("tracking_providers.id"), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("container_id", sa.Integer(), sa.ForeignKey("containers.id"), nullable=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=True),
            sa.Column("observation_type", sa.String(40), nullable=False),
            sa.Column("source", sa.String(40), nullable=False, server_default="manual"),
            sa.Column("raw_status", sa.String(255), nullable=True),
            sa.Column("normalized_status", sa.String(80), nullable=False),
            sa.Column("status_time", sa.DateTime(), nullable=True),
            sa.Column("location_text", sa.String(255), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("eta", sa.DateTime(), nullable=True),
            sa.Column("etd", sa.DateTime(), nullable=True),
            sa.Column("vessel_name", sa.String(150), nullable=True),
            sa.Column("voyage_no", sa.String(60), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
            sa.Column("is_customer_visible", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("observed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("received_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "tracking_events" not in tables:
        op.create_table(
            "tracking_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tracking_observation_id", sa.Integer(), sa.ForeignKey("tracking_observations.id"), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("container_id", sa.Integer(), sa.ForeignKey("containers.id"), nullable=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=True),
            sa.Column("event_key", sa.String(80), nullable=False),
            sa.Column("event_label", sa.String(255), nullable=False),
            sa.Column("event_time", sa.DateTime(), nullable=True),
            sa.Column("location_text", sa.String(255), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
            sa.Column("matched_internal_state", sa.String(80), nullable=True),
            sa.Column("match_status", sa.String(30), nullable=False, server_default="new_information"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "tracking_suggested_updates" not in tables:
        op.create_table(
            "tracking_suggested_updates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tracking_observation_id", sa.Integer(), sa.ForeignKey("tracking_observations.id"), nullable=True),
            sa.Column("tracking_event_id", sa.Integer(), sa.ForeignKey("tracking_events.id"), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("container_id", sa.Integer(), sa.ForeignKey("containers.id"), nullable=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=True),
            sa.Column("suggestion_type", sa.String(40), nullable=False),
            sa.Column("target_entity_type", sa.String(30), nullable=False),
            sa.Column("target_entity_id", sa.Integer(), nullable=True),
            sa.Column("target_field", sa.String(80), nullable=False),
            sa.Column("current_value", sa.String(255), nullable=True),
            sa.Column("suggested_value", sa.String(255), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
            sa.Column("risk_level", sa.String(20), nullable=False, server_default="low"),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending_review"),
            sa.Column("approval_request_id", sa.Integer(), sa.ForeignKey("approval_requests.id"), nullable=True),
            sa.Column("exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_by_name", sa.String(150), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "tracking_mismatches" not in tables:
        op.create_table(
            "tracking_mismatches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tracking_observation_id", sa.Integer(), sa.ForeignKey("tracking_observations.id"), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("container_id", sa.Integer(), sa.ForeignKey("containers.id"), nullable=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=True),
            sa.Column("mismatch_type", sa.String(40), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("linked_exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("resolved_by_name", sa.String(150), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "tracking_sync_runs" not in tables:
        op.create_table(
            "tracking_sync_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tracking_provider_id", sa.Integer(), sa.ForeignKey("tracking_providers.id"), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
            sa.Column("scope", sa.String(30), nullable=False, server_default="manual"),
            sa.Column("watch_items_processed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("observations_created", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("suggestions_created", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("mismatches_created", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_name", sa.String(150), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "tracking_activity_logs" not in tables:
        op.create_table(
            "tracking_activity_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("container_id", sa.Integer(), sa.ForeignKey("containers.id"), nullable=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=True),
            sa.Column("tracking_provider_id", sa.Integer(), sa.ForeignKey("tracking_providers.id"), nullable=True),
            sa.Column("activity_type", sa.String(60), nullable=False),
            sa.Column("safe_summary", sa.Text(), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_name", sa.String(150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    # Indexes
    _ci("ix_tracking_providers_key", "tracking_providers", "provider_key")
    _ci("ix_tracking_providers_type", "tracking_providers", "provider_type")
    _ci("ix_tracking_providers_status", "tracking_providers", "status")
    _ci("ix_tracking_adapter_configs_prov", "tracking_adapter_configs", "tracking_provider_id")
    _ci("ix_tracking_watch_items_shipment", "tracking_watch_items", "shipment_id")
    _ci("ix_tracking_watch_items_container", "tracking_watch_items", "container_id")
    _ci("ix_tracking_watch_items_status", "tracking_watch_items", "status")
    _ci("ix_tracking_watch_items_type", "tracking_watch_items", "watch_type")
    _ci("ix_tracking_watch_items_ident", "tracking_watch_items", "tracking_identifier")
    _ci("ix_tracking_obs_watch", "tracking_observations", "tracking_watch_item_id")
    _ci("ix_tracking_obs_shipment", "tracking_observations", "shipment_id")
    _ci("ix_tracking_obs_type", "tracking_observations", "observation_type")
    _ci("ix_tracking_obs_provider", "tracking_observations", "tracking_provider_id")
    _ci("ix_tracking_events_obs", "tracking_events", "tracking_observation_id")
    _ci("ix_tracking_events_key", "tracking_events", "event_key")
    _ci("ix_tracking_events_shipment", "tracking_events", "shipment_id")
    _ci("ix_tracking_suggestions_status", "tracking_suggested_updates", "status")
    _ci("ix_tracking_suggestions_type", "tracking_suggested_updates", "suggestion_type")
    _ci("ix_tracking_suggestions_obs", "tracking_suggested_updates", "tracking_observation_id")
    _ci("ix_tracking_mismatches_status", "tracking_mismatches", "status")
    _ci("ix_tracking_mismatches_type", "tracking_mismatches", "mismatch_type")
    _ci("ix_tracking_mismatches_obs", "tracking_mismatches", "tracking_observation_id")
    _ci("ix_tracking_sync_runs_status", "tracking_sync_runs", "status")
    _ci("ix_tracking_sync_runs_provider", "tracking_sync_runs", "tracking_provider_id")
    _ci("ix_tracking_activity_shipment", "tracking_activity_logs", "shipment_id")


def downgrade() -> None:
    for t in [
        "tracking_activity_logs",
        "tracking_sync_runs",
        "tracking_mismatches",
        "tracking_suggested_updates",
        "tracking_events",
        "tracking_observations",
        "tracking_watch_items",
        "tracking_adapter_configs",
        "tracking_providers",
    ]:
        op.drop_table(t)
