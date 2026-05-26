from decimal import Decimal
from typing import Optional

from app.schemas.ai import AIAskResponse
from app.services.ai_context_service import AIContextBundle


def build_fallback_response(context: AIContextBundle, reason: Optional[str] = None) -> AIAskResponse:
    answer = _answer_for_context(context)
    if reason:
        answer = f"The LLM service is unavailable right now, so I used rule-based fallback data. {answer}"
    return AIAskResponse(
        answer=answer,
        priority=context.priority,
        suggested_actions=context.suggested_actions,
        data_points=context.data_points,
        used_llm=False,
        provider="fallback",
        model=None,
        fallback_used=True,
    )


def _answer_for_context(context: AIContextBundle) -> str:
    if context.result_note:
        return context.result_note
    if context.intent == "general_dashboard_summary":
        return _dashboard_answer(context)
    if context.intent == "notifications_summary":
        return _notifications_summary_answer(context)
    if context.intent == "validation_issues_summary":
        return _validation_issues_answer(context)
    if context.intent == "events_recent":
        return _recent_events_answer(context)
    if context.intent == "workflow_review_summary":
        return _workflow_review_answer(context)
    if context.intent == "shipment_workflow_state":
        return _shipment_workflow_state_answer(context)
    if context.intent == "shipment_workflow_next_steps":
        return _shipment_workflow_next_steps_answer(context)
    if context.intent in {"shipment_status", "shipment_detail"}:
        return _shipment_answer(context)
    if context.intent == "workflow_next_action":
        return _workflow_answer(context)
    if context.intent == "pending_tasks":
        return _task_answer(context, "Pending tasks")
    if context.intent == "overdue_tasks":
        return _task_answer(context, "Overdue tasks")
    if context.intent == "cancelled_tasks":
        return _task_answer(context, "Cancelled tasks")
    if context.intent == "bl_pending":
        return _simple_records_answer(context, "BL approval is pending for")
    if context.intent == "demurrage_risk":
        return _demurrage_answer(context)
    if context.intent == "open_followups":
        return _followup_answer(context)
    if context.intent == "pending_receivables":
        return _money_rows_answer(context, "Pending receivables")
    if context.intent == "pending_payables":
        return _money_rows_answer(context, "Pending payables")
    if context.intent == "shipment_profit":
        return _shipment_profit_answer(context)
    if context.intent == "monthly_profit":
        currency = context.totals.get("currency", "INR")
        return f"This month profit is {currency} {context.totals.get('this_month_profit', 0)}."
    if context.intent == "loss_making_shipments":
        return _money_rows_answer(context, "Loss-making shipments", profit_field="net_profit")
    if context.intent == "charges_summary":
        return _money_rows_answer(context, "Shipment P&L", profit_field="net_profit")
    if context.intent == "archived_shipments":
        return _shipment_list_answer(context, "Archived shipments")
    if context.intent == "inactive_parties":
        return _inactive_parties_answer(context)
    return "The system does not have enough data to answer this."


def _dashboard_answer(context: AIContextBundle) -> str:
    totals = context.totals
    return (
        f"Dashboard summary: {totals.get('live_shipments', 0)} live shipments, "
        f"{totals.get('pending_tasks', 0)} pending tasks, {totals.get('alerts_today', 0)} alerts today, "
        f"and this month profit {totals.get('currency', 'INR')} {totals.get('this_month_profit', 0)}."
    )


def _notifications_summary_answer(context: AIContextBundle) -> str:
    totals = context.totals
    return (
        f"Today needs attention: {totals.get('unread_notifications', 0)} unread notifications, "
        f"{totals.get('overdue_tasks', 0)} overdue tasks, "
        f"{totals.get('demurrage_risks', 0)} demurrage risk(s), "
        f"{totals.get('pending_bl_approvals', 0)} pending BL approval(s), "
        f"pending receivables {totals.get('currency', 'INR')} {totals.get('pending_receivables_total', 0)}, "
        f"and pending payables {totals.get('currency', 'INR')} {totals.get('pending_payables_total', 0)}."
    )


def _shipment_answer(context: AIContextBundle) -> str:
    if not context.records:
        return "No shipments have been created yet."
    if len(context.records) == 1:
        row = context.records[0]
        archived = " It is archived." if row.get("is_archived") else ""
        return f"{row.get('shipment_code')} is currently {row.get('status')}.{archived}"
    lines = [f"{row.get('shipment_code')}: {row.get('status')}" for row in context.records[:10]]
    return "Shipment status: " + "; ".join(lines)


def _shipment_list_answer(context: AIContextBundle, label: str) -> str:
    if not context.records:
        return f"No {label.lower()} found."
    lines = [f"{row.get('shipment_code')}: {row.get('status')}" for row in context.records[:10]]
    return f"{label}: " + "; ".join(lines)


def _workflow_answer(context: AIContextBundle) -> str:
    if context.suggested_actions:
        return f"Next action for {context.shipment_code}: {context.suggested_actions[0]}."
    return context.result_note or f"No mapped next action was found for {context.shipment_code}."


def _task_answer(context: AIContextBundle, label: str) -> str:
    if not context.records:
        return f"There are no {label.lower()}."
    lines = [
        f"{row.get('title')} for {row.get('shipment_code') or 'shipment'}"
        for row in context.records[:10]
    ]
    return f"{label}: " + "; ".join(lines)


def _simple_records_answer(context: AIContextBundle, label: str) -> str:
    if not context.records:
        return f"{label}: none."
    codes = sorted({str(row.get("shipment_code")) for row in context.records if row.get("shipment_code")})
    return f"{label}: " + ", ".join(codes[:10])


def _demurrage_answer(context: AIContextBundle) -> str:
    if not context.records:
        return "No shipments currently have demurrage risk."
    lines = [
        f"{row.get('shipment_code')}: {row.get('status')} ({row.get('days_remaining')} day(s) remaining)"
        for row in context.records[:10]
    ]
    return "Demurrage risk: " + "; ".join(lines)


def _followup_answer(context: AIContextBundle) -> str:
    if not context.records:
        return "There are no open follow-ups."
    lines = [
        f"{row.get('shipment_code')}: {row.get('summary')}"
        for row in context.records[:10]
    ]
    return "Open follow-ups: " + "; ".join(lines)


def _money_rows_answer(context: AIContextBundle, label: str, profit_field: Optional[str] = None) -> str:
    if not context.records:
        return f"There are no {label.lower()}."
    if profit_field:
        lines = [
            f"{row.get('shipment_code')}: {row.get('currency', 'INR')} {row.get(profit_field, 0)}"
            for row in context.records[:10]
        ]
        return f"{label}: " + "; ".join(lines)
    total = context.totals.get("amount", Decimal("0"))
    currency = context.totals.get("currency", "INR")
    lines = [
        f"{row.get('shipment_code')}: {row.get('currency', currency)} {row.get('amount', 0)}"
        for row in context.records[:10]
    ]
    return f"{label} total: {currency} {total}. " + "; ".join(lines)


def _shipment_profit_answer(context: AIContextBundle) -> str:
    if not context.records:
        return context.result_note or "No shipment P&L was found."
    row = context.records[0]
    currency = row.get("currency", "INR")
    return (
        f"{row.get('shipment_code')} P&L: receivable {currency} {row.get('total_receivable', 0)}, "
        f"payable {currency} {row.get('total_payable', 0)}, "
        f"net profit {currency} {row.get('net_profit', 0)}."
    )


def _inactive_parties_answer(context: AIContextBundle) -> str:
    if not context.records:
        return "No inactive parties found."
    lines = [f"{row.get('name')} ({row.get('type')})" for row in context.records[:10]]
    return "Inactive parties: " + "; ".join(lines)


def _validation_issues_answer(context: AIContextBundle) -> str:
    totals = context.totals
    if not context.records:
        return "There are no open validation issues."
    summary = (
        f"Open validation issues: {totals.get('open_count', 0)} "
        f"(critical {totals.get('critical', 0)}, warning {totals.get('warning', 0)}, info {totals.get('info', 0)})."
    )
    items = "; ".join(
        f"{row.get('rule_key')} on {row.get('entity_type')} #{row.get('entity_id')}"
        for row in context.records[:5]
    )
    return f"{summary} {items}"


def _recent_events_answer(context: AIContextBundle) -> str:
    if not context.records:
        return "No recent operational events were recorded."
    lines = [
        f"{row.get('event_type')} on {row.get('entity_label') or row.get('entity_type')} ({row.get('validation_status')})"
        for row in context.records[:5]
    ]
    return "Recent operational events: " + "; ".join(lines)


def _workflow_review_answer(context: AIContextBundle) -> str:
    totals = context.totals
    if not context.records and not totals.get("blocked_transitions"):
        return "No shipments need manual workflow review and no recent blocked transitions."
    flagged = [row.get("shipment_code") for row in context.records[:5]]
    parts = []
    if flagged:
        parts.append(f"Manual review needed: {', '.join(filter(None, flagged))}.")
    if totals.get("blocked_transitions"):
        parts.append(f"Recent blocked transitions: {totals['blocked_transitions']}.")
    return " ".join(parts)


def _shipment_workflow_state_answer(context: AIContextBundle) -> str:
    if not context.records:
        return context.result_note or "Shipment not found."
    row = context.records[0]
    review = " (manual review required)" if row.get("manual_review_required") else ""
    return (
        f"{row.get('shipment_code')} is in workflow state "
        f"{row.get('workflow_state') or 'unset'}{review}."
    )


def _shipment_workflow_next_steps_answer(context: AIContextBundle) -> str:
    if not context.suggested_actions:
        return f"No allowed next workflow steps were found for {context.shipment_code or 'this shipment'}."
    return (
        f"Allowed next workflow steps for {context.shipment_code}: "
        + "; ".join(context.suggested_actions)
    )
