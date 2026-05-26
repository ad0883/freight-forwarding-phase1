from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class DocumentIntelligenceRun(Base):
    __tablename__ = "document_intelligence_runs"

    id = Column(Integer, primary_key=True, index=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False, index=True)
    document_file_id = Column(Integer, ForeignKey("document_files.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    document_type = Column(String(80), nullable=True, index=True)
    run_type = Column(String(40), nullable=False, default="full", index=True)
    status = Column(String(40), nullable=False, default="queued", index=True)
    ocr_engine = Column(String(80), nullable=True)
    classification_engine = Column(String(80), nullable=True)
    extraction_engine = Column(String(80), nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    triggered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    triggered_by_name = Column(String(150), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    version = relationship("DocumentVersion")
    file = relationship("DocumentFile")
    extraction = relationship(
        "DocumentExtraction",
        back_populates="run",
        uselist=False,
    )


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("document_intelligence_runs.id"), nullable=True, index=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False, index=True)
    document_file_id = Column(Integer, ForeignKey("document_files.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    document_type = Column(String(80), nullable=False, index=True)
    detected_document_type = Column(String(80), nullable=True, index=True)
    classification_confidence = Column(Float, nullable=True)
    ocr_text_preview = Column(Text, nullable=True)
    ocr_text_hash = Column(String(64), nullable=True, index=True)
    ocr_char_count = Column(Integer, nullable=True)
    ocr_page_count = Column(Integer, nullable=True)
    overall_confidence = Column(Float, nullable=True, index=True)
    status = Column(String(40), nullable=False, default="extracted", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    run = relationship("DocumentIntelligenceRun", back_populates="extraction")
    version = relationship("DocumentVersion")
    file = relationship("DocumentFile")
    fields = relationship(
        "DocumentExtractedField",
        back_populates="extraction",
        cascade="all, delete-orphan",
    )
    mismatches = relationship(
        "DocumentMismatchResult",
        back_populates="extraction",
        cascade="all, delete-orphan",
    )
    suggestions = relationship(
        "DocumentIntelligenceSuggestion",
        back_populates="extraction",
        cascade="all, delete-orphan",
    )


class DocumentExtractedField(Base):
    __tablename__ = "document_extracted_fields"

    id = Column(Integer, primary_key=True, index=True)
    extraction_id = Column(Integer, ForeignKey("document_extractions.id"), nullable=False, index=True)
    field_key = Column(String(80), nullable=False, index=True)
    field_value = Column(Text, nullable=False)
    normalized_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True, index=True)
    source_text = Column(Text, nullable=True)
    page_number = Column(Integer, nullable=True)
    status = Column(String(40), nullable=False, default="candidate", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    metadata_json = Column(JSON, nullable=True)

    extraction = relationship("DocumentExtraction", back_populates="fields")


class DocumentMismatchResult(Base):
    __tablename__ = "document_mismatch_results"

    id = Column(Integer, primary_key=True, index=True)
    extraction_id = Column(Integer, ForeignKey("document_extractions.id"), nullable=False, index=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    rule_key = Column(String(120), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="warning", index=True)
    status = Column(String(40), nullable=False, default="open", index=True)
    field_key = Column(String(80), nullable=True, index=True)
    system_value = Column(Text, nullable=True)
    extracted_value = Column(Text, nullable=True)
    message = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=True)
    validation_issue_id = Column(Integer, ForeignKey("validation_issues.id"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    extraction = relationship("DocumentExtraction", back_populates="mismatches")
    validation_issue = relationship("ValidationIssue")


class DocumentIntelligenceSuggestion(Base):
    __tablename__ = "document_intelligence_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    extraction_id = Column(Integer, ForeignKey("document_extractions.id"), nullable=False, index=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    suggestion_type = Column(String(80), nullable=False, index=True)
    target_entity_type = Column(String(80), nullable=False, index=True)
    target_entity_id = Column(Integer, nullable=True, index=True)
    suggested_action = Column(String(120), nullable=False)
    confidence = Column(Float, nullable=True, index=True)
    status = Column(String(40), nullable=False, default="pending", index=True)
    payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    extraction = relationship("DocumentExtraction", back_populates="suggestions")
