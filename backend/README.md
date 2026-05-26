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
- `../docs/PHASE_11_CONTAINER_LIFECYCLE_DEMURRAGE_DETENTION.md`

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
