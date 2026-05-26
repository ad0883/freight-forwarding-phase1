# Freight Forwarding Phase 1 Backend

FastAPI backend for the Phase 1 freight forwarding MVP.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `DATABASE_URL` in `.env` with a PostgreSQL connection string, then run:

```bash
uvicorn app.main:app --reload
```

API docs open at `http://localhost:8000/docs`.

## Phase 8 Migration Foundation

Phase 8 introduces Alembic as the forward migration path while keeping the existing startup compatibility behavior in place temporarily.

Common commands:

```bash
cd backend
alembic history
alembic current
alembic upgrade head
```

Existing production-style databases that were created with `Base.metadata.create_all()` should be stamped to the empty baseline before future migrations are applied:

```bash
cd backend
alembic stamp phase8_baseline
alembic upgrade head
```

For local scratch databases, `alembic upgrade head` creates the Phase 8 migration state. The app still supports `AUTO_CREATE_TABLES=true` during this transition so fresh local environments continue to boot.

Safety rules:

- Do not run destructive migrations on production.
- Take a Neon/PostgreSQL backup before major migrations.
- Do not commit a real `DATABASE_URL`, JWT secret, Groq key, Google secret, OAuth JSON, or token file.
- Do not print production connection strings in logs.

## Default Organization

Phase 8 creates a default organization for existing users:

```txt
Default Freight Organization
default-freight-organization
freight_forwarder
```

Current roles remain global (`ADMIN`, `STAFF`, `VIEW_ONLY`). Phase 8 adds organization metadata but does not enforce tenant isolation on shipments, parties, tasks, charges, documents, or reports.

## Master 1.1 Architecture Docs

See:

- `../MASTER_1_1_GAP_MAP.md`
- `../docs/EVENT_VALIDATION_FOUNDATION.md`
- `../docs/PHASE_9_EVENT_VALIDATION_RULE_ENGINE.md`
- `../docs/PHASE_9_1_GMAIL_HARDENING.md`
- `../docs/PHASE_10_EXPORT_IMPORT_STATE_MACHINES.md`
- `../docs/PHASE_11_CONTAINER_LIFECYCLE_DEMURRAGE_DETENTION.md`
- `../docs/PHASE_12_DOCUMENT_UPLOAD_VERSIONING.md`
- `../docs/PHASE_13_DOCUMENT_INTELLIGENCE_OCR_MISMATCH_VALIDATION.md`

## Phase 13 Document Intelligence + OCR

Phase 13 adds controlled document intelligence on top of Phase 12 uploads.
It can extract text from text-based PDFs and TXT/CSV files, classify the
document, extract candidate fields, compare them to shipment/BL/container/
charge records, and create reviewable mismatches, validation issues, and
suggestions.

Settings:

```txt
DOCUMENT_OCR_ENABLED=true
DOCUMENT_OCR_IMAGE_ENABLED=false
DOCUMENT_OCR_MAX_PAGES=5
DOCUMENT_OCR_MAX_CHARS=20000
DOCUMENT_EXTRACTION_CONFIDENCE_THRESHOLD=0.70
DOCUMENT_LOW_CONFIDENCE_THRESHOLD=0.50
```

Important limits:

- OCR output is untrusted until reviewed.
- Full OCR text is not stored in audit, events, notifications, or list APIs.
- Suggestions are review-only in Phase 13; they are not applied automatically.
- Image OCR is disabled by default and requires optional local OCR tooling.
- Running document intelligence never mutates shipments, BL records, charges,
  containers, parties, Gmail, or uploaded files.

## Phase 12 Document Upload + Versioning

Phase 12 adds controlled upload and version history for shipment documents
without changing existing checklist behavior. Run `alembic upgrade head` to
apply `phase12_document_versions`.

Document storage settings:

```txt
DOCUMENT_STORAGE_BACKEND=database
DOCUMENT_MAX_UPLOAD_MB=10
DOCUMENT_LOCAL_STORAGE_DIR=uploaded_documents
```

The default `database` backend stores file bytes in `document_file_blobs`.
`local` is intended for local development only and writes under the ignored
`uploaded_documents` directory. Do not commit uploaded files.

Allowed uploads are PDF, PNG/JPEG, Word, Excel, CSV, and plain text documents.
Executable uploads are blocked. Uploaded files are not OCR-read, AI-parsed,
Gmail-ingested, or used to mutate shipment data in Phase 12.

Review permissions:

- `ADMIN`: upload, approve, reject, archive, rollback, download, list.
- `STAFF`: upload, approve, reject, download, list.
- `VIEW_ONLY`: download and list only.

## Phase 11 Container Lifecycle + Demurrage/Detention

Phase 11 adds first-class containers, append-only container events, separated
demurrage and detention engines, dedicated APIs at `/api/containers` and
`/api/shipments/{id}/containers`, container risk notifications, validation
rules, and a dashboard widget. It does not change Phase 3 charges, Phase 7
notifications, Phase 9 events/validation pipelines, or the existing
shipment-level `Demurrage` table - that table stays for legacy data.

Run `alembic upgrade head` to apply `phase11_container_lifecycle`. Existing
shipment fields like `shipment.container_no` and `shipment.container_type`
remain untouched. Use the ADMIN-only backfill endpoint
`POST /api/containers/backfill-from-shipments` (dry-run by default) to migrate
legacy text into Container rows safely.

See `../docs/PHASE_11_CONTAINER_LIFECYCLE_DEMURRAGE_DETENTION.md` for the full
state lists, API contract, validation rules, and notification dedupe scheme.

## Phase 10 Export Import State Machines

Phase 10 layers a controlled state-machine on top of existing shipments without
removing any current behaviour:

- Canonical export and import states are seeded into `workflow_state_definitions`.
- Transitions are seeded into `workflow_transition_definitions` and gated by
  `is_sensitive`, `requires_confirmation`, `requires_reason`, and
  `requires_manual_review` flags.
- `workflow_transition_logs` records every transition attempt with status,
  validation status, actor, reason, and links to the operational event/issue.
- Shipments gain `workflow_state`, `workflow_state_updated_at`,
  `workflow_state_reason`, `manual_review_required`, and `manual_review_reason`.

API base path: `/api/workflow`. See `../docs/PHASE_10_EXPORT_IMPORT_STATE_MACHINES.md`
for the full state list, transition rules, permissions, and rule integration.

The Shipment detail page now includes a Workflow tab with a state badge,
available transitions, and a transition timeline. Sensitive transitions require
explicit confirmation and ADMIN role. VIEW_ONLY users can read state and
timeline only.

For migration: `alembic upgrade head` applies `phase10_export_import_states`.

## Phase 9.1 Gmail Automation Hardening

Phase 9.1 fixes Gmail automation data hygiene without changing scopes:

- Cached emails and suggestions are scoped by `user_id` and `gmail_account_email`. Listings default to the currently connected account; an `Include hidden` toggle and `current_account_only=false` query expose other accounts when needed.
- Suggestions deduplicate by `email_message_id + suggestion_type + shipment_id + extracted_data_hash`. Re-running a scan does not create duplicate cached emails or duplicate pending suggestions.
- New endpoints: `PATCH /api/email/suggestions/{id}/reject`, `PATCH /api/email/suggestions/{id}/dismiss`, `DELETE /api/email/suggestions/{id}` (ADMIN only, blocks delete on `applied`), `POST /api/email/suggestions/bulk-reject`, `POST /api/email/suggestions/clear-pending`, `POST /api/email/cleanup`. The classic `POST /api/email/suggestions/{id}/reject` keeps working.
- `POST /api/email/disconnect` accepts `{"clear_cache": true}` to reject pending suggestions and hide cached emails for the disconnected account. Applied charges/tasks/documents are not deleted.
- Classifier rejects non-freight senders (IRCTC, Shopify, Amazon, newsletters, promos, social) unless freight terms are present. BL numbers must pass length, charset, and entropy checks - token-like or base64-looking strings are rejected. Ports must be alphabetic, amounts must be realistic.
- Email Automation page adds bulk-select checkboxes, Reject/Dismiss/Delete row actions, low-confidence and no-shipment cleanup buttons, current-account toggle, hidden emails toggle, and a cleanup-old-data button. ADMIN can hard-delete pending/rejected/dismissed suggestions.

See `../docs/PHASE_9_1_GMAIL_HARDENING.md` for the full spec.

## Phase 9 Event Validation Rule Engine

Phase 9 records operational events for representative actions, runs deterministic
validation rules against each event, and persists reviewable validation issues.

- Events table: `operational_events`. Browse via `GET /api/events`.
- Validation issues table: `validation_issues`. Browse via `GET /api/validation-issues`.
- Rule definitions table: `rule_definitions`. Browse via `GET /api/rules`.

Phase 9 rules ship as non-blocking warnings. Critical issues create deduped
internal notifications under `category=system, priority=critical`. Phase 9
cannot mutate shipments, tasks, charges, documents, BL records, parties, users,
or Gmail records.

Frontend pages:

- `/events` (ADMIN, STAFF): operational event log with filters and detail drawer.
- `/validation-issues` (ADMIN, STAFF): issue triage with acknowledge/resolve/dismiss.
- `/rules` (ADMIN edits, STAFF reads): toggle rule enable/blocking and severity.

The dashboard adds a Validation & Manual Review widget surfacing the latest open
issues. The AI assistant can summarize validation issues and recent events in
read-only mode.

For migration instructions, run `alembic upgrade head` to apply
`phase9_event_validation`. Existing databases are not modified
destructively. Local fresh databases keep working through `AUTO_CREATE_TABLES`.

## Default Admin

The app creates the first admin on startup when no admin exists:

```txt
admin@example.com
admin123
```

Use the default password only for local development. Set a strong `ADMIN_PASSWORD` and `JWT_SECRET_KEY` before the first production deployment, and never commit `.env`.
