from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_roles, require_write_access
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.shipment import Shipment
from app.schemas.document_version import (
    DocumentDashboardSummary,
    DocumentLibraryItem,
    DocumentVersionActionRequest,
    DocumentVersionEventRead,
    DocumentVersionRead,
)
from app.services.document_storage_service import get_document_file_content, store_document_file
from app.services.document_version_service import (
    approve_document_version,
    archive_document_version,
    create_document_version,
    get_document_version,
    list_document_version_events,
    list_document_versions,
    log_document_download,
    reject_document_version,
    rollback_to_version,
)


router = APIRouter(tags=["document-versions"])


@router.get("/document-versions", response_model=list[DocumentVersionRead])
def list_versions_route(
    shipment_id: Optional[int] = None,
    document_id: Optional[int] = None,
    document_type: Optional[str] = None,
    review_status: Optional[str] = None,
    current_only: bool = False,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[DocumentVersion]:
    return list_document_versions(
        db,
        shipment_id=shipment_id,
        document_id=document_id,
        document_type=document_type,
        review_status=review_status,
        current_only=current_only,
        limit=limit,
        offset=offset,
    )


@router.post("/document-versions/upload", response_model=DocumentVersionRead)
def upload_version_route(
    request: Request,
    file: UploadFile = File(...),
    shipment_id: int = Form(...),
    document_id: Optional[int] = Form(default=None),
    document_type: Optional[str] = Form(default=None),
    version_label: Optional[str] = Form(default=None),
    notes: Optional[str] = Form(default=None),
    review_status: str = Form(default="pending_review"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> DocumentVersion:
    document_file = store_document_file(
        db,
        file,
        current_user,
        shipment_id=shipment_id,
        document_id=document_id,
        metadata={"source": "ui_upload"},
    )
    return create_document_version(
        db,
        shipment_id=shipment_id,
        document_file=document_file,
        document_id=document_id,
        document_type=document_type,
        version_label=version_label,
        notes=notes,
        review_status=review_status,
        user=current_user,
        metadata={"source": "ui_upload"},
        request=request,
    )


@router.get("/document-versions/dashboard-summary", response_model=DocumentDashboardSummary)
def document_dashboard_summary_route(
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> DocumentDashboardSummary:
    # Pending review: get count and top 5 in one pass
    pending_query = (
        db.query(DocumentVersion)
        .join(Shipment, Shipment.id == DocumentVersion.shipment_id)
        .filter(
            DocumentVersion.review_status == "pending_review",
            DocumentVersion.status == "active",
            DocumentVersion.is_current.is_(True),
            Shipment.is_archived.is_(False),
        )
    )
    pending_count = pending_query.count()
    pending = (
        pending_query
        .order_by(DocumentVersion.created_at.desc(), DocumentVersion.id.desc())
        .limit(5)
        .all()
    )

    # Recent uploads: top 5
    recent = (
        db.query(DocumentVersion)
        .join(Shipment, Shipment.id == DocumentVersion.shipment_id)
        .filter(Shipment.is_archived.is_(False))
        .order_by(DocumentVersion.created_at.desc(), DocumentVersion.id.desc())
        .limit(5)
        .all()
    )

    # Missing required: count and top 10
    missing_query = (
        db.query(Document)
        .join(Shipment, Shipment.id == Document.shipment_id)
        .filter(
            Document.is_required.is_(True),
            Document.current_version_id.is_(None),
            Shipment.is_archived.is_(False),
        )
    )
    missing_count = missing_query.count()
    missing_rows = (
        missing_query
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(10)
        .all()
    )
    missing = [
        {
            "document_id": row.id,
            "shipment_id": row.shipment_id,
            "document_type": row.doc_type,
            "status": row.status,
        }
        for row in missing_rows
    ]

    return DocumentDashboardSummary(
        pending_review_count=pending_count,
        missing_required_count=missing_count,
        recent_uploads=recent,
        pending_review=pending,
        missing_required=missing,
    )


@router.get("/document-versions/{version_id}", response_model=DocumentVersionRead)
def get_version_route(
    version_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> DocumentVersion:
    return get_document_version(db, version_id)


@router.get("/document-versions/{version_id}/download")
def download_version_route(
    version_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    version = get_document_version(db, version_id)
    content = get_document_file_content(db, version.document_file_id)
    log_document_download(db, version, current_user, request=request)
    filename = version.file.sanitized_filename if version.file else f"document-version-{version.id}"
    content_type = version.file.content_type if version.file else "application/octet-stream"
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
    )


@router.patch("/document-versions/{version_id}/approve", response_model=DocumentVersionRead)
def approve_version_route(
    version_id: int,
    payload: DocumentVersionActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> DocumentVersion:
    return approve_document_version(db, version_id, current_user, notes=payload.notes, request=request)


@router.patch("/document-versions/{version_id}/reject", response_model=DocumentVersionRead)
def reject_version_route(
    version_id: int,
    payload: DocumentVersionActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> DocumentVersion:
    return reject_document_version(db, version_id, current_user, notes=payload.notes, request=request)


@router.patch("/document-versions/{version_id}/archive", response_model=DocumentVersionRead)
def archive_version_route(
    version_id: int,
    payload: DocumentVersionActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> DocumentVersion:
    return archive_document_version(db, version_id, current_user, reason=payload.reason or payload.notes, request=request)


@router.post("/document-versions/{version_id}/rollback", response_model=DocumentVersionRead)
def rollback_version_route(
    version_id: int,
    payload: DocumentVersionActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> DocumentVersion:
    return rollback_to_version(db, version_id, current_user, reason=payload.reason or payload.notes, request=request)


@router.get("/document-versions/{version_id}/events", response_model=list[DocumentVersionEventRead])
def list_version_events_route(
    version_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list:
    return list_document_version_events(db, version_id)


@router.get("/shipments/{shipment_id}/document-versions", response_model=list[DocumentVersionRead])
def list_shipment_versions_route(
    shipment_id: int,
    document_id: Optional[int] = None,
    document_type: Optional[str] = None,
    review_status: Optional[str] = None,
    current_only: bool = False,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[DocumentVersion]:
    return list_document_versions(
        db,
        shipment_id=shipment_id,
        document_id=document_id,
        document_type=document_type,
        review_status=review_status,
        current_only=current_only,
    )


@router.post("/shipments/{shipment_id}/document-versions/upload", response_model=DocumentVersionRead)
def upload_shipment_version_route(
    shipment_id: int,
    request: Request,
    file: UploadFile = File(...),
    document_id: Optional[int] = Form(default=None),
    document_type: Optional[str] = Form(default=None),
    version_label: Optional[str] = Form(default=None),
    notes: Optional[str] = Form(default=None),
    review_status: str = Form(default="pending_review"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> DocumentVersion:
    document_file = store_document_file(
        db,
        file,
        current_user,
        shipment_id=shipment_id,
        document_id=document_id,
        metadata={"source": "ui_upload"},
    )
    return create_document_version(
        db,
        shipment_id=shipment_id,
        document_file=document_file,
        document_id=document_id,
        document_type=document_type,
        version_label=version_label,
        notes=notes,
        review_status=review_status,
        user=current_user,
        metadata={"source": "ui_upload"},
        request=request,
    )


@router.get("/shipments/{shipment_id}/document-library", response_model=list[DocumentLibraryItem])
def shipment_document_library_route(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[DocumentLibraryItem]:
    documents = (
        db.query(Document)
        .filter(Document.shipment_id == shipment_id)
        .order_by(Document.created_at.asc(), Document.id.asc())
        .all()
    )
    versions = list_document_versions(db, shipment_id=shipment_id, limit=200)
    versions_by_document: dict[Optional[int], list[DocumentVersion]] = {}
    for version in versions:
        versions_by_document.setdefault(version.document_id, []).append(version)

    items: list[DocumentLibraryItem] = []
    for document in documents:
        doc_versions = versions_by_document.pop(document.id, [])
        current = next(
            (
                version
                for version in doc_versions
                if version.is_current and version.status == "active"
            ),
            None,
        )
        items.append(
            DocumentLibraryItem(
                document_id=document.id,
                document_type=document.doc_type,
                required=document.is_required,
                current_version=current,
                versions=doc_versions,
            )
        )

    for doc_versions in versions_by_document.values():
        if not doc_versions:
            continue
        current = next(
            (
                version
                for version in doc_versions
                if version.is_current and version.status == "active"
            ),
            None,
        )
        items.append(
            DocumentLibraryItem(
                document_id=None,
                document_type=(current or doc_versions[0]).document_type,
                required=False,
                current_version=current,
                versions=doc_versions,
            )
        )
    return items
