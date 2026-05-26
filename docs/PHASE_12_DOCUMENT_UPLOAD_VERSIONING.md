# Phase 12 Document Upload Versioning

Phase 12 turns shipment documents from checklist/link rows into uploaded,
versioned operational records while preserving the existing checklist behavior.

## What Changed

- New upload/version API under `/api/document-versions`.
- Shipment-scoped API under `/api/shipments/{shipment_id}/document-versions`.
- New shipment document library endpoint:
  `/api/shipments/{shipment_id}/document-library`.
- Existing checklist endpoint `/api/documents/shipment/{shipment_id}` still works
  and now includes current version metadata.
- Dashboard includes a document review widget.
- Shipment detail Documents tab supports upload, download, review actions,
  version history, and event history.
- AI assistant can summarize document metadata only. It does not read file
  contents.

## Storage

Default storage is database-backed:

```txt
DOCUMENT_STORAGE_BACKEND=database
DOCUMENT_MAX_UPLOAD_MB=10
DOCUMENT_LOCAL_STORAGE_DIR=uploaded_documents
```

`DOCUMENT_STORAGE_BACKEND=local` is available for local development. Local
files are written under `DOCUMENT_LOCAL_STORAGE_DIR`, which is ignored by git.
Do not commit uploaded files.

Allowed MIME types:

- `application/pdf`
- `image/png`
- `image/jpeg`
- Microsoft Word and Excel formats
- `text/csv`
- `application/csv`
- `text/plain`

Executable extensions are blocked.

## Version Rules

- Every upload creates a new `document_versions` row.
- Previous current versions are preserved and marked `superseded`.
- A document can have one current version.
- Approval/rejection affects the version review status only.
- Archive and rollback are admin-only.
- Rejecting the current version clears the checklist's current version pointer;
  it does not mutate shipment data.

## Permissions

- `ADMIN`: upload, approve, reject, archive, rollback, download, list.
- `STAFF`: upload, approve, reject, download, list.
- `VIEW_ONLY`: download and list only.

## Audit, Events, Notifications

Phase 12 records:

- `document.version_uploaded`
- `document.version_approved`
- `document.version_rejected`
- `document.version_archived`
- `document.version_rollback`
- `document.file_downloaded`

Upload and review actions create audit logs. Uploads create deduped document
notifications for pending review and new versions. Rejections create a deduped
warning notification.

Duplicate file hashes within a shipment create non-blocking validation issues.

## Non-Goals

Phase 12 does not perform OCR, content extraction, classification, mismatch
validation, Gmail attachment ingestion, Google Drive upload, S3/R2 integration,
or autonomous AI writes. Uploaded files are stored and served, but their
contents are not interpreted.
