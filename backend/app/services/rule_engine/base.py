from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.rule_definition import RuleDefinition


@dataclass
class RuleResult:
    """Result returned by a single rule evaluation."""

    passed: bool
    severity: str
    message: str
    rule_key: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    recommended_action: Optional[str] = None
    metadata: Optional[dict[str, Any]] = field(default=None)


DEFAULT_RULE_DEFINITIONS: list[dict[str, Any]] = [
    # Shipment
    {
        "rule_key": "shipment_missing_required_fields",
        "name": "Shipment missing required fields",
        "description": "Shipment is missing one or more recommended operational fields.",
        "entity_type": "shipment",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "shipment_invalid_type",
        "name": "Shipment invalid type",
        "description": "Shipment type is not import or export.",
        "entity_type": "shipment",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "shipment_archived_write_warning",
        "name": "Write on archived shipment",
        "description": "A write happened on an archived shipment.",
        "entity_type": "shipment",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "shipment_duplicate_code",
        "name": "Duplicate shipment code",
        "description": "Multiple shipments share the same shipment code.",
        "entity_type": "shipment",
        "event_type": None,
        "severity": "critical",
    },
    # Task
    {
        "rule_key": "task_missing_title",
        "name": "Task missing title",
        "description": "Task title is empty.",
        "entity_type": "task",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "task_due_date_in_past_warning",
        "name": "Task due date in the past",
        "description": "Open task has a due date in the past.",
        "entity_type": "task",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "task_cancelled_write_warning",
        "name": "Write on cancelled task",
        "description": "A write happened on a cancelled task.",
        "entity_type": "task",
        "event_type": None,
        "severity": "warning",
    },
    # Charge
    {
        "rule_key": "charge_negative_amount",
        "name": "Charge negative amount",
        "description": "Charge amount is negative.",
        "entity_type": "charge",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "charge_direction_status_mismatch",
        "name": "Charge direction/status mismatch",
        "description": "Charge status is not valid for its direction.",
        "entity_type": "charge",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "charge_cancelled_write_warning",
        "name": "Write on cancelled charge",
        "description": "A write happened on a cancelled charge.",
        "entity_type": "charge",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "charge_missing_currency",
        "name": "Charge missing currency",
        "description": "Charge currency is missing or invalid.",
        "entity_type": "charge",
        "event_type": None,
        "severity": "warning",
    },
    # Document
    {
        "rule_key": "document_missing_type",
        "name": "Document missing type",
        "description": "Document type is missing.",
        "entity_type": "document",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "document_status_invalid",
        "name": "Document status invalid",
        "description": "Document status is not in the supported set.",
        "entity_type": "document",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "document_missing_url_warning",
        "name": "Document missing URL warning",
        "description": "Document is marked received but no URL is set.",
        "entity_type": "document",
        "event_type": None,
        "severity": "info",
    },
    {
        "rule_key": "document_intelligence_low_confidence",
        "name": "Document intelligence low confidence",
        "description": "OCR/classification/extraction confidence is below the review threshold.",
        "entity_type": "document_extraction",
        "event_type": "document_intelligence.run_completed",
        "severity": "warning",
    },
    {
        "rule_key": "document_type_mismatch",
        "name": "Document type mismatch",
        "description": "Detected document type differs from the uploaded checklist type.",
        "entity_type": "document_extraction",
        "event_type": "document_intelligence.mismatch_found",
        "severity": "warning",
    },
    {
        "rule_key": "shipment_code_not_found",
        "name": "Extracted shipment code not found",
        "description": "Document intelligence extracted a shipment code that does not exist.",
        "entity_type": "document_extraction",
        "event_type": "document_intelligence.mismatch_found",
        "severity": "critical",
    },
    {
        "rule_key": "shipment_code_mismatch",
        "name": "Document shipment code mismatch",
        "description": "Extracted shipment code points to another shipment.",
        "entity_type": "document_extraction",
        "event_type": "document_intelligence.mismatch_found",
        "severity": "critical",
    },
    {
        "rule_key": "bl_number_mismatch",
        "name": "Document BL number mismatch",
        "description": "Extracted BL number differs from the shipment BL number.",
        "entity_type": "document_extraction",
        "event_type": "document_intelligence.mismatch_found",
        "severity": "warning",
    },
    {
        "rule_key": "invoice_amount_mismatch",
        "name": "Document invoice amount mismatch",
        "description": "Extracted invoice amount does not match active shipment charges.",
        "entity_type": "document_extraction",
        "event_type": "document_intelligence.mismatch_found",
        "severity": "warning",
    },
    {
        "rule_key": "container_number_not_in_shipment",
        "name": "Document container missing from shipment",
        "description": "Extracted container number is not linked to the shipment.",
        "entity_type": "document_extraction",
        "event_type": "document_intelligence.mismatch_found",
        "severity": "warning",
    },
    {
        "rule_key": "container_number_format_invalid",
        "name": "Document container format invalid",
        "description": "Extracted container number does not pass ISO format validation.",
        "entity_type": "document_extraction",
        "event_type": "document_intelligence.mismatch_found",
        "severity": "warning",
    },
    {
        "rule_key": "origin_port_mismatch",
        "name": "Document origin port mismatch",
        "description": "Extracted origin port differs from shipment origin.",
        "entity_type": "document_extraction",
        "event_type": "document_intelligence.mismatch_found",
        "severity": "warning",
    },
    {
        "rule_key": "destination_port_mismatch",
        "name": "Document destination port mismatch",
        "description": "Extracted destination port differs from shipment destination.",
        "entity_type": "document_extraction",
        "event_type": "document_intelligence.mismatch_found",
        "severity": "warning",
    },
    # BL
    {
        "rule_key": "bl_final_without_draft_warning",
        "name": "Final BL without draft warning",
        "description": "Final BL date set but draft BL date is missing.",
        "entity_type": "bl_management",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "bl_approved_without_draft_warning",
        "name": "BL approved without draft",
        "description": "BL approved without a recorded draft.",
        "entity_type": "bl_management",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "bl_missing_number_warning",
        "name": "BL missing number warning",
        "description": "BL is final or approved but BL number is missing.",
        "entity_type": "bl_management",
        "event_type": None,
        "severity": "info",
    },
    # Gmail
    {
        "rule_key": "gmail_suggestion_missing_shipment",
        "name": "Gmail suggestion missing shipment",
        "description": "Gmail suggestion was applied without a matched shipment.",
        "entity_type": "email_suggestion",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "gmail_suggestion_low_confidence",
        "name": "Gmail suggestion low confidence",
        "description": "Gmail suggestion confidence is below the safe threshold.",
        "entity_type": "email_suggestion",
        "event_type": None,
        "severity": "info",
    },
    # Organization / auth
    {
        "rule_key": "user_missing_organization_warning",
        "name": "User missing organization",
        "description": "User has no organization linkage.",
        "entity_type": "user",
        "event_type": None,
        "severity": "info",
    },
    # Workflow state machine (Phase 10)
    {
        "rule_key": "workflow_invalid_transition",
        "name": "Workflow invalid transition",
        "description": "Requested transition is not defined for the current workflow state.",
        "entity_type": "shipment",
        "event_type": "workflow.transition_requested",
        "severity": "warning",
    },
    {
        "rule_key": "workflow_missing_required_state_data",
        "name": "Workflow missing required state data",
        "description": "Required reason or supporting data is missing for this transition.",
        "entity_type": "shipment",
        "event_type": "workflow.transition_requested",
        "severity": "warning",
    },
    {
        "rule_key": "workflow_sensitive_transition_requires_confirmation",
        "name": "Sensitive transition requires confirmation",
        "description": "Sensitive transition was requested without explicit confirmation.",
        "entity_type": "shipment",
        "event_type": "workflow.transition_requested",
        "severity": "critical",
    },
    {
        "rule_key": "workflow_completed_shipment_transition_warning",
        "name": "Completed shipment transition warning",
        "description": "Transition requested on a completed shipment.",
        "entity_type": "shipment",
        "event_type": "workflow.transition_requested",
        "severity": "warning",
    },
    {
        "rule_key": "workflow_archived_shipment_transition_block",
        "name": "Archived shipment transition block",
        "description": "Transitions are blocked on archived shipments.",
        "entity_type": "shipment",
        "event_type": "workflow.transition_requested",
        "severity": "critical",
    },
    {
        "rule_key": "workflow_import_do_without_free_days_warning",
        "name": "Import DO received without free days",
        "description": "DO_RECEIVED transition observed without demurrage free days configured.",
        "entity_type": "shipment",
        "event_type": "workflow.transition_applied",
        "severity": "warning",
    },
    {
        "rule_key": "workflow_export_bl_approval_without_draft_warning",
        "name": "Export BL approval without draft",
        "description": "Export BL_APPROVED transition without a recorded draft BL.",
        "entity_type": "shipment",
        "event_type": "workflow.transition_applied",
        "severity": "warning",
    },
    {
        "rule_key": "workflow_payment_state_without_charge_warning",
        "name": "Payment state without charge",
        "description": "Payment-related transition without a matching charge record.",
        "entity_type": "shipment",
        "event_type": "workflow.transition_applied",
        "severity": "info",
    },
    # Container lifecycle (Phase 11)
    {
        "rule_key": "container_number_format_warning",
        "name": "Container number format",
        "description": "Container number does not match ISO 6346 ABCD1234567 format.",
        "entity_type": "container",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "container_duplicate_active_warning",
        "name": "Duplicate active container",
        "description": "Container number is active in another shipment.",
        "entity_type": "container",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "container_loaded_before_gate_in_warning",
        "name": "Loaded before gate-in",
        "description": "Loaded-on-vessel date is earlier than gate-in date.",
        "entity_type": "container",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "import_container_delivered_before_do_warning",
        "name": "Delivered before DO",
        "description": "Import container delivery is recorded before DO received.",
        "entity_type": "container",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "empty_return_before_delivery_warning",
        "name": "Empty return before delivery",
        "description": "Empty return is dated before container delivery.",
        "entity_type": "container",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "gate_in_after_cutoff_warning",
        "name": "Gate-in after cutoff",
        "description": "Container gate-in is after the shipment VGM cutoff.",
        "entity_type": "container",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "partial_delivery_supported_info",
        "name": "Partial delivery info",
        "description": "Container delivered but empty return is still pending.",
        "entity_type": "container",
        "event_type": None,
        "severity": "info",
    },
    # Finance / credit-control (Phase 14)
    {
        "rule_key": "finance_invoice_missing_party",
        "name": "Finance invoice missing party",
        "description": "Finance invoice was created without a party.",
        "entity_type": "finance_invoice",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "finance_invoice_negative_amount",
        "name": "Finance invoice negative amount",
        "description": "Finance invoice total is negative.",
        "entity_type": "finance_invoice",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "finance_payment_overallocated",
        "name": "Finance payment over-allocated",
        "description": "Payment allocation exceeds available amount.",
        "entity_type": "finance_payment",
        "event_type": None,
        "severity": "critical",
    },
    {
        "rule_key": "finance_payment_currency_mismatch",
        "name": "Finance payment currency mismatch",
        "description": "Payment currency differs from invoice currency.",
        "entity_type": "finance_payment",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "finance_invoice_overdue",
        "name": "Finance invoice overdue",
        "description": "Finance invoice is past its due date.",
        "entity_type": "finance_invoice",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "finance_receivable_overdue",
        "name": "Finance receivable overdue",
        "description": "A customer has overdue receivables.",
        "entity_type": "finance_risk",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "finance_payable_overdue",
        "name": "Finance payable overdue",
        "description": "A vendor payable is past its due date.",
        "entity_type": "finance_risk",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "finance_credit_limit_warning",
        "name": "Finance credit limit warning",
        "description": "Customer outstanding nearing credit limit.",
        "entity_type": "finance_risk",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "finance_credit_limit_exceeded",
        "name": "Finance credit limit exceeded",
        "description": "Customer outstanding exceeds credit limit.",
        "entity_type": "finance_risk",
        "event_type": None,
        "severity": "critical",
    },
    {
        "rule_key": "finance_missing_fx_rate",
        "name": "Finance missing FX rate",
        "description": "FX rate missing for a multi-currency operation.",
        "entity_type": "finance_risk",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "finance_negative_margin_warning",
        "name": "Finance negative margin",
        "description": "Shipment net P&L is negative.",
        "entity_type": "finance_risk",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "finance_release_blocked_credit_hold",
        "name": "Release blocked by credit hold",
        "description": "Sensitive shipment release blocked by an active credit hold.",
        "entity_type": "finance_risk",
        "event_type": None,
        "severity": "critical",
    },
    {
        "rule_key": "finance_demurrage_invoice_mismatch",
        "name": "Finance demurrage invoice mismatch",
        "description": "Demurrage finalised invoice differs from container exposure.",
        "entity_type": "finance_invoice",
        "event_type": None,
        "severity": "warning",
    },
    {
        "rule_key": "finance_detention_invoice_mismatch",
        "name": "Finance detention invoice mismatch",
        "description": "Detention finalised invoice differs from container exposure.",
        "entity_type": "finance_invoice",
        "event_type": None,
        "severity": "warning",
    },
]


def seed_default_rule_definitions(db: Session) -> None:
    existing = {
        row.rule_key
        for row in db.query(RuleDefinition.rule_key)
        .filter(
            RuleDefinition.rule_key.in_(
                [rule["rule_key"] for rule in DEFAULT_RULE_DEFINITIONS]
            )
        )
        .all()
    }
    created = False
    for rule in DEFAULT_RULE_DEFINITIONS:
        if rule["rule_key"] in existing:
            continue
        db.add(RuleDefinition(**rule))
        created = True
    if created:
        db.commit()


def get_rule_definition(db: Session, rule_key: str) -> Optional[RuleDefinition]:
    return (
        db.query(RuleDefinition)
        .filter(RuleDefinition.rule_key == rule_key)
        .first()
    )


def is_rule_enabled(db: Session, rule_key: str) -> bool:
    rule = get_rule_definition(db, rule_key)
    return bool(rule and rule.is_enabled)


def get_rules_by_key(db: Session) -> dict[str, RuleDefinition]:
    return {rule.rule_key: rule for rule in db.query(RuleDefinition).all()}
