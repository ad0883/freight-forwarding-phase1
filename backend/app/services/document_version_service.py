from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import AuthenticatedUser
from app.models.document import Document
from app.models.document_version import (
    DocumentAccessLog,
    DocumentFile,
    DocumentVersion,
    DocumentVersionEvent,
)
from app.models.notification import Notification
from app.models.shipment import Shipment
from app.models.validation_issue import ValidationIssue
from app.services.audit_service import record_audit_log
from app.services.event_service import OperationalEventType, record_operational_event
from app.services.notification_service import create_notification


REVIEW_STATUSES = {"pending_review", "approved", "rejected", "not_required"}


def list_document_versions(
    db: Session,
    *,
    shipment_id: Optional[int] = None,
    document_id: Optional[int] = None,
    document_type: Optional[str] = None,
    review_status: Optional[str] = None,
    current_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[DocumentVersion]:
    query = _version_query(db)
    if shipment_id is not None:
        query = query.filter(DocumentVersion.shipment_id == shipment_id)
    if document_id is not None:
        query = query.filter(DocumentVersion.document_id == document_id)
    if document_type:
        query = query.filter(DocumentVersion.document_type == document_type)
    if review_status:
        query = query.filter(DocumentVersion.review_status == review_status)
    if current_only:
        query = query.filter(DocumentVersion.is_current.is_(True))
    return (
        query.order_by(DocumentVersion.created_at.desc(), DocumentVersion.id.desc())
        .limit(min(max(limit, 1), 200))
        .offset(max(offset, 0))
        .all()
    )


def get_document_version(db: Session, version_id: int) -> DocumentVersion:
    version = _version_query(db).filter(DocumentVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Document version not found")
    return version


def create_document_version(
    db: Session,
    *,
    shipment_id: int,
    document_file: DocumentFile,
    user: AuthenticatedUser,
    document_id: Optional[int] = None,
    document_type: Optional[str] = None,
    version_label: Optional[str] = None,
    notes: Optional[str] = None,
    review_status: str = "pending_review",
    metadata: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> DocumentVersion:
    shipment = _get_shipment(db, shipment_id)
    document = _get_document(db, document_id, shipment_id) if document_id is not None else None
    resolved_type = (document.doc_type if document else document_type or "").strip()
    if not resolved_type:
        raise HTTPException(status_code=400, detail="Document type is required")
    if review_status not in REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid document review status")

    previous_current = _current_version(db, shipment_id, document.id if document else None, resolved_type)
    next_version_no = _next_version_no(db, shipment_id, document.id if document else None, resolved_type)

    if previous_current:
        previous_current.is_current = False
        if previous_current.status == "active":
            previous_current.status = "superseded"
        _record_version_event(
            db,
            previous_current,
            "document.version_superseded",
            user,
            notes="Superseded by a newer upload.",
            metadata={"superseded_by_version_no": next_version_no},
        )
        _expire_document_version_notifications(db, previous_current)

    version = DocumentVersion(
        organization_id=user.organization_id,
        shipment_id=shipment.id,
        document_id=document.id if document else None,
        document_type=resolved_type,
        document_file_id=document_file.id,
        version_no=next_version_no,
        version_label=(version_label or "").strip()[:120] or None,
        status="active",
        review_status=review_status,
        is_current=True,
        replaces_version_id=previous_current.id if previous_current else None,
        created_by=user.id,
        created_by_name=user.name,
        notes=(notes or "").strip() or None,
        metadata_json=_safe_metadata(metadata),
    )
    document_file.shipment_id = shipment.id
    document_file.document_id = document.id if document else None
    db.add(version)
    db.flush()

    if document:
        document.current_version_id = version.id
        document.uploaded_file_count = int(document.uploaded_file_count or 0) + 1
        document.latest_uploaded_at = version.created_at

    _record_version_event(
        db,
        version,
        OperationalEventType.DOCUMENT_VERSION_UPLOADED.value,
        user,
        notes=notes,
        metadata={"filename": document_file.sanitized_filename, "sha256": document_file.sha256},
    )
    _create_duplicate_hash_warning(db, version, document_file)
    _create_upload_notifications(db, shipment, version)
    db.commit()
    db.refresh(version)

    _audit_and_operational_event(
        db,
        version,
        user,
        action="document.version_upload",
        event_type=OperationalEventType.DOCUMENT_VERSION_UPLOADED.value,
        description="Document version uploaded.",
        request=request,
        metadata={
            "document_type": version.document_type,
            "version_no": version.version_no,
            "review_status": version.review_status,
            "filename": document_file.sanitized_filename,
            "file_size": document_file.file_size,
        },
    )
    return get_document_version(db, version.id)


def approve_document_version(
    db: Session,
    version_id: int,
    user: AuthenticatedUser,
    *,
    notes: Optional[str] = None,
    request: Optional[Request] = None,
) -> DocumentVersion:
    version = get_document_version(db, version_id)
    version.review_status = "approved"
    version.reviewed_by = user.id
    version.reviewed_by_name = user.name
    version.reviewed_at = datetime.utcnow()
    version.review_notes = notes or version.review_notes
    _record_version_event(db, version, OperationalEventType.DOCUMENT_VERSION_APPROVED.value, user, notes=notes)
    _expire_document_version_notifications(db, version, pending_only=True)
    db.commit()
    db.refresh(version)
    _audit_and_operational_event(
        db,
        version,
        user,
        action="document.version_approve",
        event_type=OperationalEventType.DOCUMENT_VERSION_APPROVED.value,
        description="Document version approved.",
        request=request,
        metadata={"review_status": version.review_status, "version_no": version.version_no},
    )
    return version


def reject_document_version(
    db: Session,
    version_id: int,
    user: AuthenticatedUser,
    *,
    notes: Optional[str] = None,
    request: Optional[Request] = None,
) -> DocumentVersion:
    version = get_document_version(db, version_id)
    version.review_status = "rejected"
    version.status = "rejected"
    version.reviewed_by = user.id
    version.reviewed_by_name = user.name
    version.reviewed_at = datetime.utcnow()
    version.review_notes = notes or version.review_notes
    if version.is_current:
        version.is_current = False
        _clear_current_document_version(db, version)
    _record_version_event(db, version, OperationalEventType.DOCUMENT_VERSION_REJECTED.value, user, notes=notes)
    _expire_document_version_notifications(db, version, pending_only=True)
    _create_rejection_notification(db, version)
    db.commit()
    db.refresh(version)
    _audit_and_operational_event(
        db,
        version,
        user,
        action="document.version_reject",
        event_type=OperationalEventType.DOCUMENT_VERSION_REJECTED.value,
        description="Document version rejected.",
        request=request,
        metadata={"review_status": version.review_status, "version_no": version.version_no},
    )
    return version


def archive_document_version(
    db: Session,
    version_id: int,
    user: AuthenticatedUser,
    *,
    reason: Optional[str] = None,
    request: Optional[Request] = None,
) -> DocumentVersion:
    version = get_document_version(db, version_id)
    version.status = "archived"
    version.is_current = False
    version.archived_by = user.id
    version.archived_by_name = user.name
    version.archived_at = datetime.utcnow()
    version.archive_reason = reason or version.archive_reason
    _clear_current_document_version(db, version)
    _expire_document_version_notifications(db, version)
    _record_version_event(
        db,
        version,
        OperationalEventType.DOCUMENT_VERSION_ARCHIVED.value,
        user,
        notes=reason,
    )
    db.commit()
    db.refresh(version)
    _audit_and_operational_event(
        db,
        version,
        user,
        action="document.version_archive",
        event_type=OperationalEventType.DOCUMENT_VERSION_ARCHIVED.value,
        description="Document version archived.",
        request=request,
        metadata={"reason": reason, "version_no": version.version_no},
    )
    return version


def rollback_to_version(
    db: Session,
    version_id: int,
    user: AuthenticatedUser,
    *,
    reason: Optional[str] = None,
    request: Optional[Request] = None,
) -> DocumentVersion:
    target = get_document_version(db, version_id)
    if target.status in {"archived", "rejected"}:
        raise HTTPException(status_code=400, detail="Cannot roll back to archived or rejected document versions")
    current = _current_version(db, target.shipment_id, target.document_id, target.document_type)
    if current and current.id != target.id:
        current.is_current = False
        if current.status == "active":
            current.status = "superseded"
    target.is_current = True
    target.status = "active"
    if target.document:
        target.document.current_version_id = target.id
        target.document.latest_uploaded_at = target.created_at
    _record_version_event(
        db,
        target,
        OperationalEventType.DOCUMENT_VERSION_ROLLBACK.value,
        user,
        notes=reason,
        metadata={"previous_current_version_id": current.id if current else None},
    )
    db.commit()
    db.refresh(target)
    _audit_and_operational_event(
        db,
        target,
        user,
        action="document.version_rollback",
        event_type=OperationalEventType.DOCUMENT_VERSION_ROLLBACK.value,
        description="Document version restored as current.",
        request=request,
        metadata={"reason": reason, "version_no": target.version_no},
    )
    return target


def list_document_version_events(db: Session, version_id: int) -> list[DocumentVersionEvent]:
    get_document_version(db, version_id)
    return (
        db.query(DocumentVersionEvent)
        .filter(DocumentVersionEvent.document_version_id == version_id)
        .order_by(DocumentVersionEvent.created_at.desc(), DocumentVersionEvent.id.desc())
        .all()
    )


def log_document_download(
    db: Session,
    version: DocumentVersion,
    user: AuthenticatedUser,
    *,
    request: Optional[Request] = None,
) -> None:
    db.add(
        DocumentAccessLog(
            document_file_id=version.document_file_id,
            document_version_id=version.id,
            shipment_id=version.shipment_id,
            actor_user_id=user.id,
            actor_name=user.name,
            action="download",
        )
    )
    _record_version_event(
        db,
        version,
        OperationalEventType.DOCUMENT_FILE_DOWNLOADED.value,
        user,
        metadata={"filename": version.file.sanitized_filename if version.file else None},
    )
    db.commit()
    record_operational_event(
        db,
        OperationalEventType.DOCUMENT_FILE_DOWNLOADED.value,
        "document_version",
        entity_id=version.id,
        entity_label=_version_label(version),
        shipment_id=version.shipment_id,
        actor_user=user,
        source="user",
        metadata={"document_type": version.document_type, "version_no": version.version_no},
        request=request,
        run_validation=False,
    )


def _version_query(db: Session):
    return db.query(DocumentVersion).options(
        joinedload(DocumentVersion.file),
        joinedload(DocumentVersion.shipment),
        joinedload(DocumentVersion.document),
    )


def _get_shipment(db: Session, shipment_id: int) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


def _get_document(db: Session, document_id: int, shipment_id: int) -> Document:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.shipment_id != shipment_id:
        raise HTTPException(status_code=400, detail="Document does not belong to shipment")
    return document


def _current_version(
    db: Session,
    shipment_id: int,
    document_id: Optional[int],
    document_type: str,
) -> Optional[DocumentVersion]:
    query = (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.shipment_id == shipment_id,
            DocumentVersion.document_type == document_type,
            DocumentVersion.is_current.is_(True),
        )
    )
    if document_id is None:
        query = query.filter(DocumentVersion.document_id.is_(None))
    else:
        query = query.filter(DocumentVersion.document_id == document_id)
    return query.order_by(DocumentVersion.version_no.desc(), DocumentVersion.id.desc()).first()


def _next_version_no(
    db: Session,
    shipment_id: int,
    document_id: Optional[int],
    document_type: str,
) -> int:
    query = db.query(func.max(DocumentVersion.version_no)).filter(
        DocumentVersion.shipment_id == shipment_id,
        DocumentVersion.document_type == document_type,
    )
    if document_id is None:
        query = query.filter(DocumentVersion.document_id.is_(None))
    else:
        query = query.filter(DocumentVersion.document_id == document_id)
    return int(query.scalar() or 0) + 1


def _record_version_event(
    db: Session,
    version: DocumentVersion,
    event_type: str,
    user: AuthenticatedUser,
    *,
    notes: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> DocumentVersionEvent:
    event = DocumentVersionEvent(
        document_version_id=version.id,
        shipment_id=version.shipment_id,
        document_id=version.document_id,
        event_type=event_type,
        actor_user_id=user.id,
        actor_name=user.name,
        notes=notes,
        metadata_json=_safe_metadata(metadata),
    )
    db.add(event)
    db.flush()
    return event


def _clear_current_document_version(db: Session, version: DocumentVersion) -> None:
    if version.document and version.document.current_version_id == version.id:
        version.document.current_version_id = None
        db.flush()


def _create_duplicate_hash_warning(db: Session, version: DocumentVersion, file: DocumentFile) -> None:
    duplicate = (
        db.query(DocumentFile.id)
        .filter(
            DocumentFile.id != file.id,
            DocumentFile.sha256 == file.sha256,
            DocumentFile.shipment_id == version.shipment_id,
            DocumentFile.status == "active",
        )
        .first()
    )
    if not duplicate:
        return
    db.add(
        ValidationIssue(
            rule_key="document_duplicate_file_hash_warning",
            entity_type="document_version",
            entity_id=version.id,
            entity_label=_version_label(version),
            shipment_id=version.shipment_id,
            severity="warning",
            status="open",
            message="Uploaded document content matches another file already stored for this shipment.",
            recommended_action="Confirm whether this was intentional before approval.",
            metadata_json={
                "document_type": version.document_type,
                "version_no": version.version_no,
                "duplicate_file_id": duplicate[0],
                "sha256": file.sha256,
            },
        )
    )


def _create_upload_notifications(db: Session, shipment: Shipment, version: DocumentVersion) -> None:
    if version.review_status == "pending_review":
        create_notification(
            db,
            title="Document pending review",
            message=f"{version.document_type} v{version.version_no} is pending review for {shipment.shipment_code}.",
            category="document",
            priority="info",
            target_role="STAFF",
            entity_type="document_version",
            entity_id=version.id,
            entity_label=_version_label(version),
            action_url=f"/shipments/{shipment.id}",
            dedupe_key=f"document_pending_review:{version.id}",
            source="workflow",
            metadata={"shipment_id": shipment.id, "document_type": version.document_type},
        )
    create_notification(
        db,
        title="New document version uploaded",
        message=f"{shipment.shipment_code}: {version.document_type} v{version.version_no} was uploaded.",
        category="document",
        priority="info",
        target_role="STAFF",
        entity_type="document_version",
        entity_id=version.id,
        entity_label=_version_label(version),
        action_url=f"/shipments/{shipment.id}",
        dedupe_key=f"document_new_version:{shipment.id}:{version.document_type}:{version.version_no}",
        source="workflow",
        metadata={"shipment_id": shipment.id, "document_type": version.document_type},
    )


def _expire_document_version_notifications(
    db: Session, version: DocumentVersion, *, pending_only: bool = False
) -> None:
    dedupe_keys = [f"document_pending_review:{version.id}"]
    if not pending_only:
        dedupe_keys.append(
            f"document_new_version:{version.shipment_id}:{version.document_type}:{version.version_no}"
        )
    now = datetime.utcnow()
    (
        db.query(Notification)
        .filter(Notification.dedupe_key.in_(dedupe_keys))
        .update({"expires_at": now}, synchronize_session=False)
    )


def _create_rejection_notification(db: Session, version: DocumentVersion) -> None:
    create_notification(
        db,
        title="Document version rejected",
        message=f"{version.document_type} v{version.version_no} was rejected.",
        category="document",
        priority="warning",
        target_role="STAFF",
        entity_type="document_version",
        entity_id=version.id,
        entity_label=_version_label(version),
        action_url=f"/shipments/{version.shipment_id}",
        dedupe_key=f"document_rejected:{version.id}",
        source="workflow",
        metadata={"shipment_id": version.shipment_id, "document_type": version.document_type},
    )


def _audit_and_operational_event(
    db: Session,
    version: DocumentVersion,
    user: AuthenticatedUser,
    *,
    action: str,
    event_type: str,
    description: str,
    request: Optional[Request],
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    safe_metadata = _safe_metadata(metadata)
    record_audit_log(
        db,
        user,
        action,
        "document_version",
        entity_id=version.id,
        entity_label=_version_label(version),
        description=description,
        metadata={**safe_metadata, "shipment_id": version.shipment_id},
        request=request,
    )
    record_operational_event(
        db,
        event_type,
        "document_version",
        entity_id=version.id,
        entity_label=_version_label(version),
        shipment_id=version.shipment_id,
        actor_user=user,
        source="user",
        new_state={
            "document_type": version.document_type,
            "version_no": version.version_no,
            "status": version.status,
            "review_status": version.review_status,
            "is_current": version.is_current,
        },
        metadata=safe_metadata,
        request=request,
        run_validation=False,
    )


def _version_label(version: DocumentVersion) -> str:
    return f"{version.document_type} v{version.version_no}"


def _safe_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not metadata:
        return {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        lowered = key.lower()
        if lowered in {"content", "bytes", "body", "token", "secret", "storage_key"}:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
    return safe
