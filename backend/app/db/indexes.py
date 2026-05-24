from sqlalchemy import text
from sqlalchemy.engine import Engine


PERFORMANCE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_shipments_status_created_at ON shipments (status, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_shipments_status_etd ON shipments (status, etd)",
    "CREATE INDEX IF NOT EXISTS ix_shipments_type_created_at ON shipments (type, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_shipments_archived_created_at ON shipments (is_archived, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_shipments_export_cutoffs ON shipments (type, vgm_cutoff_date, bl_cutoff_date, si_cutoff_date)",
    "CREATE INDEX IF NOT EXISTS ix_shipments_import_dates ON shipments (type, eta, do_received_date, container_delivered_date)",
    "CREATE INDEX IF NOT EXISTS ix_tasks_status_due_date ON tasks (status, due_date)",
    "CREATE INDEX IF NOT EXISTS ix_tasks_shipment_status ON tasks (shipment_id, status)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_created_at ON alerts (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_is_read_created_at ON alerts (is_read, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_documents_shipment_status ON documents (shipment_id, status)",
    "CREATE INDEX IF NOT EXISTS ix_documents_doc_type_status ON documents (doc_type, status)",
    "CREATE INDEX IF NOT EXISTS ix_bl_management_shipment ON bl_management (shipment_id)",
    "CREATE INDEX IF NOT EXISTS ix_demurrage_shipment_status ON demurrage (shipment_id, status)",
    "CREATE INDEX IF NOT EXISTS ix_follow_up_logs_shipment_date ON follow_up_logs (shipment_id, date)",
    "CREATE INDEX IF NOT EXISTS ix_parties_type_name ON parties (type, name)",
    "CREATE INDEX IF NOT EXISTS ix_parties_active_name ON parties (is_active, name)",
    "CREATE INDEX IF NOT EXISTS ix_charges_shipment_status ON charges (shipment_id, status)",
    "CREATE INDEX IF NOT EXISTS ix_charges_direction_status ON charges (direction, status)",
    "CREATE INDEX IF NOT EXISTS ix_charges_date_created_at ON charges (date, created_at)",
]


def ensure_performance_indexes(engine: Engine) -> None:
    with engine.begin() as connection:
        for statement in PERFORMANCE_INDEXES:
            connection.execute(text(statement))
