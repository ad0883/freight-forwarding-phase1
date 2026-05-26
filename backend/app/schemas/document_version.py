from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


DocumentVersionStatus = Literal["active", "superseded", "rejected", "archived"]
DocumentReviewStatus = Literal["pending_review", "approved", "rejected", "not_required"]


class DocumentFileRead(BaseModel):
    id: int
    shipment_id: Optional[int] = None
    document_id: Optional[int] = None
    original_filename: str
    sanitized_filename: str
    content_type: str
    file_size: int
    sha256: str
    storage_backend: str
    status: str
    uploaded_by: Optional[int] = None
    uploaded_by_name: Optional[str] = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentVersionRead(BaseModel):
    id: int
    organization_id: Optional[int] = None
    shipment_id: int
    shipment_code: Optional[str] = None
    document_id: Optional[int] = None
    document_type: str
    document_file_id: int
    version_no: int
    version_label: Optional[str] = None
    status: DocumentVersionStatus
    review_status: DocumentReviewStatus
    is_current: bool
    replaces_version_id: Optional[int] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    reviewed_by: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    archived_by: Optional[int] = None
    archived_by_name: Optional[str] = None
    archived_at: Optional[datetime] = None
    archive_reason: Optional[str] = None
    notes: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    file: Optional[DocumentFileRead] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentVersionEventRead(BaseModel):
    id: int
    document_version_id: int
    shipment_id: int
    document_id: Optional[int] = None
    event_type: str
    actor_user_id: Optional[int] = None
    actor_name: Optional[str] = None
    notes: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentVersionActionRequest(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=1000)
    reason: Optional[str] = Field(default=None, max_length=1000)


class DocumentLibraryItem(BaseModel):
    document_id: Optional[int] = None
    document_type: str
    required: bool = False
    current_version: Optional[DocumentVersionRead] = None
    versions: list[DocumentVersionRead] = Field(default_factory=list)


class DocumentDashboardSummary(BaseModel):
    pending_review_count: int = 0
    missing_required_count: int = 0
    recent_uploads: list[DocumentVersionRead] = Field(default_factory=list)
    pending_review: list[DocumentVersionRead] = Field(default_factory=list)
    missing_required: list[dict[str, Any]] = Field(default_factory=list)
