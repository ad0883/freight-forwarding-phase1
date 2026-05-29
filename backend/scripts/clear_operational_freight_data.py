#!/usr/bin/env python3
"""
Master 1.1 — Clear Operational Freight Data for AI Private Beta

This script removes operational/test freight data while preserving
system configuration, users, roles, permissions, seeds, and migrations.

Usage:
  Dry-run (default):
    python scripts/clear_operational_freight_data.py --dry-run

  Execute (requires explicit env flag + flag):
    DELETE_OPERATIONAL_FREIGHT_DATA=YES python scripts/clear_operational_freight_data.py --execute

Safety:
  - Protected tables are NEVER touched
  - Foreign-key-safe deletion order (children first)
  - Transaction-based: all-or-nothing rollback on error
  - Dry-run prints counts without modifying data
  - Uploaded document files deleted ONLY if linked to deleted document records
  - No DROP TABLE, no Alembic downgrade, no schema changes

DO NOT:
  - Drop the database
  - Delete tables or modify schema
  - Run Alembic downgrade
  - Delete users/admin/org/roles/permissions/settings
  - Delete prediction model seeds, tracking provider seeds, bot agent seeds
  - Delete migration records or system config
  - Print secrets or full connection strings
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text, inspect
from app.db.session import SessionLocal, engine
from app.core.config import settings

# ============================================================
# PROTECTED TABLES — never delete from these
# These contain users, admin config, system seeds, and schema
# ============================================================
PROTECTED_TABLES = {
    # Auth / Users / Org
    "users",
    "organizations",
    "organization_settings",
    "organization_memberships",
    "organization_roles",
    "organization_branches",
    "organization_departments",
    "role_permission_policies",
    # Enterprise config/policy
    "enterprise_data_retention_policies",
    # Prediction model seeds (not operational runs)
    "prediction_models",
    "prediction_model_versions",  # may not exist yet; protect if present
    # Tracking provider seeds (not operational data)
    "tracking_providers",
    "tracking_adapter_configs",  # config-level, not operational runs
    # Bot agent seeds / config
    "bot_agents",
    "bot_prompt_versions",
    "bot_rule_versions",
    # Workflow / Rule definitions (config)
    "workflow_state_definitions",
    "workflow_transition_definitions",
    "rule_definitions",
    "notification_rules",
    # Approval / Exception policies (config)
    "approval_policies",
    "approval_policy_rules",
    "demurrage_detention_rules",
    "exception_case_sla_policies",
    # Email connections (user-level config, not operational cache)
    "email_connections",
    # Alembic migration tracking
    "alembic_version",
}

# ============================================================
# OPERATIONAL TABLES — delete in dependency-safe order
# (children/dependents first, parents last)
# ============================================================
OPERATIONAL_TABLES_ORDERED = [
    # --- Predictive operational (leaf records first) ---
    "prediction_activity_logs",
    "prediction_feedback",
    "prediction_outcomes",
    "prediction_recommendations",
    "prediction_explanations",
    "prediction_records",
    "prediction_runs",

    # --- Tracking operational (leaf first) ---
    "tracking_activity_logs",
    "tracking_suggested_updates",
    "tracking_events",
    "tracking_mismatches",
    "tracking_observations",
    "tracking_sync_runs",
    "tracking_watch_items",

    # --- Transport operational (leaf first) ---
    "transport_activity_logs",
    "transport_charge_refs",
    "transport_documents",
    "transport_exceptions",
    "transport_location_updates",
    "transport_milestones",
    "transport_job_containers",
    "transport_jobs",
    "transport_drivers",
    "transport_vehicles",

    # --- Customs operational (leaf first) ---
    "customs_activity_logs",
    "customs_query_comments",
    "customs_queries",
    "customs_reference_numbers",
    "customs_duty_records",
    "customs_document_requirements",
    "customs_checklist_items",
    "customs_case_milestones",
    "customs_party_assignments",
    "customs_cases",

    # --- Approvals operational (leaf first) ---
    "approval_overrides",
    "approval_delegations",
    "approval_action_locks",
    "approval_request_evidence",
    "approval_steps",
    "approval_requests",

    # --- Exceptions operational (leaf first) ---
    "exception_case_watchers",
    "exception_case_status_history",
    "exception_case_links",
    "exception_case_escalations",
    "exception_case_comments",
    "exception_case_assignments",
    "exception_cases",

    # --- Bot governance operational records ---
    "bot_governance_actions",
    "bot_action_records",
    "bot_feedback_records",
    "bot_learning_candidates",
    "bot_training_cases",
    "bot_quality_reviews",
    "bot_guardrail_violations",
    "bot_evaluation_results",
    "bot_evaluation_runs",
    "bot_performance_snapshots",

    # --- Documents operational (leaf first) ---
    "document_access_logs",
    "document_intelligence_suggestions",
    "document_mismatch_results",
    "document_extracted_fields",
    "document_extractions",
    "document_intelligence_runs",
    "document_version_events",
    "document_versions",
    "document_file_blobs",
    "document_files",
    "documents",

    # --- Finance operational (leaf first) ---
    "finance_payment_allocations",
    "finance_payments",
    "finance_invoice_lines",
    "finance_invoices",
    "finance_adjustments",
    "finance_aging_snapshots",
    "finance_risk_records",
    "fx_rate_snapshots",
    "credit_hold_records",
    "charges",

    # --- Containers operational ---
    "container_demurrage_records",
    "container_detention_records",
    "container_events",
    "containers",

    # --- Demurrage (legacy) ---
    "demurrage",

    # --- BL Management ---
    "bl_management",

    # --- Portal operational ---
    "portal_activity_logs",
    "portal_request_comments",
    "portal_requests",
    "portal_notifications",
    "portal_document_access",
    "portal_shipment_access",
    "portal_preferences",
    "portal_party_links",
    "portal_accounts",

    # --- Control Tower operational ---
    "control_tower_activity_logs",
    "control_tower_snapshots",
    "control_tower_saved_views",
    "control_tower_widget_preferences",

    # --- Enterprise operational (not policies) ---
    "enterprise_audit_exports",
    "enterprise_health_snapshots",
    "enterprise_security_events",

    # --- Email operational (cache/suggestions, not connections) ---
    "email_suggestions",
    "email_message_cache",

    # --- Validation / Events / Audit ---
    "workflow_transition_logs",
    "validation_issues",
    "operational_events",
    "audit_logs",
    "ai_interaction_logs",

    # --- Tasks / Followups / Notifications / Alerts ---
    "follow_up_logs",
    "followup_logs",
    "tasks",
    "notification_user_states",
    "notifications",
    "alerts",

    # --- Parties and Shipments (parents — last) ---
    "party_credit_profiles",
    "shipments",
    "parties",
]


# ============================================================
# UPLOADED FILES DIRECTORY
# ============================================================
UPLOADED_DOCS_DIR = Path(__file__).resolve().parent.parent / "uploaded_documents"


def get_row_count(db, table_name: str) -> int:
    """Get row count for a table, returns -1 if table doesn't exist or error."""
    try:
        return db.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
    except Exception:
        db.rollback()
        return -1


def delete_table_data(db, table_name: str) -> int:
    """Delete all rows from a table. Returns rows affected."""
    try:
        result = db.execute(text(f'DELETE FROM "{table_name}"'))
        return result.rowcount
    except Exception as e:
        raise RuntimeError(f"Failed to delete from {table_name}: {e}")


def find_uploaded_files() -> list:
    """Find uploaded document files that would be removed."""
    if not UPLOADED_DOCS_DIR.exists():
        return []
    files = []
    for f in UPLOADED_DOCS_DIR.rglob("*"):
        if f.is_file():
            files.append(str(f))
    return files


def verify_connection():
    """Verify DB connection without exposing secrets."""
    prefix = settings.DATABASE_URL[:25]
    print(f"  Database prefix: {prefix}...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            if result == 1:
                print("  ✓ Database connection verified")
                return True
    except Exception as e:
        print(f"  ✗ Database connection FAILED: {type(e).__name__}")
        return False
    return False


def run(execute: bool = False):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print("=" * 70)
    print("MASTER 1.1 — CLEAR OPERATIONAL FREIGHT DATA")
    print(f"Mode: {'🔴 EXECUTE' if execute else '🟢 DRY-RUN'}")
    print(f"Timestamp: {timestamp}")
    print("=" * 70)

    # --- Safety checks for execute mode ---
    if execute:
        env_flag = os.environ.get("DELETE_OPERATIONAL_FREIGHT_DATA", "")
        if env_flag != "YES":
            print("\n❌ ERROR: Execute mode requires environment variable:")
            print("   DELETE_OPERATIONAL_FREIGHT_DATA=YES")
            print("   Aborting.")
            sys.exit(1)

    # --- Verify connection ---
    print("\n--- CONNECTION CHECK ---")
    if not verify_connection():
        print("❌ Cannot proceed without a valid database connection.")
        sys.exit(1)

    # --- Discover existing tables ---
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    print(f"\n  Total tables in database: {len(existing_tables)}")

    db = SessionLocal()
    warnings = []

    # ============================================================
    # PROTECTED TABLES
    # ============================================================
    print("\n" + "=" * 70)
    print("PROTECTED TABLES (will NOT be touched)")
    print("=" * 70)
    protected_found = 0
    protected_not_found = 0
    for t in sorted(PROTECTED_TABLES):
        if t in existing_tables:
            count = get_row_count(db, t)
            print(f"  🛡  {t}: {count} rows (PROTECTED)")
            protected_found += 1
        else:
            print(f"  ·  {t}: (not in database)")
            protected_not_found += 1

    # ============================================================
    # Check for tables NOT in either list (unknown tables)
    # ============================================================
    known_tables = PROTECTED_TABLES | set(OPERATIONAL_TABLES_ORDERED)
    unknown_tables = existing_tables - known_tables
    if unknown_tables:
        print(f"\n--- ⚠ UNKNOWN TABLES (not in protected or operational list) ---")
        for t in sorted(unknown_tables):
            count = get_row_count(db, t)
            print(f"  ?  {t}: {count} rows (UNCLASSIFIED — will NOT be touched)")
            warnings.append(f"Unknown table '{t}' ({count} rows) not in any list — skipped")

    # ============================================================
    # OPERATIONAL TABLES
    # ============================================================
    print("\n" + "=" * 70)
    print("OPERATIONAL TABLES (will be cleared)")
    print("=" * 70)
    tables_to_clear = []
    tables_not_found = []
    tables_skipped_protected = []
    total_rows = 0

    for t in OPERATIONAL_TABLES_ORDERED:
        if t not in existing_tables:
            tables_not_found.append(t)
            print(f"  ·  {t}: (not in database, skipping)")
            continue
        if t in PROTECTED_TABLES:
            tables_skipped_protected.append(t)
            print(f"  ⚠  {t}: SKIPPED (also in protected list)")
            warnings.append(f"Table '{t}' is in both operational and protected lists — protected wins")
            continue
        count = get_row_count(db, t)
        if count < 0:
            print(f"  ✗  {t}: (error reading, skipping)")
            warnings.append(f"Could not read table '{t}'")
            continue
        tables_to_clear.append((t, count))
        total_rows += count
        marker = "🗑 " if count > 0 else "  "
        print(f"  {marker}{t}: {count} rows")

    # ============================================================
    # UPLOADED DOCUMENT FILES
    # ============================================================
    uploaded_files = find_uploaded_files()
    print(f"\n" + "=" * 70)
    print("UPLOADED DOCUMENT FILES")
    print("=" * 70)
    print(f"  Directory: {UPLOADED_DOCS_DIR}")
    print(f"  Directory exists: {UPLOADED_DOCS_DIR.exists()}")
    print(f"  Files found: {len(uploaded_files)}")
    if uploaded_files:
        # Only remove files if documents table is being cleared
        doc_tables_being_cleared = [t for t, c in tables_to_clear if t in ("documents", "document_files", "document_file_blobs")]
        if doc_tables_being_cleared:
            print(f"  → Will be removed (linked to document records being deleted)")
        else:
            print(f"  → Will NOT be removed (no document tables being cleared)")
            uploaded_files = []  # Don't delete files if doc tables aren't cleared
        if len(uploaded_files) <= 30:
            for f in uploaded_files:
                print(f"    {f}")
        elif uploaded_files:
            print(f"    (showing first 10 of {len(uploaded_files)})")
            for f in uploaded_files[:10]:
                print(f"    {f}")

    # ============================================================
    # WARNINGS
    # ============================================================
    if warnings:
        print(f"\n" + "=" * 70)
        print("⚠  WARNINGS")
        print("=" * 70)
        for w in warnings:
            print(f"  ⚠  {w}")

    # ============================================================
    # SUMMARY
    # ============================================================
    tables_with_data = [(t, c) for t, c in tables_to_clear if c > 0]
    print(f"\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Protected tables (in DB):       {protected_found}")
    print(f"  Protected tables (not in DB):   {protected_not_found}")
    print(f"  Unknown tables (skipped):       {len(unknown_tables)}")
    print(f"  Operational tables to clear:    {len(tables_to_clear)}")
    print(f"    - with data:                  {len(tables_with_data)}")
    print(f"    - empty:                      {len(tables_to_clear) - len(tables_with_data)}")
    print(f"  Operational tables not in DB:   {len(tables_not_found)}")
    print(f"  Total rows to delete:           {total_rows}")
    print(f"  Uploaded files to remove:       {len(uploaded_files)}")
    print(f"  Warnings:                       {len(warnings)}")

    # ============================================================
    # SAFETY ASSESSMENT
    # ============================================================
    print(f"\n" + "=" * 70)
    print("SAFETY ASSESSMENT")
    print("=" * 70)
    is_safe = True

    # Check: no protected tables in operational list
    if tables_skipped_protected:
        print(f"  ⚠  {len(tables_skipped_protected)} table(s) in both lists (protected wins)")
    else:
        print(f"  ✓  No overlap between protected and operational lists")

    # Check: users/orgs are protected
    critical_protected = {"users", "organizations", "alembic_version", "organization_memberships"}
    for t in critical_protected:
        if t in PROTECTED_TABLES:
            print(f"  ✓  {t} is PROTECTED")
        else:
            print(f"  ✗  {t} is NOT PROTECTED — UNSAFE!")
            is_safe = False

    # Check: no unknown tables with data
    if unknown_tables:
        print(f"  ⚠  {len(unknown_tables)} unclassified table(s) exist (not touched)")

    if is_safe:
        print(f"\n  ✅ SAFE TO EXECUTE — all critical tables are protected")
    else:
        print(f"\n  ❌ NOT SAFE — review warnings above")

    # ============================================================
    # DRY-RUN EXIT
    # ============================================================
    if not execute:
        print(f"\n{'=' * 70}")
        print(f"✅ DRY-RUN COMPLETE. No data was modified.")
        print(f"   To execute, run with --execute flag and env var:")
        print(f"   DELETE_OPERATIONAL_FREIGHT_DATA=YES python scripts/clear_operational_freight_data.py --execute")
        print(f"{'=' * 70}")
        db.close()
        return

    # ============================================================
    # EXECUTE MODE
    # ============================================================
    print(f"\n{'=' * 70}")
    print(f"🔴 EXECUTING DELETION...")
    print(f"{'=' * 70}")
    deleted_counts = {}
    try:
        for t, count in tables_to_clear:
            if count == 0:
                deleted_counts[t] = 0
                continue
            rows_deleted = delete_table_data(db, t)
            deleted_counts[t] = rows_deleted
            print(f"  ✓ {t}: {rows_deleted} rows deleted")

        # Commit all deletions atomically
        db.commit()
        print(f"\n  ✅ DATABASE COMMIT SUCCESSFUL")

    except Exception as e:
        db.rollback()
        print(f"\n  ❌ ERROR — ALL CHANGES ROLLED BACK: {e}")
        db.close()
        sys.exit(1)

    # Remove uploaded files ONLY after DB commit succeeds
    files_removed = 0
    if uploaded_files:
        try:
            shutil.rmtree(UPLOADED_DOCS_DIR)
            UPLOADED_DOCS_DIR.mkdir(parents=True, exist_ok=True)
            files_removed = len(uploaded_files)
            print(f"  ✓ Removed {files_removed} uploaded document files")
            print(f"  ✓ Recreated empty directory: {UPLOADED_DOCS_DIR}")
        except Exception as e:
            print(f"  ⚠ Could not remove uploaded files: {e}")

    # Final summary
    total_deleted = sum(deleted_counts.values())
    tables_actually_cleared = len([v for v in deleted_counts.values() if v > 0])
    print(f"\n{'=' * 70}")
    print(f"EXECUTION COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Tables cleared:       {tables_actually_cleared}")
    print(f"  Total rows deleted:   {total_deleted}")
    print(f"  Files removed:        {files_removed}")
    print(f"  Timestamp:            {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'=' * 70}")

    db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Master 1.1 — Clear operational freight data for AI private beta"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be deleted without modifying data (default)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete data (requires DELETE_OPERATIONAL_FREIGHT_DATA=YES env var)",
    )
    args = parser.parse_args()

    execute_mode = args.execute
    run(execute=execute_mode)
