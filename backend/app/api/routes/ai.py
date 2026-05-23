from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.document import Document
from app.models.shipment import Shipment
from app.models.task import Task
from app.models.user import User


router = APIRouter(prefix="/ai", tags=["mock-ai"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class AskResponse(BaseModel):
    answer: str


@router.post("/ask", response_model=AskResponse)
def ask_mock_ai(
    payload: AskRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
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
        shipments = db.query(Shipment).order_by(Shipment.created_at.desc()).limit(10).all()
        if not shipments:
            return AskResponse(answer="No shipments have been created yet.")
        lines = [f"{shipment.shipment_code}: {shipment.status}" for shipment in shipments]
        return AskResponse(answer="Shipment status: " + "; ".join(lines))

    return AskResponse(
        answer=(
            "I can answer Phase 1 questions like: Which tasks are pending? "
            "Which shipments have BL approval pending? Show shipment status."
        )
    )
