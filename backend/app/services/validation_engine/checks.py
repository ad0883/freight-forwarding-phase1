"""Deterministic Phase 9 validation checks.

Each check accepts a context dictionary derived from an OperationalEvent and
returns a list of RuleResult objects. Checks must remain read-only and free of
side effects.
"""
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.services.rule_engine import RuleResult


SHIPMENT_TYPE_VALUES = {"import", "export"}
DOCUMENT_VALID_STATUSES = {"pending", "received", "sent", "approved", "rejected", "cancelled"}
CHARGE_VALID_STATUS_BY_DIRECTION = {
    "payable": {"pending", "paid", "cancelled"},
    "receivable": {"pending", "received", "cancelled"},
}
LOW_CONFIDENCE_THRESHOLD = 0.5


def _result(
    rule_key: str,
    severity: str,
    message: str,
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    recommended_action: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    passed: bool = False,
) -> RuleResult:
    return RuleResult(
        passed=passed,
        severity=severity,
        message=message,
        rule_key=rule_key,
        entity_type=entity_type,
        entity_id=entity_id,
        recommended_action=recommended_action,
        metadata=metadata,
    )


def run_shipment_checks(
    db: Session,
    event,
    new_state: dict[str, Any],
    enabled_rules: dict,
) -> list[RuleResult]:
    results: list[RuleResult] = []
    state = new_state or {}
    entity_id = event.entity_id

    if "shipment_invalid_type" in enabled_rules:
        type_value = state.get("type")
        if type_value and str(type_value).lower() not in SHIPMENT_TYPE_VALUES:
            results.append(
                _result(
                    "shipment_invalid_type",
                    "warning",
                    f"Shipment type '{type_value}' is not import or export.",
                    entity_type="shipment",
                    entity_id=entity_id,
                    recommended_action="Set shipment type to import or export.",
                    metadata={"type": str(type_value)},
                )
            )

    if "shipment_missing_required_fields" in enabled_rules:
        missing = [
            field
            for field in ("shipment_code", "type")
            if not state.get(field)
        ]
        if missing:
            results.append(
                _result(
                    "shipment_missing_required_fields",
                    "warning",
                    f"Shipment missing required fields: {', '.join(missing)}.",
                    entity_type="shipment",
                    entity_id=entity_id,
                    recommended_action="Fill missing required shipment fields.",
                    metadata={"missing_fields": missing},
                )
            )

    if "shipment_archived_write_warning" in enabled_rules and state.get("is_archived"):
        if event.event_type and event.event_type not in {"shipment.restored"}:
            results.append(
                _result(
                    "shipment_archived_write_warning",
                    "warning",
                    "Write happened on an archived shipment.",
                    entity_type="shipment",
                    entity_id=entity_id,
                    recommended_action="Restore the shipment before editing.",
                )
            )

    if "shipment_duplicate_code" in enabled_rules:
        code = state.get("shipment_code")
        if code:
            from app.models.shipment import Shipment

            duplicates = (
                db.query(func.count(Shipment.id))
                .filter(Shipment.shipment_code == code)
                .scalar()
            )
            if duplicates and duplicates > 1:
                results.append(
                    _result(
                        "shipment_duplicate_code",
                        "critical",
                        f"Shipment code {code} appears {duplicates} times.",
                        entity_type="shipment",
                        entity_id=entity_id,
                        recommended_action="Investigate the duplicated shipment code.",
                        metadata={"shipment_code": str(code), "count": int(duplicates)},
                    )
                )

    return results


def run_task_checks(event, new_state: dict[str, Any], enabled_rules: dict) -> list[RuleResult]:
    results: list[RuleResult] = []
    state = new_state or {}
    entity_id = event.entity_id

    if "task_missing_title" in enabled_rules:
        title = state.get("title")
        if title is not None and not str(title).strip():
            results.append(
                _result(
                    "task_missing_title",
                    "warning",
                    "Task title is empty.",
                    entity_type="task",
                    entity_id=entity_id,
                    recommended_action="Add a descriptive task title.",
                )
            )

    if "task_due_date_in_past_warning" in enabled_rules:
        due_date = state.get("due_date")
        status_value = state.get("status")
        if (
            due_date
            and status_value not in {None, "done", "cancelled"}
            and _to_date(due_date)
            and _to_date(due_date) < date.today()
        ):
            results.append(
                _result(
                    "task_due_date_in_past_warning",
                    "warning",
                    "Open task has a due date in the past.",
                    entity_type="task",
                    entity_id=entity_id,
                    recommended_action="Reschedule or close the overdue task.",
                    metadata={"due_date": _to_date(due_date).isoformat()},
                )
            )

    if "task_cancelled_write_warning" in enabled_rules and state.get("status") == "cancelled":
        if event.event_type and event.event_type not in {"task.cancelled", "task.restored"}:
            results.append(
                _result(
                    "task_cancelled_write_warning",
                    "warning",
                    "Write happened on a cancelled task.",
                    entity_type="task",
                    entity_id=entity_id,
                    recommended_action="Restore the task before editing.",
                )
            )
    return results


def run_charge_checks(event, new_state: dict[str, Any], enabled_rules: dict) -> list[RuleResult]:
    results: list[RuleResult] = []
    state = new_state or {}
    entity_id = event.entity_id

    if "charge_negative_amount" in enabled_rules:
        amount = state.get("amount")
        try:
            decimal_amount = Decimal(str(amount)) if amount is not None else None
        except Exception:
            decimal_amount = None
        if decimal_amount is not None and decimal_amount < 0:
            results.append(
                _result(
                    "charge_negative_amount",
                    "warning",
                    "Charge amount is negative.",
                    entity_type="charge",
                    entity_id=entity_id,
                    recommended_action="Use cancel rather than negative amounts.",
                    metadata={"amount": str(decimal_amount)},
                )
            )

    if "charge_direction_status_mismatch" in enabled_rules:
        direction = state.get("direction")
        status_value = state.get("status")
        valid = CHARGE_VALID_STATUS_BY_DIRECTION.get(direction or "", set())
        if direction and status_value and status_value not in valid:
            results.append(
                _result(
                    "charge_direction_status_mismatch",
                    "warning",
                    f"Status '{status_value}' is not valid for {direction} charges.",
                    entity_type="charge",
                    entity_id=entity_id,
                    recommended_action="Use a status that matches the charge direction.",
                    metadata={"direction": direction, "status": status_value},
                )
            )

    if "charge_cancelled_write_warning" in enabled_rules and state.get("status") == "cancelled":
        if event.event_type not in {"charge.cancelled", "charge.created"}:
            results.append(
                _result(
                    "charge_cancelled_write_warning",
                    "warning",
                    "Write happened on a cancelled charge.",
                    entity_type="charge",
                    entity_id=entity_id,
                    recommended_action="Avoid editing cancelled charges.",
                )
            )

    if "charge_missing_currency" in enabled_rules:
        currency = state.get("currency")
        if currency is not None and not str(currency).strip():
            results.append(
                _result(
                    "charge_missing_currency",
                    "warning",
                    "Charge currency is missing.",
                    entity_type="charge",
                    entity_id=entity_id,
                    recommended_action="Set a valid 3-letter currency code.",
                )
            )
    return results


def run_document_checks(event, new_state: dict[str, Any], enabled_rules: dict) -> list[RuleResult]:
    results: list[RuleResult] = []
    state = new_state or {}
    entity_id = event.entity_id

    if "document_missing_type" in enabled_rules:
        if "doc_type" in state and not state.get("doc_type"):
            results.append(
                _result(
                    "document_missing_type",
                    "warning",
                    "Document type is missing.",
                    entity_type="document",
                    entity_id=entity_id,
                    recommended_action="Set a document type.",
                )
            )

    if "document_status_invalid" in enabled_rules:
        status_value = state.get("status")
        if status_value and status_value not in DOCUMENT_VALID_STATUSES:
            results.append(
                _result(
                    "document_status_invalid",
                    "warning",
                    f"Document status '{status_value}' is not valid.",
                    entity_type="document",
                    entity_id=entity_id,
                    recommended_action="Pick a supported document status.",
                    metadata={"status": status_value},
                )
            )

    if "document_missing_url_warning" in enabled_rules:
        if state.get("status") in {"received", "approved"} and not state.get("file_url"):
            results.append(
                _result(
                    "document_missing_url_warning",
                    "info",
                    "Document is marked received but file URL is missing.",
                    entity_type="document",
                    entity_id=entity_id,
                    recommended_action="Add a Drive link or remove the received status.",
                )
            )
    return results


def run_bl_checks(event, new_state: dict[str, Any], enabled_rules: dict) -> list[RuleResult]:
    results: list[RuleResult] = []
    state = new_state or {}
    entity_id = event.entity_id
    draft = state.get("draft_received") or state.get("draft_date")
    final = state.get("final_bl_date") or state.get("final_received")
    approval = state.get("approval_date") or state.get("approved_at")
    bl_number = state.get("bl_number")

    if "bl_final_without_draft_warning" in enabled_rules and final and not draft:
        results.append(
            _result(
                "bl_final_without_draft_warning",
                "warning",
                "Final BL date set without a recorded draft date.",
                entity_type="bl_management",
                entity_id=entity_id,
                recommended_action="Record the draft BL date for full audit trail.",
            )
        )

    if "bl_approved_without_draft_warning" in enabled_rules and approval and not draft:
        results.append(
            _result(
                "bl_approved_without_draft_warning",
                "warning",
                "BL approved without a recorded draft.",
                entity_type="bl_management",
                entity_id=entity_id,
                recommended_action="Record draft BL before approval.",
            )
        )

    if "bl_missing_number_warning" in enabled_rules and (final or approval) and not bl_number:
        results.append(
            _result(
                "bl_missing_number_warning",
                "info",
                "BL is final/approved but BL number is missing.",
                entity_type="bl_management",
                entity_id=entity_id,
                recommended_action="Add the BL number.",
            )
        )

    return results


def run_email_suggestion_checks(
    event,
    new_state: dict[str, Any],
    metadata: dict[str, Any],
    enabled_rules: dict,
) -> list[RuleResult]:
    results: list[RuleResult] = []
    state = new_state or {}
    meta = metadata or {}
    entity_id = event.entity_id

    if (
        "gmail_suggestion_missing_shipment" in enabled_rules
        and state.get("shipment_id") in (None, 0)
    ):
        results.append(
            _result(
                "gmail_suggestion_missing_shipment",
                "warning",
                "Gmail suggestion has no matched shipment.",
                entity_type="email_suggestion",
                entity_id=entity_id,
                recommended_action="Match the suggestion to a shipment before applying.",
            )
        )

    if "gmail_suggestion_low_confidence" in enabled_rules:
        confidence = state.get("confidence") if "confidence" in state else meta.get("confidence")
        if confidence is not None:
            try:
                value = float(confidence)
            except (TypeError, ValueError):
                value = None
            if value is not None and value < LOW_CONFIDENCE_THRESHOLD:
                results.append(
                    _result(
                        "gmail_suggestion_low_confidence",
                        "info",
                        f"Gmail suggestion confidence is low ({value:.2f}).",
                        entity_type="email_suggestion",
                        entity_id=entity_id,
                        recommended_action="Verify extracted fields manually before applying.",
                        metadata={"confidence": value},
                    )
                )

    return results


def run_user_checks(event, new_state: dict[str, Any], enabled_rules: dict) -> list[RuleResult]:
    results: list[RuleResult] = []
    state = new_state or {}
    if "user_missing_organization_warning" in enabled_rules and (
        state.get("organization_id") in (None, 0)
    ):
        results.append(
            _result(
                "user_missing_organization_warning",
                "info",
                "User is not linked to an organization.",
                entity_type="user",
                entity_id=event.entity_id,
                recommended_action="Assign the user to an organization.",
            )
        )
    return results


def _to_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None
