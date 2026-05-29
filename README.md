# Freight Forwarding Phase 1 MVP

Phase 1 implementation of a freight forwarding operations system with a FastAPI backend, PostgreSQL database, and React + Vite frontend.

## Features

- JWT login with default admin creation
- Role-ready backend permissions for `ADMIN`, `STAFF`, and `VIEW_ONLY`
- Export and import shipment creation
- Auto-generated shipment IDs such as `FF-EXP-2026-001`
- Default document checklist per shipment
- Google Drive URL storage in document `file_url`
- Party directory
- Task list with done/reopen flow
- APScheduler overdue-task alert foundation
- AI Assistant with Groq LLM support and rule-based fallback
- Phase 2 workflow status automation for export and import shipments
- BL Management tab with final BL Google Drive link
- Import demurrage tracker with free-day calculations
- Shipment follow-up log with party/channel/status tracking
- Improved dashboard pending-task and critical-alert panels
- Charges module for manual payable and receivable tracking
- Shipment-wise Profit & Loss summary
- Financial dashboard cards and reports page
- AI finance questions backed by database context
- Phase 3.5 admin cleanup controls for shipment archive/restore, party deactivate/reactivate, safe party delete, task cancel/restore, and manual task delete
- Phase 5 Gmail email automation for read-only scanning, deterministic extraction, and reviewable suggestions
- Phase 6 production hardening with audit logs, admin user lifecycle controls, status checks, CSV exports, dry-run cleanup, and password-change settings
- Phase 7 internal notification center with per-user read/dismiss state, workflow reminder checks, daily operations summary, notification rules, and AI read-only attention summaries
- Phase 9 operational event log, deterministic validation rule engine, and reviewable validation issues feeding deduped manual-review notifications
- Phase 9.1 Gmail automation hardening: account scoping, deterministic dedupe, classifier filtering for non-freight senders, BL-number validation, dismiss/delete/bulk-reject/cleanup controls
- Phase 10 controlled export/import workflow state machines with transition logs, sensitivity-aware permissions, manual-review notifications, and a Workflow Control dashboard widget
- Phase 11 multi-container support with append-only container events, separated demurrage/detention engines, container risk dashboard widget, and a safe legacy-field backfill
- Phase 14 finance + credit control: invoices, payments + allocations, party credit profiles, credit holds, aging buckets, FX rate snapshots, finance risk records, and advisory release controls (OBL/DO/dispatch). Existing charges/P&L flow unchanged.
- Phase 15 exception engine + manual review center: central exception layer tying together validation issues, document mismatches, finance holds, workflow blocks, container risks, Gmail suggestions, and overdue tasks. Includes detection, dedupe, assignment, escalation, resolution, SLA policies, and a full Manual Review Center UI. AI can summarize exceptions read-only.
- Phase 16 approval engine + HOD bot governance: formal approval layer for sensitive actions (finance hold waivers, document releases, workflow transitions, credit overrides, bot actions). Includes maker-checker policies, multi-step approvals, action locks, bot governance proposals, approval delegation, and an Approval Center UI. AI remains read-only.
- Phase 17 bot governance + learning system: measurable bot performance with action records, human feedback, learning candidates, prompt/rule versioning, training cases, evaluation runs, guardrail violations, and quality reviews. Bots cannot self-modify; all improvements require human approval. Bot Governance UI with agent management, scorecards, and guardrail monitoring.
- Phase 18 exporter/importer portal: customer-scoped portal for exporters/importers to view assigned shipments, milestones, containers, customer-visible documents, finance status, and raise requests. Permission-isolated with explicit shipment access grants. Internal cost/margin/payables/Gmail/audit/bot data hidden from portal users.
- Phase 19 CHA/customs coordination: customs case lifecycle tracking with CHA assignment, milestones, checklists, document requirements, customs queries, reference numbers (SB/BOE/OOC/LEO), duty records, and activity logs. Auto-seeds milestones and document requirements per direction. Portal-safe customs visibility. No direct customs filing.
- Phase 20 transport + GPS layer: transport job lifecycle with transporter assignment, vehicle/driver capture, pickup/delivery milestones, container movement tracking, manual GPS/location updates, POD/delivery proof tracking, empty return coordination, transport exceptions and delays, and portal-safe transport visibility. Prepares data model for future GPS provider integration (Phase 21). No live GPS vendor connections.
- Phase 21 tracking adapters: safe adapter framework for external tracking data sources (shipping lines, vessel schedules, terminals, transport GPS). Provider registry with manual/mock adapters, watch items, tracking observations with normalization and confidence scoring, suggested state updates for human review, tracking mismatches, sync runs, and portal-safe tracking visibility. External tracking data is evidence, not truth — no automatic state mutation.
- Phase 22 + 22.1 control tower dashboard: unified operational command center combining all modules into one view. Real-data risk heatmap, top risks, SLA overdue, map-ready placeholders, ETA/ETD change panel, tracking adapter health, stale data monitor, party performance snapshot, drill-down links to source modules, role-safe visibility, and failure-isolated widgets. Dashboard observes and links — no direct state mutation.
- Phase 23 predictive intelligence: rule-based prediction engine with 11 risk models (ETA delay, demurrage, detention, customs delay, document readiness, finance/credit, transport delay, tracking reliability, party performance, SLA breach, overall shipment risk). Prediction records with explainable factors, confidence scoring, recommendations, outcomes, and feedback. Predictions are advisory evidence — no automatic business mutation.
- Phase 24 enterprise scaling + governance: multi-organization readiness with default organization, membership model, 12 enterprise roles, 23 role-permission policies, organization branches/departments, enterprise health checks (11 checks all passing), security events, audit exports, and data retention policies. Preserves existing ADMIN/STAFF/VIEW_ONLY behavior while adding enterprise governance layer.

## Backend Local Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `backend/.env` with a valid PostgreSQL connection string:

```env
DATABASE_URL=postgresql://username:password@host/dbname?sslmode=require
```

Run the API:

```bash
uvicorn app.main:app --reload
```

API docs are available at `http://localhost:8000/docs`.

Default development login:

```txt
admin@example.com
admin123
```

Use that password for local development only. Change `ADMIN_PASSWORD` before the first production deploy.

## Frontend Local Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The frontend runs at `http://localhost:5173`.

## Neon Setup

1. Create a Neon PostgreSQL project.
2. Copy the pooled or direct connection string.
3. Paste it into `backend/.env` as `DATABASE_URL`.
4. Keep `sslmode=require` in the URL for Neon.

Never commit `backend/.env` or `frontend/.env`. They are ignored by git and should stay local or in your hosting provider's environment settings.

## Document Link Workflow

Phase 1 stores document links only. Upload files manually to Google Drive, copy the share URL, then paste it into the document `file_url` field in the shipment Documents tab.

## Phase 2 Tracking And Alerts

Phase 2 adds operational tracking after shipment creation:

- Workflow status dropdown on shipment detail pages.
- Export workflow side effects for SI, VGM, BL draft, final BL, invoice, and packing list documents.
- Import workflow side effects for freight invoice, DO received, and demurrage start date.
- BL Management tab for BL type, draft date, corrections, approval, final BL, surrender/telex flags, and Google Drive link.
- Demurrage tab for import shipments with free days, start date, rate, currency, alert threshold, container count, days remaining, running status, and estimated due amount.
- Follow-up Log tab for shipment-linked email/call/WhatsApp/meeting follow-ups.
- APScheduler alert rules for overdue tasks, export cutoffs, free days expiry, demurrage started, DO not collected, and freight invoice chase.
- Mock AI examples: `Which shipments have free days expiring?`, `Which shipments have demurrage running?`, `Which follow-ups are open?`, and `What is the status of FF-EXP-2026-001?`.

## Phase 3 Charges And Reporting

Phase 3 adds a manual finance layer:

- Charges tab on shipment detail pages for payable and receivable entries.
- Payable charges are amounts the company must pay to vendors, lines, agents, CHA, courier, or other parties.
- Receivable charges are amounts the company must collect from clients, exporters, importers, or other parties.
- Charge status rules:
  - payable: `pending`, `paid`, or `cancelled`
  - receivable: `pending`, `received`, or `cancelled`
- Cancelling a charge keeps the record in the database with `status = cancelled`; cancelled charges are excluded from active P&L, dashboard, and report totals.
- Shipment P&L formula: `net_profit = total_receivable - total_payable`, excluding cancelled charges.
- Dashboard financial cards show pending receivables, pending payables, this month receivables, this month payables, and this month profit.
- Reports page shows monthly summary, pending receivables, pending payables, and shipment-wise P&L.
- Mock AI finance examples: `How much freight is uncollected?`, `Which shipments have pending receivables?`, `Which shipments have pending payables?`, `Show profit for FF-EXP-2026-001`, `Which shipments are loss-making?`, and `What is this month profit?`.

## Phase 3.5 Admin Cleanup

Phase 3.5 adds safe cleanup controls without removing operational history:

- Shipments can be archived and restored by `ADMIN` users only. Archived shipments keep linked documents, tasks, charges, BL, demurrage, follow-ups, and alerts.
- Shipment lists hide archived records by default. Use Include Archived to show them with an Archived badge.
- Parties can be deactivated and reactivated by `ADMIN` users only. Inactive parties are hidden from new shipment, charge, and follow-up dropdowns by default, but old linked records still show their names.
- Parties can be permanently deleted only when unused. Parties linked to shipments, charges, or follow-ups are blocked with `Party is used in existing records. Deactivate it instead.`
- Tasks can be cancelled and restored by `ADMIN` and `STAFF`. Cancelled tasks are hidden by default and do not count as pending tasks.
- Manual tasks can be permanently deleted only when they are not auto-generated and are not referenced by alerts. Auto-generated workflow tasks should be cancelled instead of deleted.
- `VIEW_ONLY` users can read archived/inactive/cancelled state but cannot use cleanup write controls.

Archive, deactivate, and cancel actions keep history safe while reducing clutter in normal day-to-day screens.

### Database Compatibility

The app keeps using the existing `Base.metadata.create_all()` startup pattern, but Phase 3.5 also runs an idempotent compatibility helper:

- Missing shipment archive columns and party deactivation columns are added with `ALTER TABLE ... ADD COLUMN` only if they are absent.
- If a column already exists, startup skips it.
- Existing data is not dropped, recreated, truncated, or reset.
- If an installed PostgreSQL database uses a native enum for task status, startup safely allows the `cancelled` status value without crashing on repeated runs.

## Phase 4 Groq AI Assistant

Phase 4 upgrades the `/ai` page from a mock assistant into a database-aware AI Assistant with a Groq-backed LLM path and rule-based fallback.

- The backend builds a small, read-only context from relevant shipments, tasks, BL records, demurrage, follow-ups, charges, and reports.
- The LLM never receives full database tables or API keys.
- The assistant is read-only in Phase 4. It may suggest actions, but it cannot archive shipments, deactivate parties, cancel tasks, edit charges, send emails, upload files, or perform any write action.
- If `AI_ENABLED=false`, `GROQ_API_KEY` is missing, Groq times out, or the LLM returns an invalid response, the existing rule-based fallback answers are returned with `fallback_used=true`.
- All authenticated roles, including `VIEW_ONLY`, can ask read-only AI questions.

Backend-only AI environment variables:

```env
AI_PROVIDER=groq
AI_ENABLED=true
GROQ_API_KEY=your_groq_api_key
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
AI_TIMEOUT_SECONDS=30
AI_MAX_CONTEXT_ROWS=30
AI_LOG_INTERACTIONS=true
```

Never put `GROQ_API_KEY` or `OPENAI_API_KEY` in frontend environment variables, never expose them through API responses, and never commit `backend/.env`.

Supported examples include:

- `What shipments need attention today?`
- `Which tasks are overdue?`
- `Which shipments have demurrage running?`
- `Which BL approvals are pending?`
- `Which follow-ups are open?`
- `How much freight is uncollected?`
- `Which shipments have pending receivables?`
- `Which shipments have pending payables?`
- `Which shipments are loss-making?`
- `Show profit for FF-EXP-2026-001.`
- `What is the next action for FF-IMP-2026-001?`
- `Show archived shipments.`
- `Show inactive parties.`
- `Show cancelled tasks.`

## Phase 5 Gmail Email Automation

Phase 5 adds a backend-only Gmail integration for turning freight emails into reviewable suggestions.

- Gmail access uses OAuth on the backend only. The frontend never receives Google client secrets, access tokens, or refresh tokens.
- The only Gmail scope is `https://www.googleapis.com/auth/gmail.readonly`.
- The app reads freight-related Gmail messages, caches safe previews, classifies them, extracts fields deterministically, and creates suggestions.
- Email scans never update shipments, documents, BL records, demurrage, charges, follow-ups, or tasks by themselves.
- Business records change only when an `ADMIN` or `STAFF` user reviews a suggestion and clicks Apply.
- `VIEW_ONLY` users cannot access Gmail automation.
- Phase 5 does not send, delete, archive, label, forward, or modify Gmail messages.
- Phase 5 does not send email content to Groq.

Backend-only Gmail environment variables:

```env
GMAIL_ENABLED=true
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/email/oauth/callback
FRONTEND_BASE_URL=http://localhost:5173
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly
EMAIL_MAX_RESULTS=20
EMAIL_LOOKBACK_DAYS=30
TOKEN_ENCRYPTION_KEY=your_fernet_key
```

Generate a Fernet key for `TOKEN_ENCRYPTION_KEY`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

For Render, set:

```env
GOOGLE_REDIRECT_URI=https://freight-backend-au6c.onrender.com/api/email/oauth/callback
FRONTEND_BASE_URL=https://freight-frontend-u051.onrender.com
```

The Google Cloud OAuth client must include both the local and Render callback URLs if you use both environments:

```txt
http://localhost:8000/api/email/oauth/callback
https://freight-backend-au6c.onrender.com/api/email/oauth/callback
```

Keep downloaded Google OAuth JSON files untracked. Copy only the client ID and client secret into backend environment variables. `client_secret*.json` is ignored by git.

## Phase 6 Production Hardening

Phase 6 adds safer production operations around the existing freight workflows:

- `ADMIN` users can review Audit Logs, Users, Status, and Admin Tools pages.
- All authenticated users can change their own password from Settings.
- Admin user lifecycle APIs support create, update, password reset, deactivate, and reactivate with safeguards that keep at least one active admin.
- Audit logs are stored in `audit_logs` and available through `GET /api/audit-logs`.
- Audit metadata is allowlisted and redacted. Password changes and resets only log that the action happened with actor/target metadata.
- Audit logs must never include old passwords, new passwords, password hashes, JWTs, Gmail access or refresh tokens, OAuth codes, Google client secrets, API keys, database URLs, or environment values.
- Health checks are available at public `GET /api/health` and admin-only `GET /api/health/details`.

## Phase 7 Notifications And Workflow Automation

Phase 7 adds an internal notification and reminder layer without replacing legacy alerts.

- Existing `/api/alerts` endpoints and dashboard alert panels remain backward-compatible.
- `/api/notifications` provides notification list, unread count, read/unread, dismiss, mark-all-read, manual run checks, daily summary, and notification rule APIs.
- Notification rules are stored in `notification_rules` and can be enabled, disabled, and tuned by `ADMIN` users.
- Notification read and dismiss state is per user through `notification_user_states`, so one staff member marking a notification read or dismissed does not hide it for another staff member.
- Ongoing issues use stable dedupe keys such as `overdue_task:{task_id}`, `demurrage_running:{shipment_id}`, `bl_approval_pending:{shipment_id}`, and `pending_receivable:{charge_id}`. Repeated hourly checks do not create duplicate active notifications for the same unchanged issue.
- Daily reminder rules use date-specific dedupe keys only when a fresh daily reminder is intended, such as tasks due today and Gmail suggestions pending.
- The scheduler runs best-effort hourly notification checks and a daily operations summary job. Render free services may sleep, so `ADMIN` and `STAFF` users can also run checks manually from the Notifications page.
- Daily summary is available inside the Notifications page and as a dashboard widget. It includes overdue tasks, demurrage risk, pending BL approvals, pending receivables, pending payables, Gmail review count, and top urgent notification items.
- The AI Assistant can answer questions like `What needs attention today?`, `Show my notifications`, and `What are today's urgent issues?` from notification and summary data only.

Phase 7 automation is intentionally limited:

- Notification checks may create internal notifications and summaries only.
- Notification checks must not automatically mutate shipments, documents, BL records, tasks, charges, parties, users, Gmail records, or AI-managed state.
- Gmail remains read-only and suggestion review-based. Phase 7 does not send, modify, delete, archive, label, or auto-apply Gmail messages or suggestions.
- Phase 7 does not add n8n, WhatsApp, SMS, Drive upload, OCR, Celery, Redis, payment gateways, invoice PDFs, external webhooks, or autonomous AI writes.
- Admin CSV exports are available for shipments, parties, charges, tasks, and audit logs.
- Admin test-data cleanup is dry-run only at `POST /api/admin/cleanup-test-data`; it reports candidates and does not modify records.
- Risky admin actions in the frontend use confirmation dialogs.

Phase 6 CSV exports intentionally omit password hashes, token fields, API keys, secrets, database URLs, and environment values.

## Phase 9 Event Validation Rule Engine

Phase 9 adds the first operational-brain layer beside the existing flows:

- Operational events are recorded for representative actions across shipments, parties, tasks, charges, documents, BL, demurrage, Gmail suggestions, and notification runs.
- Deterministic validation rules run for each event without blocking the original action.
- Validation issues persist in `validation_issues` with statuses `open`, `acknowledged`, `resolved`, or `dismissed`.
- Critical issues create deduped internal notifications under `category=system`, `priority=critical`, with action URL `/validation-issues`.
- Phase 9 frontend pages: `/events`, `/validation-issues`, and `/rules`. ADMIN can edit rule severity, enable/disable, and the blocking flag. STAFF can read rules and triage issues.
- All Phase 9 rules ship as non-blocking warnings by default. The blocking flag captures intent for Phase 10 and is not enforced anywhere in Phase 9.
- The AI assistant can summarize validation issues and recent events read-only.

Phase 9 cannot mutate shipments, tasks, charges, documents, BL records, parties, users, or Gmail records. See `docs/PHASE_9_EVENT_VALIDATION_RULE_ENGINE.md` for architecture, models, default rules, and the planned Phase 10 transition.

## Phase 10 Export Import State Machines

Phase 10 introduces controlled lifecycle states for export and import shipments without changing the existing shipment status fields:

- Canonical export and import state catalogs (37 export, 33 import states) seeded on startup.
- Transition definitions seeded with sensitivity, confirmation, reason, and manual-review flags. Sensitive transitions (`BL_APPROVED`, `FINAL_BL_RECEIVED`, `PAYMENT_RECEIVED`, `FREIGHT_PAID`, `EXPORT_COMPLETED`, `IMPORT_COMPLETED`) require ADMIN plus explicit `confirm_sensitive=true`.
- New API base path `/api/workflow` exposes states, transitions, current state, available transitions, transition requests, and timelines.
- Each transition produces an `OperationalEvent`, a `WorkflowTransitionLog`, and an `AuditLog` row. Manual-review and blocked outcomes also create deduped critical notifications and validation issues.
- Shipment detail page adds a `Workflow` tab with a state badge, allowed next transitions, and a workflow timeline. The dashboard adds a `Workflow Control` widget for flagged shipments and recent blocked transitions.
- Existing shipments without a `workflow_state` are inferred best-effort via `workflow_state_mapper`. Inference does not persist until a transition is applied.
- Phase 10 cannot mutate BL approvals, payments, document releases, demurrage charges, customs filings, or any external system. The state machine remains a workflow-control layer, not an autonomous workflow.

See `docs/PHASE_10_EXPORT_IMPORT_STATE_MACHINES.md` for full state lists, API contracts, permission model, and rule integration.

## Phase 11 Container Lifecycle + Demurrage/Detention

Phase 11 makes containers first-class operational entities:

- Each shipment can have multiple containers with their own lifecycle dates and append-only event history.
- Demurrage and detention are calculated by separate engines using container-level overrides, optional `DemurrageDetentionRule` rows, and safe defaults (7 free days, INR 50/day).
- Container risk surfaces through deduped notifications (`container_demurrage_running:{id}`, `container_detention_running:{id}`, `container_empty_return_overdue:{id}`) and a dashboard widget.
- Validation rules cover ISO container number format, duplicate active containers, loaded-before-gate-in, delivered-before-DO, empty-return-before-delivery, gate-in-after-cutoff, and partial-delivery info.
- `POST /api/containers/backfill-from-shipments` is ADMIN-only and dry-run by default. It splits comma-separated legacy container numbers into individual containers without overwriting existing records.
- Container amounts and statuses never auto-create Phase 3 charges. Charges remain user-driven.

See `docs/PHASE_11_CONTAINER_LIFECYCLE_DEMURRAGE_DETENTION.md` for full state lists, APIs, and integration details.

## Phase 1 Limitations

The app still intentionally does not include OpenAI as the primary AI provider, real file uploads, Google Drive API upload, S3, Celery, Redis, courier automation, invoice PDF generation, payment gateway integration, accounting software integration, GST invoice automation, bank reconciliation, exchange-rate automation, OCR, autonomous database writes, auto-reply email, Gmail message modification, destructive cleanup automation, or AI-executed archive/delete/cancel actions.

Phase 3 finance entries are manual. The app stores currencies per charge and flags mixed-currency totals, but it does not convert exchange rates automatically.

Phase 5 email extraction is deterministic and limited to subject/snippet/body previews. Gmail readonly is a restricted Google scope, so production usage may require Google verification and additional security review.

Shipment codes are unique in the database, but the current counter-based generator can race if two shipments of the same type are created at exactly the same time. Use single-user/admin workflows for Phase 1; replace this with a database sequence before high-concurrency production use.

## Render Deployment

Backend web service:

```txt
Root directory: backend
Build command: pip install -r requirements.txt
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Backend environment variables:

```env
DATABASE_URL=your_neon_postgres_url
JWT_SECRET_KEY=your_secret_key
BACKEND_CORS_ORIGINS=https://your-frontend.onrender.com
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE_SECONDS=1800
AUTO_CREATE_TABLES=true
AI_PROVIDER=groq
AI_ENABLED=true
GROQ_API_KEY=your_groq_api_key
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
AI_TIMEOUT_SECONDS=30
AI_MAX_CONTEXT_ROWS=30
AI_LOG_INTERACTIONS=true
GMAIL_ENABLED=true
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://freight-backend-au6c.onrender.com/api/email/oauth/callback
FRONTEND_BASE_URL=https://freight-frontend-u051.onrender.com
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly
EMAIL_MAX_RESULTS=20
EMAIL_LOOKBACK_DAYS=30
TOKEN_ENCRYPTION_KEY=your_fernet_key
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-this-password
```

For production speed, use Neon's pooled connection URL, deploy the backend in the same or nearest region as the database, and run without `--reload`.
Set a long random `JWT_SECRET_KEY`, and change `ADMIN_PASSWORD` before the service starts for the first time.
Add Groq and Google variables only to the backend Render service. Do not add Groq, OpenAI, or Google client secrets to the frontend Render service.

Frontend static site:

```txt
Root directory: frontend
Build command: npm install && npm run build
Publish directory: dist
```

Frontend environment variable:

```env
VITE_API_BASE_URL=https://your-backend.onrender.com/api
```

## GitHub Push

```bash
git init
git add .
git commit -m "Initial freight forwarding phase 1 MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/freight-forwarding-phase1.git
git push -u origin main
```
