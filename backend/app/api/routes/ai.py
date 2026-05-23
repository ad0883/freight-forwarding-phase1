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


router = APIRouter(prefix="/ai", tags=["mock-ai"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class AskResponse(BaseModel):
    answer: str


@router.post("/ask", response_model=AskResponse)
def ask_mock_ai(
    payload: AskRequest,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> AskResponse:
    question = payload.question.strip().lower()
    if "pending" in question and "task" in question:
        tasks = db.query(Task).filter(Task.status == "open").order_by(Task.created_at.desc()).all()
        if not tasks:
            return AskResponse(answer="There are no pending tasks.")
        lines = [f"{task.title} for shipment #{task.shipment_id}" for task in tasks[:10]]
        return AskResponse(answer="Pending tasks: " + "; ".join(lines))

    if "bl" in question and "pending" in question:
        docs = (
            db.query(Document, Shipment)
            .join(Shipment, Shipment.id == Document.shipment_id)
            .filter(Document.doc_type.ilike("%BL%"), Document.status.in_(["pending", "received", "sent"]))
            .order_by(Shipment.created_at.desc())
            .all()
        )
        if not docs:
            return AskResponse(answer="No shipments currently have BL approval pending.")
        codes = sorted({shipment.shipment_code for _, shipment in docs})
        return AskResponse(answer="BL approval is pending for: " + ", ".join(codes[:10]))

    if "shipment" in question and "status" in question:
        for word in payload.question.replace("?", " ").split():
            if word.upper().startswith("FF-"):
                shipment = db.query(Shipment).filter(Shipment.shipment_code == word.upper()).first()
                if shipment:
                    return AskResponse(answer=f"{shipment.shipment_code} is currently {shipment.status}.")
        shipments = db.query(Shipment).order_by(Shipment.created_at.desc()).limit(10).all()
        if not shipments:
            return AskResponse(answer="No shipments have been created yet.")
        lines = [f"{shipment.shipment_code}: {shipment.status}" for shipment in shipments]
        return AskResponse(answer="Shipment status: " + "; ".join(lines))

    if "free days" in question and ("expiring" in question or "expire" in question):
        rows = db.query(Demurrage, Shipment).join(Shipment, Shipment.id == Demurrage.shipment_id).all()
        matches = []
        for demurrage, shipment in rows:
            read = calculate_demurrage(demurrage)
            if read.days_remaining is not None and 0 < read.days_remaining <= demurrage.alert_at_days:
                matches.append(f"{shipment.shipment_code}: {read.days_remaining} day(s) remaining")
        return AskResponse(answer="Free days expiring: " + "; ".join(matches) if matches else "No shipments have free days expiring.")

    if "demurrage" in question and "running" in question:
        rows = db.query(Demurrage, Shipment).join(Shipment, Shipment.id == Demurrage.shipment_id).all()
        matches = [
            shipment.shipment_code
            for demurrage, shipment in rows
            if calculate_demurrage(demurrage).is_demurrage_running
        ]
        return AskResponse(answer="Demurrage running for: " + ", ".join(matches) if matches else "No shipments currently have demurrage running.")

    if "follow-up" in question or "follow up" in question or "followups" in question:
        followups = db.query(FollowUpLog).filter(FollowUpLog.status == "open").order_by(FollowUpLog.date.desc()).limit(10).all()
        if not followups:
            return AskResponse(answer="There are no open follow-ups.")
        lines = [f"Shipment #{item.shipment_id}: {item.summary}" for item in followups]
        return AskResponse(answer="Open follow-ups: " + "; ".join(lines))

    return AskResponse(
        answer=(
            "I can answer Phase 1 questions like: Which tasks are pending? "
            "Which shipments have BL approval pending? Show shipment status. "
            "Phase 2 examples: Which shipments have free days expiring? "
            "Which shipments have demurrage running? Which follow-ups are open?"
        )
    )
