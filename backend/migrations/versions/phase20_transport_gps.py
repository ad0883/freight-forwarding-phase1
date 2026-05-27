"""Phase 20 Transport + GPS layer.

Revision ID: phase20_transport_gps
Revises: phase19_customs_coord
Create Date: 2026-05-28
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "phase20_transport_gps"
down_revision: Union[str, None] = "phase19_customs_coord"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ci(n, t, c):
    op.execute(f"CREATE INDEX IF NOT EXISTS {n} ON {t} ({c})")


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())

    if "transport_vehicles" not in tables:
        op.create_table(
            "transport_vehicles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("transporter_party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
            sa.Column("vehicle_number", sa.String(30), nullable=False),
            sa.Column("vehicle_type", sa.String(30), nullable=False, server_default="trailer_20"),
            sa.Column("capacity", sa.String(60), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("insurance_valid_until", sa.DateTime(), nullable=True),
            sa.Column("fitness_valid_until", sa.DateTime(), nullable=True),
            sa.Column("permit_valid_until", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "transport_drivers" not in tables:
        op.create_table(
            "transport_drivers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("transporter_party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
            sa.Column("driver_name", sa.String(150), nullable=False),
            sa.Column("phone", sa.String(20), nullable=True),
            sa.Column("license_number", sa.String(40), nullable=True),
            sa.Column("license_valid_until", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "transport_jobs" not in tables:
        op.create_table(
            "transport_jobs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=False),
            sa.Column("job_number", sa.String(60), nullable=False, unique=True),
            sa.Column("job_type", sa.String(40), nullable=False),
            sa.Column("movement_type", sa.String(40), nullable=False, server_default="containerized"),
            sa.Column("status", sa.String(40), nullable=False, server_default="planned"),
            sa.Column("priority", sa.String(10), nullable=False, server_default="p3"),
            sa.Column("transporter_party_id", sa.Integer(), sa.ForeignKey("parties.id"), nullable=True),
            sa.Column("transporter_name", sa.String(255), nullable=True),
            sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("assigned_to_name", sa.String(150), nullable=True),
            sa.Column("pickup_location", sa.String(255), nullable=True),
            sa.Column("delivery_location", sa.String(255), nullable=True),
            sa.Column("origin_address", sa.Text(), nullable=True),
            sa.Column("destination_address", sa.Text(), nullable=True),
            sa.Column("planned_pickup_at", sa.DateTime(), nullable=True),
            sa.Column("actual_pickup_at", sa.DateTime(), nullable=True),
            sa.Column("planned_delivery_at", sa.DateTime(), nullable=True),
            sa.Column("actual_delivery_at", sa.DateTime(), nullable=True),
            sa.Column("planned_empty_return_at", sa.DateTime(), nullable=True),
            sa.Column("actual_empty_return_at", sa.DateTime(), nullable=True),
            sa.Column("eta", sa.DateTime(), nullable=True),
            sa.Column("last_location_text", sa.String(255), nullable=True),
            sa.Column("last_latitude", sa.Float(), nullable=True),
            sa.Column("last_longitude", sa.Float(), nullable=True),
            sa.Column("last_location_at", sa.DateTime(), nullable=True),
            sa.Column("delay_reason", sa.Text(), nullable=True),
            sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("transport_vehicles.id"), nullable=True),
            sa.Column("driver_id", sa.Integer(), sa.ForeignKey("transport_drivers.id"), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_name", sa.String(150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "transport_job_containers" not in tables:
        op.create_table(
            "transport_job_containers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=False),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("container_id", sa.Integer(), sa.ForeignKey("containers.id"), nullable=True),
            sa.Column("container_number", sa.String(20), nullable=True),
            sa.Column("movement_role", sa.String(30), nullable=False, server_default="pickup"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "transport_milestones" not in tables:
        op.create_table(
            "transport_milestones",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=False),
            sa.Column("milestone_key", sa.String(80), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("planned_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("completed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("completed_by_name", sa.String(150), nullable=True),
            sa.Column("location_text", sa.String(255), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("evidence_document_version_id", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "transport_location_updates" not in tables:
        op.create_table(
            "transport_location_updates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=False),
            sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
            sa.Column("location_text", sa.String(255), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("recorded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("recorded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("recorded_by_name", sa.String(150), nullable=True),
            sa.Column("accuracy_meters", sa.Float(), nullable=True),
            sa.Column("speed", sa.Float(), nullable=True),
            sa.Column("heading", sa.Float(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if "transport_documents" not in tables:
        op.create_table(
            "transport_documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=False),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("document_version_id", sa.Integer(), nullable=True),
            sa.Column("document_type", sa.String(60), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("visible_to_customer", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("uploaded_by_name", sa.String(150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "transport_exceptions" not in tables:
        op.create_table(
            "transport_exceptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=False),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("container_id", sa.Integer(), sa.ForeignKey("containers.id"), nullable=True),
            sa.Column("exception_type", sa.String(40), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("delay_minutes", sa.Integer(), nullable=True),
            sa.Column("linked_exception_case_id", sa.Integer(), sa.ForeignKey("exception_cases.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("resolved_by_name", sa.String(150), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "transport_activity_logs" not in tables:
        op.create_table(
            "transport_activity_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=False),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("activity_type", sa.String(60), nullable=False),
            sa.Column("safe_summary", sa.Text(), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_by_name", sa.String(150), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    if "transport_charge_refs" not in tables:
        op.create_table(
            "transport_charge_refs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("transport_job_id", sa.Integer(), sa.ForeignKey("transport_jobs.id"), nullable=False),
            sa.Column("shipment_id", sa.Integer(), sa.ForeignKey("shipments.id"), nullable=True),
            sa.Column("charge_id", sa.Integer(), sa.ForeignKey("charges.id"), nullable=True),
            sa.Column("charge_type", sa.String(60), nullable=False, server_default="transport"),
            sa.Column("estimated_amount", sa.Numeric(14, 2), nullable=True),
            sa.Column("actual_amount", sa.Numeric(14, 2), nullable=True),
            sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )

    # Indexes
    _ci("ix_transport_jobs_shipment", "transport_jobs", "shipment_id")
    _ci("ix_transport_jobs_status", "transport_jobs", "status")
    _ci("ix_transport_jobs_type", "transport_jobs", "job_type")
    _ci("ix_transport_jobs_number", "transport_jobs", "job_number")
    _ci("ix_transport_jobs_vehicle", "transport_jobs", "vehicle_id")
    _ci("ix_transport_jobs_driver", "transport_jobs", "driver_id")
    _ci("ix_transport_job_containers_job", "transport_job_containers", "transport_job_id")
    _ci("ix_transport_job_containers_ctr", "transport_job_containers", "container_id")
    _ci("ix_transport_milestones_job", "transport_milestones", "transport_job_id")
    _ci("ix_transport_locations_job", "transport_location_updates", "transport_job_id")
    _ci("ix_transport_documents_job", "transport_documents", "transport_job_id")
    _ci("ix_transport_exceptions_job", "transport_exceptions", "transport_job_id")
    _ci("ix_transport_exceptions_status", "transport_exceptions", "status")
    _ci("ix_transport_exceptions_type", "transport_exceptions", "exception_type")
    _ci("ix_transport_activity_job", "transport_activity_logs", "transport_job_id")
    _ci("ix_transport_charge_refs_job", "transport_charge_refs", "transport_job_id")
    _ci("ix_transport_vehicles_number", "transport_vehicles", "vehicle_number")
    _ci("ix_transport_vehicles_status", "transport_vehicles", "status")
    _ci("ix_transport_drivers_status", "transport_drivers", "status")


def downgrade() -> None:
    for t in [
        "transport_charge_refs",
        "transport_activity_logs",
        "transport_exceptions",
        "transport_documents",
        "transport_location_updates",
        "transport_milestones",
        "transport_job_containers",
        "transport_jobs",
        "transport_drivers",
        "transport_vehicles",
    ]:
        op.drop_table(t)
