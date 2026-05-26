from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, inspect, text
from sqlalchemy.engine import Engine

from app.services.organization_scope_service import (
    DEFAULT_ORGANIZATION_NAME,
    DEFAULT_ORGANIZATION_SLUG,
    DEFAULT_ORGANIZATION_TYPE,
)


SHIPMENT_PHASE2_COLUMNS = {
    "vgm_cutoff_date": "DATE",
    "bl_cutoff_date": "DATE",
    "si_cutoff_date": "DATE",
    "do_received_date": "DATE",
    "container_delivered_date": "DATE",
}

SHIPMENT_PHASE35_COLUMNS = {
    "is_archived": "BOOLEAN NOT NULL DEFAULT FALSE",
    "archived_at": "TIMESTAMP NULL",
    "archived_by": "INTEGER NULL REFERENCES users(id)",
    "archive_reason": "TEXT NULL",
}

PARTY_PHASE35_COLUMNS = {
    "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
    "deactivated_at": "TIMESTAMP NULL",
    "deactivated_by": "INTEGER NULL REFERENCES users(id)",
    "deactivation_reason": "TEXT NULL",
}


SHIPMENT_PHASE10_COLUMNS = {
    "workflow_state": "VARCHAR(80) NULL",
    "workflow_state_updated_at": "TIMESTAMP NULL",
    "workflow_state_reason": "TEXT NULL",
    "manual_review_required": "BOOLEAN NOT NULL DEFAULT FALSE",
    "manual_review_reason": "TEXT NULL",
}


EMAIL_CONNECTION_PHASE91_COLUMNS = {
    "gmail_account_email": "VARCHAR(255) NULL",
    "gmail_account_id": "VARCHAR(120) NULL",
    "disconnected_at": "TIMESTAMP NULL",
    "last_cleanup_at": "TIMESTAMP NULL",
}

EMAIL_MESSAGE_PHASE91_COLUMNS = {
    "user_id": "INTEGER NULL",
    "gmail_account_email": "VARCHAR(255) NULL",
    "visibility": "VARCHAR(30) NOT NULL DEFAULT 'visible'",
    "subject_hash": "VARCHAR(64) NULL",
}

EMAIL_SUGGESTION_PHASE91_COLUMNS = {
    "user_id": "INTEGER NULL",
    "gmail_account_email": "VARCHAR(255) NULL",
    "extracted_data_hash": "VARCHAR(64) NULL",
}


def ensure_phase10_workflow_schema(engine: Engine) -> None:
    """Ensure Phase 10 shipment columns and workflow indexes exist."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as connection:
        if "shipments" in table_names:
            existing_columns = {column["name"] for column in inspector.get_columns("shipments")}
            for name, column_type in SHIPMENT_PHASE10_COLUMNS.items():
                if name in existing_columns:
                    continue
                connection.execute(
                    text(f"ALTER TABLE shipments ADD COLUMN {name} {column_type}")
                )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_shipments_workflow_state "
                    "ON shipments (workflow_state)"
                )
            )
        if "workflow_state_definitions" in table_names:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_workflow_state_def_flow_type "
                    "ON workflow_state_definitions (flow_type)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_workflow_state_def_state_key "
                    "ON workflow_state_definitions (state_key)"
                )
            )
        if "workflow_transition_definitions" in table_names:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_workflow_transition_def_flow_type "
                    "ON workflow_transition_definitions (flow_type)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_workflow_transition_def_from_state "
                    "ON workflow_transition_definitions (from_state)"
                )
            )
        if "workflow_transition_logs" in table_names:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_workflow_logs_shipment_id "
                    "ON workflow_transition_logs (shipment_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_workflow_logs_status "
                    "ON workflow_transition_logs (status)"
                )
            )


def ensure_phase9_1_gmail_schema(engine: Engine) -> None:
    """Ensure Phase 9.1 columns/indexes exist for Gmail cleanup."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as connection:
        if "email_connections" in table_names:
            existing = {column["name"] for column in inspector.get_columns("email_connections")}
            for name, column_type in EMAIL_CONNECTION_PHASE91_COLUMNS.items():
                if name not in existing:
                    connection.execute(
                        text(f"ALTER TABLE email_connections ADD COLUMN {name} {column_type}")
                    )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_email_connections_gmail_account_email "
                    "ON email_connections (gmail_account_email)"
                )
            )
        if "email_message_cache" in table_names:
            existing = {column["name"] for column in inspector.get_columns("email_message_cache")}
            for name, column_type in EMAIL_MESSAGE_PHASE91_COLUMNS.items():
                if name not in existing:
                    connection.execute(
                        text(f"ALTER TABLE email_message_cache ADD COLUMN {name} {column_type}")
                    )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_email_message_cache_visibility "
                    "ON email_message_cache (visibility)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_email_message_cache_subject_hash "
                    "ON email_message_cache (subject_hash)"
                )
            )
        if "email_suggestions" in table_names:
            existing = {column["name"] for column in inspector.get_columns("email_suggestions")}
            for name, column_type in EMAIL_SUGGESTION_PHASE91_COLUMNS.items():
                if name not in existing:
                    connection.execute(
                        text(f"ALTER TABLE email_suggestions ADD COLUMN {name} {column_type}")
                    )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_email_suggestions_extracted_data_hash "
                    "ON email_suggestions (extracted_data_hash)"
                )
            )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_email_suggestion_dedupe "
                    "ON email_suggestions (email_message_id, suggestion_type, shipment_id, extracted_data_hash)"
                )
            )


def ensure_phase9_event_validation_schema(engine: Engine) -> None:
    """Ensure Phase 9 indexes exist on databases booted via create_all."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as connection:
        if "operational_events" in table_names:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_operational_events_validation_status "
                    "ON operational_events (validation_status)"
                )
            )
        if "rule_definitions" in table_names:
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_rule_definitions_rule_key "
                    "ON rule_definitions (rule_key)"
                )
            )
        if "validation_issues" in table_names:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_validation_issues_status "
                    "ON validation_issues (status)"
                )
            )


def ensure_phase8_organization_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as connection:
        _ensure_organizations_table(connection)
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_organizations_slug ON organizations (slug)")
        )

        if "users" in table_names:
            existing_user_columns = {column["name"] for column in inspector.get_columns("users")}
            if "organization_id" not in existing_user_columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN organization_id INTEGER NULL REFERENCES organizations(id)")
                )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_users_organization_id ON users (organization_id)")
            )
            default_org_id = _ensure_default_organization(connection)
            connection.execute(
                text(
                    "UPDATE users "
                    "SET organization_id = :organization_id "
                    "WHERE organization_id IS NULL"
                ),
                {"organization_id": default_org_id},
            )
        else:
            _ensure_default_organization(connection)


def ensure_phase2_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    if "shipments" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("shipments")}
    missing_columns = [
        (name, column_type)
        for name, column_type in SHIPMENT_PHASE2_COLUMNS.items()
        if name not in existing_columns
    ]
    if not missing_columns:
        return
    with engine.begin() as connection:
        for name, column_type in missing_columns:
            connection.execute(text(f"ALTER TABLE shipments ADD COLUMN {name} {column_type}"))


def ensure_phase35_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    missing_by_table: dict[str, list[tuple[str, str]]] = {}

    if "shipments" in table_names:
        existing_columns = {column["name"] for column in inspector.get_columns("shipments")}
        missing_by_table["shipments"] = [
            (name, column_type)
            for name, column_type in SHIPMENT_PHASE35_COLUMNS.items()
            if name not in existing_columns
        ]

    if "parties" in table_names:
        existing_columns = {column["name"] for column in inspector.get_columns("parties")}
        missing_by_table["parties"] = [
            (name, column_type)
            for name, column_type in PARTY_PHASE35_COLUMNS.items()
            if name not in existing_columns
        ]

    with engine.begin() as connection:
        for table_name, missing_columns in missing_by_table.items():
            for name, column_type in missing_columns:
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {column_type}"))
        _ensure_cancelled_task_status_value(connection, inspector)


def _ensure_cancelled_task_status_value(connection, inspector) -> None:
    if connection.dialect.name != "postgresql":
        return
    if "tasks" not in inspector.get_table_names():
        return
    status_column = next(
        (column for column in inspector.get_columns("tasks") if column["name"] == "status"),
        None,
    )
    if status_column is None:
        return
    column_type = status_column["type"]
    enum_values = getattr(column_type, "enums", None)
    enum_name = getattr(column_type, "name", None)
    if not enum_name or not enum_values or "cancelled" in enum_values:
        return
    connection.execute(
        text(f"ALTER TYPE {_quote_identifier(enum_name)} ADD VALUE IF NOT EXISTS 'cancelled'")
    )


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _ensure_organizations_table(connection) -> None:
    metadata = MetaData()
    organizations = Table(
        "organizations",
        metadata,
        Column("id", Integer, primary_key=True, index=True),
        Column("name", String(255), nullable=False),
        Column("slug", String(255), nullable=False, unique=True, index=True),
        Column("org_type", String(50), nullable=False),
        Column("is_active", Boolean, nullable=False),
        Column("created_at", DateTime, nullable=False),
        Column("updated_at", DateTime, nullable=False),
    )
    organizations.create(connection, checkfirst=True)


def _ensure_default_organization(connection) -> int:
    now = datetime.utcnow()
    connection.execute(
        text(
            "INSERT INTO organizations (name, slug, org_type, is_active, created_at, updated_at) "
            "SELECT :name, :slug, :org_type, :is_active, :created_at, :updated_at "
            "WHERE NOT EXISTS (SELECT 1 FROM organizations WHERE slug = :slug)"
        ),
        {
            "name": DEFAULT_ORGANIZATION_NAME,
            "slug": DEFAULT_ORGANIZATION_SLUG,
            "org_type": DEFAULT_ORGANIZATION_TYPE,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
    )
    default_org_id = connection.execute(
        text("SELECT id FROM organizations WHERE slug = :slug"),
        {"slug": DEFAULT_ORGANIZATION_SLUG},
    ).scalar_one()
    return int(default_org_id)
