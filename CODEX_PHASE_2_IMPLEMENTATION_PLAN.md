# Codex Implementation Plan — Phase 2 Freight Forwarding System

## Purpose

Implement **Phase 2** of the Freight Forwarding AI-Powered Management System.

Phase 1 is already complete, tested, reviewed, and committed.

Phase 1 included:

```txt
React.js + Vite frontend
FastAPI backend
PostgreSQL / Neon-compatible database
JWT + bcrypt authentication
Role-based access: ADMIN, STAFF, VIEW_ONLY
Shipment creation for export/import
Auto shipment code generation
Party directory
Document checklist
Google Drive file_url field
Task module
Dashboard cards
Basic alerts
Mock AI assistant
```

Phase 2 should build on the existing app without breaking Phase 1.

---

# 1. Phase 2 Goal

Phase 2 is **Tracking & Alerts**.

Implement only these modules:

```txt
1. Export workflow automation
2. Import workflow automation
3. BL Management tab
4. Demurrage calculator
5. Follow-up Log UI and API completion
6. Improved alert rules
7. Dashboard/pending task improvements
8. Role permission polish
```

The main goal is to make the system operationally useful after shipment creation.

The app should now guide users through the export/import process, create next tasks automatically, track BL progress, track import free days/demurrage, log follow-ups, and show better alerts.

---

# 2. Strict Phase 2 Non-Goals

Do **not** implement these yet:

```txt
Charges module
Courier module
OpenAI API integration
Real AI agent
Gmail API
Email parsing
Google Drive API upload
AWS S3
Celery
Redis
Full reports module
Invoice/P&L module
Production-grade workflow engine
```

Do not start Phase 3, Phase 4, or Phase 5.

Use the existing stack:

```txt
Frontend: React.js + Vite
Backend: FastAPI
Database: PostgreSQL
Auth: JWT + bcrypt
Alerts/jobs: APScheduler
File handling: Google Drive links only
AI: Mock AI only
```

---

# 3. Before Coding

Codex must first inspect the existing repository.

Run:

```bash
git status
git log --oneline -5
```

Confirm the working tree is clean before starting.

If the previous Phase 1 label clarity commit is not present, apply it first:

```txt
Dashboard card label should be:
Completed Shipments This Month
```

Do not change the backend logic for that card.

Then create a new branch:

```bash
git checkout -b phase-2-tracking-alerts
```

---

# 4. Database and Model Additions

## 4.1 Existing Models to Preserve

Do not break existing models:

```txt
User
Party
Shipment
Document
Task
Alert
FollowUpLog
```

Do not rename existing routes unless necessary.

Do not break existing Phase 1 tests.

---

## 4.2 Add BLManagement Model

Create backend model:

```txt
BLManagement
```

Suggested table name:

```txt
bl_management
```

Fields:

```txt
id
shipment_id
bl_type
draft_received
corrections
approval_date
final_bl_date
surrender_done
telex_release
file_url
created_at
updated_at
```

Field details:

```txt
shipment_id: FK to shipments.id, required, unique if one BL record per shipment
bl_type: enum/string: OBL, HBL, Surrender, Telex, Seaway, Ocean
draft_received: date nullable
corrections: text nullable
approval_date: date nullable
final_bl_date: date nullable
surrender_done: boolean default false
telex_release: boolean default false
file_url: text nullable, stores Google Drive link
created_at: datetime
updated_at: datetime
```

Rules:

```txt
BLManagement must always link to shipment_id.
Create BLManagement lazily when first opened or on shipment creation.
For Phase 2, one BLManagement record per shipment is acceptable.
```

---

## 4.3 Add Demurrage Model

Create backend model:

```txt
Demurrage
```

Suggested table name:

```txt
demurrage
```

Fields:

```txt
id
shipment_id
free_days
start_date
rate_per_day
currency
alert_at_days
container_count
status
created_at
updated_at
```

Computed values should be returned by API, not necessarily stored:

```txt
free_days_end_date
days_used
days_remaining
is_demurrage_running
total_demurrage_due
```

Field details:

```txt
shipment_id: FK to shipments.id, required, unique if one demurrage record per shipment
free_days: integer nullable
start_date: date nullable
rate_per_day: decimal nullable
currency: string default INR
alert_at_days: integer default 3
container_count: integer default 1
status: within_free_days / expiring_soon / running / not_started
created_at: datetime
updated_at: datetime
```

Rules:

```txt
Demurrage is mainly for import shipments.
Frontend should hide or disable demurrage tab for export shipments or show "Not applicable for export".
Free days countdown starts when start_date is set.
Usually start_date may be DO received date or discharge date. For Phase 2, let user manually set start_date.
```

---

## 4.4 Optional Shipment Fields for Alert Deadlines

To support document deadline alerts, add nullable fields to Shipment only if they are not already present:

```txt
vgm_cutoff_date
bl_cutoff_date
si_cutoff_date
do_received_date
container_delivered_date
```

If adding migration is complex in the current repo, use `AUTO_CREATE_TABLES=true` only for local dev but document that production should use Alembic later.

For this Phase 2 implementation, it is acceptable to add these fields with nullable dates.

---

# 5. Backend Schemas

Add or update Pydantic schemas.

## 5.1 BL Schemas

Create:

```txt
BLManagementRead
BLManagementUpdate
```

Update fields:

```txt
bl_type
draft_received
corrections
approval_date
final_bl_date
surrender_done
telex_release
file_url
```

---

## 5.2 Demurrage Schemas

Create:

```txt
DemurrageRead
DemurrageUpdate
```

Read schema should include computed fields:

```txt
id
shipment_id
free_days
start_date
rate_per_day
currency
alert_at_days
container_count
status
free_days_end_date
days_used
days_remaining
is_demurrage_running
total_demurrage_due
created_at
updated_at
```

Update schema:

```txt
free_days
start_date
rate_per_day
currency
alert_at_days
container_count
```

---

## 5.3 FollowUp Schemas

If not already complete, create:

```txt
FollowUpCreate
FollowUpUpdate
FollowUpRead
```

Fields:

```txt
shipment_id
party_id
channel
summary
next_action
status
date
logged_by
```

---

# 6. Backend API Routes

## 6.1 BL Management Routes

Create route file:

```txt
backend/app/api/routes/bl_management.py
```

Add routes:

```txt
GET   /api/shipments/{shipment_id}/bl
PATCH /api/shipments/{shipment_id}/bl
```

Behavior:

```txt
GET should return existing BLManagement record.
If not exists, create default BLManagement record for the shipment and return it.
PATCH should update BL fields.
```

Permissions:

```txt
ADMIN and STAFF can update.
VIEW_ONLY can read only.
```

---

## 6.2 Demurrage Routes

Create route file:

```txt
backend/app/api/routes/demurrage.py
```

Add routes:

```txt
GET   /api/shipments/{shipment_id}/demurrage
PATCH /api/shipments/{shipment_id}/demurrage
```

Behavior:

```txt
GET should return existing Demurrage record with computed fields.
If not exists, create default Demurrage record and return it.
PATCH should update demurrage fields and recalculate status.
```

Permissions:

```txt
ADMIN and STAFF can update.
VIEW_ONLY can read only.
```

Rules:

```txt
For export shipments, GET can return a clear message or default record with not_applicable flag.
Do not block imports.
```

Preferred simple behavior:

```txt
Frontend hides/labels demurrage as not applicable for export.
Backend can still allow a record but should not auto-create alerts for export demurrage.
```

---

## 6.3 Follow-Up Routes

Create or complete route file:

```txt
backend/app/api/routes/followups.py
```

Routes:

```txt
GET   /api/shipments/{shipment_id}/followups
POST  /api/shipments/{shipment_id}/followups
PATCH /api/followups/{followup_id}
DELETE /api/followups/{followup_id}
```

Permissions:

```txt
ADMIN and STAFF can create/update/delete.
VIEW_ONLY can read only.
```

Behavior:

```txt
List follow-ups newest first.
Each follow-up must link to shipment_id.
logged_by should be current user id.
```

---

## 6.4 Workflow Routes

Add a dedicated workflow endpoint.

Preferred route:

```txt
PATCH /api/shipments/{shipment_id}/workflow-status
```

Input:

```json
{
  "status": "Container Booked"
}
```

Behavior:

```txt
1. Validate shipment exists.
2. Validate status belongs to that shipment type's workflow.
3. Update shipment.status.
4. Create next auto-generated task if one exists.
5. Avoid duplicate auto-generated tasks for the same shipment and title.
6. Optionally update related document/BL/demurrage fields for key statuses.
7. Return updated shipment detail.
```

Permissions:

```txt
ADMIN and STAFF can update workflow.
VIEW_ONLY can read only.
```

Keep existing PATCH /api/shipments/{id} working for generic updates.

---

# 7. Workflow Automation

## 7.1 Export Workflow Statuses

Add these export statuses exactly:

```txt
Booking Received
Container Booked
SI Submitted
VGM Filed
BL Draft Received
BL Approved
Final BL Received
Docs Collected
Docs Dispatched
Overseas Coordinated
Freight Invoiced
Vessel Sailed
Completed
```

## 7.2 Export Next Task Mapping

When status is changed, create the next task:

```txt
Booking Received -> Book container with line
Container Booked -> Send Shipping Instruction
SI Submitted -> Follow up VGM
VGM Filed -> Check BL draft from line
BL Draft Received -> Get BL approval from exporter
BL Approved -> Request final BL from line
Final BL Received -> Collect Invoice and Packing List
Docs Collected -> Dispatch documents via courier
Docs Dispatched -> Coordinate with overseas FF
Overseas Coordinated -> Raise freight invoice to client
Freight Invoiced -> Confirm vessel sailing
Vessel Sailed -> Monitor until shipment completion
Completed -> No next task
```

---

## 7.3 Import Workflow Statuses

Add these import statuses exactly:

```txt
Pre-Alert Received
ETA Tracking Active
IGM Filed
Freight Invoice Received
BL Surrender Confirmed
DO Received
DO Handed to CHA
Clearance In Progress
Container Delivered
Freight Collected
Completed
```

## 7.4 Import Next Task Mapping

When status is changed, create the next task:

```txt
Pre-Alert Received -> Track ETA updates from line
ETA Tracking Active -> File IGM with shipping line
IGM Filed -> Follow up line for freight invoice
Freight Invoice Received -> Confirm BL surrender or telex
BL Surrender Confirmed -> Pay freight and get DO
DO Received -> Hand DO to CHA
DO Handed to CHA -> Track clearance status
Clearance In Progress -> Track container delivery
Container Delivered -> Collect freight from importer
Freight Collected -> Mark shipment completed
Completed -> No next task
```

---

## 7.5 Workflow Side Effects

When status changes, update related records where obvious.

Export side effects:

```txt
SI Submitted:
- update SI document status to sent if currently pending

VGM Filed:
- update VGM document status to received or approved if currently pending

BL Draft Received:
- update BL_DRAFT document status to received
- set BLManagement.draft_received to today if empty

BL Approved:
- update BL_DRAFT document status to approved
- set BLManagement.approval_date to today if empty

Final BL Received:
- update FINAL_BL document status to received
- set BLManagement.final_bl_date to today if empty

Docs Collected:
- update INVOICE and PACKING_LIST status to received if pending
```

Import side effects:

```txt
Freight Invoice Received:
- update FREIGHT_INVOICE document status to received

BL Surrender Confirmed:
- update TELEX_RELEASE document status to received/approved if applicable
- set BLManagement.surrender_done or telex_release manually from UI, not automatically unless clearly known

DO Received:
- update DO document status to received
- set Shipment.do_received_date to today if field exists
- set Demurrage.start_date to today if empty

Container Delivered:
- set Shipment.container_delivered_date to today if field exists
- stop demurrage running by status if applicable
```

Do not make destructive changes.

Do not overwrite user-entered dates if they already exist.

---

# 8. Improved Alert Rules

Keep APScheduler for Phase 2.

Do not add Celery or Redis.

Update:

```txt
backend/app/services/alert_service.py
```

## 8.1 Alert Types

Add alert priorities:

```txt
critical
warning
info
```

Existing priority system may already exist. Reuse it.

---

## 8.2 Alert Rules to Implement

Implement these rules:

### Rule 1: Task Overdue

```txt
If task.status = open and task.due_date < today:
    create WARNING alert
```

Avoid duplicates.

---

### Rule 2: VGM Deadline Warning

```txt
If shipment.type = export
and shipment.vgm_cutoff_date is not null
and vgm_cutoff_date is within next 2 days
and VGM document is not approved/received:
    create WARNING alert
```

---

### Rule 3: BL/SI Cutoff Warning

```txt
If shipment.type = export
and bl_cutoff_date or si_cutoff_date is within next 2 days
and SI or BL_DRAFT relevant document is not complete:
    create WARNING alert
```

---

### Rule 4: Free Days Expiry Alert

```txt
If shipment.type = import
and demurrage.start_date is set
and demurrage.days_remaining <= demurrage.alert_at_days
and demurrage.days_remaining > 0:
    create CRITICAL alert
```

---

### Rule 5: Demurrage Started

```txt
If shipment.type = import
and demurrage.days_remaining <= 0
and shipment.status is not Container Delivered / Freight Collected / Completed:
    create CRITICAL alert
    set demurrage.status = running
```

---

### Rule 6: DO Not Collected

```txt
If shipment.type = import
and shipment.eta is before today - 2 days
and DO document status is not received:
    create CRITICAL alert
```

---

### Rule 7: Freight Invoice Chase

```txt
If shipment.type = import
and shipment.eta is within next 3 days
and FREIGHT_INVOICE document status is pending:
    create WARNING alert
```

---

## 8.3 Avoid Duplicate Alerts

Use a stable duplicate check.

Example:

```txt
same shipment_id
same title
same priority
same alert type if alert_type field exists
not read or created recently
```

If no alert_type field exists, use title + shipment_id.

Do not spam duplicate alerts every scheduler run.

---

# 9. Frontend Phase 2 Changes

## 9.1 Shipment Detail Tabs

Update shipment detail page.

Tabs should become:

```txt
Overview
Documents
Tasks
BL Management
Follow-up Log
Demurrage
```

For export shipments:

```txt
Show BL Management.
Show Follow-up Log.
Show Demurrage as "Not applicable for export" or hide it.
```

For import shipments:

```txt
Show BL Management.
Show Follow-up Log.
Show Demurrage.
```

---

## 9.2 Workflow Status UI

In shipment detail Overview tab, add:

```txt
Current Status dropdown
Update Status button
```

The dropdown should show statuses based on shipment type.

For export shipments, show export statuses.

For import shipments, show import statuses.

When user updates status:

```txt
Call PATCH /api/shipments/{shipment_id}/workflow-status
Show success message
Reload shipment details
New auto task should appear in Tasks tab
Related document/BL/demurrage side effects should reflect
```

VIEW_ONLY users should not see update button or should be blocked gracefully.

---

## 9.3 BL Management Tab

Create frontend component/page section.

Fields:

```txt
BL Type dropdown
Draft Received date
Corrections textarea
Approval Date
Final BL Date
Surrender Done checkbox
Telex Release checkbox
Final BL Google Drive Link
Save button
```

BL type options:

```txt
OBL
HBL
Surrender
Telex
Seaway
Ocean
```

Behavior:

```txt
Load with GET /api/shipments/{shipment_id}/bl
Save with PATCH /api/shipments/{shipment_id}/bl
```

VIEW_ONLY:

```txt
Can view fields.
Cannot edit/save.
```

---

## 9.4 Demurrage Tab

Create frontend component/page section.

Fields:

```txt
Free Days Allowed
Start Date
Rate Per Day
Currency
Alert At Days
Container Count
Save button
```

Computed display:

```txt
Free Days End Date
Days Used
Days Remaining
Status
Demurrage Running: Yes/No
Total Demurrage Due
```

Visual behavior:

```txt
If days_remaining <= 0: show critical styling
If days_remaining <= alert_at_days and > 0: show warning styling
Otherwise normal styling
```

For export:

```txt
Display:
Demurrage tracking is mainly applicable to import shipments.
```

Do not create complicated charts.

---

## 9.5 Follow-Up Log Tab

Create frontend UI.

Fields for new follow-up:

```txt
Party dropdown
Channel dropdown: email / call / whatsapp / meeting
Summary textarea
Next Action textarea
Status dropdown: open / closed
Save button
```

List view:

```txt
Date
Party
Channel
Summary
Next Action
Status
Logged By if available
```

Behavior:

```txt
Load with GET /api/shipments/{shipment_id}/followups
Create with POST /api/shipments/{shipment_id}/followups
Update status with PATCH /api/followups/{followup_id}
Delete optional for ADMIN/STAFF
```

VIEW_ONLY:

```txt
Can read follow-ups.
Cannot create/update/delete.
```

---

## 9.6 Dashboard Improvements

Keep dashboard simple.

Add or improve sections:

```txt
Pending Tasks panel sorted by urgency
Recent Critical Alerts panel
```

Dashboard cards should remain:

```txt
Live Shipments
Pending Tasks
Future Bookings
Alerts Today
Completed Shipments This Month
```

Do not add charges/revenue cards yet.

Do not add completed tasks card unless very simple and not disruptive.

---

# 10. Mock AI Phase 2 Improvements

Keep mock AI only.

Extend `/api/ai/ask` with simple database-rule answers:

```txt
Which shipments have free days expiring?
Which shipments have demurrage running?
Which shipments have BL approval pending?
Which follow-ups are open?
What is the status of [shipment code]?
```

Do not call OpenAI API.

Do not add API key.

Do not add LLM logic.

---

# 11. Permissions

Maintain role logic:

```txt
ADMIN:
- full read/write access

STAFF:
- operational read/write access
- cannot manage users unless already allowed intentionally

VIEW_ONLY:
- read-only access
- cannot create/update/delete anything
```

Phase 2 routes must follow this rule.

VIEW_ONLY must not be able to:

```txt
Update workflow status
Update BL management
Update demurrage
Create/update/delete follow-ups
Create/update tasks
Update documents
```

---

# 12. Error Handling Requirements

Backend should return:

```txt
401 for unauthenticated requests
403 for insufficient permission
404 for missing shipment/record
400 for invalid workflow status
```

Frontend should show readable errors.

Do not crash to blank screen.

---

# 13. README Updates

Update README with Phase 2 information.

Add:

```txt
Phase 2 features
Workflow status automation
BL Management tab
Demurrage calculator
Follow-up Log tab
Improved alert rules
Mock AI Phase 2 examples
```

Add clear notes:

```txt
Charges are not implemented yet.
Courier tracking is not implemented yet.
OpenAI API is not implemented yet.
Email parsing is not implemented yet.
File upload is not implemented yet; use Google Drive links.
Celery/Redis are not used yet; APScheduler is used for Phase 2 alerts.
```

---

# 14. Testing Requirements

After coding, run backend checks:

```bash
cd backend
source .venv/bin/activate
python -m compileall app
uvicorn app.main:app --reload
```

Open:

```txt
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

Run frontend checks:

```bash
cd frontend
npm install
npm run build
npm run dev
```

Open:

```txt
http://127.0.0.1:5173
```

---

# 15. Manual Test Flow

Test as ADMIN:

```txt
1. Login as admin.
2. Create exporter/importer/CHA/shipping line parties if needed.
3. Create export shipment.
4. Open shipment detail.
5. Change export status from Booking Received to Container Booked.
6. Confirm next task is created.
7. Change status to SI Submitted.
8. Confirm SI document status updates.
9. Change status to BL Draft Received.
10. Confirm BL Draft document updates and BL draft date is set.
11. Open BL Management tab.
12. Save BL type, correction notes, approval date, final BL link.
13. Confirm save persists.
14. Create import shipment.
15. Change import status to DO Received.
16. Confirm DO document updates.
17. Confirm demurrage start_date is set if empty.
18. Open Demurrage tab.
19. Add free days, rate, currency, container count.
20. Confirm days remaining and total demurrage due display.
21. Add follow-up log.
22. Confirm follow-up appears in list.
23. Trigger/list alerts.
24. Ask Mock AI: Which shipments have demurrage running?
```

Test as VIEW_ONLY:

```txt
1. Login as VIEW_ONLY.
2. Open dashboard.
3. Open shipment detail.
4. Confirm Overview/Documents/Tasks/BL/Demurrage/Follow-up are readable.
5. Try to update workflow status.
6. Try to update BL.
7. Try to update demurrage.
8. Try to create follow-up.
9. All write attempts should be blocked with 403 or hidden UI.
```

---

# 16. Smoke Test Acceptance Criteria

Phase 2 is complete only when:

```txt
[ ] Backend compiles
[ ] Frontend builds
[ ] Existing Phase 1 flows still work
[ ] Admin login works
[ ] VIEW_ONLY read works
[ ] VIEW_ONLY write is blocked
[ ] Export workflow statuses work
[ ] Import workflow statuses work
[ ] Workflow status update creates next task
[ ] Duplicate workflow tasks are not created
[ ] Export workflow side effects update relevant documents
[ ] Import workflow side effects update relevant documents
[ ] BL Management GET works
[ ] BL Management PATCH works
[ ] BL tab appears in shipment detail
[ ] Demurrage GET works
[ ] Demurrage PATCH works
[ ] Demurrage computed fields display correctly
[ ] Demurrage tab appears for import
[ ] Export demurrage is hidden or marked not applicable
[ ] Follow-up list works
[ ] Follow-up create works
[ ] Follow-up update works
[ ] Alert rules run without crashing
[ ] Duplicate alerts are avoided
[ ] Dashboard still loads
[ ] Pending tasks panel works
[ ] Mock AI Phase 2 questions work
[ ] README updated
[ ] No OpenAI API added
[ ] No charges module added
[ ] No email parser added
[ ] No Celery/Redis added
[ ] No real secrets committed
```

---

# 17. Final Git Commands

After implementation and successful testing:

```bash
git status
git diff
git add .
git commit -m "Implement phase 2 tracking and alerts"
```

If already on feature branch:

```bash
git push -u origin phase-2-tracking-alerts
```

If working directly on main and user wants direct push:

```bash
git push
```

---

# 18. Final Codex Instruction

Implement Phase 2 only.

Do not start Phase 3.

Do not add charges, courier, OpenAI, Gmail, email parsing, Google Drive API, Celery, Redis, AWS S3, or reports.

Preserve all working Phase 1 behavior.

Use the existing project structure and coding style.

Use normal CSS only.

Make small, safe, testable changes.

After implementation, run backend compile check, frontend build, and smoke tests.

Commit with:

```bash
git commit -m "Implement phase 2 tracking and alerts"
```

Report clearly:

```txt
What changed
What was tested
Any files modified
Any new routes
Any new database tables/fields
Any known limitations
```
