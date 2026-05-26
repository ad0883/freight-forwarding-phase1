from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_roles
from app.models.document_intelligence import (
    DocumentExtraction,
    DocumentExtractedField,
    DocumentIntelligenceRun,
    DocumentIntelligenceSuggestion,
    DocumentMismatchResult,
)
from app.schemas.document_intelligence import (
    DocumentExtractedFieldRead,
    DocumentExtractionRead,
    DocumentIntelligenceActionRequest,
    DocumentIntelligenceDashboardSummary,
    DocumentIntelligenceRunRead,
    DocumentIntelligenceRunRequest,
    DocumentIntelligenceSuggestionRead,
    DocumentIntelligenceSummary,
    DocumentMismatchRead,
)
from app.services.document_intelligence import (
    get_document_intelligence_summary,
    run_document_intelligence,
)
from app.services.document_intelligence.suggestion_service import (
    apply_suggestion,
    approve_suggestion,
    dismiss_suggestion,
    reject_suggestion,
)


router = APIRouter(tags=["document-intelligence"])

OperationalUser = Depends(require_roles("ADMIN", "STAFF"))


@router.post("/document-intelligence/versions/{version_id}/run", response_model=DocumentIntelligenceSummary)
def run_intelligence(
    version_id: int,
    payload: DocumentIntelligenceRunRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> DocumentIntelligenceSummary:
    return run_document_intelligence(db, version_id, current_user, run_type=payload.run_type, request=request)


@router.get("/document-intelligence/versions/{version_id}/summary", response_model=DocumentIntelligenceSummary)
def version_summary(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DocumentIntelligenceSummary:
    return get_document_intelligence_summary(db, version_id, current_user)


@router.get("/document-intelligence/extractions", response_model=list[DocumentExtractionRead])
def list_extractions(
    shipment_id: Optional[int] = None,
    document_version_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[DocumentExtraction]:
    query = db.query(DocumentExtraction)
    if shipment_id is not None:
        query = query.filter(DocumentExtraction.shipment_id == shipment_id)
    if document_version_id is not None:
        query = query.filter(DocumentExtraction.document_version_id == document_version_id)
    if status:
        query = query.filter(DocumentExtraction.status == status)
    return query.order_by(DocumentExtraction.created_at.desc(), DocumentExtraction.id.desc()).limit(limit).offset(offset).all()


@router.get("/document-intelligence/extractions/{extraction_id}", response_model=DocumentExtractionRead)
def get_extraction(
    extraction_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> DocumentExtraction:
    return _get_extraction(db, extraction_id)


@router.get("/document-intelligence/extractions/{extraction_id}/fields", response_model=list[DocumentExtractedFieldRead])
def list_fields(
    extraction_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[DocumentExtractedField]:
    _get_extraction(db, extraction_id)
    return (
        db.query(DocumentExtractedField)
        .filter(DocumentExtractedField.extraction_id == extraction_id)
        .order_by(DocumentExtractedField.field_key.asc(), DocumentExtractedField.id.asc())
        .all()
    )


@router.get("/document-intelligence/extractions/{extraction_id}/mismatches", response_model=list[DocumentMismatchRead])
def list_extraction_mismatches(
    extraction_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[DocumentMismatchResult]:
    _get_extraction(db, extraction_id)
    return (
        db.query(DocumentMismatchResult)
        .filter(DocumentMismatchResult.extraction_id == extraction_id)
        .order_by(DocumentMismatchResult.severity.asc(), DocumentMismatchResult.id.desc())
        .all()
    )


@router.get("/document-intelligence/suggestions", response_model=list[DocumentIntelligenceSuggestionRead])
def list_suggestions(
    shipment_id: Optional[int] = None,
    status: Optional[str] = None,
    suggestion_type: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[DocumentIntelligenceSuggestion]:
    query = db.query(DocumentIntelligenceSuggestion)
    if shipment_id is not None:
        query = query.filter(DocumentIntelligenceSuggestion.shipment_id == shipment_id)
    if status:
        query = query.filter(DocumentIntelligenceSuggestion.status == status)
    if suggestion_type:
        query = query.filter(DocumentIntelligenceSuggestion.suggestion_type == suggestion_type)
    return query.order_by(DocumentIntelligenceSuggestion.created_at.desc(), DocumentIntelligenceSuggestion.id.desc()).limit(limit).offset(offset).all()


@router.patch("/document-intelligence/suggestions/{suggestion_id}/approve", response_model=DocumentIntelligenceSuggestionRead)
def approve_suggestion_route(
    suggestion_id: int,
    payload: DocumentIntelligenceActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> DocumentIntelligenceSuggestion:
    return approve_suggestion(db, suggestion_id, current_user, notes=payload.notes, request=request)


@router.patch("/document-intelligence/suggestions/{suggestion_id}/reject", response_model=DocumentIntelligenceSuggestionRead)
def reject_suggestion_route(
    suggestion_id: int,
    payload: DocumentIntelligenceActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> DocumentIntelligenceSuggestion:
    return reject_suggestion(db, suggestion_id, current_user, reason=payload.reason or payload.notes, request=request)


@router.patch("/document-intelligence/suggestions/{suggestion_id}/dismiss", response_model=DocumentIntelligenceSuggestionRead)
def dismiss_suggestion_route(
    suggestion_id: int,
    payload: DocumentIntelligenceActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> DocumentIntelligenceSuggestion:
    return dismiss_suggestion(db, suggestion_id, current_user, reason=payload.reason or payload.notes, request=request)


@router.post("/document-intelligence/suggestions/{suggestion_id}/apply", response_model=DocumentIntelligenceSuggestionRead)
def apply_suggestion_route(
    suggestion_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> DocumentIntelligenceSuggestion:
    return apply_suggestion(db, suggestion_id, current_user, request=request)


@router.get("/document-intelligence/runs", response_model=list[DocumentIntelligenceRunRead])
def list_runs(
    shipment_id: Optional[int] = None,
    document_version_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[DocumentIntelligenceRun]:
    query = db.query(DocumentIntelligenceRun)
    if shipment_id is not None:
        query = query.filter(DocumentIntelligenceRun.shipment_id == shipment_id)
    if document_version_id is not None:
        query = query.filter(DocumentIntelligenceRun.document_version_id == document_version_id)
    if status:
        query = query.filter(DocumentIntelligenceRun.status == status)
    return query.order_by(DocumentIntelligenceRun.started_at.desc(), DocumentIntelligenceRun.id.desc()).limit(limit).offset(offset).all()


@router.get("/document-intelligence/dashboard-summary", response_model=DocumentIntelligenceDashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> DocumentIntelligenceDashboardSummary:
    pending_suggestions = db.query(DocumentIntelligenceSuggestion).filter(DocumentIntelligenceSuggestion.status == "pending").count()
    critical_mismatches = (
        db.query(DocumentMismatchResult)
        .filter(DocumentMismatchResult.status == "open", DocumentMismatchResult.severity == "critical")
        .count()
    )
    low_confidence = (
        db.query(DocumentExtraction)
        .filter(DocumentExtraction.status.in_(["low_confidence", "manual_review_required"]))
        .count()
    )
    recent = (
        db.query(DocumentExtraction)
        .order_by(DocumentExtraction.created_at.desc(), DocumentExtraction.id.desc())
        .limit(5)
        .all()
    )
    critical_items = (
        db.query(DocumentMismatchResult)
        .filter(DocumentMismatchResult.status == "open", DocumentMismatchResult.severity == "critical")
        .order_by(DocumentMismatchResult.created_at.desc(), DocumentMismatchResult.id.desc())
        .limit(5)
        .all()
    )
    return DocumentIntelligenceDashboardSummary(
        pending_suggestions=pending_suggestions,
        critical_mismatches=critical_mismatches,
        low_confidence_extractions=low_confidence,
        manual_review_required=low_confidence + critical_mismatches,
        recent_extractions=recent,
        critical_items=critical_items,
    )


@router.get("/shipments/{shipment_id}/document-intelligence", response_model=list[DocumentExtractionRead])
def shipment_intelligence(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[DocumentExtraction]:
    return (
        db.query(DocumentExtraction)
        .filter(DocumentExtraction.shipment_id == shipment_id, DocumentExtraction.status != "superseded")
        .order_by(DocumentExtraction.created_at.desc(), DocumentExtraction.id.desc())
        .all()
    )


@router.get("/shipments/{shipment_id}/document-mismatches", response_model=list[DocumentMismatchRead])
def shipment_mismatches(
    shipment_id: int,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[DocumentMismatchResult]:
    query = db.query(DocumentMismatchResult).filter(DocumentMismatchResult.shipment_id == shipment_id)
    if status:
        query = query.filter(DocumentMismatchResult.status == status)
    if severity:
        query = query.filter(DocumentMismatchResult.severity == severity)
    if date_from:
        query = query.filter(DocumentMismatchResult.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(DocumentMismatchResult.created_at <= datetime.combine(date_to, time.max))
    return query.order_by(DocumentMismatchResult.created_at.desc(), DocumentMismatchResult.id.desc()).all()


def _get_extraction(db: Session, extraction_id: int) -> DocumentExtraction:
    extraction = db.query(DocumentExtraction).filter(DocumentExtraction.id == extraction_id).first()
    if not extraction:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document extraction not found")
    return extraction
