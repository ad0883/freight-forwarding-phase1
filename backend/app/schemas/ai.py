from typing import Literal, Optional

from pydantic import BaseModel, Field


AIPriority = Literal["critical", "warning", "info", "none"]


class AIAskRequest(BaseModel):
    question: str = Field(min_length=1)
    shipment_id: Optional[int] = None
    shipment_code: Optional[str] = None


class AIDataPoint(BaseModel):
    label: str
    value: str


AISuggestedAction = str


class AIAskResponse(BaseModel):
    answer: str
    priority: AIPriority = "none"
    suggested_actions: list[AISuggestedAction] = Field(default_factory=list)
    data_points: list[AIDataPoint] = Field(default_factory=list)
    used_llm: bool = False
    provider: str = "fallback"
    model: Optional[str] = None
    fallback_used: bool = True


class AIExamplesResponse(BaseModel):
    examples: list[str]


class AIStatusResponse(BaseModel):
    ai_enabled: bool
    provider: str
    model: str
    fallback_available: bool = True
