import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.bl_management import BLManagement
from app.models.demurrage import Demurrage
from app.models.document import Document
from app.models.followup import FollowUpLog
from app.models.party import Party
from app.models.shipment import Shipment
from app.models.task import Task
from app.schemas.ai import AIAskRequest, AIDataPoint, AIPriority
from app.services.dashboard_service import get_dashboard_summary
from app.services.demurrage_service import calculate_demurrage
from app.services.finance_service import (
    calculate_dashboard_financials,
    calculate_shipment_pnl,
    list_pending_payables,
    list_pending_receivables,
    list_shipment_pnl,
)
from app.services.workflow_service import next_task_for


SHIPMENT_CODE_RE = re.compile(r"\bFF-[A-Z]+-\d{4}-\d+\b", re.IGNORECASE)
DEFAULT_TOP_LIMIT = 10


@dataclass
class AIContextBundle:
    intent: str
    question: str
    shipment_code: Optional[str] = None
    summary: str = ""
    records: list[dict[str, Any]] = field(default_factory=list)
    totals: dict[str, Any] = field(default_factory=dict)
    data_points: list[AIDataPoint] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    priority: AIPriority = "none"
    result_note: Optional[str] = None

    def for_prompt(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "summary": self.summary,
            "shipment_code": self.shipment_code,
            "records": _clean(self.records),
            "totals": _clean(self.totals),
            "data_points": [item.model_dump() for item in self.data_points],
            "suggested_actions": self.suggested_actions,
            "priority": self.priority,
            "result_note": self.result_note,
        }


def build_ai_context(db: Session, request: AIAskRequest, max_rows: int) -> AIContextBundle:
    question = request.question.strip()
    shipment_code = _shipment_code_from_request(request)
    intent = _detect_intent(question, shipment_code)
    limit = max(1, min(max_rows, DEFAULT_TOP_LIMIT))

    if intent == "general_dashboard_summary":
        return _dashboard_context(db, question)
    if intent in {"shipment_status", "shipment_detail"}:
        return _shipment_context(db, question, intent, shipment_code, request.shipment_id, max_rows)
    if intent == "workflow_next_action":
        return _workflow_context(db, question, shipment_code, request.shipment_id)
    if intent == "pending_tasks":
        return _tasks_context(db, question, "open", limit)
    if intent == "overdue_tasks":
        return _overdue_tasks_context(db, question, limit)
    if intent == "bl_pending":
        return _bl_pending_context(db, question, limit)
    if intent == "demurrage_risk":
        return _demurrage_context(db, question, limit)
    if intent == "open_followups":
        return _followups_context(db, question, limit)
    if intent == "pending_receivables":
        return _pending_charge_context(db, question, "receivable", limit)
    if intent == "pending_payables":
        return _pending_charge_context(db, question, "payable", limit)
    if intent == "shipment_profit":
        return _shipment_profit_context(db, question, shipment_code, request.shipment_id)
    if intent == "monthly_profit":
        return _monthly_profit_context(db, question)
    if intent == "loss_making_shipments":
        return _loss_making_context(db, question, limit)
    if intent == "charges_summary":
        return _charges_summary_context(db, question, limit)
    if intent == "archived_shipments":
        return _archived_shipments_context(db, question, max_rows)
    if intent == "inactive_parties":
        return _inactive_parties_context(db, question, max_rows)
    if intent == "cancelled_tasks":
        return _tasks_context(db, question, "cancelled", max_rows)
    return _unknown_context(question)


def _shipment_code_from_request(request: AIAskRequest) -> Optional[str]:
    if request.shipment_code:
        return request.shipment_code.upper()
    match = SHIPMENT_CODE_RE.search(request.question)
    return match.group(0).upper() if match else None


def _detect_intent(question: str, shipment_code: Optional[str]) -> str:
    text = question.lower()
    if "archived" in text and "shipment" in text:
        return "archived_shipments"
    if "inactive" in text and ("part" in text or "vendor" in text or "client" in text):
        return "inactive_parties"
    if "cancelled" in text and "task" in text:
        return "cancelled_tasks"
    if shipment_code and ("next action" in text or "what next" in text or "next step" in text):
        return "workflow_next_action"
    if shipment_code and any(token in text for token in ["profit", "p&l", "pnl"]):
        return "shipment_profit"
    if shipment_code and any(token in text for token in ["detail", "details", "status", "show"]):
        return "shipment_detail"
    if "overdue" in text and "task" in text:
        return "overdue_tasks"
    if "pending" in text and "task" in text:
        return "pending_tasks"
    if "demurrage" in text or "free days" in text:
        return "demurrage_risk"
    if "follow-up" in text or "follow up" in text or "followups" in text:
        return "open_followups"
    if "receivable" in text or "uncollected" in text:
        return "pending_receivables"
    if "payable" in text:
        return "pending_payables"
    if (_has_bl_keyword(text)) and any(token in text for token in ["pending", "approval", "draft"]):
        return "bl_pending"
    if "loss-making" in text or "loss making" in text or "loss" in text:
        return "loss_making_shipments"
    if "this month" in text and "profit" in text:
        return "monthly_profit"
    if "charge" in text or "finance" in text or "p&l" in text or "pnl" in text:
        return "charges_summary"
    if "attention" in text or "dashboard" in text or "summary" in text:
        return "general_dashboard_summary"
    if "shipment" in text and "status" in text:
        return "shipment_status"
    return "unknown"


def _has_bl_keyword(text: str) -> bool:
    return bool(re.search(r"\bbl\b", text)) or "bill of lading" in text


def _dashboard_context(db: Session, question: str) -> AIContextBundle:
    dashboard = get_dashboard_summary(db)
    financials = calculate_dashboard_financials(db)
    priority: AIPriority = "warning" if dashboard.alerts_today or dashboard.pending_tasks else "none"
    return AIContextBundle(
        intent="general_dashboard_summary",
        question=question,
        summary="Active operational dashboard and finance summary.",
        totals={
            "live_shipments": dashboard.live_shipments,
            "pending_tasks": dashboard.pending_tasks,
            "future_bookings": dashboard.future_bookings,
            "alerts_today": dashboard.alerts_today,
            "completed_this_month": dashboard.completed_this_month,
            "pending_receivables": financials.pending_receivables,
            "pending_payables": financials.pending_payables,
            "this_month_profit": financials.this_month_profit,
            "currency": financials.currency,
        },
        records=[_shipment_row(shipment) for shipment in dashboard.shipments[:5]],
        data_points=[
            AIDataPoint(label="Live shipments", value=str(dashboard.live_shipments)),
            AIDataPoint(label="Pending tasks", value=str(dashboard.pending_tasks)),
            AIDataPoint(label="This month profit", value=f"{financials.currency} {financials.this_month_profit}"),
        ],
        suggested_actions=["Review critical alerts", "Follow up pending tasks"] if priority != "none" else [],
        priority=priority,
    )


def _shipment_context(
    db: Session,
    question: str,
    intent: str,
    shipment_code: Optional[str],
    shipment_id: Optional[int],
    max_rows: int,
) -> AIContextBundle:
    query = db.query(Shipment).options(
        joinedload(Shipment.exporter),
        joinedload(Shipment.importer),
        joinedload(Shipment.documents),
        joinedload(Shipment.tasks),
    )
    if shipment_id:
        shipment = query.filter(Shipment.id == shipment_id).first()
    elif shipment_code:
        shipment = query.filter(Shipment.shipment_code == shipment_code).first()
    else:
        shipments = (
            query.filter(Shipment.is_archived.is_(False))
            .order_by(Shipment.created_at.desc())
            .limit(max_rows)
            .all()
        )
        return AIContextBundle(
            intent=intent,
            question=question,
            summary=f"Showing latest {len(shipments)} active shipment status records.",
            records=[_shipment_row(shipment) for shipment in shipments],
            data_points=[AIDataPoint(label="Shipments shown", value=str(len(shipments)))],
            priority="none",
        )
    if not shipment:
        code = shipment_code or f"shipment #{shipment_id}"
        return AIContextBundle(
            intent=intent,
            question=question,
            shipment_code=shipment_code,
            summary=f"Shipment {code} was not found.",
            result_note=f"I could not find shipment {code} in the system.",
        )
    return AIContextBundle(
        intent=intent,
        question=question,
        shipment_code=shipment.shipment_code,
        summary=f"Shipment detail for {shipment.shipment_code}.",
        records=[
            {
                **_shipment_row(shipment),
                "exporter": shipment.exporter.name if shipment.exporter else None,
                "importer": shipment.importer.name if shipment.importer else None,
                "documents": [
                    _document_row(document, shipment.shipment_code)
                    for document in sorted(shipment.documents, key=lambda item: item.doc_type)
                ],
                "tasks": [
                    _task_row(task, shipment.shipment_code)
                    for task in sorted(shipment.tasks, key=lambda item: (item.status, item.created_at))
                    if task.status != "cancelled"
                ],
            }
        ],
        data_points=[
            AIDataPoint(label="Shipment", value=shipment.shipment_code),
            AIDataPoint(label="Status", value=shipment.status),
            AIDataPoint(label="Archived", value="yes" if shipment.is_archived else "no"),
        ],
        priority="warning" if shipment.is_archived else "none",
    )


def _workflow_context(
    db: Session, question: str, shipment_code: Optional[str], shipment_id: Optional[int]
) -> AIContextBundle:
    shipment = _get_shipment(db, shipment_code, shipment_id)
    if not shipment:
        code = shipment_code or f"shipment #{shipment_id}"
        return AIContextBundle(
            intent="workflow_next_action",
            question=question,
            shipment_code=shipment_code,
            summary=f"Shipment {code} was not found.",
            result_note=f"I could not find shipment {code} in the system.",
        )
    next_action = next_task_for(shipment, shipment.status)
    actions = [next_action] if next_action else []
    return AIContextBundle(
        intent="workflow_next_action",
        question=question,
        shipment_code=shipment.shipment_code,
        summary=f"Workflow next action for {shipment.shipment_code}.",
        records=[_shipment_row(shipment)],
        data_points=[
            AIDataPoint(label="Shipment", value=shipment.shipment_code),
            AIDataPoint(label="Current status", value=shipment.status),
        ],
        suggested_actions=actions,
        priority="info" if actions else "none",
        result_note="No mapped next action was found for this workflow status." if not actions else None,
    )


def _tasks_context(db: Session, question: str, status_value: str, limit: int) -> AIContextBundle:
    query = (
        db.query(Task)
        .options(joinedload(Task.shipment))
        .join(Shipment, Shipment.id == Task.shipment_id)
        .filter(Task.status == status_value)
    )
    if status_value != "cancelled":
        query = query.filter(Shipment.is_archived.is_(False))
    tasks = query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).limit(limit).all()
    intent = "cancelled_tasks" if status_value == "cancelled" else "pending_tasks"
    return AIContextBundle(
        intent=intent,
        question=question,
        summary=f"Showing {len(tasks)} {status_value} task records.",
        records=[_task_row(task, task.shipment.shipment_code if task.shipment else None) for task in tasks],
        data_points=[AIDataPoint(label=f"{status_value.title()} tasks", value=str(len(tasks)))],
        suggested_actions=["Review due dates and assign owners"] if status_value == "open" and tasks else [],
        priority="warning" if status_value == "open" and tasks else "none",
    )


def _overdue_tasks_context(db: Session, question: str, limit: int) -> AIContextBundle:
    today = date.today()
    tasks = (
        db.query(Task)
        .options(joinedload(Task.shipment))
        .join(Shipment, Shipment.id == Task.shipment_id)
        .filter(
            Task.status == "open",
            Task.due_date.isnot(None),
            Task.due_date < today,
            Shipment.is_archived.is_(False),
        )
        .order_by(Task.due_date.asc(), Task.priority.asc())
        .limit(limit)
        .all()
    )
    return AIContextBundle(
        intent="overdue_tasks",
        question=question,
        summary=f"Showing {len(tasks)} overdue task records.",
        records=[_task_row(task, task.shipment.shipment_code if task.shipment else None) for task in tasks],
        data_points=[AIDataPoint(label="Overdue tasks", value=str(len(tasks)))],
        suggested_actions=["Close or reassign overdue tasks"],
        priority="critical" if tasks else "none",
    )


def _bl_pending_context(db: Session, question: str, limit: int) -> AIContextBundle:
    docs = (
        db.query(Document, Shipment)
        .join(Shipment, Shipment.id == Document.shipment_id)
        .filter(
            Document.doc_type.ilike("%BL%"),
            Document.status.in_(["pending", "received", "sent"]),
            Shipment.is_archived.is_(False),
        )
        .order_by(Shipment.created_at.desc())
        .limit(limit)
        .all()
    )
    records = [_document_row(document, shipment.shipment_code) for document, shipment in docs]
    return AIContextBundle(
        intent="bl_pending",
        question=question,
        summary=f"Showing {len(records)} BL-related pending records.",
        records=records,
        data_points=[AIDataPoint(label="BL pending records", value=str(len(records)))],
        suggested_actions=["Follow up with line or exporter for BL approval"] if records else [],
        priority="warning" if records else "none",
    )


def _demurrage_context(db: Session, question: str, limit: int) -> AIContextBundle:
    rows = (
        db.query(Demurrage, Shipment)
        .join(Shipment, Shipment.id == Demurrage.shipment_id)
        .filter(Shipment.is_archived.is_(False))
        .all()
    )
    records = []
    for demurrage, shipment in rows:
        read = calculate_demurrage(demurrage)
        if read.is_demurrage_running or (
            read.days_remaining is not None and read.days_remaining <= demurrage.alert_at_days
        ):
            records.append(
                {
                    "shipment_code": shipment.shipment_code,
                    "free_days": read.free_days,
                    "start_date": read.start_date,
                    "days_remaining": read.days_remaining,
                    "status": read.status,
                    "currency": read.currency,
                    "total_demurrage_due": read.total_demurrage_due,
                }
            )
    records = records[:limit]
    priority: AIPriority = "critical" if any(row["status"] == "running" for row in records) else ("warning" if records else "none")
    return AIContextBundle(
        intent="demurrage_risk",
        question=question,
        summary=f"Showing {len(records)} demurrage risk records.",
        records=records,
        data_points=[AIDataPoint(label="Demurrage risk shipments", value=str(len(records)))],
        suggested_actions=["Follow up DO handover and container delivery status"] if records else [],
        priority=priority,
    )


def _followups_context(db: Session, question: str, limit: int) -> AIContextBundle:
    followups = (
        db.query(FollowUpLog)
        .options(joinedload(FollowUpLog.shipment), joinedload(FollowUpLog.party))
        .join(Shipment, Shipment.id == FollowUpLog.shipment_id)
        .filter(FollowUpLog.status == "open", Shipment.is_archived.is_(False))
        .order_by(FollowUpLog.date.desc())
        .limit(limit)
        .all()
    )
    records = [_followup_row(item) for item in followups]
    return AIContextBundle(
        intent="open_followups",
        question=question,
        summary=f"Showing {len(records)} open follow-up records.",
        records=records,
        data_points=[AIDataPoint(label="Open follow-ups", value=str(len(records)))],
        suggested_actions=["Update follow-up status after client/vendor response"] if records else [],
        priority="info" if records else "none",
    )


def _pending_charge_context(db: Session, question: str, direction: str, limit: int) -> AIContextBundle:
    rows = list_pending_receivables(db, active_only=True) if direction == "receivable" else list_pending_payables(db, active_only=True)
    rows = rows[:limit]
    total = sum((row.amount for row in rows), Decimal("0"))
    label = "Pending receivables" if direction == "receivable" else "Pending payables"
    return AIContextBundle(
        intent=f"pending_{direction}s",
        question=question,
        summary=f"Showing {len(rows)} {label.lower()} records.",
        records=[row.model_dump() for row in rows],
        totals={"amount": total, "currency": rows[0].currency if rows else "INR"},
        data_points=[AIDataPoint(label=label, value=f"{rows[0].currency if rows else 'INR'} {total}")],
        suggested_actions=["Follow up collection from client"] if direction == "receivable" and rows else [],
        priority="warning" if rows else "none",
    )


def _shipment_profit_context(
    db: Session, question: str, shipment_code: Optional[str], shipment_id: Optional[int]
) -> AIContextBundle:
    shipment = _get_shipment(db, shipment_code, shipment_id)
    if not shipment:
        code = shipment_code or f"shipment #{shipment_id}"
        return AIContextBundle(
            intent="shipment_profit",
            question=question,
            shipment_code=shipment_code,
            summary=f"Shipment {code} was not found.",
            result_note=f"I could not find shipment {code} in the system.",
        )
    summary = calculate_shipment_pnl(db, shipment.id)
    return AIContextBundle(
        intent="shipment_profit",
        question=question,
        shipment_code=shipment.shipment_code,
        summary=f"Shipment P&L for {shipment.shipment_code}.",
        records=[summary.model_dump()],
        data_points=[
            AIDataPoint(label="Shipment", value=shipment.shipment_code),
            AIDataPoint(label="Net profit", value=f"{summary.currency} {summary.net_profit}"),
        ],
        suggested_actions=["Review payable and receivable charges"] if summary.net_profit < 0 else [],
        priority="critical" if summary.net_profit < 0 else "none",
    )


def _monthly_profit_context(db: Session, question: str) -> AIContextBundle:
    summary = calculate_dashboard_financials(db)
    return AIContextBundle(
        intent="monthly_profit",
        question=question,
        summary="This month active-operation financial summary.",
        totals=summary.model_dump(),
        data_points=[
            AIDataPoint(label="This month profit", value=f"{summary.currency} {summary.this_month_profit}"),
            AIDataPoint(label="Pending receivables", value=f"{summary.currency} {summary.pending_receivables}"),
        ],
        priority="warning" if summary.this_month_profit < 0 else "none",
    )


def _loss_making_context(db: Session, question: str, limit: int) -> AIContextBundle:
    rows = [row for row in list_shipment_pnl(db, active_only=True) if row.net_profit < 0][:limit]
    return AIContextBundle(
        intent="loss_making_shipments",
        question=question,
        summary=f"Showing {len(rows)} active loss-making shipment records.",
        records=[row.model_dump() for row in rows],
        data_points=[AIDataPoint(label="Loss-making shipments", value=str(len(rows)))],
        suggested_actions=["Review costs and pending receivables for loss-making shipments"] if rows else [],
        priority="critical" if rows else "none",
    )


def _charges_summary_context(db: Session, question: str, limit: int) -> AIContextBundle:
    rows = list_shipment_pnl(db, active_only=True)[:limit]
    return AIContextBundle(
        intent="charges_summary",
        question=question,
        summary=f"Showing {len(rows)} active shipment P&L rows.",
        records=[row.model_dump() for row in rows],
        data_points=[AIDataPoint(label="P&L rows", value=str(len(rows)))],
        priority="none",
    )


def _archived_shipments_context(db: Session, question: str, max_rows: int) -> AIContextBundle:
    shipments = (
        db.query(Shipment)
        .filter(Shipment.is_archived.is_(True))
        .order_by(Shipment.archived_at.desc().nullslast(), Shipment.created_at.desc())
        .limit(max_rows)
        .all()
    )
    return AIContextBundle(
        intent="archived_shipments",
        question=question,
        summary=f"Showing {len(shipments)} archived shipments.",
        records=[_shipment_row(shipment) for shipment in shipments],
        data_points=[AIDataPoint(label="Archived shipments", value=str(len(shipments)))],
        priority="info" if shipments else "none",
    )


def _inactive_parties_context(db: Session, question: str, max_rows: int) -> AIContextBundle:
    parties = (
        db.query(Party)
        .filter(Party.is_active.is_(False))
        .order_by(Party.deactivated_at.desc().nullslast(), Party.name.asc())
        .limit(max_rows)
        .all()
    )
    return AIContextBundle(
        intent="inactive_parties",
        question=question,
        summary=f"Showing {len(parties)} inactive parties.",
        records=[
            {
                "name": party.name,
                "type": party.type,
                "country": party.country,
                "deactivated_at": party.deactivated_at,
                "deactivation_reason": party.deactivation_reason,
            }
            for party in parties
        ],
        data_points=[AIDataPoint(label="Inactive parties", value=str(len(parties)))],
        priority="info" if parties else "none",
    )


def _unknown_context(question: str) -> AIContextBundle:
    return AIContextBundle(
        intent="unknown",
        question=question,
        summary="No specific database context matched this question.",
        result_note="The system does not have enough scoped data to answer this question.",
    )


def _get_shipment(db: Session, shipment_code: Optional[str], shipment_id: Optional[int]) -> Optional[Shipment]:
    query = db.query(Shipment)
    if shipment_id:
        return query.filter(Shipment.id == shipment_id).first()
    if shipment_code:
        return query.filter(Shipment.shipment_code == shipment_code).first()
    return None


def _shipment_row(shipment: Shipment) -> dict[str, Any]:
    return {
        "shipment_code": shipment.shipment_code,
        "type": shipment.type,
        "status": shipment.status,
        "origin_port": shipment.origin_port,
        "dest_port": shipment.dest_port,
        "etd": shipment.etd,
        "eta": shipment.eta,
        "shipping_line": shipment.shipping_line,
        "is_archived": shipment.is_archived,
    }


def _task_row(task: Task, shipment_code: Optional[str]) -> dict[str, Any]:
    return {
        "title": task.title,
        "status": task.status,
        "due_date": task.due_date,
        "priority": task.priority,
        "shipment_code": shipment_code,
        "auto_generated": task.auto_generated,
    }


def _document_row(document: Document, shipment_code: str) -> dict[str, Any]:
    return {
        "doc_type": document.doc_type,
        "status": document.status,
        "shipment_code": shipment_code,
    }


def _followup_row(followup: FollowUpLog) -> dict[str, Any]:
    return {
        "shipment_code": followup.shipment.shipment_code if followup.shipment else None,
        "party_name": followup.party.name if followup.party else None,
        "channel": followup.channel,
        "summary": followup.summary,
        "next_action": followup.next_action,
        "status": followup.status,
        "date": followup.date,
    }


def _clean(value: Any) -> Any:
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
