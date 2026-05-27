"""Safely identify and optionally delete obvious QA/test data only.

Usage:
    python scripts/cleanup_test_data_only.py --dry-run
    python scripts/cleanup_test_data_only.py --execute

The execute mode prompts for the exact phrase DELETE_ONLY_TEST_DATA. It never
prints environment values and intentionally skips system/default definition
tables.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import String, Text, and_, delete, func, or_, select
from sqlalchemy.sql.elements import ColumnElement


ROOT = Path(__file__).resolve().parents[1]


def load_backend_env() -> None:
    if os.environ.get("DATABASE_URL"):
        return
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key == "DATABASE_URL" and not os.environ.get("DATABASE_URL"):
            os.environ[key] = value.strip().strip("'\"")
            return


load_backend_env()
sys.path.insert(0, str(ROOT))

from app.db.session import Base, SessionLocal  # noqa: E402
from app import models as _models  # noqa: F401,E402


TEST_PREFIXES = ("QA-", "TEST-", "HUMAN-TEST-", "CLAUDE-QA-")
PROTECTED_TABLES = {
    "alembic_version",
    "workflow_state_definitions",
    "workflow_transition_definitions",
    "notification_rules",
    "rule_definitions",
    "demurrage_detention_rules",
}
PROTECTED_SUFFIXES = ("_definitions",)


def is_protected_table(table_name: str) -> bool:
    return table_name in PROTECTED_TABLES or table_name.endswith(PROTECTED_SUFFIXES)


def text_prefix_conditions(table, column_names: tuple[str, ...]) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    for name in column_names:
        if name not in table.c:
            continue
        column = table.c[name]
        if not isinstance(column.type, (String, Text)):
            continue
        for prefix in TEST_PREFIXES:
            conditions.append(func.lower(column).like(f"{prefix.lower()}%"))
    return conditions


def ids_for(session, table_name: str, conditions: list[ColumnElement[bool]]) -> set[int]:
    table = Base.metadata.tables.get(table_name)
    if table is None or "id" not in table.c or not conditions:
        return set()
    rows = session.execute(select(table.c.id).where(or_(*conditions))).scalars().all()
    return {int(row) for row in rows}


def linked_ids(session, table_name: str, conditions: list[ColumnElement[bool]]) -> set[int]:
    return ids_for(session, table_name, conditions)


def in_ids(column, values: set[int]) -> ColumnElement[bool] | None:
    if not values:
        return None
    return column.in_(sorted(values))


def table_count(session, table, condition: ColumnElement[bool]) -> int:
    return int(session.execute(select(func.count()).select_from(table).where(condition)).scalar_one())


def build_targets(session) -> dict[str, set[int]]:
    tables = Base.metadata.tables
    targets: dict[str, set[int]] = {}

    shipments = tables.get("shipments")
    if shipments is not None:
        targets["shipments"] = ids_for(
            session,
            "shipments",
            text_prefix_conditions(
                shipments,
                (
                    "shipment_code",
                    "shipping_line",
                    "vessel_name",
                    "voyage_no",
                    "booking_ref",
                    "container_no",
                    "commodity",
                ),
            ),
        )

    parties = tables.get("parties")
    if parties is not None:
        targets["parties"] = ids_for(
            session,
            "parties",
            text_prefix_conditions(parties, ("name", "email", "contact_person", "gstin")),
        )

    users = tables.get("users")
    if users is not None:
        user_conditions = text_prefix_conditions(users, ("name", "email"))
        if user_conditions and "role" in users.c:
            user_conditions = [and_(or_(*user_conditions), users.c.role != "ADMIN")]
        targets["users_manual_review"] = ids_for(session, "users", user_conditions)

    organizations = tables.get("organizations")
    if organizations is not None:
        targets["organizations_manual_review"] = ids_for(
            session,
            "organizations",
            text_prefix_conditions(organizations, ("name", "slug")),
        )

    shipment_ids = targets.get("shipments", set())
    party_ids = targets.get("parties", set())

    documents = tables.get("documents")
    if documents is not None:
        conditions: list[ColumnElement[bool]] = []
        if "shipment_id" in documents.c:
            match = in_ids(documents.c.shipment_id, shipment_ids)
            if match is not None:
                conditions.append(match)
        conditions.extend(text_prefix_conditions(documents, ("doc_type", "file_url", "notes")))
        targets["documents"] = linked_ids(session, "documents", conditions)

    doc_ids = targets.get("documents", set())
    document_files = tables.get("document_files")
    if document_files is not None:
        conditions = []
        for column_name, values in (
            ("shipment_id", shipment_ids),
            ("document_id", doc_ids),
        ):
            if column_name in document_files.c:
                match = in_ids(document_files.c[column_name], values)
                if match is not None:
                    conditions.append(match)
        conditions.extend(
            text_prefix_conditions(
                document_files,
                ("original_filename", "sanitized_filename", "storage_key", "uploaded_by_name"),
            )
        )
        targets["document_files"] = linked_ids(session, "document_files", conditions)

    containers = tables.get("containers")
    if containers is not None:
        conditions = []
        if "shipment_id" in containers.c:
            match = in_ids(containers.c.shipment_id, shipment_ids)
            if match is not None:
                conditions.append(match)
        conditions.extend(text_prefix_conditions(containers, ("container_number", "seal_number", "current_location")))
        targets["containers"] = linked_ids(session, "containers", conditions)

    charges = tables.get("charges")
    if charges is not None:
        conditions = []
        for column_name, values in (("shipment_id", shipment_ids), ("party_id", party_ids)):
            if column_name in charges.c:
                match = in_ids(charges.c[column_name], values)
                if match is not None:
                    conditions.append(match)
        conditions.extend(text_prefix_conditions(charges, ("invoice_no", "notes")))
        targets["charges"] = linked_ids(session, "charges", conditions)

    for table_name in ("finance_invoices", "finance_payments"):
        table = tables.get(table_name)
        if table is None:
            continue
        conditions = []
        for column_name, values in (("shipment_id", shipment_ids), ("party_id", party_ids)):
            if column_name in table.c:
                match = in_ids(table.c[column_name], values)
                if match is not None:
                    conditions.append(match)
        conditions.extend(text_prefix_conditions(table, ("invoice_number", "reference_number", "notes", "created_by_name")))
        targets[table_name] = linked_ids(session, table_name, conditions)

    return targets


def condition_for_table(table, targets: dict[str, set[int]]) -> ColumnElement[bool] | None:
    parts: list[ColumnElement[bool]] = []
    direct_ids = targets.get(table.name, set())
    if "id" in table.c and direct_ids:
        parts.append(table.c.id.in_(sorted(direct_ids)))

    link_columns = {
        "shipment_id": "shipments",
        "party_id": "parties",
        "document_id": "documents",
        "document_file_id": "document_files",
        "container_id": "containers",
        "charge_id": "charges",
        "invoice_id": "finance_invoices",
        "payment_id": "finance_payments",
    }
    for column_name, target_name in link_columns.items():
        values = targets.get(target_name, set())
        if column_name in table.c and values:
            parts.append(table.c[column_name].in_(sorted(values)))

    if not parts:
        return None
    return or_(*parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="show matched counts without deleting")
    group.add_argument("--execute", action="store_true", help="delete matched test data after confirmation")
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL is not available. Set it in the environment or backend/.env.")
        return 2

    session = SessionLocal()
    try:
        targets = build_targets(session)
        print("Matched obvious QA/test IDs:")
        for name in sorted(targets):
            print(f"  {name}: {len(targets[name])}")

        manual_review = {
            name: values
            for name, values in targets.items()
            if name.endswith("_manual_review") and values
        }
        if manual_review:
            print("Manual review needed before deleting these protected entity types:")
            for name, values in sorted(manual_review.items()):
                print(f"  {name}: {len(values)}")

        delete_plan: list[tuple[str, int]] = []
        for table in reversed(Base.metadata.sorted_tables):
            if is_protected_table(table.name):
                continue
            if table.name in {"users", "organizations"}:
                continue
            condition = condition_for_table(table, targets)
            if condition is None:
                continue
            count = table_count(session, table, condition)
            if count:
                delete_plan.append((table.name, count))

        print("Delete plan:")
        if delete_plan:
            for table_name, count in delete_plan:
                print(f"  {table_name}: {count}")
        else:
            print("  No rows matched.")

        if args.dry_run:
            session.rollback()
            return 0

        confirmation = input("Type DELETE_ONLY_TEST_DATA to execute: ")
        if confirmation != "DELETE_ONLY_TEST_DATA":
            print("Confirmation did not match. No rows deleted.")
            session.rollback()
            return 1

        for table in reversed(Base.metadata.sorted_tables):
            if is_protected_table(table.name) or table.name in {"users", "organizations"}:
                continue
            condition = condition_for_table(table, targets)
            if condition is None:
                continue
            session.execute(delete(table).where(condition))
        session.commit()
        print("Deleted only matched QA/test-linked rows. Protected tables were skipped.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
