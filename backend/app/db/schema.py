from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


SHIPMENT_PHASE2_COLUMNS = {
    "vgm_cutoff_date": "DATE",
    "bl_cutoff_date": "DATE",
    "si_cutoff_date": "DATE",
    "do_received_date": "DATE",
    "container_delivered_date": "DATE",
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
