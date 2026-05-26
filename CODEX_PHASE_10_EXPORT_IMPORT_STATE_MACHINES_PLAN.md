# CODEX_PHASE_10_EXPORT_IMPORT_STATE_MACHINES_PLAN.md

# Phase 10 — Strong Export / Import State Machines

## Purpose

Implement **Phase 10** for the Freight Forwarding / EXIM Operational Intelligence System.

Phase 8 added Alembic, default organization groundwork, Master 1.1 gap map, and event/validation placeholders. Phase 9 added operational events, rule definitions, validation issues, rules APIs, events APIs, validation issue APIs, dashboard manual-review widget, and read-only AI validation summaries.

Phase 10 now strengthens the operational workflow layer by introducing **controlled export/import state machines**.

The goal is:

```txt
Shipments should no longer move through loose status updates only.
Export and import shipments should have controlled lifecycle states.
Each state transition should be validated, event-logged, auditable, and capable of generating tasks/notifications/manual-review issues.
```

Phase 10 must preserve all current app behavior while adding the state-machine layer safely beside the existing shipment workflow fields.

---

# 1. Current Completed Foundation

The app currently includes:

```txt
Phase 1      FF Core base
Phase 2      Workflow, BL, demurrage, follow-ups, alerts
Phase 3      Charges, P&L, reports
Phase 3.5    Safe cleanup controls
Phase 4      Groq AI assistant
Phase 5      Gmail read-only email automation
Phase 6      Production hardening
Phase 6.1    Direct login + admin user management
Phase 7      Notifications + workflow reminders
Phase 8      Migration + Master 1.1 architecture foundation
Phase 9      Event system + validation/rule engine foundation
```

Current stack:

```txt
Frontend: React + Vite
Backend: FastAPI
Database: PostgreSQL / Neon
Migrations: Alembic
Auth: JWT + bcrypt
Roles: ADMIN / STAFF / VIEW_ONLY
AI: Groq read-only assistant
Gmail: read-only OAuth + review-based suggestions
```

Preserve all existing behavior:

```txt
Login
Admin user management
Dashboard
Shipments
Parties
Tasks
Documents
BL Management
Demurrage
Follow-ups
Legacy alerts
Notifications
Charges
Reports
Archive/deactivate/cancel controls
AI assistant
Gmail automation
Audit logs
Status page
Admin tools
Organization foundation
Events
Validation issues
Rules
```

---

# 2. Master 1.1 Alignment

Master 1.1 requires workflow engine behavior such as:

```txt
validate previous state
allow/block next state
generate next task
create deadline
escalate overdue task
call validation rules
call approval rules
```

Phase 10 implements the first real export/import workflow control system.

The target flow becomes:

```txt
User action
→ workflow transition request
→ identity/context lookup
→ state-machine allowed-transition check
→ Phase 9 validation/rule checks
→ task/notification generation
→ manual-review signal if needed
→ event log
→ audit log
→ shipment state update if allowed
```

---

# 3. Strict Non-Goals

Do **not** implement in Phase 10:

```txt
Container lifecycle tables
Demurrage/detention separation
Document upload/versioning/OCR
Exporter/importer portal
CHA/customs portal
Transport/GPS layer
Tracking adapters
Full exception engine
Full approval engine
HOD bot
Bot governance/learning system
Autonomous AI writes
Gmail send/modify/delete/archive
Payment gateway
Invoice PDFs
n8n
WhatsApp/SMS
Strict tenant filtering of operational records
```

Phase 10 should only implement the workflow state-machine layer and safe UI/API integration.

---

# 4. Safety Rules

Phase 10 may:

```txt
define export/import states
define allowed transitions
log workflow transition attempts
perform transition validation
create operational events
create validation issues
create internal notifications/manual-review warnings
generate tasks for next actions where safe
show workflow timeline/state progress
```

Phase 10 must not automatically:

```txt
approve BLs
approve payments
release OBL/DO/documents
send external emails
change customs-sensitive data
delete records
override credit holds
auto-apply Gmail suggestions
```

Default policy:

```txt
Workflow transitions are user-initiated or system-suggested, not fully autonomous.
Sensitive transitions require manual confirmation and/or manual-review issue creation.
```

---

# 5. Git Workflow

Start from updated `main` after Phase 9 is merged/deployed safely.

```bash
git status
git log --oneline -8

git checkout main
git pull origin main
git checkout -b phase-10-export-import-state-machines
```

Final commit:

```bash
git add .
git commit -m "Implement phase 10 export import state machines"
git push -u origin phase-10-export-import-state-machines
```

Do not deploy until tests pass.

---

# 6. Database / Alembic Migration

Use Alembic for Phase 10 schema changes.

Add migration:

```txt
phase10_export_import_states
```

New tables:

```txt
workflow_state_definitions
workflow_transition_definitions
workflow_transition_logs
```

Add shipment columns if safe:

```txt
workflow_state nullable
workflow_state_updated_at nullable
workflow_state_reason nullable
manual_review_required boolean default false
manual_review_reason nullable
```

Rules:

```txt
No data reset
No table drops
No destructive renames
No breaking changes to existing shipment status/workflow_status columns
All new fields must be nullable or have safe defaults
Revision ID must be <= 32 chars
```

Keep existing shipment fields for backward compatibility.

---

# 7. Backend Models

## 7.1 WorkflowStateDefinition

Table:

```txt
workflow_state_definitions
```

Fields:

```txt
id
flow_type
state_key
state_label
state_order
description nullable
is_initial
is_terminal
is_active
created_at
updated_at
```

`flow_type` values:

```txt
export
import
```

Examples:

```txt
EXPORT_BOOKING_CONFIRMED
BL_DRAFT_RECEIVED
IMPORT_PRE_ALERT_RECEIVED
DO_RECEIVED
IMPORT_COMPLETED
```

---

## 7.2 WorkflowTransitionDefinition

Table:

```txt
workflow_transition_definitions
```

Fields:

```txt
id
flow_type
transition_key
from_state
to_state
label
description nullable
requires_reason
requires_confirmation
requires_manual_review
is_sensitive
is_active
created_at
updated_at
```

Examples:

```txt
export.booking_confirmed_to_shipment_created
export.bl_draft_received_to_bl_under_review
import.pre_alert_received_to_import_shipment_created
import.do_received_to_free_days_counter_started
```

---

## 7.3 WorkflowTransitionLog

Table:

```txt
workflow_transition_logs
```

Fields:

```txt
id
shipment_id
flow_type
transition_key nullable
from_state nullable
to_state
actor_user_id nullable
actor_name nullable
actor_email nullable
actor_role nullable
source
status
reason nullable
validation_status
event_id nullable
validation_issue_id nullable
metadata_json nullable
created_at
```

`status` values:

```txt
requested
applied
blocked
manual_review_required
failed
```

`source` values:

```txt
user
system
gmail
ai
workflow
scheduler
```

Rules:

```txt
Do not store passwords, tokens, secrets, raw request bodies, raw email bodies, or OAuth codes.
```

---

# 8. Canonical Export State Chain

Seed these states in `workflow_state_definitions`.

Use exact state keys:

```txt
EXPORT_INQUIRY_RECEIVED
EXPORT_QUOTED
EXPORT_BOOKING_CONFIRMED
EXPORT_SHIPMENT_CREATED
CONTAINER_PLANNED
TRANSPORTER_ASSIGNED
EMPTY_PICKUP_SCHEDULED
EMPTY_CONTAINER_PICKED
FACTORY_STUFFING_SCHEDULED
CARGO_STUFFED
SEAL_APPLIED
SI_PENDING
SI_SUBMITTED
VGM_PENDING
VGM_FILED
CUSTOMS_SB_PENDING
SHIPPING_BILL_FILED
CUSTOMS_QUERY_IF_ANY
EXAMINATION_IF_ANY
LEO_RECEIVED
GATE_IN_PENDING
CONTAINER_GATE_IN
LOADED_ON_VESSEL
BL_DRAFT_PENDING
BL_DRAFT_RECEIVED
BL_UNDER_REVIEW
BL_CORRECTION_IF_ANY
BL_APPROVED
FINAL_BL_RECEIVED
DOCUMENT_SET_PENDING
DOCUMENT_SET_VERIFIED
DOCUMENTS_DISPATCHED
PRE_ALERT_SENT
FREIGHT_INVOICED
PAYMENT_PENDING
PAYMENT_RECEIVED
EXPORT_COMPLETED
```

Do not require all existing shipments to be perfectly mapped on day one.

---

# 9. Canonical Import State Chain

Seed these states in `workflow_state_definitions`.

Use exact state keys:

```txt
IMPORT_PRE_ALERT_PENDING
PRE_ALERT_RECEIVED
IMPORT_SHIPMENT_CREATED
ETA_TRACKING_ACTIVE
IGM_PENDING
IGM_FILED
FREIGHT_INVOICE_PENDING
FREIGHT_INVOICE_RECEIVED
INCOTERM_CHARGE_VALIDATION
BL_RELEASE_STATUS_PENDING
SURRENDER_TELEX_OBL_CONFIRMED
PAYMENT_TO_LINE_PENDING
FREIGHT_PAID
DO_PENDING
DO_RECEIVED
FREE_DAYS_COUNTER_STARTED
DO_FORWARDED_TO_CHA
BOE_PENDING
BOE_FILED
DUTY_ASSESSMENT_PENDING
DUTY_PAID_IF_REQUIRED
CUSTOMS_QUERY_IF_ANY
EXAMINATION_IF_ANY
OOC_PENDING
OOC_RECEIVED
TRANSPORT_DELIVERY_PLANNED
CONTAINER_DELIVERED
EMPTY_RETURN_PENDING
EMPTY_RETURNED
DEMURRAGE_DETENTION_FINALIZED
IMPORT_INVOICE_RAISED
PAYMENT_RECEIVED
IMPORT_COMPLETED
```

Do not implement full customs filing or transport/GPS in this phase.

---

# 10. Transition Definitions

Seed basic linear transitions for export/import state chains.

Examples:

```txt
EXPORT_BOOKING_CONFIRMED -> EXPORT_SHIPMENT_CREATED
BL_DRAFT_PENDING -> BL_DRAFT_RECEIVED
BL_DRAFT_RECEIVED -> BL_UNDER_REVIEW
BL_UNDER_REVIEW -> BL_APPROVED
BL_APPROVED -> FINAL_BL_RECEIVED

PRE_ALERT_RECEIVED -> IMPORT_SHIPMENT_CREATED
DO_PENDING -> DO_RECEIVED
DO_RECEIVED -> FREE_DAYS_COUNTER_STARTED
OOC_PENDING -> OOC_RECEIVED
CONTAINER_DELIVERED -> EMPTY_RETURN_PENDING
EMPTY_RETURNED -> DEMURRAGE_DETENTION_FINALIZED
```

Allow controlled non-linear states for exception stages:

```txt
CUSTOMS_QUERY_IF_ANY
EXAMINATION_IF_ANY
BL_CORRECTION_IF_ANY
```

Do not overcomplicate. Phase 10 provides foundation; later phases add container/document/customs details.

---

# 11. Workflow State Mapping for Existing Shipments

Existing shipments may have loose fields such as:

```txt
shipment_type
status
workflow_status
bl status
demurrage status
document status
charge status
```

Add service:

```txt
backend/app/services/workflow_state_mapper.py
```

Function:

```python
infer_workflow_state_for_shipment(shipment) -> str
```

Basic mapping:

Export:

```txt
if completed -> EXPORT_COMPLETED
if final BL received -> FINAL_BL_RECEIVED
if BL approved -> BL_APPROVED
if BL draft received -> BL_DRAFT_RECEIVED
if loaded/on vessel -> LOADED_ON_VESSEL
if booking exists -> EXPORT_BOOKING_CONFIRMED
else -> EXPORT_SHIPMENT_CREATED
```

Import:

```txt
if completed -> IMPORT_COMPLETED
if empty returned -> EMPTY_RETURNED
if delivered -> CONTAINER_DELIVERED
if OOC received -> OOC_RECEIVED
if DO received -> DO_RECEIVED
if ETA present -> ETA_TRACKING_ACTIVE
if pre-alert/import shipment exists -> IMPORT_SHIPMENT_CREATED
else -> IMPORT_PRE_ALERT_PENDING
```

Use safe best-effort mapping only.

Do not overwrite existing data without transition log/event.

---

# 12. Workflow State Machine Service

Add:

```txt
backend/app/services/workflow_state_machine_service.py
```

Functions:

```python
seed_workflow_definitions(db)

get_available_transitions(db, shipment, user)

request_workflow_transition(
    db,
    shipment_id,
    to_state,
    user,
    reason=None,
    source="user",
    force_manual_review=False,
)

apply_workflow_transition(
    db,
    shipment,
    to_state,
    user,
    reason=None,
    source="user",
)
```

Responsibilities:

```txt
determine flow_type from shipment
check current workflow_state
infer initial state if missing
check transition exists and is active
run Phase 9 validation checks
log WorkflowTransitionLog
create OperationalEvent
create ValidationIssue if transition invalid/risky
create Notification if manual review is required
update shipment.workflow_state only if transition allowed
```

Failure policy:

```txt
Transition failure must return clear API error.
It must not corrupt shipment data.
It must not partially update state without log.
```

---

# 13. Validation Rules for State Transitions

Add Phase 10 rules to rule definitions:

```txt
workflow_invalid_transition
workflow_missing_required_state_data
workflow_sensitive_transition_requires_confirmation
workflow_completed_shipment_transition_warning
workflow_archived_shipment_transition_block
workflow_import_do_without_free_days_warning
workflow_export_bl_approval_without_draft_warning
workflow_payment_state_without_charge_warning
```

Default:

```txt
is_enabled = true
is_blocking = false
```

Exception:

```txt
workflow_archived_shipment_transition_block may be blocking if tested safely.
```

---

# 14. Backend APIs

Add route:

```txt
backend/app/api/routes/workflow_state_machine.py
```

Prefix:

```txt
/api/workflow
```

Routes:

```txt
GET /api/workflow/states
GET /api/workflow/transitions
GET /api/workflow/shipments/{shipment_id}/state
GET /api/workflow/shipments/{shipment_id}/available-transitions
POST /api/workflow/shipments/{shipment_id}/transition
GET /api/workflow/shipments/{shipment_id}/timeline
```

---

## 14.1 Transition Request

Request:

```json
{
  "to_state": "BL_DRAFT_RECEIVED",
  "reason": "BL draft received from shipping line",
  "confirm_sensitive": false
}
```

Response:

```json
{
  "shipment_id": 1,
  "from_state": "BL_DRAFT_PENDING",
  "to_state": "BL_DRAFT_RECEIVED",
  "status": "applied",
  "manual_review_required": false,
  "validation_status": "passed"
}
```

If blocked:

```json
{
  "status": "blocked",
  "reason": "Invalid transition",
  "manual_review_required": true
}
```

---

## 14.2 Permissions

```txt
ADMIN: all workflow transition actions
STAFF: can transition non-sensitive operational states
VIEW_ONLY: read workflow state/timeline only
```

Sensitive states should require ADMIN or explicit confirmation.

Examples sensitive:

```txt
BL_APPROVED
FINAL_BL_RECEIVED
PAYMENT_RECEIVED
FREIGHT_PAID
IMPORT_COMPLETED
EXPORT_COMPLETED
```

---

# 15. Event / Validation / Notification Integration

Each transition attempt should create:

```txt
OperationalEvent: workflow.transition_requested
```

If applied:

```txt
OperationalEvent: workflow.transition_applied
```

If blocked/manual review:

```txt
ValidationIssue
Notification: Manual review required
WorkflowTransitionLog row
```

Do not replace existing audit logs. Add audit entries for:

```txt
workflow.transition_applied
workflow.transition_blocked
workflow.manual_review_required
```

---

# 16. Frontend Changes

Add workflow state-machine UI without breaking the existing shipment detail page.

## 16.1 Shipment Detail Workflow Panel

On shipment detail page add:

```txt
Workflow State panel
Current state badge
Flow type export/import
Available next transitions
Transition reason field
Transition button
Manual review warning if applicable
Link to timeline
```

Do not remove existing workflow/status UI.

---

## 16.2 Workflow Timeline

Add section/tab:

```txt
Workflow Timeline
```

Show:

```txt
transition time
from state
to state
actor
status
validation status
reason
```

---

## 16.3 Admin/Staff Action Rules

```txt
ADMIN can transition all allowed states.
STAFF can transition normal states.
VIEW_ONLY can only view.
```

Show clear disabled state for VIEW_ONLY.

---

## 16.4 Dashboard Widget

Add small widget:

```txt
Workflow Control
```

Show:

```txt
shipments with manual_review_required
recent blocked transitions
shipments with missing workflow_state
link to validation issues/events
```

This widget should fail independently.

---

# 17. AI Assistant Integration

Update AI context/fallback for:

```txt
What is the workflow state of shipment FF-EXP-2026-001?
What shipments are stuck?
Which shipments need manual workflow review?
What are the next steps for this shipment?
Show invalid workflow transitions.
```

AI rules:

```txt
AI remains read-only.
AI cannot transition shipment state.
AI cannot approve sensitive states.
AI can recommend next allowed transitions only.
```

---

# 18. README / Docs

Update README with:

```txt
Phase 10 workflow state machines
Export state chain
Import state chain
Transition API
Workflow timeline
Manual review behavior
Permission model
Non-goals
```

Add:

```txt
docs/PHASE_10_EXPORT_IMPORT_STATE_MACHINES.md
```

Include:

```txt
Architecture
States
Transitions
APIs
Permissions
Validation/rule integration
How Phase 10 prepares Phase 11 container lifecycle
```

---

# 19. Backend Test Plan

Run:

```bash
cd backend
source .venv/bin/activate
python -m compileall app
```

Alembic:

```bash
alembic history
alembic upgrade head
alembic current
```

API smoke:

```txt
Login as ADMIN
GET /api/workflow/states
GET /api/workflow/transitions
GET shipment workflow state
GET available transitions
POST valid transition
POST invalid transition
GET workflow timeline
```

Permission smoke:

```txt
ADMIN can transition
STAFF can transition normal state
VIEW_ONLY cannot transition
VIEW_ONLY can read state/timeline
```

Regression smoke:

```txt
Existing shipment CRUD still works
Existing workflow/status UI still works
BL management still works
Demurrage still works
Tasks still work
Charges/reports still work
Events/validation issues still work
Notifications still work
AI/Gmail still work
```

---

# 20. Frontend Test Plan

Run:

```bash
cd frontend
npm run build
```

Manual smoke:

```txt
Shipment detail loads
Workflow panel appears
Current state displays
Available transitions display
Valid transition works
Invalid transition shows error/manual review
Timeline displays
VIEW_ONLY cannot transition
Dashboard still loads
Existing shipment tabs still work
```

---

# 21. Security Test Plan

Run:

```bash
git status
git diff

find . -name ".env" -o -name "node_modules" -o -name ".venv" -o -name "dist" -o -name "client_secret*.json"

grep -R "GOOGLE_CLIENT_SECRET" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "GROQ_API_KEY" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "OPENAI_API_KEY" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "postgresql://" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "JWT_SECRET_KEY=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "DATABASE_URL=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
```

Also inspect workflow transition metadata for:

```txt
password
token
secret
authorization
client_secret
refresh_token
access_token
DATABASE_URL
JWT
```

No sensitive values should be stored.

---

# 22. Acceptance Criteria

Phase 10 is complete only when:

```txt
[ ] Backend compiles
[ ] Frontend builds
[ ] Alembic migration exists
[ ] Workflow state definitions seeded
[ ] Workflow transition definitions seeded
[ ] Shipment workflow_state exists safely
[ ] Existing shipments can infer initial state
[ ] Valid transitions can be applied
[ ] Invalid transitions are blocked or sent to manual review
[ ] Transition logs are recorded
[ ] Operational events are recorded
[ ] Validation issues are created for invalid/risky transitions
[ ] Notifications are created for manual review transitions
[ ] Shipment detail workflow panel works
[ ] Workflow timeline works
[ ] ADMIN/STAFF/VIEW_ONLY permissions work
[ ] Existing Phase 1–9 features still work
[ ] AI can summarize workflow state read-only
[ ] No secrets committed or stored
```

---

# 23. Final Commit

After all checks pass:

```bash
git status
git add .
git commit -m "Implement phase 10 export import state machines"
```

Push:

```bash
git push -u origin phase-10-export-import-state-machines
```

---

# 24. Final Report Required

After implementation, report:

```txt
Backend compile result
Frontend build result
Alembic migration result
Workflow API test result
Workflow transition test result
Workflow timeline test result
Permission test result
Event/validation/notification integration result
AI workflow summary test result
Regression test result for Phases 1–9
Secret scan result
Git status
Commit hash
Known limitations
```
