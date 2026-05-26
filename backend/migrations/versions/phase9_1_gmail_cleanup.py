"""Phase 9.1 Gmail automation hardening: account scoping + dedupe.

Revision ID: phase9_1_gmail_cleanup
Revises: phase9_event_validation
Create Date: 2026-05-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "phase9_1_gmail_cleanup"
down_revision: Union[str, None] = "phase9_event_validation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONNECTION_COLUMNS = [
    ("gmail_account_email", sa.String(length=255), True, None),
    ("gmail_account_id", sa.String(length=120), True, None),
    ("disconnected_at", sa.DateTime(), True, None),
    ("last_cleanup_at", sa.DateTime(), True, None),
]

MESSAGE_COLUMNS = [
    ("user_id", sa.Integer(), True, None),
    ("gmail_account_email", sa.String(length=255), True, None),
    ("visibility", sa.String(length=30), False, sa.text("'visible'")),
    ("subject_hash", sa.String(length=64), True, None),
]

SUGGESTION_COLUMNS = [
    ("user_id", sa.Integer(), True, None),
    ("gmail_account_email", sa.String(length=255), True, None),
    ("extracted_data_hash", sa.String(length=64), True, None),
]


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())

    if "email_connections" in table_names:
        existing = {column["name"] for column in inspector.get_columns("email_connections")}
        for name, column_type, nullable, default in CONNECTION_COLUMNS:
            if name in existing:
                continue
            op.add_column(
                "email_connections",
                sa.Column(name, column_type, nullable=nullable, server_default=default),
            )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_email_connections_gmail_account_email "
            "ON email_connections (gmail_account_email)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_email_connections_gmail_account_id "
            "ON email_connections (gmail_account_id)"
        )

    if "email_message_cache" in table_names:
        existing = {column["name"] for column in inspector.get_columns("email_message_cache")}
        for name, column_type, nullable, default in MESSAGE_COLUMNS:
            if name in existing:
                continue
            op.add_column(
                "email_message_cache",
                sa.Column(name, column_type, nullable=nullable, server_default=default),
            )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_email_message_cache_user_id "
            "ON email_message_cache (user_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_email_message_cache_gmail_account_email "
            "ON email_message_cache (gmail_account_email)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_email_message_cache_visibility "
            "ON email_message_cache (visibility)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_email_message_cache_subject_hash "
            "ON email_message_cache (subject_hash)"
        )
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_email_message_account_gmail_id "
            "ON email_message_cache (user_id, gmail_account_email, gmail_message_id)"
        )

    if "email_suggestions" in table_names:
        existing = {column["name"] for column in inspector.get_columns("email_suggestions")}
        for name, column_type, nullable, default in SUGGESTION_COLUMNS:
            if name in existing:
                continue
            op.add_column(
                "email_suggestions",
                sa.Column(name, column_type, nullable=nullable, server_default=default),
            )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_email_suggestions_user_id "
            "ON email_suggestions (user_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_email_suggestions_gmail_account_email "
            "ON email_suggestions (gmail_account_email)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_email_suggestions_extracted_data_hash "
            "ON email_suggestions (extracted_data_hash)"
        )
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_email_suggestion_dedupe "
            "ON email_suggestions (email_message_id, suggestion_type, shipment_id, extracted_data_hash)"
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    if connection.dialect.name == "sqlite":
        return
    if "email_suggestions" in inspector.get_table_names():
        op.execute("DROP INDEX IF EXISTS uq_email_suggestion_dedupe")
        for name, *_ in SUGGESTION_COLUMNS:
            op.drop_column("email_suggestions", name)
    if "email_message_cache" in inspector.get_table_names():
        op.execute("DROP INDEX IF EXISTS uq_email_message_account_gmail_id")
        for name, *_ in MESSAGE_COLUMNS:
            op.drop_column("email_message_cache", name)
    if "email_connections" in inspector.get_table_names():
        for name, *_ in CONNECTION_COLUMNS:
            op.drop_column("email_connections", name)
