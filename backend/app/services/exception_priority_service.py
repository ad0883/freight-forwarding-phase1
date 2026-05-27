"""Phase 15 exception priority calculation service."""
from datetime import datetime, timedelta
from typing import Any, Optional


SEVERITY_SCORES = {
    "critical": 90,
    "high": 70,
    "medium": 50,
    "low": 30,
    "info": 10,
}

CATEGORY_WEIGHTS = {
    "finance": 1.3,
    "workflow": 1.2,
    "document": 1.1,
    "container": 1.2,
    "security": 1.4,
    "gmail": 0.8,
    "notification": 0.7,
    "sla": 1.0,
    "validation": 1.0,
    "ai": 0.9,
    "party": 1.0,
    "shipment": 1.0,
    "system": 0.9,
    "other": 0.8,
}

SLA_RESPONSE_MINUTES = {
    "p0": 30,
    "p1": 60,
    "p2": 240,
    "p3": 480,
    "p4": 1440,
}


def calculate_exception_priority(
    category: str,
    severity: str,
    entity_context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Calculate risk score, priority, due_at, and recommended action.

    Args:
        category: Exception category (workflow, finance, etc.)
        severity: Exception severity (critical, high, medium, low, info)
        entity_context: Optional dict with extra scoring signals:
            - days_overdue: int
            - credit_hold_active: bool
            - workflow_blocked: bool
            - document_required_for_release: bool
            - shipment_value: float
            - repeated_occurrence: bool

    Returns:
        dict with risk_score, priority, due_at, recommended_action
    """
    context = entity_context or {}

    # Base score from severity
    base_score = SEVERITY_SCORES.get(severity, 50)

    # Category weight
    weight = CATEGORY_WEIGHTS.get(category, 1.0)
    score = base_score * weight

    # Context adjustments
    if context.get("days_overdue", 0) > 0:
        score += min(context["days_overdue"] * 3, 20)
    if context.get("credit_hold_active"):
        score += 15
    if context.get("workflow_blocked"):
        score += 10
    if context.get("document_required_for_release"):
        score += 10
    if context.get("repeated_occurrence"):
        score += 5
    if context.get("shipment_value", 0) > 100000:
        score += 10

    # Clamp
    risk_score = max(0, min(100, int(score)))

    # Determine priority from score
    if risk_score >= 85:
        priority = "p0"
    elif risk_score >= 70:
        priority = "p1"
    elif risk_score >= 50:
        priority = "p2"
    elif risk_score >= 30:
        priority = "p3"
    else:
        priority = "p4"

    # Calculate due_at
    response_minutes = SLA_RESPONSE_MINUTES.get(priority, 480)
    due_at = datetime.utcnow() + timedelta(minutes=response_minutes)

    # Recommended action
    recommended_action = _get_recommended_action(category, severity, context)

    return {
        "risk_score": risk_score,
        "priority": priority,
        "due_at": due_at,
        "recommended_action": recommended_action,
    }


def _get_recommended_action(
    category: str,
    severity: str,
    context: dict[str, Any],
) -> str:
    """Generate a recommended action string."""
    actions = {
        "finance": "Review finance hold and contact accounts team for resolution.",
        "workflow": "Check workflow state and resolve blocking condition.",
        "document": "Review document mismatch and verify against source documents.",
        "container": "Check container status and coordinate with shipping line.",
        "gmail": "Review Gmail suggestion and verify extracted data.",
        "validation": "Review validation issue and correct data or dismiss if false positive.",
        "sla": "Address overdue item immediately to meet SLA.",
        "security": "Investigate security concern and escalate if confirmed.",
        "ai": "Review AI suggestion confidence and verify manually.",
    }

    base_action = actions.get(category, "Review exception and take appropriate action.")

    if severity == "critical":
        base_action = f"URGENT: {base_action}"
    if context.get("credit_hold_active"):
        base_action += " Finance hold is blocking operations."
    if context.get("workflow_blocked"):
        base_action += " Workflow is blocked pending resolution."

    return base_action
