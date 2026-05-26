import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.bl_management import BLManagement
from app.models.demurrage import Demurrage
from app.models.document import Document
from app.models.document_intelligence import (
    DocumentExtraction,
    DocumentExtractedField,
    DocumentMismatchResult,
)
from app.models.document_version import DocumentVersion
from app.models.followup import FollowUpLog
from app.models.party import Party
from app.models.shipment import Shipment
from app.models.task import Task
from app.schemas.ai import AIAskRequest, AIDataPoint, AIPriority
from app.api.deps import AuthenticatedUser
from app.services.daily_summary_service import build_daily_summary
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


def build_ai_context(
    db: Session,
    request: AIAskRequest,
    max_rows: int,
    current_user: Optional[AuthenticatedUser] = None,
) -> AIContextBundle:
    question = request.question.strip()
    shipment_code = _shipment_code_from_request(request)
    intent = _detect_intent(question, shipment_code)
    limit = max(1, min(max_rows, DEFAULT_TOP_LIMIT))

    if intent == "validation_issues_summary":
        return _validation_issues_context(db, question, limit)
    if intent == "events_recent":
        return _recent_events_context(db, question, limit)
    if intent == "workflow_review_summary":
        return _workflow_review_context(db, question, limit)
    if intent == "shipment_workflow_state":
        return _shipment_workflow_state_context(db, question, shipment_code, request.shipment_id)
    if intent == "shipment_workflow_next_steps":
        return _shipment_workflow_next_steps_context(db, question, shipment_code, request.shipment_id, current_user)
    if intent == "container_summary":
        return _container_summary_context(db, question, shipment_code, request.shipment_id, limit)
    if intent == "container_status_lookup":
        return _container_status_context(db, question, limit)
    if intent == "container_demurrage_risk":
        return _container_risk_context(db, question, "demurrage", limit)
    if intent == "container_detention_risk":
        return _container_risk_context(db, question, "detention", limit)
    if intent == "container_empty_return_overdue":
        return _container_empty_return_overdue_context(db, question, limit)
    if intent == "container_shipment_exposure":
        return _container_shipment_exposure_context(db, question, shipment_code, request.shipment_id)
    if intent == "document_versions_summary":
        return _document_versions_context(db, question, shipment_code, request.shipment_id, limit)
    if intent == "document_intelligence_summary":
        return _document_intelligence_context(db, question, shipment_code, request.shipment_id, limit)
    if intent == "notifications_summary" and current_user:
        return _notifications_summary_context(db, question, current_user)
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
    if (
        "stuck" in text
        or "manual workflow review" in text
        or "manual review" in text and ("workflow" in text or "shipment" in text)
        or "invalid workflow transition" in text
        or "blocked transition" in text
    ):
        return "workflow_review_summary"
    if shipment_code and ("workflow state" in text or "workflow status" in text):
        return "shipment_workflow_state"
    if "next steps for" in text and shipment_code:
        return "shipment_workflow_next_steps"
    if "empty return" in text and ("overdue" in text or "late" in text):
        return "container_empty_return_overdue"
    if "container" in text and ("demurrage" in text and "risk" in text):
        return "container_demurrage_risk"
    if "container" in text and ("detention" in text and "risk" in text):
        return "container_detention_risk"
    if shipment_code and ("demurrage exposure" in text or "container exposure" in text):
        return "container_shipment_exposure"
    if "container" in text and "status" in text and not shipment_code:
        return "container_status_lookup"
    if "container" in text and shipment_code:
        return "container_summary"
    if "container" in text and ("status of" in text or "show container" in text):
        return "container_status_lookup"
    if _has_document_intelligence_keyword(text):
        return "document_intelligence_summary"
    if _has_document_version_keyword(text, shipment_code):
        return "document_versions_summary"
    if (
        "validation issue" in text
        or "manual review" in text
        or "failed validation" in text
        or "broken workflow" in text
    ):
        return "validation_issues_summary"
    if "recent event" in text or "recent events" in text or "what events" in text or "what recent events" in text:
        return "events_recent"
    if "notification" in text or "urgent issue" in text or "needs attention" in text or "need attention" in text:
        return "notifications_summary"
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


def _notifications_summary_context(
    db: Session, question: str, current_user: AuthenticatedUser
) -> AIContextBundle:
    summary = build_daily_summary(db, current_user)
    totals = summary.totals
    records = [item.model_dump() for item in summary.top_urgent_items]
    priority: AIPriority = "none"
    if any(item.priority == "critical" for item in summary.top_urgent_items):
        priority = "critical"
    elif totals.overdue_tasks or totals.demurrage_risks or totals.pending_bl_approvals:
        priority = "warning"
    elif totals.unread_notifications or summary.top_urgent_items:
        priority = "info"
    return AIContextBundle(
        intent="notifications_summary",
        question=question,
        summary="Today's notification-backed operations summary.",
        totals=totals.model_dump(),
        records=records,
        data_points=[
            AIDataPoint(label="Unread notifications", value=str(totals.unread_notifications)),
            AIDataPoint(label="Overdue tasks", value=str(totals.overdue_tasks)),
            AIDataPoint(label="Demurrage risks", value=str(totals.demurrage_risks)),
            AIDataPoint(label="Pending BL approvals", value=str(totals.pending_bl_approvals)),
        ],
        suggested_actions=[
            item.title for item in summary.top_urgent_items[:3]
        ],
        priority=priority,
    )


def _has_bl_keyword(text: str) -> bool:
    return bool(re.search(r"\bbl\b", text)) or "bill of lading" in text


def _has_document_version_keyword(text: str, shipment_code: Optional[str]) -> bool:
    document_terms = (
        "document" in text
        or "documents" in text
        or "invoice" in text
        or "packing list" in text
        or "delivery order" in text
        or _has_bl_keyword(text)
    )
    version_terms = (
        "version" in text
        or "uploaded" in text
        or "upload" in text
        or "file" in text
        or "pending review" in text
        or "missing required" in text
        or "latest" in text
        or "history" in text
    )
    return document_terms and (version_terms or bool(shipment_code))


def _has_document_intelligence_keyword(text: str) -> bool:
    return (
        "document intelligence" in text
        or "ocr" in text
        or "extracted field" in text
        or "extracted fields" in text
        or ("mismatch" in text and "document" in text)
        or "low-confidence" in text
        or "low confidence" in text and ("document" in text or "ocr" in text)
    )


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


def _document_versions_context(
    db: Session,
    question: str,
    shipment_code: Optional[str],
    shipment_id: Optional[int],
    limit: int,
) -> AIContextBundle:
    shipment = _get_shipment(db, shipment_code, shipment_id)
    if shipment:
        versions = (
            db.query(DocumentVersion)
            .options(joinedload(DocumentVersion.file), joinedload(DocumentVersion.shipment))
            .filter(DocumentVersion.shipment_id == shipment.id)
            .order_by(DocumentVersion.created_at.desc(), DocumentVersion.id.desc())
            .limit(limit)
            .all()
        )
        missing_docs = (
            db.query(Document)
            .filter(
                Document.shipment_id == shipment.id,
                Document.is_required.is_(True),
                Document.current_version_id.is_(None),
            )
            .order_by(Document.doc_type.asc())
            .limit(limit)
            .all()
        )
        return AIContextBundle(
            intent="document_versions_summary",
            question=question,
            shipment_code=shipment.shipment_code,
            summary=f"Document upload metadata for {shipment.shipment_code}. File contents are not read by AI.",
            records=[_document_version_row(version) for version in versions],
            totals={
                "versions": len(versions),
                "missing_required_documents": len(missing_docs),
            },
            data_points=[
                AIDataPoint(label="Uploaded versions", value=str(len(versions))),
                AIDataPoint(label="Missing required", value=str(len(missing_docs))),
            ],
            suggested_actions=[f"Upload {doc.doc_type}" for doc in missing_docs[:3]],
            priority="warning" if missing_docs else ("info" if versions else "none"),
        )

    pending = (
        db.query(DocumentVersion)
        .options(joinedload(DocumentVersion.file), joinedload(DocumentVersion.shipment))
        .join(Shipment, Shipment.id == DocumentVersion.shipment_id)
        .filter(
            DocumentVersion.review_status == "pending_review",
            DocumentVersion.status == "active",
            DocumentVersion.is_current.is_(True),
            Shipment.is_archived.is_(False),
        )
        .order_by(DocumentVersion.created_at.desc(), DocumentVersion.id.desc())
        .limit(limit)
        .all()
    )
    missing_docs = (
        db.query(Document, Shipment)
        .join(Shipment, Shipment.id == Document.shipment_id)
        .filter(
            Document.is_required.is_(True),
            Document.current_version_id.is_(None),
            Shipment.is_archived.is_(False),
        )
        .order_by(Shipment.created_at.desc())
        .limit(limit)
        .all()
    )
    missing_records = [
        {
            "shipment_code": shipment.shipment_code,
            "document_type": document.doc_type,
            "status": document.status,
        }
        for document, shipment in missing_docs
    ]
    return AIContextBundle(
        intent="document_versions_summary",
        question=question,
        summary="Document upload/version summary. File contents are not read by AI.",
        records=[_document_version_row(version) for version in pending] + missing_records,
        totals={
            "pending_review": len(pending),
            "missing_required_documents": len(missing_records),
        },
        data_points=[
            AIDataPoint(label="Pending review", value=str(len(pending))),
            AIDataPoint(label="Missing required", value=str(len(missing_records))),
        ],
        suggested_actions=[
            "Review pending document versions",
            "Upload missing required documents",
        ] if pending or missing_records else [],
        priority="warning" if pending or missing_records else "none",
    )


def _document_intelligence_context(
    db: Session,
    question: str,
    shipment_code: Optional[str],
    shipment_id: Optional[int],
    limit: int,
) -> AIContextBundle:
    shipment = _get_shipment(db, shipment_code, shipment_id)
    extraction_query = db.query(DocumentExtraction)
    mismatch_query = db.query(DocumentMismatchResult).filter(DocumentMismatchResult.status == "open")
    if shipment:
        extraction_query = extraction_query.filter(DocumentExtraction.shipment_id == shipment.id)
        mismatch_query = mismatch_query.filter(DocumentMismatchResult.shipment_id == shipment.id)
    extractions = (
        extraction_query
        .filter(DocumentExtraction.status != "superseded")
        .order_by(DocumentExtraction.created_at.desc(), DocumentExtraction.id.desc())
        .limit(limit)
        .all()
    )
    mismatches = (
        mismatch_query
        .order_by(DocumentMismatchResult.severity.desc(), DocumentMismatchResult.created_at.desc())
        .limit(limit)
        .all()
    )
    low_confidence = [
        row for row in extractions if row.status in {"low_confidence", "manual_review_required"}
    ]
    field_rows = (
        db.query(DocumentExtractedField)
        .join(DocumentExtraction, DocumentExtraction.id == DocumentExtractedField.extraction_id)
        .filter(DocumentExtraction.id.in_([row.id for row in extractions] or [0]))
        .order_by(DocumentExtractedField.confidence.asc(), DocumentExtractedField.id.asc())
        .limit(limit)
        .all()
    )
    records = [
        {
            "type": "extraction",
            "document_version_id": row.document_version_id,
            "shipment_id": row.shipment_id,
            "document_type": row.document_type,
            "detected_document_type": row.detected_document_type,
            "status": row.status,
            "overall_confidence": row.overall_confidence,
            "created_at": row.created_at,
        }
        for row in extractions
    ] + [
        {
            "type": "mismatch",
            "rule_key": row.rule_key,
            "severity": row.severity,
            "field_key": row.field_key,
            "system_value": row.system_value,
            "extracted_value": row.extracted_value,
            "message": row.message,
            "shipment_id": row.shipment_id,
        }
        for row in mismatches
    ] + [
        {
            "type": "field",
            "field_key": row.field_key,
            "normalized_value": row.normalized_value,
            "confidence": row.confidence,
            "status": row.status,
        }
        for row in field_rows
    ]
    critical = [row for row in mismatches if row.severity == "critical"]
    priority: AIPriority = "critical" if critical else ("warning" if mismatches or low_confidence else ("info" if extractions else "none"))
    return AIContextBundle(
        intent="document_intelligence_summary",
        question=question,
        shipment_code=shipment.shipment_code if shipment else shipment_code,
        summary="Read-only document intelligence summary. AI cannot run OCR or approve/apply suggestions.",
        records=records,
        totals={
            "extractions": len(extractions),
            "open_mismatches": len(mismatches),
            "critical_mismatches": len(critical),
            "low_confidence": len(low_confidence),
            "fields": len(field_rows),
        },
        data_points=[
            AIDataPoint(label="Extractions", value=str(len(extractions))),
            AIDataPoint(label="Open mismatches", value=str(len(mismatches))),
            AIDataPoint(label="Low confidence", value=str(len(low_confidence))),
        ],
        suggested_actions=[row.message for row in critical[:3]],
        priority=priority,
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


def _validation_issues_context(db: Session, question: str, limit: int) -> AIContextBundle:
    from app.models.validation_issue import ValidationIssue

    rows = (
        db.query(ValidationIssue)
        .filter(ValidationIssue.status == "open")
        .order_by(
            ValidationIssue.severity.desc(),
            ValidationIssue.created_at.desc(),
            ValidationIssue.id.desc(),
        )
        .limit(limit)
        .all()
    )
    critical = [row for row in rows if row.severity == "critical"]
    warning = [row for row in rows if row.severity == "warning"]
    info = [row for row in rows if row.severity == "info"]
    priority: AIPriority = "critical" if critical else ("warning" if warning else ("info" if info else "none"))
    records = [
        {
            "rule_key": row.rule_key,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "shipment_id": row.shipment_id,
            "severity": row.severity,
            "status": row.status,
            "message": row.message,
            "recommended_action": row.recommended_action,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return AIContextBundle(
        intent="validation_issues_summary",
        question=question,
        summary=f"Showing {len(records)} open validation issues.",
        records=records,
        totals={
            "open_count": len(rows),
            "critical": len(critical),
            "warning": len(warning),
            "info": len(info),
        },
        data_points=[
            AIDataPoint(label="Open issues", value=str(len(rows))),
            AIDataPoint(label="Critical", value=str(len(critical))),
            AIDataPoint(label="Warning", value=str(len(warning))),
        ],
        suggested_actions=[row.message for row in critical[:3]],
        priority=priority,
    )


def _recent_events_context(db: Session, question: str, limit: int) -> AIContextBundle:
    from app.models.operational_event import OperationalEvent

    rows = (
        db.query(OperationalEvent)
        .order_by(OperationalEvent.created_at.desc(), OperationalEvent.id.desc())
        .limit(limit)
        .all()
    )
    records = [
        {
            "event_type": row.event_type,
            "entity_type": row.entity_type,
            "entity_label": row.entity_label,
            "validation_status": row.validation_status,
            "source": row.source,
            "actor_name": row.actor_name,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return AIContextBundle(
        intent="events_recent",
        question=question,
        summary=f"Showing {len(records)} most recent operational events.",
        records=records,
        data_points=[AIDataPoint(label="Recent events", value=str(len(records)))],
        priority="info" if records else "none",
    )


def _unknown_context(question: str) -> AIContextBundle:
    return AIContextBundle(
        intent="unknown",
        question=question,
        summary="No specific database context matched this question.",
        result_note="The system does not have enough scoped data to answer this question.",
    )


def _workflow_review_context(db: Session, question: str, limit: int) -> AIContextBundle:
    flagged = (
        db.query(Shipment)
        .filter(Shipment.manual_review_required.is_(True), Shipment.is_archived.is_(False))
        .order_by(Shipment.workflow_state_updated_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    from app.models.workflow_state_machine import WorkflowTransitionLog

    blocked = (
        db.query(WorkflowTransitionLog)
        .filter(WorkflowTransitionLog.status.in_(["blocked", "manual_review_required"]))
        .order_by(WorkflowTransitionLog.created_at.desc())
        .limit(limit)
        .all()
    )
    records = [
        {
            "shipment_code": shipment.shipment_code,
            "workflow_state": shipment.workflow_state,
            "manual_review_reason": shipment.manual_review_reason,
            "is_archived": shipment.is_archived,
        }
        for shipment in flagged
    ]
    blocked_records = [
        {
            "shipment_id": entry.shipment_id,
            "from_state": entry.from_state,
            "to_state": entry.to_state,
            "status": entry.status,
            "reason": entry.reason,
            "created_at": entry.created_at,
        }
        for entry in blocked
    ]
    priority: AIPriority = "critical" if records else ("warning" if blocked_records else "none")
    return AIContextBundle(
        intent="workflow_review_summary",
        question=question,
        summary=f"Workflow review summary with {len(records)} flagged shipment(s).",
        records=records,
        totals={"flagged": len(records), "blocked_transitions": len(blocked_records)},
        data_points=[
            AIDataPoint(label="Manual review", value=str(len(records))),
            AIDataPoint(label="Blocked transitions", value=str(len(blocked_records))),
        ],
        suggested_actions=[entry.get("reason") or f"Review {entry.get('to_state')}" for entry in blocked_records[:3]],
        priority=priority,
    )


def _shipment_workflow_state_context(
    db: Session,
    question: str,
    shipment_code: Optional[str],
    shipment_id: Optional[int],
) -> AIContextBundle:
    shipment = _get_shipment(db, shipment_code, shipment_id)
    if not shipment:
        code = shipment_code or f"shipment #{shipment_id}"
        return AIContextBundle(
            intent="shipment_workflow_state",
            question=question,
            shipment_code=shipment_code,
            summary=f"Shipment {code} was not found.",
            result_note=f"I could not find shipment {code} in the system.",
        )
    return AIContextBundle(
        intent="shipment_workflow_state",
        question=question,
        shipment_code=shipment.shipment_code,
        summary=f"Workflow state for {shipment.shipment_code}.",
        records=[
            {
                "shipment_code": shipment.shipment_code,
                "workflow_state": shipment.workflow_state,
                "manual_review_required": shipment.manual_review_required,
                "manual_review_reason": shipment.manual_review_reason,
                "type": shipment.type,
                "is_archived": shipment.is_archived,
            }
        ],
        data_points=[
            AIDataPoint(label="Shipment", value=shipment.shipment_code),
            AIDataPoint(label="Workflow state", value=str(shipment.workflow_state or "unset")),
        ],
        priority="warning" if shipment.manual_review_required else "none",
    )


def _shipment_workflow_next_steps_context(
    db: Session,
    question: str,
    shipment_code: Optional[str],
    shipment_id: Optional[int],
    current_user,
) -> AIContextBundle:
    shipment = _get_shipment(db, shipment_code, shipment_id)
    if not shipment or not current_user:
        return AIContextBundle(
            intent="shipment_workflow_next_steps",
            question=question,
            shipment_code=shipment_code,
            summary="Shipment or user context unavailable.",
            result_note="Workflow next steps need both a shipment and an authenticated user.",
        )
    try:
        from app.services.workflow_state_machine_service import (
            get_or_infer_state,
            list_available_transitions,
        )

        current_state, rows = list_available_transitions(db, shipment, current_user)
    except Exception:
        current_state = None
        rows = []
    actions = [
        transition.label
        for transition, _target, permitted, _reason in rows
        if permitted
    ][:5]
    records = [
        {
            "transition_key": transition.transition_key,
            "to_state": transition.to_state,
            "label": transition.label,
            "requires_confirmation": transition.requires_confirmation,
            "is_sensitive": transition.is_sensitive,
            "permitted": permitted,
        }
        for transition, _target, permitted, _reason in rows
    ]
    return AIContextBundle(
        intent="shipment_workflow_next_steps",
        question=question,
        shipment_code=shipment.shipment_code,
        summary=(
            f"Available next workflow steps for {shipment.shipment_code} "
            f"from {current_state or 'unset state'}."
        ),
        records=records,
        data_points=[
            AIDataPoint(label="Current state", value=str(current_state or "unset")),
            AIDataPoint(label="Allowed next steps", value=str(len(actions))),
        ],
        suggested_actions=actions,
        priority="info" if actions else "none",
    )


def _container_summary_context(
    db: Session,
    question: str,
    shipment_code: Optional[str],
    shipment_id: Optional[int],
    limit: int,
) -> AIContextBundle:
    from app.models.container import Container

    shipment = _get_shipment(db, shipment_code, shipment_id)
    if not shipment:
        return AIContextBundle(
            intent="container_summary",
            question=question,
            summary="Shipment not found.",
            result_note="I could not find that shipment.",
        )
    rows = (
        db.query(Container)
        .filter(Container.shipment_id == shipment.id, Container.is_active.is_(True))
        .order_by(Container.id.asc())
        .limit(limit)
        .all()
    )
    records = [
        {
            "container_number": container.container_number,
            "current_status": container.current_status,
            "container_size": container.container_size,
            "container_type": container.container_type,
            "delivery_date": container.delivery_date,
            "empty_return_deadline": container.empty_return_deadline,
        }
        for container in rows
    ]
    return AIContextBundle(
        intent="container_summary",
        question=question,
        shipment_code=shipment.shipment_code,
        summary=f"Showing {len(records)} container(s) for {shipment.shipment_code}.",
        records=records,
        data_points=[
            AIDataPoint(label="Containers", value=str(len(records))),
        ],
        priority="info" if records else "none",
    )


def _container_status_context(db: Session, question: str, limit: int) -> AIContextBundle:
    from app.models.container import Container

    text = question.upper()
    match = re.search(r"\b[A-Z]{4}\d{7}\b", text)
    if not match:
        return AIContextBundle(
            intent="container_status_lookup",
            question=question,
            summary="No container number recognized.",
            result_note="Please include an ISO container number (e.g. ABCD1234567).",
        )
    container_number = match.group(0)
    container = (
        db.query(Container)
        .filter(Container.container_number == container_number)
        .order_by(Container.updated_at.desc())
        .first()
    )
    if not container:
        return AIContextBundle(
            intent="container_status_lookup",
            question=question,
            summary=f"Container {container_number} not found.",
            result_note="No active container record matches that number.",
        )
    return AIContextBundle(
        intent="container_status_lookup",
        question=question,
        summary=f"Status for container {container.container_number}.",
        records=[
            {
                "container_number": container.container_number,
                "shipment_id": container.shipment_id,
                "current_status": container.current_status,
                "delivery_date": container.delivery_date,
                "empty_return_deadline": container.empty_return_deadline,
            }
        ],
        data_points=[
            AIDataPoint(label="Container", value=container.container_number),
            AIDataPoint(label="Status", value=container.current_status),
        ],
        priority="info",
    )


def _container_risk_context(db: Session, question: str, kind: str, limit: int) -> AIContextBundle:
    from app.services.demurrage_detention_service import list_recent_container_risk

    rows = list_recent_container_risk(db, limit=limit * 4)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        status_value = row.get(f"{kind}_status")
        if status_value in {"running", "estimated"} and row.get(f"{kind}_estimated_amount"):
            filtered.append(row)
        if len(filtered) >= limit:
            break
    if not filtered:
        return AIContextBundle(
            intent=f"container_{kind}_risk",
            question=question,
            summary=f"No containers currently show {kind} risk.",
            priority="none",
        )
    return AIContextBundle(
        intent=f"container_{kind}_risk",
        question=question,
        summary=f"{len(filtered)} container(s) with {kind} risk.",
        records=filtered,
        data_points=[
            AIDataPoint(label=f"{kind.title()} risk containers", value=str(len(filtered))),
        ],
        priority="warning" if filtered else "none",
    )


def _container_empty_return_overdue_context(
    db: Session, question: str, limit: int
) -> AIContextBundle:
    from app.models.container import Container

    today = date.today()
    rows = (
        db.query(Container)
        .filter(
            Container.is_active.is_(True),
            Container.empty_return_deadline.isnot(None),
            Container.empty_return_date.is_(None),
            Container.empty_return_deadline < today,
        )
        .order_by(Container.empty_return_deadline.asc())
        .limit(limit)
        .all()
    )
    records = [
        {
            "container_number": container.container_number,
            "shipment_id": container.shipment_id,
            "current_status": container.current_status,
            "empty_return_deadline": container.empty_return_deadline,
        }
        for container in rows
    ]
    return AIContextBundle(
        intent="container_empty_return_overdue",
        question=question,
        summary=f"{len(records)} container(s) overdue on empty return.",
        records=records,
        data_points=[
            AIDataPoint(label="Overdue containers", value=str(len(records))),
        ],
        priority="critical" if records else "none",
    )


def _container_shipment_exposure_context(
    db: Session,
    question: str,
    shipment_code: Optional[str],
    shipment_id: Optional[int],
) -> AIContextBundle:
    shipment = _get_shipment(db, shipment_code, shipment_id)
    if not shipment:
        return AIContextBundle(
            intent="container_shipment_exposure",
            question=question,
            summary="Shipment not found.",
            result_note="I could not find that shipment.",
        )
    from app.services.demurrage_detention_service import refresh_shipment_container_exposure

    snapshots = refresh_shipment_container_exposure(db, shipment.id)
    if not snapshots:
        return AIContextBundle(
            intent="container_shipment_exposure",
            question=question,
            shipment_code=shipment.shipment_code,
            summary=f"{shipment.shipment_code} has no containers yet.",
        )
    demurrage_total = sum(s.demurrage_estimated_amount for s in snapshots)
    detention_total = sum(s.detention_estimated_amount for s in snapshots)
    return AIContextBundle(
        intent="container_shipment_exposure",
        question=question,
        shipment_code=shipment.shipment_code,
        summary=f"Container exposure for {shipment.shipment_code}.",
        totals={
            "containers": len(snapshots),
            "demurrage_total": demurrage_total,
            "detention_total": detention_total,
            "currency": snapshots[0].currency,
        },
        data_points=[
            AIDataPoint(label="Containers", value=str(len(snapshots))),
            AIDataPoint(label="Demurrage", value=f"{snapshots[0].currency} {demurrage_total}"),
            AIDataPoint(label="Detention", value=f"{snapshots[0].currency} {detention_total}"),
        ],
        priority="warning" if (demurrage_total or detention_total) else "info",
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
        "current_version_id": document.current_version_id,
        "current_version_no": document.current_version_no,
        "current_review_status": document.current_review_status,
        "uploaded_file_count": document.uploaded_file_count,
    }


def _document_version_row(version: DocumentVersion) -> dict[str, Any]:
    return {
        "shipment_code": version.shipment.shipment_code if version.shipment else None,
        "document_type": version.document_type,
        "version_no": version.version_no,
        "version_label": version.version_label,
        "status": version.status,
        "review_status": version.review_status,
        "is_current": version.is_current,
        "file_name": version.file.sanitized_filename if version.file else None,
        "content_type": version.file.content_type if version.file else None,
        "file_size": version.file.file_size if version.file else None,
        "uploaded_by_name": version.created_by_name,
        "uploaded_at": version.created_at,
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
