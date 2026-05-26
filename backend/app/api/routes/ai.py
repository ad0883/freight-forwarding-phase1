from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db
from app.core.config import settings
from app.models.ai_log import AIInteractionLog
from app.schemas.ai import AIAskRequest, AIAskResponse, AIExamplesResponse, AIStatusResponse
from app.services.ai_context_service import build_ai_context
from app.services.ai_fallback_service import build_fallback_response
from app.services.llm_service import LLMServiceError, ai_can_use_llm, ask_llm


router = APIRouter(prefix="/ai", tags=["ai-assistant"])


AI_EXAMPLES = [
    "What shipments need attention today?",
    "Show my notifications.",
    "What are today's urgent issues?",
    "What validation issues exist?",
    "What needs manual review?",
    "What recent events happened?",
    "What is the workflow state of shipment FF-EXP-2026-001?",
    "What are the next steps for FF-EXP-2026-001?",
    "Which shipments are stuck?",
    "Show invalid workflow transitions.",
    "Show containers for FF-EXP-2026-001.",
    "Which containers have demurrage risk?",
    "Which containers have detention risk?",
    "Which empty returns are overdue?",
    "What is the demurrage exposure for FF-IMP-2026-001?",
    "Which document versions are pending review?",
    "What documents are missing for FF-EXP-2026-001?",
    "Show uploaded document history for FF-IMP-2026-001.",
    "Which tasks are overdue?",
    "Which shipments have demurrage running?",
    "Which BL approvals are pending?",
    "Which follow-ups are open?",
    "How much freight is uncollected?",
    "Which shipments have pending receivables?",
    "Which shipments have pending payables?",
    "Which shipments are loss-making?",
    "Show profit for FF-EXP-2026-001.",
    "What is the next action for FF-IMP-2026-001?",
    "Show archived shipments.",
    "Show inactive parties.",
    "Show cancelled tasks.",
]


@router.get("/examples", response_model=AIExamplesResponse)
def ai_examples(_: AuthenticatedUser = Depends(get_current_user)) -> AIExamplesResponse:
    return AIExamplesResponse(examples=AI_EXAMPLES)


@router.get("/status", response_model=AIStatusResponse)
def ai_status(_: AuthenticatedUser = Depends(get_current_user)) -> AIStatusResponse:
    return AIStatusResponse(
        ai_enabled=ai_can_use_llm(),
        provider=settings.AI_PROVIDER,
        model=settings.GROQ_MODEL,
        fallback_available=True,
    )


@router.post("/ask", response_model=AIAskResponse)
def ask_ai(
    payload: AIAskRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AIAskResponse:
    context = build_ai_context(db, payload, settings.AI_MAX_CONTEXT_ROWS, current_user=current_user)
    fallback_reason = None
    response: AIAskResponse

    if ai_can_use_llm():
        try:
            response = ask_llm(context)
        except LLMServiceError:
            fallback_reason = "Groq request failed"
            response = build_fallback_response(context, reason=fallback_reason)
    else:
        fallback_reason = "AI is disabled or Groq is not configured"
        response = build_fallback_response(context, reason=fallback_reason)

    _log_interaction(db, current_user.id, payload.question, response)
    return response


def _log_interaction(db: Session, user_id: int, question: str, response: AIAskResponse) -> None:
    if not settings.AI_LOG_INTERACTIONS:
        return
    try:
        db.add(
            AIInteractionLog(
                user_id=user_id,
                question=question,
                answer=response.answer,
                used_llm=response.used_llm,
                provider=response.provider,
                model=response.model,
                fallback_used=response.fallback_used,
                priority=response.priority,
            )
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
