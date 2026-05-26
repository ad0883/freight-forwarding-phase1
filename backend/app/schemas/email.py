from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import (
    EmailClassification,
    EmailProcessedStatus,
    EmailSuggestionStatus,
    EmailSuggestionType,
)


class EmailConnectionStatus(BaseModel):
    connected: bool
    provider: str = "gmail"
    email_address: Optional[str] = None
    gmail_account_email: Optional[str] = None
    enabled: bool = False
    pending_suggestions: int = 0
    cached_messages: int = 0


class EmailOAuthStartResponse(BaseModel):
    auth_url: str


class EmailDebugConfigResponse(BaseModel):
    gmail_enabled: bool
    has_google_client_id: bool
    has_google_client_secret: bool
    google_redirect_uri: str
    frontend_base_url: str
    gmail_scopes: list[str]
    has_token_encryption_key: bool
    token_encryption_key_valid: bool


class EmailScanRequest(BaseModel):
    query: Optional[str] = None
    lookback_days: int = Field(default=30, ge=1, le=365)
    max_results: int = Field(default=20, ge=1, le=100)


class EmailScanResponse(BaseModel):
    scanned: int
    cached: int
    suggestions_created: int
    duplicates_skipped: int = 0


class EmailSuggestionRead(BaseModel):
    id: int
    email_message_id: int
    shipment_id: Optional[int] = None
    shipment_code: Optional[str] = None
    shipment_is_archived: bool = False
    shipment_archive_reason: Optional[str] = None
    suggestion_type: EmailSuggestionType
    classification: EmailClassification
    confidence: float
    extracted_data_json: dict[str, Any]
    status: EmailSuggestionStatus
    gmail_account_email: Optional[str] = None
    created_at: datetime


class EmailMessageRead(BaseModel):
    id: int
    connection_id: int
    gmail_message_id: str
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipients: Optional[str] = None
    snippet: Optional[str] = None
    body_preview: Optional[str] = None
    received_at: Optional[datetime] = None
    has_attachments: bool
    classification: EmailClassification
    matched_shipment_id: Optional[int] = None
    matched_shipment_code: Optional[str] = None
    processed_status: EmailProcessedStatus
    visibility: str = "visible"
    gmail_account_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    suggestions: list[EmailSuggestionRead] = Field(default_factory=list)


class EmailSuggestionUpdate(BaseModel):
    shipment_id: Optional[int] = None
    extracted_data_json: Optional[dict[str, Any]] = None


class EmailSuggestionApplyRequest(BaseModel):
    force: bool = False


class EmailSuggestionRejectRequest(BaseModel):
    reason: Optional[str] = None


class EmailApplyConflict(BaseModel):
    field: str
    existing_value: Optional[Any] = None
    suggested_value: Optional[Any] = None
    message: str


class EmailSuggestionApplyResponse(BaseModel):
    applied: bool
    suggestion: EmailSuggestionRead
    conflicts: list[EmailApplyConflict] = Field(default_factory=list)


class EmailDisconnectRequest(BaseModel):
    clear_cache: bool = False


class EmailDisconnectResponse(BaseModel):
    disconnected: bool
    suggestions_rejected: int = 0
    messages_hidden: int = 0


class EmailMessageListItem(BaseModel):
    id: int
    subject: Optional[str] = None
    sender: Optional[str] = None
    snippet: Optional[str] = None
    received_at: Optional[datetime] = None
    has_attachments: bool
    classification: EmailClassification
    matched_shipment_id: Optional[int] = None
    matched_shipment_code: Optional[str] = None
    processed_status: EmailProcessedStatus
    visibility: str = "visible"
    gmail_account_email: Optional[str] = None
    suggestion_count: int

    model_config = ConfigDict(from_attributes=True)


class EmailBulkRejectRequest(BaseModel):
    suggestion_ids: list[int] = Field(default_factory=list)


class EmailClearPendingRequest(BaseModel):
    current_account_only: bool = True
    low_confidence: bool = False
    no_shipment: bool = False
    older_than: Optional[datetime] = None
    suggestion_type: Optional[str] = None
    gmail_account_email: Optional[str] = None


class EmailClearPendingResponse(BaseModel):
    rejected: int


class EmailCleanupRequest(BaseModel):
    gmail_account_email: Optional[str] = None
    hide_messages: bool = True
    reject_pending: bool = True


class EmailCleanupResponse(BaseModel):
    suggestions_rejected: int
    messages_hidden: int
