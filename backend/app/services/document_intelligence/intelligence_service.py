import hashlib
import logging
from datetime import datetime
from statistics import mean
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import AuthenticatedUser
from app.core.config import settings
from app.models.document_intelligence import (
    DocumentExtractedField,
    DocumentExtraction,
    DocumentIntelligenceRun,
    DocumentIntelligenceSuggestion,
    DocumentMismatchResult,
)
from app.models.document_version import DocumentVersion
from app.schemas.document_intelligence import (
    DocumentIntelligenceSummary,
)
from app.services.audit_service import record_audit_log
from app.services.document_intelligence.document_classifier import classify_document_text
from app.services.document_intelligence.extraction_service import extract_fields
from app.services.document_intelligence.mismatch_service import compare_extraction_to_system
from app.services.document_intelligence.ocr_service import extract_text_from_document_file
from app.services.document_intelligence.suggestion_service import create_suggestions_from_extraction
from app.services.event_service import OperationalEventType, record_operational_event


logger = logging.getLogger(__name__)


def run_document_intelligence(
    db: Session,
    document_version_id: int,
    user: AuthenticatedUser,
    *,
    run_type: str = "full",
    request=None,
) -> DocumentIntelligenceSummary:
    version = _get_version(db, document_version_id)
    run = DocumentIntelligenceRun(
        document_version_id=version.id,
        document_file_id=version.document_file_id,
        shipment_id=version.shipment_id,
        document_type=version.document_type,
        run_type=run_type,
        status="running",
        started_at=datetime.utcnow(),
        triggered_by_user_id=user.id,
        triggered_by_name=user.name,
        metadata_json={"source": "manual"},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    record_operational_event(
        db,
        OperationalEventType.DOCUMENT_INTELLIGENCE_RUN_STARTED.value,
        "document_intelligence_run",
        entity_id=run.id,
        entity_label=f"{version.document_type} v{version.version_no}",
        shipment_id=version.shipment_id,
        actor_user=user,
        source="user",
        metadata={"document_version_id": version.id, "run_type": run_type},
        request=request,
        run_validation=False,
    )

    try:
        ocr = extract_text_from_document_file(db, version.file)
        run.ocr_engine = ocr.engine
        if ocr.status != "completed":
            run.status = "unsupported" if ocr.status == "unsupported" else "failed"
            run.error_message = ocr.error_message
            run.completed_at = datetime.utcnow()
            db.commit()
            _audit_run(db, run, user, request)
            _record_run_finished_event(db, run, user, success=False, request=request)
            return get_document_intelligence_summary(db, version.id, user)

        classification = classify_document_text(
            ocr.text,
            filename=version.file.sanitized_filename if version.file else None,
            declared_document_type=version.document_type,
        )
        run.classification_engine = classification.engine
        run.extraction_engine = "deterministic-regex-v1"
        _supersede_previous_extractions(db, version.id)
        candidates = extract_fields(classification.detected_document_type, ocr.text)
        field_confidences = [candidate.confidence for candidate in candidates] or [classification.confidence]
        overall_confidence = min(classification.confidence, mean(field_confidences))
        extraction_status = _extraction_status(overall_confidence)
        extraction = DocumentExtraction(
            run_id=run.id,
            document_version_id=version.id,
            document_file_id=version.document_file_id,
            shipment_id=version.shipment_id,
            document_type=version.document_type,
            detected_document_type=classification.detected_document_type,
            classification_confidence=classification.confidence,
            ocr_text_preview=_preview(ocr.text),
            ocr_text_hash=hashlib.sha256(ocr.text.encode("utf-8")).hexdigest(),
            ocr_char_count=ocr.char_count,
            ocr_page_count=ocr.page_count,
            overall_confidence=round(float(overall_confidence), 4),
            status=extraction_status,
            metadata_json={
                "ocr_status": ocr.status,
                "matched_keywords": classification.matched_keywords or [],
            },
        )
        db.add(extraction)
        db.flush()
        for candidate in candidates:
            db.add(
                DocumentExtractedField(
                    extraction_id=extraction.id,
                    field_key=candidate.field_key,
                    field_value=candidate.field_value[:1000],
                    normalized_value=(candidate.normalized_value or None),
                    confidence=candidate.confidence,
                    source_text=(candidate.source_text or "")[:500] or None,
                    page_number=candidate.page_number,
                    status=candidate.status,
                    metadata_json=candidate.metadata or None,
                )
            )
        db.flush()
        db.refresh(extraction)
        mismatches = compare_extraction_to_system(db, extraction)
        _mark_mismatch_fields(extraction, mismatches)
        suggestions = create_suggestions_from_extraction(db, extraction)
        run.status = "manual_review_required" if extraction.status in {"low_confidence", "manual_review_required"} or mismatches else "completed"
        run.completed_at = datetime.utcnow()
        run.metadata_json = {
            **(run.metadata_json or {}),
            "mismatch_count": len(mismatches),
            "suggestion_count": len(suggestions),
            "field_count": len(candidates),
        }
        db.commit()
        db.refresh(run)
        _audit_run(db, run, user, request)
        _record_run_finished_event(db, run, user, success=True, request=request)
        for mismatch in mismatches:
            record_operational_event(
                db,
                OperationalEventType.DOCUMENT_INTELLIGENCE_MISMATCH_FOUND.value,
                "document_mismatch",
                entity_id=mismatch.id,
                entity_label=mismatch.rule_key,
                shipment_id=mismatch.shipment_id,
                actor_user=user,
                source="system",
                new_state={"severity": mismatch.severity, "status": mismatch.status},
                metadata={"document_version_id": mismatch.document_version_id, "field_key": mismatch.field_key},
                request=request,
                run_validation=False,
            )
        return get_document_intelligence_summary(db, version.id, user)
    except Exception as exc:
        logger.exception("Document intelligence run failed version_id=%s", document_version_id)
        db.rollback()
        run = db.query(DocumentIntelligenceRun).filter(DocumentIntelligenceRun.id == run.id).first()
        if run:
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.utcnow()
            db.commit()
            _audit_run(db, run, user, request)
            _record_run_finished_event(db, run, user, success=False, request=request)
        return get_document_intelligence_summary(db, document_version_id, user)


def get_document_intelligence_summary(
    db: Session,
    document_version_id: int,
    user: Optional[AuthenticatedUser] = None,
) -> DocumentIntelligenceSummary:
    _get_version(db, document_version_id)
    runs = (
        db.query(DocumentIntelligenceRun)
        .filter(DocumentIntelligenceRun.document_version_id == document_version_id)
        .order_by(DocumentIntelligenceRun.started_at.desc(), DocumentIntelligenceRun.id.desc())
        .limit(20)
        .all()
    )
    extraction = (
        db.query(DocumentExtraction)
        .options(
            joinedload(DocumentExtraction.fields),
            joinedload(DocumentExtraction.mismatches),
            joinedload(DocumentExtraction.suggestions),
        )
        .filter(
            DocumentExtraction.document_version_id == document_version_id,
            DocumentExtraction.status != "superseded",
        )
        .order_by(DocumentExtraction.created_at.desc(), DocumentExtraction.id.desc())
        .first()
    )
    return DocumentIntelligenceSummary(
        document_version_id=document_version_id,
        latest_run=runs[0] if runs else None,
        latest_extraction=extraction,
        fields=extraction.fields if extraction else [],
        mismatches=extraction.mismatches if extraction else [],
        suggestions=extraction.suggestions if extraction else [],
        runs=runs,
    )


def _get_version(db: Session, version_id: int) -> DocumentVersion:
    version = (
        db.query(DocumentVersion)
        .options(joinedload(DocumentVersion.file))
        .filter(DocumentVersion.id == version_id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document version not found")
    if not version.file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found")
    return version


def _supersede_previous_extractions(db: Session, version_id: int) -> None:
    (
        db.query(DocumentExtraction)
        .filter(DocumentExtraction.document_version_id == version_id, DocumentExtraction.status != "superseded")
        .update({"status": "superseded"}, synchronize_session=False)
    )
    (
        db.query(DocumentIntelligenceSuggestion)
        .filter(DocumentIntelligenceSuggestion.document_version_id == version_id, DocumentIntelligenceSuggestion.status == "pending")
        .update({"status": "superseded"}, synchronize_session=False)
    )


def _extraction_status(confidence: float) -> str:
    if confidence < settings.DOCUMENT_LOW_CONFIDENCE_THRESHOLD:
        return "manual_review_required"
    if confidence < settings.DOCUMENT_EXTRACTION_CONFIDENCE_THRESHOLD:
        return "low_confidence"
    return "extracted"


def _preview(text: str) -> str:
    return " ".join((text or "").split())[:1200]


def _mark_mismatch_fields(
    extraction: DocumentExtraction,
    mismatches: list[DocumentMismatchResult],
) -> None:
    mismatched_keys = {mismatch.field_key for mismatch in mismatches if mismatch.field_key}
    for field in extraction.fields:
        if field.status == "low_confidence":
            continue
        field.status = "mismatch" if field.field_key in mismatched_keys else "matched"


def _audit_run(db: Session, run: DocumentIntelligenceRun, user: AuthenticatedUser, request) -> None:
    record_audit_log(
        db,
        user,
        "document_intelligence.run",
        "document_intelligence_run",
        entity_id=run.id,
        entity_label=run.document_type,
        description="Document intelligence run completed.",
        metadata={
            "document_version_id": run.document_version_id,
            "shipment_id": run.shipment_id,
            "status": run.status,
            "run_type": run.run_type,
        },
        request=request,
    )


def _record_run_finished_event(
    db: Session,
    run: DocumentIntelligenceRun,
    user: AuthenticatedUser,
    *,
    success: bool,
    request,
) -> None:
    event_type = (
        OperationalEventType.DOCUMENT_INTELLIGENCE_RUN_COMPLETED.value
        if success
        else OperationalEventType.DOCUMENT_INTELLIGENCE_RUN_FAILED.value
    )
    record_operational_event(
        db,
        event_type,
        "document_intelligence_run",
        entity_id=run.id,
        entity_label=run.document_type,
        shipment_id=run.shipment_id,
        actor_user=user,
        source="system",
        new_state={"status": run.status},
        metadata={
            "document_version_id": run.document_version_id,
            "run_type": run.run_type,
            "ocr_engine": run.ocr_engine,
        },
        request=request,
        run_validation=False,
    )
