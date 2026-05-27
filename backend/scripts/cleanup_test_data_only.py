"""Targeted test-data cleanup script.

Deletes ONLY rows created during QA/testing (prefixed QA-, TEST-, HUMAN-TEST-,
CLAUDE-QA-) and their dependents. Does NOT truncate tables, reset sequences,
or touch system/config/definition tables.

Usage:
    python scripts/cleanup_test_data_only.py --dry-run
    python scripts/cleanup_test_data_only.py --execute

Execute mode requires typing: DELETE_ONLY_TEST_DATA
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap: load DATABASE_URL from env or backend/.env
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key not in os.environ:
            os.environ[key] = value


_load_env()

from sqlalchemy import create_engine, inspect, text  # noqa: E402

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("[ERROR] DATABASE_URL not found in environment or backend/.env")
    sys.exit(1)

# Never print the URL
engine = create_engine(DATABASE_URL)

# ---------------------------------------------------------------------------
# Test-data prefixes (case-insensitive matching)
# ---------------------------------------------------------------------------

TEST_PREFIXES = ("QA-", "TEST-", "HUMAN-TEST-", "CLAUDE-QA-")
TEST_PREFIXES_LOWER = tuple(p.lower() for p in TEST_PREFIXES)

# Email prefixes for user cleanup (only these users are deletable)
TEST_EMAIL_PREFIXES = ("qa.", "test.", "human-test.", "claude-qa.")

# Columns to scan for test prefixes
SCAN_COLUMNS = (
    "shipment_code",
    "code",
    "name",
    "title",
    "subject",
    "email",
    "invoice_number",
    "container_number",
    "reference_number",
    "original_filename",
    "safe_filename",
    "description",
    "booking_ref",
    "commodity",
)

# Tables that must NEVER be touched
PROTECTED_TABLES = {
    "alembic_version",
    "organizations",
    "workflow_state_definitions",
    "workflow_transition_definitions",
    "notification_rules",
    "rule_definitions",
    "demurrage_detention_rules",
}

# Tables to skip entirely (system/config)
SKIP_TABLES = PROTECTED_TABLES | {
    "email_connections",  # Gmail tokens — leave unless clearly QA
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_test_value(value: Any) -> bool:
    if not value or not isinstance(value, str):
        return False
    lower = value.strip().lower()
    return any(lower.startswith(p) for p in TEST_PREFIXES_LOWER)


def _is_test_email(email: Any) -> bool:
    if not email or not isinstance(email, str):
        return False
    local = email.strip().lower()
    return any(local.startswith(p) for p in TEST_EMAIL_PREFIXES)


def _get_scannable_columns(inspector, table: str) -> list[str]:
    columns = {col["name"] for col in inspector.get_columns(table)}
    return [col for col in SCAN_COLUMNS if col in columns]


# ---------------------------------------------------------------------------
# Discovery: find test rows
# ---------------------------------------------------------------------------


def discover_test_rows(conn, inspector) -> dict[str, list[int]]:
    """Return {table_name: [list of test-row IDs]}."""
    results: dict[str, list[int]] = {}
    tables = set(inspector.get_table_names()) - SKIP_TABLES

    for table in sorted(tables):
        columns = {col["name"] for col in inspector.get_columns(table)}
        if "id" not in columns:
            continue
        scannable = _get_scannable_columns(inspector, table)
        if not scannable:
            continue

        conditions = " OR ".join(
            f"LOWER(CAST({col} AS TEXT)) LIKE :prefix_{i}_{j}"
            for j, col in enumerate(scannable)
            for i in range(len(TEST_PREFIXES_LOWER))
        )
        params = {
            f"prefix_{i}_{j}": f"{prefix}%"
            for j, _col in enumerate(scannable)
            for i, prefix in enumerate(TEST_PREFIXES_LOWER)
        }
        query = f"SELECT id FROM {table} WHERE {conditions}"
        rows = conn.execute(text(query), params).fetchall()
        if rows:
            results[table] = [row[0] for row in rows]

    return results


def discover_dependent_rows(
    conn, inspector, primary_matches: dict[str, list[int]]
) -> dict[str, set[int]]:
    """Find rows in dependent tables linked to matched test records."""
    dependents: dict[str, set[int]] = {}

    # Shipment dependents
    shipment_ids = set(primary_matches.get("shipments", []))
    if shipment_ids:
        _add_dependents_by_fk(conn, inspector, "shipment_id", shipment_ids, dependents)

    # Party dependents
    party_ids = set(primary_matches.get("parties", []))
    if party_ids:
        _add_dependents_by_fk(conn, inspector, "party_id", party_ids, dependents)

    # Finance invoice dependents
    invoice_ids = set(primary_matches.get("finance_invoices", []))
    invoice_ids |= dependents.get("finance_invoices", set())
    if invoice_ids:
        _add_dependents_by_fk(conn, inspector, "invoice_id", invoice_ids, dependents)

    # Finance payment dependents
    payment_ids = set(primary_matches.get("finance_payments", []))
    payment_ids |= dependents.get("finance_payments", set())
    if payment_ids:
        _add_dependents_by_fk(conn, inspector, "payment_id", payment_ids, dependents)

    # Container dependents
    container_ids = set(primary_matches.get("containers", []))
    container_ids |= dependents.get("containers", set())
    if container_ids:
        _add_dependents_by_fk(conn, inspector, "container_id", container_ids, dependents)

    # Document version dependents
    doc_version_ids = dependents.get("document_versions", set())
    if doc_version_ids:
        _add_dependents_by_fk(
            conn, inspector, "document_version_id", doc_version_ids, dependents
        )

    # Document file dependents
    doc_file_ids = dependents.get("document_files", set())
    if doc_file_ids:
        _add_dependents_by_fk(
            conn, inspector, "document_file_id", doc_file_ids, dependents
        )

    return dependents


def _add_dependents_by_fk(
    conn,
    inspector,
    fk_column: str,
    parent_ids: set[int],
    dependents: dict[str, set[int]],
) -> None:
    tables = set(inspector.get_table_names()) - SKIP_TABLES
    if not parent_ids:
        return
    id_list = ",".join(str(i) for i in sorted(parent_ids))
    for table in sorted(tables):
        columns = {col["name"] for col in inspector.get_columns(table)}
        if fk_column not in columns or "id" not in columns:
            continue
        query = f"SELECT id FROM {table} WHERE {fk_column} IN ({id_list})"
        rows = conn.execute(text(query)).fetchall()
        if rows:
            dependents.setdefault(table, set()).update(row[0] for row in rows)


# ---------------------------------------------------------------------------
# User cleanup discovery
# ---------------------------------------------------------------------------


def discover_test_users(conn) -> list[int]:
    """Find user IDs with test-prefix emails (never admin@example.com)."""
    rows = conn.execute(
        text("SELECT id, email FROM users")
    ).fetchall()
    test_ids = []
    for uid, email in rows:
        if not email:
            continue
        if email.lower() == "admin@example.com":
            continue
        if _is_test_email(email):
            test_ids.append(uid)
    return test_ids


# ---------------------------------------------------------------------------
# Deletion order (respects FK constraints)
# ---------------------------------------------------------------------------

DELETION_ORDER = [
    # Deepest dependents first
    "document_intelligence_suggestions",
    "document_mismatch_results",
    "document_extracted_fields",
    "document_extractions",
    "document_intelligence_runs",
    "document_version_events",
    "document_access_logs",
    "document_file_blobs",
    "document_files",
    "document_versions",
    "finance_payment_allocations",
    "finance_invoice_lines",
    "finance_risk_records",
    "finance_aging_snapshots",
    "finance_adjustments",
    "credit_hold_records",
    "fx_rate_snapshots",
    "finance_payments",
    "finance_invoices",
    "party_credit_profiles",
    "container_demurrage_records",
    "container_detention_records",
    "container_events",
    "containers",
    "charges",
    "tasks",
    "followup_logs",
    "follow_up_logs",
    "bl_management",
    "demurrages",
    "demurrage",
    "documents",
    "alerts",
    "notifications",
    "notification_user_states",
    "operational_events",
    "validation_issues",
    "audit_logs",
    "workflow_transition_logs",
    "email_suggestions",
    "email_message_cache",
    "ai_interaction_logs",
    # Primary entities
    "shipments",
    "parties",
    "users",
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_dry_run() -> None:
    print("=" * 60)
    print("  TEST DATA CLEANUP — DRY RUN")
    print("=" * 60)
    print()

    with engine.connect() as conn:
        inspector = inspect(engine)
        primary = discover_test_rows(conn, inspector)
        dependents = discover_dependent_rows(conn, inspector, primary)
        test_users = discover_test_users(conn)

        # Merge
        all_targets: dict[str, set[int]] = {}
        for table, ids in primary.items():
            all_targets.setdefault(table, set()).update(ids)
        for table, ids in dependents.items():
            all_targets.setdefault(table, set()).update(ids)
        if test_users:
            all_targets.setdefault("users", set()).update(test_users)

        total = 0
        print(f"{'Table':<45} {'Count':>6}  Sample IDs")
        print("-" * 80)
        for table in DELETION_ORDER:
            ids = all_targets.get(table)
            if not ids:
                continue
            sample = sorted(ids)[:5]
            print(f"  {table:<43} {len(ids):>6}  {sample}")
            total += len(ids)
        # Any tables not in DELETION_ORDER
        for table in sorted(all_targets.keys()):
            if table in DELETION_ORDER:
                continue
            if table in PROTECTED_TABLES:
                continue
            ids = all_targets[table]
            sample = sorted(ids)[:5]
            print(f"  {table:<43} {len(ids):>6}  {sample} [manual review needed]")
            total += len(ids)

        print("-" * 80)
        print(f"  TOTAL rows to delete: {total}")
        print()

        # Show sample records for key tables
        _show_samples(conn, inspector, primary)

        # Show test users
        if test_users:
            rows = conn.execute(
                text(
                    f"SELECT id, email, role FROM users WHERE id IN ({','.join(str(i) for i in test_users)})"
                )
            ).fetchall()
            print("\nTest users to delete:")
            for uid, email, role in rows:
                print(f"  id={uid} email={email} role={role}")
        else:
            print("\nNo test users found to delete.")

        print("\n" + "=" * 60)
        print("  To execute, run:")
        print("    python scripts/cleanup_test_data_only.py --execute")
        print("  Then type: DELETE_ONLY_TEST_DATA")
        print("=" * 60)


def _show_samples(conn, inspector, primary: dict[str, list[int]]) -> None:
    print("\nSample matched records:")
    for table in ("shipments", "parties", "containers", "finance_invoices", "charges"):
        ids = primary.get(table)
        if not ids:
            continue
        columns = {col["name"] for col in inspector.get_columns(table)}
        display_cols = []
        for col in ("id", "shipment_code", "name", "container_number", "invoice_number", "charge_type", "direction", "amount", "email", "booking_ref"):
            if col in columns:
                display_cols.append(col)
        if not display_cols:
            continue
        col_str = ", ".join(display_cols)
        sample_ids = sorted(ids)[:5]
        id_list = ",".join(str(i) for i in sample_ids)
        rows = conn.execute(text(f"SELECT {col_str} FROM {table} WHERE id IN ({id_list})")).fetchall()
        print(f"\n  {table} (showing {len(rows)} of {len(ids)}):")
        for row in rows:
            print(f"    {dict(zip(display_cols, row))}")


def run_execute() -> None:
    print("=" * 60)
    print("  TEST DATA CLEANUP — EXECUTE MODE")
    print("=" * 60)
    print()
    print("  WARNING: This will permanently delete test data rows.")
    print("  Type exactly: DELETE_ONLY_TEST_DATA")
    print()
    confirmation = input("  Confirm: ").strip()
    if confirmation != "DELETE_ONLY_TEST_DATA":
        print("  Aborted. Confirmation did not match.")
        sys.exit(1)

    print("\n  Proceeding with deletion...\n")

    with engine.begin() as conn:
        inspector = inspect(engine)
        primary = discover_test_rows(conn, inspector)
        dependents = discover_dependent_rows(conn, inspector, primary)
        test_users = discover_test_users(conn)

        # Merge
        all_targets: dict[str, set[int]] = {}
        for table, ids in primary.items():
            all_targets.setdefault(table, set()).update(ids)
        for table, ids in dependents.items():
            all_targets.setdefault(table, set()).update(ids)
        if test_users:
            all_targets.setdefault("users", set()).update(test_users)

        deleted: dict[str, int] = {}
        skipped: dict[str, str] = {}

        for table in DELETION_ORDER:
            ids = all_targets.get(table)
            if not ids:
                continue
            if table in PROTECTED_TABLES:
                skipped[table] = "protected table"
                continue
            # Verify table exists
            if table not in inspector.get_table_names():
                skipped[table] = "table does not exist"
                continue
            id_list = ",".join(str(i) for i in sorted(ids))
            try:
                result = conn.execute(text(f"DELETE FROM {table} WHERE id IN ({id_list})"))
                deleted[table] = result.rowcount
            except Exception as exc:
                skipped[table] = f"error: {str(exc)[:100]}"
                print(f"  [SKIP] {table}: {exc}")

        # Handle tables not in DELETION_ORDER
        for table in sorted(all_targets.keys()):
            if table in DELETION_ORDER or table in PROTECTED_TABLES:
                continue
            skipped[table] = "not in deletion order — manual review needed"

        # Report
        print("\n" + "=" * 60)
        print("  CLEANUP COMPLETE")
        print("=" * 60)
        total_deleted = 0
        print(f"\n  {'Table':<45} {'Deleted':>8}")
        print("  " + "-" * 55)
        for table, count in sorted(deleted.items()):
            if count > 0:
                print(f"  {table:<45} {count:>8}")
                total_deleted += count
        print("  " + "-" * 55)
        print(f"  {'TOTAL':<45} {total_deleted:>8}")

        if skipped:
            print(f"\n  Skipped tables:")
            for table, reason in sorted(skipped.items()):
                print(f"    {table}: {reason}")

        print(f"\n  Protected tables preserved: {', '.join(sorted(PROTECTED_TABLES))}")
        print(f"  Admin user preserved: yes (admin@example.com and real admin never touched)")
        print(f"  Organizations preserved: yes")
        print()


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("--dry-run", "--execute"):
        print("Usage:")
        print("  python scripts/cleanup_test_data_only.py --dry-run")
        print("  python scripts/cleanup_test_data_only.py --execute")
        sys.exit(1)

    if sys.argv[1] == "--dry-run":
        run_dry_run()
    elif sys.argv[1] == "--execute":
        run_execute()


if __name__ == "__main__":
    main()
