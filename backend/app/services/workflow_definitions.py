"""Canonical Phase 10 workflow state and transition definitions."""
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.workflow_state_machine import (
    WorkflowStateDefinition,
    WorkflowTransitionDefinition,
)


SENSITIVE_STATES = {
    "BL_APPROVED",
    "FINAL_BL_RECEIVED",
    "PAYMENT_RECEIVED",
    "FREIGHT_PAID",
    "IMPORT_COMPLETED",
    "EXPORT_COMPLETED",
}

# Each entry: (state_key, state_label, is_initial, is_terminal, description)
EXPORT_STATES: list[tuple[str, str, bool, bool, str]] = [
    ("EXPORT_INQUIRY_RECEIVED", "Inquiry Received", True, False, "Initial export inquiry received."),
    ("EXPORT_QUOTED", "Quoted", False, False, "Quotation shared with customer."),
    ("EXPORT_BOOKING_CONFIRMED", "Booking Confirmed", False, False, "Booking confirmed with line."),
    ("EXPORT_SHIPMENT_CREATED", "Shipment Created", False, False, "Operational shipment record created."),
    ("CONTAINER_PLANNED", "Container Planned", False, False, "Container plan published."),
    ("TRANSPORTER_ASSIGNED", "Transporter Assigned", False, False, "Transporter assigned for empty pickup."),
    ("EMPTY_PICKUP_SCHEDULED", "Empty Pickup Scheduled", False, False, "Empty pickup scheduled."),
    ("EMPTY_CONTAINER_PICKED", "Empty Picked", False, False, "Empty container picked from yard."),
    ("FACTORY_STUFFING_SCHEDULED", "Factory Stuffing Scheduled", False, False, "Factory stuffing scheduled."),
    ("CARGO_STUFFED", "Cargo Stuffed", False, False, "Cargo stuffed at factory."),
    ("SEAL_APPLIED", "Seal Applied", False, False, "Container seal applied."),
    ("SI_PENDING", "SI Pending", False, False, "SI submission pending."),
    ("SI_SUBMITTED", "SI Submitted", False, False, "SI submitted to line."),
    ("VGM_PENDING", "VGM Pending", False, False, "VGM filing pending."),
    ("VGM_FILED", "VGM Filed", False, False, "VGM filed with line."),
    ("CUSTOMS_SB_PENDING", "Customs SB Pending", False, False, "Shipping bill pending."),
    ("SHIPPING_BILL_FILED", "Shipping Bill Filed", False, False, "Shipping bill filed."),
    ("CUSTOMS_QUERY_IF_ANY", "Customs Query (if any)", False, False, "Optional customs query branch."),
    ("EXAMINATION_IF_ANY", "Examination (if any)", False, False, "Optional examination branch."),
    ("LEO_RECEIVED", "LEO Received", False, False, "Let Export Order received."),
    ("GATE_IN_PENDING", "Gate-in Pending", False, False, "Container awaiting gate-in."),
    ("CONTAINER_GATE_IN", "Container Gate-in", False, False, "Container gated in at port."),
    ("LOADED_ON_VESSEL", "Loaded on Vessel", False, False, "Container loaded on vessel."),
    ("BL_DRAFT_PENDING", "BL Draft Pending", False, False, "BL draft pending from line."),
    ("BL_DRAFT_RECEIVED", "BL Draft Received", False, False, "BL draft received from line."),
    ("BL_UNDER_REVIEW", "BL Under Review", False, False, "BL draft under internal review."),
    ("BL_CORRECTION_IF_ANY", "BL Correction (if any)", False, False, "Optional BL correction branch."),
    ("BL_APPROVED", "BL Approved", False, False, "BL approved internally."),
    ("FINAL_BL_RECEIVED", "Final BL Received", False, False, "Final BL received from line."),
    ("DOCUMENT_SET_PENDING", "Document Set Pending", False, False, "Document set assembly pending."),
    ("DOCUMENT_SET_VERIFIED", "Document Set Verified", False, False, "Document set verified."),
    ("DOCUMENTS_DISPATCHED", "Documents Dispatched", False, False, "Documents dispatched."),
    ("PRE_ALERT_SENT", "Pre-alert Sent", False, False, "Pre-alert sent to overseas agent."),
    ("FREIGHT_INVOICED", "Freight Invoiced", False, False, "Freight invoiced."),
    ("PAYMENT_PENDING", "Payment Pending", False, False, "Payment pending from customer."),
    ("PAYMENT_RECEIVED", "Payment Received", False, False, "Payment received."),
    ("EXPORT_COMPLETED", "Export Completed", False, True, "Export shipment complete."),
]

IMPORT_STATES: list[tuple[str, str, bool, bool, str]] = [
    ("IMPORT_PRE_ALERT_PENDING", "Pre-alert Pending", True, False, "Pre-alert from origin pending."),
    ("PRE_ALERT_RECEIVED", "Pre-alert Received", False, False, "Pre-alert received from origin."),
    ("IMPORT_SHIPMENT_CREATED", "Shipment Created", False, False, "Operational import record created."),
    ("ETA_TRACKING_ACTIVE", "ETA Tracking Active", False, False, "ETA tracking active."),
    ("IGM_PENDING", "IGM Pending", False, False, "IGM filing pending."),
    ("IGM_FILED", "IGM Filed", False, False, "IGM filed."),
    ("FREIGHT_INVOICE_PENDING", "Freight Invoice Pending", False, False, "Freight invoice pending."),
    ("FREIGHT_INVOICE_RECEIVED", "Freight Invoice Received", False, False, "Freight invoice received."),
    ("INCOTERM_CHARGE_VALIDATION", "Incoterm Charge Validation", False, False, "Incoterm-based charge validation."),
    ("BL_RELEASE_STATUS_PENDING", "BL Release Status Pending", False, False, "BL release status pending."),
    ("SURRENDER_TELEX_OBL_CONFIRMED", "Surrender/Telex/OBL Confirmed", False, False, "BL release type confirmed."),
    ("PAYMENT_TO_LINE_PENDING", "Payment to Line Pending", False, False, "Payment to line pending."),
    ("FREIGHT_PAID", "Freight Paid", False, False, "Freight paid to line."),
    ("DO_PENDING", "DO Pending", False, False, "DO from line pending."),
    ("DO_RECEIVED", "DO Received", False, False, "DO received from line."),
    ("FREE_DAYS_COUNTER_STARTED", "Free Days Counter Started", False, False, "Free days counter started."),
    ("DO_FORWARDED_TO_CHA", "DO Forwarded to CHA", False, False, "DO handed to CHA."),
    ("BOE_PENDING", "BOE Pending", False, False, "Bill of Entry pending."),
    ("BOE_FILED", "BOE Filed", False, False, "Bill of Entry filed."),
    ("DUTY_ASSESSMENT_PENDING", "Duty Assessment Pending", False, False, "Duty assessment pending."),
    ("DUTY_PAID_IF_REQUIRED", "Duty Paid (if required)", False, False, "Duty paid where applicable."),
    ("CUSTOMS_QUERY_IF_ANY", "Customs Query (if any)", False, False, "Optional customs query branch."),
    ("EXAMINATION_IF_ANY", "Examination (if any)", False, False, "Optional examination branch."),
    ("OOC_PENDING", "OOC Pending", False, False, "Out-of-charge pending."),
    ("OOC_RECEIVED", "OOC Received", False, False, "Out-of-charge received."),
    ("TRANSPORT_DELIVERY_PLANNED", "Transport Delivery Planned", False, False, "Delivery planned."),
    ("CONTAINER_DELIVERED", "Container Delivered", False, False, "Container delivered to consignee."),
    ("EMPTY_RETURN_PENDING", "Empty Return Pending", False, False, "Empty container return pending."),
    ("EMPTY_RETURNED", "Empty Returned", False, False, "Empty container returned."),
    ("DEMURRAGE_DETENTION_FINALIZED", "Demurrage/Detention Finalized", False, False, "Demurrage/detention finalized."),
    ("IMPORT_INVOICE_RAISED", "Import Invoice Raised", False, False, "Import invoice raised to customer."),
    ("PAYMENT_RECEIVED", "Payment Received", False, False, "Payment received from customer."),
    ("IMPORT_COMPLETED", "Import Completed", False, True, "Import shipment complete."),
]


BRANCH_STATES = {
    "CUSTOMS_QUERY_IF_ANY",
    "EXAMINATION_IF_ANY",
    "BL_CORRECTION_IF_ANY",
}


def _linear_chain_skipping_branches(states: list[tuple[str, str, bool, bool, str]]) -> list[str]:
    return [state[0] for state in states if state[0] not in BRANCH_STATES]


# Linear and selected non-linear transitions. Phase 10 keeps the chain
# pragmatic; Phase 11 will refine the branching states.
EXPORT_TRANSITIONS: list[tuple[str, str, str]] = []
_export_chain = _linear_chain_skipping_branches(EXPORT_STATES)
for index in range(len(_export_chain) - 1):
    from_state = _export_chain[index]
    to_state = _export_chain[index + 1]
    EXPORT_TRANSITIONS.append((from_state, to_state, f"Move to {to_state.lower()}."))

# Selected branches outside the linear chain.
EXPORT_TRANSITIONS.extend(
    [
        ("BL_DRAFT_RECEIVED", "BL_CORRECTION_IF_ANY", "Mark BL draft for correction."),
        ("BL_CORRECTION_IF_ANY", "BL_DRAFT_RECEIVED", "Receive corrected BL draft."),
        ("BL_UNDER_REVIEW", "BL_CORRECTION_IF_ANY", "Send BL back for correction."),
        ("SHIPPING_BILL_FILED", "CUSTOMS_QUERY_IF_ANY", "Customs query raised."),
        ("CUSTOMS_QUERY_IF_ANY", "EXAMINATION_IF_ANY", "Customs query escalated to examination."),
        ("EXAMINATION_IF_ANY", "LEO_RECEIVED", "Examination cleared, LEO received."),
        ("CUSTOMS_QUERY_IF_ANY", "LEO_RECEIVED", "Customs query resolved, LEO received."),
    ]
)


IMPORT_TRANSITIONS: list[tuple[str, str, str]] = []
_import_chain = _linear_chain_skipping_branches(IMPORT_STATES)
for index in range(len(_import_chain) - 1):
    from_state = _import_chain[index]
    to_state = _import_chain[index + 1]
    IMPORT_TRANSITIONS.append((from_state, to_state, f"Move to {to_state.lower()}."))

IMPORT_TRANSITIONS.extend(
    [
        ("DO_RECEIVED", "DO_FORWARDED_TO_CHA", "DO handed to CHA."),
        ("BOE_FILED", "CUSTOMS_QUERY_IF_ANY", "Customs query raised."),
        ("CUSTOMS_QUERY_IF_ANY", "EXAMINATION_IF_ANY", "Examination triggered."),
        ("EXAMINATION_IF_ANY", "OOC_PENDING", "Examination complete, awaiting OOC."),
        ("CUSTOMS_QUERY_IF_ANY", "OOC_PENDING", "Query resolved, awaiting OOC."),
    ]
)


def seed_workflow_definitions(db: Session) -> None:
    """Seed canonical Phase 10 workflow state/transition definitions."""
    _seed_states(db, "export", EXPORT_STATES)
    _seed_states(db, "import", IMPORT_STATES)
    _seed_transitions(db, "export", EXPORT_TRANSITIONS)
    _seed_transitions(db, "import", IMPORT_TRANSITIONS)
    db.commit()


def _seed_states(
    db: Session,
    flow_type: str,
    rows: Iterable[tuple[str, str, bool, bool, str]],
) -> None:
    existing = {
        row.state_key
        for row in db.query(WorkflowStateDefinition.state_key).filter(
            WorkflowStateDefinition.flow_type == flow_type
        )
    }
    for order, (state_key, label, is_initial, is_terminal, description) in enumerate(rows):
        if state_key in existing:
            continue
        db.add(
            WorkflowStateDefinition(
                flow_type=flow_type,
                state_key=state_key,
                state_label=label,
                state_order=order,
                description=description,
                is_initial=is_initial,
                is_terminal=is_terminal,
                is_active=True,
            )
        )


def _seed_transitions(
    db: Session,
    flow_type: str,
    rows: Iterable[tuple[str, str, str]],
) -> None:
    existing = {
        row.transition_key
        for row in db.query(WorkflowTransitionDefinition.transition_key).filter(
            WorkflowTransitionDefinition.flow_type == flow_type
        )
    }
    seen: set[str] = set()
    for from_state, to_state, label in rows:
        transition_key = f"{flow_type}.{from_state.lower()}_to_{to_state.lower()}"
        if transition_key in existing or transition_key in seen:
            continue
        seen.add(transition_key)
        is_sensitive = to_state in SENSITIVE_STATES
        db.add(
            WorkflowTransitionDefinition(
                flow_type=flow_type,
                transition_key=transition_key,
                from_state=from_state,
                to_state=to_state,
                label=label,
                description=None,
                requires_reason=False,
                requires_confirmation=is_sensitive,
                requires_manual_review=False,
                is_sensitive=is_sensitive,
                is_active=True,
            )
        )
