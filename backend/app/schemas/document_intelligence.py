from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


DocumentIntelligenceRunType = Literal["ocr", "classification", "extraction", "mismatch_validation", "full"]
DocumentIntelligenceRunStatus = Literal[
    "queued",
    "running",
    "completed",
    "failed",
    "unsupported",
    "manual_review_required",
]
DocumentExtractionStatus = Literal[
    "extracted",
    "low_confidence",
    "failed",
    "manual_review_required",
    "approved",
    "rejected",
    "superseded",
]
DocumentExtractedFieldStatus = Literal[
    "candidate",
    "matched",
    "mismatch",
    "low_confidence",
    "approved",
    "rejected",
    "ignored",
]
DocumentMismatchStatus = Literal["open", "acknowledged", "resolved", "dismissed", "approved_override"]
DocumentIntelligenceSuggestionStatus = Literal[
    "pending",
    "approved",
    "rejected",
    "applied",
    "dismissed",
    "superseded",
]


class DocumentIntelligenceRunRequest(BaseModel):
    run_type: DocumentIntelligenceRunType = "full"


class DocumentIntelligenceActionRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=1000)
    notes: Optional[str] = Field(default=None, max_length=1000)


class DocumentIntelligenceRunRead(BaseModel):
    id: int
    document_version_id: int
    document_file_id: int
    shipment_id: Optional[int] = None
    document_type: Optional[str] = None
    run_type: str
    status: str
    ocr_engine: Optional[str] = None
    classification_engine: Optional[str] = None
    extraction_engine: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    triggered_by_user_id: Optional[int] = None
    triggered_by_name: Optional[str] = None
    error_message: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentExtractedFieldRead(BaseModel):
    id: int
    extraction_id: int
    field_key: str
    field_value: str
    normalized_value: Optional[str] = None
    confidence: Optional[float] = None
    source_text: Optional[str] = None
    page_number: Optional[int] = None
    status: str
    created_at: datetime
    metadata_json: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentMismatchRead(BaseModel):
    id: int
    extraction_id: int
    document_version_id: int
    shipment_id: Optional[int] = None
    rule_key: str
    severity: str
    status: str
    field_key: Optional[str] = None
    system_value: Optional[str] = None
    extracted_value: Optional[str] = None
    message: str
    recommended_action: Optional[str] = None
    validation_issue_id: Optional[int] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    metadata_json: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentIntelligenceSuggestionRead(BaseModel):
    id: int
    extraction_id: int
    document_version_id: int
    shipment_id: Optional[int] = None
    suggestion_type: str
    target_entity_type: str
    target_entity_id: Optional[int] = None
    suggested_action: str
    confidence: Optional[float] = None
    status: str
    payload_json: Optional[dict[str, Any]] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by_user_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentExtractionRead(BaseModel):
    id: int
    run_id: Optional[int] = None
    document_version_id: int
    document_file_id: int
    shipment_id: Optional[int] = None
    document_type: str
    detected_document_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    ocr_text_preview: Optional[str] = None
    ocr_text_hash: Optional[str] = None
    ocr_char_count: Optional[int] = None
    ocr_page_count: Optional[int] = None
    overall_confidence: Optional[float] = None
    status: str
    created_at: datetime
    updated_at: datetime
    metadata_json: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentIntelligenceSummary(BaseModel):
    document_version_id: int
    latest_run: Optional[DocumentIntelligenceRunRead] = None
    latest_extraction: Optional[DocumentExtractionRead] = None
    fields: list[DocumentExtractedFieldRead] = Field(default_factory=list)
    mismatches: list[DocumentMismatchRead] = Field(default_factory=list)
    suggestions: list[DocumentIntelligenceSuggestionRead] = Field(default_factory=list)
    runs: list[DocumentIntelligenceRunRead] = Field(default_factory=list)


class DocumentIntelligenceDashboardSummary(BaseModel):
    pending_suggestions: int = 0
    critical_mismatches: int = 0
    low_confidence_extractions: int = 0
    manual_review_required: int = 0
    recent_extractions: list[DocumentExtractionRead] = Field(default_factory=list)
    critical_items: list[DocumentMismatchRead] = Field(default_factory=list)
