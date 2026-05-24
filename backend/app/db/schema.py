from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


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
