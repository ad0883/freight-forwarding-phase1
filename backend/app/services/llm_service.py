import json
from typing import Any

from app.core.config import settings
from app.schemas.ai import AIAskResponse, AIDataPoint
from app.services.ai_context_service import AIContextBundle


SYSTEM_PROMPT = """
You are a freight forwarding operations assistant.

Answer only using the provided application context.
If the answer is not present in context, say that the system does not have enough data.
Do not invent shipment statuses, parties, ports, dates, financial amounts, charges, BL details, demurrage values, or task information.
Do not claim an action was performed.
You cannot modify records, archive shipments, deactivate parties, cancel tasks, edit charges, send emails, or upload files.
You cannot create, dismiss, or mark notifications read.
You may suggest next actions, but they are recommendations only.
For operational risks, mark priority as critical, warning, info, or none.
Keep answers concise, practical, and business-focused.

Return JSON only with keys:
answer: string
priority: one of critical, warning, info, none
suggested_actions: array of strings
data_points: array of objects with label and value strings
""".strip()


class LLMServiceError(Exception):
    pass


def ai_can_use_llm() -> bool:
    return (
        settings.AI_ENABLED
        and settings.AI_PROVIDER.lower() == "groq"
        and bool(settings.GROQ_API_KEY.strip())
    )


def ask_llm(context: AIContextBundle) -> AIAskResponse:
    if not ai_can_use_llm():
        raise LLMServiceError("AI is disabled or Groq API key is missing")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMServiceError("OpenAI-compatible client is not installed") from exc

    payload = {
        "question": context.question,
        "context": context.for_prompt(),
    }
    try:
        client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_BASE_URL,
            timeout=settings.AI_TIMEOUT_SECONDS,
        )
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, default=str)},
            ],
            temperature=0.2,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        raise LLMServiceError("Groq request failed") from exc

    content = completion.choices[0].message.content if completion.choices else None
    if not content:
        raise LLMServiceError("Groq returned an empty response")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMServiceError("Groq returned non-JSON content") from exc

    return _response_from_parsed(parsed, context)


def _response_from_parsed(parsed: dict[str, Any], context: AIContextBundle) -> AIAskResponse:
    priority = parsed.get("priority") or context.priority
    if priority not in {"critical", "warning", "info", "none"}:
        priority = context.priority
    suggested_actions = parsed.get("suggested_actions")
    if not isinstance(suggested_actions, list):
        suggested_actions = context.suggested_actions
    suggested_actions = [str(item) for item in suggested_actions if str(item).strip()]

    parsed_data_points = parsed.get("data_points")
    data_points = []
    if isinstance(parsed_data_points, list):
        for item in parsed_data_points:
            if isinstance(item, dict) and item.get("label") is not None and item.get("value") is not None:
                data_points.append(AIDataPoint(label=str(item["label"]), value=str(item["value"])))
    if not data_points:
        data_points = context.data_points

    answer = str(parsed.get("answer") or context.result_note or "The system does not have enough data to answer this.")
    return AIAskResponse(
        answer=answer,
        priority=priority,
        suggested_actions=suggested_actions,
        data_points=data_points,
        used_llm=True,
        provider=settings.AI_PROVIDER,
        model=settings.GROQ_MODEL,
        fallback_used=False,
    )
