# Phase 13 Document Intelligence OCR Mismatch Validation

Phase 13 adds a controlled document intelligence layer for uploaded document
versions. It reads supported documents, stores extracted metadata separately
from operational records, highlights mismatches, and creates review-only
suggestions.

## Architecture

- `document_intelligence_runs` records every manual OCR/classification run.
- `document_extractions` stores OCR preview, text hash, detected type, and
  confidence.
- `document_extracted_fields` stores candidate extracted fields.
- `document_mismatch_results` stores comparisons against system records.
- `document_intelligence_suggestions` stores review-only suggestions.

The orchestration entry point is:

```txt
app.services.document_intelligence.intelligence_service.run_document_intelligence
```

## OCR Strategy

Supported by default:

- Text-based PDF extraction through `pypdf`.
- TXT/CSV text decoding.

Unsupported or failed OCR creates a visible run status and does not affect
document upload/download. Image OCR is behind `DOCUMENT_OCR_IMAGE_ENABLED=false`
and is not required for normal deployment.

## Classification

The deterministic classifier uses declared document type, filename hints, and
keywords. It detects BL, invoice, packing list, delivery order, freight invoice,
pre-alert, arrival notice, BOE, COO, and related document families. Declared
document type is treated as a strong hint, not an absolute truth.

## Extraction Fields

Phase 13 extracts candidate values only:

- shipment code
- BL number
- invoice number and date
- amount and currency
- container number
- vessel and voyage
- origin and destination port
- shipper and consignee
- weights, package count, free days, arrival date

Token-like values, invalid container numbers, unrealistic amounts, impossible
dates, and noisy ports are downgraded or rejected.

## Mismatch Rules

Initial mismatch checks include:

- extracted shipment code not found
- extracted shipment code belongs to another shipment
- detected document type differs from declared upload type
- BL number differs from shipment BL number
- invoice amount does not match active non-cancelled charges
- container number is invalid or not linked to the shipment
- origin/destination port differs from shipment data
- low-confidence extraction requires review

Critical and warning mismatches create Phase 9 validation issues and internal
notifications. Cancelled charges remain excluded from financial comparisons.

## Suggestion Lifecycle

Suggestions may be listed, approved, rejected, or dismissed. Applying
suggestions to operational records is intentionally disabled in Phase 13.
This keeps OCR output review-only until a later approval workflow is built.

## APIs

```txt
POST /api/document-intelligence/versions/{version_id}/run
GET /api/document-intelligence/versions/{version_id}/summary
GET /api/document-intelligence/extractions
GET /api/document-intelligence/extractions/{extraction_id}
GET /api/document-intelligence/extractions/{extraction_id}/fields
GET /api/document-intelligence/extractions/{extraction_id}/mismatches
GET /api/document-intelligence/suggestions
PATCH /api/document-intelligence/suggestions/{suggestion_id}/approve
PATCH /api/document-intelligence/suggestions/{suggestion_id}/reject
PATCH /api/document-intelligence/suggestions/{suggestion_id}/dismiss
POST /api/document-intelligence/suggestions/{suggestion_id}/apply
GET /api/document-intelligence/runs
GET /api/document-intelligence/dashboard-summary
GET /api/shipments/{shipment_id}/document-intelligence
GET /api/shipments/{shipment_id}/document-mismatches
```

`apply` currently returns a controlled error explaining that Phase 13 is
review-only.

## Security Limits

- Raw file bytes are never stored in audit/event/notification metadata.
- Full OCR text is not exposed in list APIs.
- Audit and event metadata only store IDs, counts, statuses, and safe labels.
- OCR does not send emails, modify Gmail, update business records, or approve
  documents automatically.

## Phase 14 Preparation

The review-only suggestion model prepares later finance and credit-control work
without bypassing operational approvals. Future phases can add controlled apply
flows for charge creation or shipment updates after dedicated permission,
audit, and approval checks are in place.
