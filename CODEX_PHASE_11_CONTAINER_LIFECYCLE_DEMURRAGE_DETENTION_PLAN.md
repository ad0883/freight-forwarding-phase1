# CODEX_PHASE_11_CONTAINER_LIFECYCLE_DEMURRAGE_DETENTION_PLAN.md

# Phase 11 — Container Lifecycle + Demurrage / Detention Separation

## Purpose

Implement **Phase 11** for the Freight Forwarding / EXIM Operational Intelligence System.

Phase 10 introduced strong export/import workflow state machines. Phase 11 now adds the next Master 1.1 operational layer:

```txt
Containers become real operational entities.
Multi-container shipments are supported properly.
Container-wise events are tracked.
Demurrage and detention are separated into different engines.
Import delivery and empty return become container-wise.
```

This phase is a major operational upgrade. It should be implemented safely without breaking existing shipment, demurrage, charge, report, notification, event, validation, or workflow behavior.

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
Phase 9.1    Gmail automation cleanup/dedupe/account scoping if completed
Phase 10     Strong export/import state machines
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
Workflow: Phase 10 export/import state machine
Events/validation: Phase 9 operational event + rule/validation issue foundation
```

Preserve all existing behavior:

```txt
Login
Users/admin management
Dashboard
Shipments
Parties
Tasks
Documents
BL Management
Existing demurrage page
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
Workflow state machine
```

---

# 2. Master 1.1 Alignment

Master 1.1 says:

```txt
Container is an operational entity, not a text field.
One shipment can have multiple containers.
Each container must have its own lifecycle, dates, demurrage/detention exposure, delivery/return status, and exception history.
Demurrage and detention must be separate engines.
```

Phase 11 implements this.

The target flow:

```txt
Shipment
→ one or more Container records
→ container-wise events
→ container-wise demurrage exposure
→ container-wise detention exposure
→ delivery / empty return lifecycle
→ validation issues / notifications / audit logs
→ finance links later
```

---

# 3. Strict Non-Goals

Do **not** implement in Phase 11:

```txt
Document upload/versioning/OCR
Exporter/importer portal
CHA/customs portal
Transporter portal
GPS integration
Tracking provider API adapters
Full exception engine
Approval engine / HOD bot
Bot governance / learning system
Payment gateway
Invoice PDF generation
Accounting integration
n8n
WhatsApp/SMS
Gmail send/modify/delete/archive
Autonomous AI writes
Strict tenant isolation for all operational records
```

Phase 11 is focused on:

```txt
container lifecycle
container events
demurrage vs detention separation
container-wise dashboard/reporting integration
```

---

# 4. Safety Rules

Phase 11 may:

```txt
create container records
create container events
calculate demurrage exposure
calculate detention exposure
create notifications for risk
create validation issues for broken container dates/statuses
create operational events and audit logs
show container lifecycle UI
```

Phase 11 must not automatically:

```txt
approve payments
raise invoices
release DO/OBL/documents
send emails
change customs-sensitive data
delete shipments
auto-apply Gmail suggestions
override workflow state without user action
```

Default policy:

```txt
Container lifecycle updates are user-driven.
Risk calculations are advisory until user confirms charges.
Demurrage/detention exposure does not automatically create payable/receivable charges.
```

---

# 5. Git Workflow

Start from updated `main` after Phase 10 and Gmail cleanup are stable.

```bash
git status
git log --oneline -8

git checkout main
git pull origin main
git checkout -b phase-11-container-lifecycle-demurrage-detention
```

Final commit:

```bash
git add .
git commit -m "Implement phase 11 container lifecycle demurrage detention"
git push -u origin phase-11-container-lifecycle-demurrage-detention
```

Do not deploy until tests pass.

---

# 6. Database / Alembic Migration

Use Alembic.

Add migration:

```txt
phase11_container_lifecycle
```

Revision ID must be <= 32 characters.

New tables:

```txt
containers
container_events
demurrage_detention_rules
container_demurrage_records
container_detention_records
```

Optional if useful:

```txt
container_exposure_snapshots
```

Shipment compatibility:

```txt
Keep old shipment-level container_no/container_type fields if they exist.
Do not remove old demurrage fields.
Do not break current demurrage page.
```

All new fields must be nullable or have safe defaults.

Rules:

```txt
No data reset
No table drops
No destructive renames
No breaking changes to existing shipment or demurrage schema
```

---

# 7. Backend Models

## 7.1 Container

Table:

```txt
containers
```

Fields:

```txt
id
shipment_id
container_number
container_size
container_type
soc_coc nullable
seal_number nullable
gross_weight nullable
tare_weight nullable
package_count nullable
current_status
current_location nullable
is_active
created_at
updated_at

planned_date nullable
empty_release_date nullable
empty_pickup_date nullable
factory_arrival_date nullable
stuffing_start_date nullable
stuffing_completed_date nullable
sealed_date nullable
gate_in_date nullable
loaded_on_vessel_date nullable
departed_date nullable

expected_arrival_date nullable
discharge_date nullable
do_received_date nullable
gate_out_date nullable
delivery_date nullable
empty_return_deadline nullable
empty_return_date nullable
closed_at nullable

demurrage_free_days nullable
detention_free_days nullable
demurrage_start_date nullable
demurrage_end_date nullable
detention_start_date nullable
detention_end_date nullable

metadata_json nullable
```

Indexes:

```txt
shipment_id
container_number
current_status
empty_return_deadline
discharge_date
delivery_date
```

Constraints:

```txt
Container number should be unique among active containers when feasible.
Do not break if old historical duplicate text exists.
```

---

## 7.2 ContainerEvent

Table:

```txt
container_events
```

Fields:

```txt
id
container_id
shipment_id
event_type
event_date
location nullable
source
description nullable
actor_user_id nullable
actor_name nullable
metadata_json nullable
created_at
```

Sources:

```txt
user
system
gmail
workflow
tracking
transport
line
cha
```

Event types:

```txt
CONTAINER_CREATED
CONTAINER_PLANNED
EMPTY_RELEASED
EMPTY_PICKUP_SCHEDULED
EMPTY_PICKED_UP
ARRIVED_AT_FACTORY
STUFFING_STARTED
STUFFING_COMPLETED
SEALED
DISPATCHED_TO_PORT
GATE_IN
LOADED_ON_VESSEL
DEPARTED

EXPECTED_ON_VESSEL
ARRIVED_AT_PORT
DISCHARGED
DO_RECEIVED
CLEARED_FOR_DELIVERY
GATE_OUT
OUT_FOR_DELIVERY
DELIVERED
DE_STUFFED_IF_APPLICABLE
EMPTY_RETURN_PENDING
EMPTY_RETURNED
CLOSED

DEMURRAGE_STARTED
DEMURRAGE_STOPPED
DETENTION_STARTED
DETENTION_STOPPED
MANUAL_CORRECTION
```

Rules:

```txt
Do not store secrets/raw email bodies.
Events are append-only.
```

---

## 7.3 DemurrageDetentionRule

Table:

```txt
demurrage_detention_rules
```

Fields:

```txt
id
name
rule_type
shipment_direction nullable
container_size nullable
container_type nullable
free_days
currency
rate_per_day nullable
slab_json nullable
source nullable
is_active
created_at
updated_at
```

`rule_type`:

```txt
demurrage
detention
```

Purpose:

```txt
Store basic free-day and daily-rate assumptions.
Detailed line-wise tariff engine can come later.
```

---

## 7.4 ContainerDemurrageRecord

Table:

```txt
container_demurrage_records
```

Fields:

```txt
id
container_id
shipment_id
start_date
end_date nullable
free_days
days_used
chargeable_days
currency
estimated_amount
status
source
created_at
updated_at
```

Status:

```txt
estimated
running
finalized
waived
not_applicable
```

---

## 7.5 ContainerDetentionRecord

Table:

```txt
container_detention_records
```

Fields:

```txt
id
container_id
shipment_id
start_date
end_date nullable
free_days
days_used
chargeable_days
currency
estimated_amount
status
source
created_at
updated_at
```

Status:

```txt
estimated
running
finalized
waived
not_applicable
```

---

# 8. Container State Chains

## 8.1 Export Container Lifecycle

Use exact statuses:

```txt
CONTAINER_PLANNED
EMPTY_RELEASED
EMPTY_PICKUP_SCHEDULED
EMPTY_PICKED_UP
ARRIVED_AT_FACTORY
STUFFING_STARTED
STUFFING_COMPLETED
SEALED
DISPATCHED_TO_PORT
GATE_IN
LOADED_ON_VESSEL
DEPARTED
CLOSED
```

## 8.2 Import Container Lifecycle

Use exact statuses:

```txt
EXPECTED_ON_VESSEL
ARRIVED_AT_PORT
DISCHARGED
DO_RECEIVED
CLEARED_FOR_DELIVERY
GATE_OUT
OUT_FOR_DELIVERY
DELIVERED
DE_STUFFED_IF_APPLICABLE
EMPTY_RETURN_PENDING
EMPTY_RETURNED
CLOSED
```

---

# 9. Demurrage vs Detention Logic

## 9.1 Demurrage

Demurrage occurs in port/terminal/storage context.

Tracked by:

```txt
arrival/discharge date
free days start date
free days end date
delivery date / gate-out date
port/CFS basis
daily/slab rate
```

Basic Phase 11 rule:

```txt
demurrage_start_date = discharge_date or arrival date
demurrage_end_date = delivery_date or gate_out_date if available
chargeable_days = max(0, days_used - free_days)
```

For export:

```txt
demurrage may apply if gate-in/storage context exceeds allowed days.
Keep export demurrage simple/advisory in Phase 11.
```

## 9.2 Detention

Detention occurs outside terminal/container usage context.

Tracked by:

```txt
gate_out/delivery date
empty return deadline
empty return date
free detention days
daily/slab rate
```

Basic Phase 11 rule:

```txt
detention_start_date = delivery_date or gate_out_date
detention_end_date = empty_return_date if available else today
chargeable_days = max(0, days_used - free_days)
```

## 9.3 Important Separation Rule

Do not mix:

```txt
demurrage amount
detention amount
```

They must be displayed, calculated, and finalized separately.

Do not automatically create charge entries from estimates.

---

# 10. Backfill / Migration From Existing Shipment Fields

Existing shipments may have fields like:

```txt
container_number
container_type
free_days
demurrage fields
```

Add safe service:

```txt
backend/app/services/container_backfill_service.py
```

Function:

```python
backfill_containers_from_shipments(db, dry_run=True)
```

Rules:

```txt
Dry-run by default.
Do not run automatically in production.
If a shipment has one container_number text, create one Container suggestion or record only with explicit admin action.
If container_number contains comma-separated values, split only if confident and show warnings.
Do not delete old shipment fields.
Do not overwrite existing Container records.
```

Add admin-only endpoint:

```txt
POST /api/containers/backfill-from-shipments
```

Input:

```json
{
  "dry_run": true
}
```

---

# 11. Backend Services

## 11.1 container_service.py

File:

```txt
backend/app/services/container_service.py
```

Functions:

```python
create_container(db, shipment_id, data, user)
update_container(db, container_id, data, user)
list_containers(db, filters, user)
get_container(db, container_id, user)
record_container_event(db, container, event_type, event_date=None, user=None, source="user", metadata=None)
transition_container_status(db, container_id, new_status, user, reason=None)
```

Responsibilities:

```txt
validate shipment exists
validate container number format
create container events
record operational events
create audit logs
create validation issues for risky data
```

---

## 11.2 container_validation_service.py

Checks:

```txt
container_number_format_warning
container_duplicate_active_warning
container_loaded_before_gate_in_warning
import_container_delivered_before_do_warning
empty_return_before_delivery_warning
gate_in_after_cutoff_warning
partial_delivery_supported_info
```

Integrate with Phase 9 validation issues.

---

## 11.3 demurrage_detention_service.py

File:

```txt
backend/app/services/demurrage_detention_service.py
```

Functions:

```python
calculate_demurrage_for_container(db, container_id)
calculate_detention_for_container(db, container_id)
refresh_container_exposure(db, container_id, user=None)
refresh_shipment_container_exposure(db, shipment_id, user=None)
```

Output:

```txt
demurrage_days_used
demurrage_chargeable_days
demurrage_estimated_amount
detention_days_used
detention_chargeable_days
detention_estimated_amount
risk_level
```

Risk levels:

```txt
none
info
warning
critical
running
```

---

# 12. Backend APIs

Add route:

```txt
backend/app/api/routes/containers.py
```

Prefix:

```txt
/api/containers
```

Routes:

```txt
GET /api/containers
POST /api/containers
GET /api/containers/{container_id}
PATCH /api/containers/{container_id}
DELETE /api/containers/{container_id}
GET /api/containers/{container_id}/events
POST /api/containers/{container_id}/events
POST /api/containers/{container_id}/transition
GET /api/containers/{container_id}/exposure
POST /api/containers/{container_id}/refresh-exposure
POST /api/containers/backfill-from-shipments
```

Shipment-specific routes:

```txt
GET /api/shipments/{shipment_id}/containers
POST /api/shipments/{shipment_id}/containers
GET /api/shipments/{shipment_id}/container-exposure
POST /api/shipments/{shipment_id}/refresh-container-exposure
```

Permissions:

```txt
ADMIN: all
STAFF: create/update/transition/refresh
VIEW_ONLY: read-only
```

Delete behavior:

```txt
Prefer soft-delete/deactivate if implemented.
Do not hard-delete containers with events unless ADMIN and confirmed.
```

---

# 13. Notifications / Alerts Integration

Create notifications for:

```txt
demurrage free days remaining <= 3
demurrage free days remaining <= 1
demurrage running
detention deadline within 3 days
detention deadline within 1 day
detention running
empty return overdue
container lifecycle broken
```

Dedupe keys:

```txt
container_demurrage_warning:{container_id}:{date}
container_demurrage_running:{container_id}
container_detention_warning:{container_id}:{date}
container_detention_running:{container_id}
container_empty_return_overdue:{container_id}
container_lifecycle_broken:{container_id}:{rule_key}
```

Do not duplicate notifications on repeated refresh.

---

# 14. Events / Audit Integration

Operational events:

```txt
container.created
container.updated
container.status_changed
container.event_added
container.exposure_refreshed
container.backfill_dry_run
container.backfill_applied
demurrage.calculated
detention.calculated
```

Audit logs:

```txt
container.create
container.update
container.status_change
container.event_add
container.backfill
container.exposure_refresh
```

Sanitize metadata.

---

# 15. Workflow Integration

Phase 11 should integrate softly with Phase 10 workflow.

Examples:

```txt
When container status changes to GATE_IN, suggest or allow workflow move to CONTAINER_GATE_IN.
When import container status changes to DO_RECEIVED, suggest or allow workflow move to DO_RECEIVED.
When empty return completes, suggest workflow move to EMPTY_RETURNED.
```

Do not automatically force shipment workflow transitions without user confirmation.

---

# 16. AI Assistant Integration

Update AI read-only context/fallback for:

```txt
Show containers for FF-EXP-2026-001.
Which containers have demurrage risk?
Which containers have detention risk?
Which empty returns are overdue?
What is container ABCD1234567 status?
What is the demurrage exposure for this shipment?
```

AI rules:

```txt
AI remains read-only.
AI cannot create/update containers.
AI cannot finalize demurrage/detention.
AI cannot create charges automatically.
```

---

# 17. Frontend Changes

## 17.1 Shipment Detail Containers Tab

Add or improve tab:

```txt
Containers
```

Show:

```txt
Container list
Container number
Size/type
Seal number
Current status
Important dates
Demurrage risk
Detention risk
Actions
```

Actions:

```txt
Add container
Edit container
Add event
Transition status
Refresh exposure
View timeline
```

VIEW_ONLY:

```txt
read-only
```

---

## 17.2 Container Detail / Drawer

Show:

```txt
Container summary
Lifecycle timeline
Dates
Demurrage panel
Detention panel
Events
Validation issues
Notifications
```

---

## 17.3 Dashboard Widgets

Add widgets:

```txt
Container Risk
Demurrage / Detention Exposure
Empty Return Overdue
```

Do not break existing dashboard widgets.

Widgets should fail independently.

---

## 17.4 Reports

Add simple report section:

```txt
Container Exposure Report
```

Columns:

```txt
Shipment
Container
Status
Demurrage risk
Demurrage estimated amount
Detention risk
Detention estimated amount
Empty return deadline
```

Do not change existing financial P&L calculations.

---

# 18. README / Docs

Update README with:

```txt
Phase 11 container lifecycle
multi-container support
demurrage vs detention separation
container events
container exposure calculations
backfill strategy
non-goals
```

Add:

```txt
docs/PHASE_11_CONTAINER_LIFECYCLE_DEMURRAGE_DETENTION.md
```

Include:

```txt
Architecture
Models
APIs
State chains
Demurrage calculation
Detention calculation
Validation rules
Notifications
How Phase 11 prepares transport/GPS and tracking adapters
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
Create shipment
Create container for shipment
List shipment containers
Update container
Add container event
Transition container status
Refresh container exposure
Get shipment container exposure
Run backfill dry-run
```

Validation tests:

```txt
Invalid container number creates validation issue
Duplicate active container creates warning
Empty return before delivery creates validation issue
Import delivery before DO creates validation issue
Demurrage risk notification created
Detention risk notification created
```

Regression:

```txt
Existing shipment CRUD still works
Existing demurrage page still works
Charges/P&L unchanged
Reports unchanged
Workflow state machine still works
Events/validation issues still work
Gmail automation still works
AI still works
Notifications still work
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
Containers tab loads
Add container works
Edit container works
Add event works
Transition status works
Refresh exposure works
Container timeline displays
Dashboard container widgets load
Reports still load
VIEW_ONLY cannot write
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

Also inspect metadata for:

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

Phase 11 is complete only when:

```txt
[ ] Backend compiles
[ ] Frontend builds
[ ] Alembic migration exists
[ ] Container model/table exists
[ ] ContainerEvent model/table exists
[ ] Demurrage/detention records exist
[ ] Shipment can have multiple containers
[ ] Container events are append-only
[ ] Container status transitions work
[ ] Container-wise demurrage is calculated
[ ] Container-wise detention is calculated
[ ] Demurrage and detention are separated
[ ] Demurrage/detention notifications work
[ ] Container validation issues work
[ ] Shipment detail Containers tab works
[ ] Container timeline works
[ ] Dashboard container risk widget works
[ ] Reports remain stable
[ ] Existing Phase 1–10 features still work
[ ] AI can summarize container/demurrage/detention read-only
[ ] No secrets committed or stored
```

---

# 23. Final Commit

After all checks pass:

```bash
git status
git add .
git commit -m "Implement phase 11 container lifecycle demurrage detention"
```

Push:

```bash
git push -u origin phase-11-container-lifecycle-demurrage-detention
```

---

# 24. Final Report Required

After implementation, report:

```txt
Backend compile result
Frontend build result
Alembic migration result
Container API test result
Container event/timeline test result
Container transition test result
Demurrage calculation test result
Detention calculation test result
Notification integration result
Validation issue integration result
AI container summary test result
Regression test result for Phases 1–10
Secret scan result
Git status
Commit hash
Known limitations
```
