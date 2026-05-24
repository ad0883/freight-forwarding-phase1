import re
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db
from app.models.demurrage import Demurrage
from app.models.document import Document
from app.models.followup import FollowUpLog
from app.models.shipment import Shipment
from app.models.task import Task
from app.services.demurrage_service import calculate_demurrage
from app.services.finance_service import (
    calculate_dashboard_financials,
    calculate_shipment_pnl,
    list_pending_payables,
    list_pending_receivables,
    list_shipment_pnl,
)


router = APIRouter(prefix="/ai", tags=["mock-ai"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class AskResponse(BaseModel):
    answer: str


def _format_money(amount, currency: str) -> str:
    return f"{currency} {amount}"


def _shipment_code_from_question(question_text: str) -> Optional[str]:
    code_match = re.search(r"\bFF-[A-Z]+-\d{4}-\d+\b", question_text.upper())
    if code_match:
        return code_match.group(0)
    return None


@router.post("/ask", response_model=AskResponse)
def ask_mock_ai(
    payload: AskRequest,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> AskResponse:
    question = payload.question.strip().lower()
    shipment_code = _shipment_code_from_question(payload.question)

    if "uncollected" in question or ("pending" in question and "receivable" in question):
        rows = list_pending_receivables(db, active_only=True)
        total = sum((row.amount for row in rows), start=Decimal("0"))
        if "which" in question or "shipment" in question:
            if not rows:
                return AskResponse(answer="There are no pending receivables.")
            lines = [f"{row.shipment_code}: {_format_money(row.amount, row.currency)}" for row in rows[:10]]
            return AskResponse(answer="Pending receivables: " + "; ".join(lines))
        currency = rows[0].currency if rows else "INR"
        return AskResponse(answer=f"Uncollected receivables total: {_format_money(total, currency)}.")

    if "pending" in question and "payable" in question:
        rows = list_pending_payables(db, active_only=True)
        if not rows:
            return AskResponse(answer="There are no pending payables.")
        lines = [f"{row.shipment_code}: {_format_money(row.amount, row.currency)}" for row in rows[:10]]
        return AskResponse(answer="Pending payables: " + "; ".join(lines))

    if shipment_code and ("profit" in question or "p&l" in question or "pnl" in question):
        shipment = db.query(Shipment).filter(Shipment.shipment_code == shipment_code).first()
        if shipment:
            summary = calculate_shipment_pnl(db, shipment.id)
            archived_note = " This shipment is archived." if shipment.is_archived else ""
            return AskResponse(
                answer=(
                    f"{shipment.shipment_code} P&L: receivable {_format_money(summary.total_receivable, summary.currency)}, "
                    f"payable {_format_money(summary.total_payable, summary.currency)}, "
                    f"net profit {_format_money(summary.net_profit, summary.currency)}.{archived_note}"
                )
            )

    if "loss-making" in question or "loss making" in question or "loss" in question:
        rows = [row for row in list_shipment_pnl(db, active_only=True) if row.net_profit < 0]
        if not rows:
            return AskResponse(answer="No shipments are currently loss-making.")
        lines = [f"{row.shipment_code}: {_format_money(row.net_profit, row.currency)}" for row in rows[:10]]
        return AskResponse(answer="Loss-making shipments: " + "; ".join(lines))

    if "this month" in question and "profit" in question:
        summary = calculate_dashboard_financials(db)
        return AskResponse(answer=f"This month profit is {_format_money(summary.this_month_profit, summary.currency)}.")

    if "pending" in question and "task" in question:
        tasks = (
            db.query(Task)
            .join(Shipment, Shipment.id == Task.shipment_id)
            .filter(Task.status == "open", Shipment.is_archived.is_(False))
            .order_by(Task.created_at.desc())
            .all()
        )
        if not tasks:
            return AskResponse(answer="There are no pending tasks.")
        lines = [f"{task.title} for shipment #{task.shipment_id}" for task in tasks[:10]]
        return AskResponse(answer="Pending tasks: " + "; ".join(lines))

    if "bl" in question and "pending" in question:
        docs = (
            db.query(Document, Shipment)
            .join(Shipment, Shipment.id == Document.shipment_id)
            .filter(
                Document.doc_type.ilike("%BL%"),
                Document.status.in_(["pending", "received", "sent"]),
                Shipment.is_archived.is_(False),
            )
            .order_by(Shipment.created_at.desc())
            .all()
        )
        if not docs:
            return AskResponse(answer="No shipments currently have BL approval pending.")
        codes = sorted({shipment.shipment_code for _, shipment in docs})
        return AskResponse(answer="BL approval is pending for: " + ", ".join(codes[:10]))

    if "status" in question:
        if shipment_code:
            shipment = db.query(Shipment).filter(Shipment.shipment_code == shipment_code).first()
            if shipment:
                archived_note = " It is archived." if shipment.is_archived else ""
                return AskResponse(answer=f"{shipment.shipment_code} is currently {shipment.status}.{archived_note}")
    if "shipment" in question and "status" in question:
        shipments = (
            db.query(Shipment)
            .filter(Shipment.is_archived.is_(False))
            .order_by(Shipment.created_at.desc())
            .limit(10)
            .all()
        )
        if not shipments:
            return AskResponse(answer="No shipments have been created yet.")
        lines = [f"{shipment.shipment_code}: {shipment.status}" for shipment in shipments]
        return AskResponse(answer="Shipment status: " + "; ".join(lines))

    if "free days" in question and ("expiring" in question or "expire" in question):
        rows = (
            db.query(Demurrage, Shipment)
            .join(Shipment, Shipment.id == Demurrage.shipment_id)
            .filter(Shipment.is_archived.is_(False))
            .all()
        )
        matches = []
        for demurrage, shipment in rows:
            read = calculate_demurrage(demurrage)
            if read.days_remaining is not None and 0 < read.days_remaining <= demurrage.alert_at_days:
                matches.append(f"{shipment.shipment_code}: {read.days_remaining} day(s) remaining")
        return AskResponse(answer="Free days expiring: " + "; ".join(matches) if matches else "No shipments have free days expiring.")

    if "demurrage" in question and "running" in question:
        rows = (
            db.query(Demurrage, Shipment)
            .join(Shipment, Shipment.id == Demurrage.shipment_id)
            .filter(Shipment.is_archived.is_(False))
            .all()
        )
        matches = [
            shipment.shipment_code
            for demurrage, shipment in rows
            if calculate_demurrage(demurrage).is_demurrage_running
        ]
        return AskResponse(answer="Demurrage running for: " + ", ".join(matches) if matches else "No shipments currently have demurrage running.")

    if "follow-up" in question or "follow up" in question or "followups" in question:
        followups = (
            db.query(FollowUpLog)
            .join(Shipment, Shipment.id == FollowUpLog.shipment_id)
            .filter(FollowUpLog.status == "open", Shipment.is_archived.is_(False))
            .order_by(FollowUpLog.date.desc())
            .limit(10)
            .all()
        )
        if not followups:
            return AskResponse(answer="There are no open follow-ups.")
        lines = [f"Shipment #{item.shipment_id}: {item.summary}" for item in followups]
        return AskResponse(answer="Open follow-ups: " + "; ".join(lines))

    return AskResponse(
        answer=(
            "I can answer Phase 1 questions like: Which tasks are pending? "
            "Which shipments have BL approval pending? Show shipment status. "
            "Phase 2 examples: Which shipments have free days expiring? "
            "Which shipments have demurrage running? Which follow-ups are open? "
            "Phase 3 examples: Which shipments have pending receivables? "
            "Show profit for FF-EXP-2026-001. What is this month profit?"
        )
    )
