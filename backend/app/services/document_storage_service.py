import hashlib
import os
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.core.config import settings
from app.models.document_version import DocumentFile, DocumentFileBlob


ALLOWED_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "application/csv",
    "text/plain",
}

BLOCKED_EXTENSIONS = {
    ".app",
    ".bat",
    ".bin",
    ".cmd",
    ".com",
    ".dll",
    ".dmg",
    ".exe",
    ".js",
    ".msi",
    ".ps1",
    ".scr",
    ".sh",
}


def validate_upload_file(file: UploadFile, content_bytes: Optional[bytes] = None) -> None:
    content_type = _normalized_content_type(file.content_type)
    if content_type not in ALLOWED_DOCUMENT_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported document type: {content_type or 'unknown'}",
        )
    filename = sanitize_filename(file.filename or "")
    extension = Path(filename).suffix.lower()
    if extension in BLOCKED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Executable uploads are not allowed",
        )
    if content_bytes is not None:
        max_bytes = settings.DOCUMENT_MAX_UPLOAD_MB * 1024 * 1024
        if len(content_bytes) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Document exceeds {settings.DOCUMENT_MAX_UPLOAD_MB} MB upload limit",
            )
        if len(content_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded document is empty")


def sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename or "").strip()
    if not base:
        return "document"
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", base)
    stem = re.sub(r"\s+", " ", stem).strip(" .")
    return (stem or "document")[:180]


def calculate_sha256(content_bytes: bytes) -> str:
    return hashlib.sha256(content_bytes).hexdigest()


def store_document_file(
    db: Session,
    file: UploadFile,
    user: AuthenticatedUser,
    shipment_id: Optional[int] = None,
    document_id: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> DocumentFile:
    content = file.file.read()
    validate_upload_file(file, content)
    content_type = _normalized_content_type(file.content_type)
    filename = sanitize_filename(file.filename or "document")
    checksum = calculate_sha256(content)
    backend = (settings.DOCUMENT_STORAGE_BACKEND or "database").strip().lower()
    if backend not in {"database", "local"}:
        raise HTTPException(status_code=500, detail="Unsupported document storage backend")

    record = DocumentFile(
        organization_id=user.organization_id,
        shipment_id=shipment_id,
        document_id=document_id,
        original_filename=(file.filename or filename)[:255],
        sanitized_filename=filename,
        content_type=content_type,
        file_size=len(content),
        sha256=checksum,
        storage_backend=backend,
        storage_key=None,
        uploaded_by=user.id,
        uploaded_by_name=user.name,
        metadata_json=_safe_metadata(metadata),
    )
    db.add(record)
    db.flush()

    if backend == "database":
        record.storage_key = f"document_file:{record.id}"
        db.add(DocumentFileBlob(document_file_id=record.id, content=content))
    else:
        storage_dir = _local_storage_dir()
        storage_dir.mkdir(parents=True, exist_ok=True)
        storage_name = f"{record.id}_{checksum[:16]}_{filename}"
        storage_path = storage_dir / storage_name
        storage_path.write_bytes(content)
        record.storage_key = str(storage_path)
    db.flush()
    return record


def get_document_file_content(db: Session, document_file_id: int) -> bytes:
    record = db.query(DocumentFile).filter(DocumentFile.id == document_file_id).first()
    if not record or record.status != "active":
        raise HTTPException(status_code=404, detail="Document file not found")
    if record.storage_backend == "database":
        if not record.blob:
            raise HTTPException(status_code=404, detail="Document file content not found")
        return bytes(record.blob.content)
    if record.storage_backend == "local":
        storage_key = record.storage_key or ""
        storage_path = Path(storage_key)
        if not storage_path.exists() or not storage_path.is_file():
            raise HTTPException(status_code=404, detail="Document file content not found")
        return storage_path.read_bytes()
    raise HTTPException(status_code=500, detail="Unsupported document storage backend")


def delete_or_archive_document_file(
    db: Session, document_file_id: int, user: AuthenticatedUser
) -> DocumentFile:
    record = db.query(DocumentFile).filter(DocumentFile.id == document_file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Document file not found")
    record.status = "archived"
    record.metadata_json = {
        **(record.metadata_json or {}),
        "archived_by": user.id,
        "archived_by_name": user.name,
    }
    db.flush()
    return record


def _normalized_content_type(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.split(";", 1)[0].strip().lower()


def _safe_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not metadata:
        return {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if key.lower() in {"content", "bytes", "body", "token", "secret"}:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
    return safe


def _local_storage_dir() -> Path:
    configured = Path(settings.DOCUMENT_LOCAL_STORAGE_DIR)
    if configured.is_absolute():
        return configured
    return Path.cwd() / configured
