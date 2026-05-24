# Codex Implementation Plan — Phase 3.5 Admin Cleanup & Safe Removal Controls

## Purpose

Implement **Phase 3.5** of the Freight Forwarding AI-Powered Management System.

Phase 3.5 is not a new business module. It is an **admin cleanup and safe removal patch** that should be implemented before Phase 4.

The system now has important linked data from Phase 1, Phase 2, and Phase 3:

```txt
Shipments
Parties
Documents
Tasks
Alerts
Follow-ups
BL Management
Demurrage
Charges
Reports
Dashboard summaries
Mock AI answers
```

Because records are now linked to finance and operations history, the system should not blindly hard-delete important operational records.

Phase 3.5 adds:

```txt
Safe Shipment Archive / Restore
Safe Party Deactivate / Reactivate
Party Permanent Delete only if unused
Safe Task Cancel / Restore
Manual Task Delete only if safe
Dashboard/list filtering for archived/inactive/cancelled records
README and tests
```

---

# 1. Existing System Context

The app already has:

```txt
Frontend: React.js + Vite
Backend: FastAPI
Database: PostgreSQL / Neon
Auth: JWT + bcrypt
Roles: ADMIN / STAFF / VIEW_ONLY
Phase 1: Core shipments, parties, documents, tasks, dashboard
Phase 2: Workflow, BL, demurrage, follow-ups, alerts
Phase 3: Charges, P&L, reports, dashboard financial cards
```

Existing hosted app:

```txt
Frontend: https://freight-frontend-u051.onrender.com
Backend:  https://freight-backend-au6c.onrender.com
```

Preserve all existing Phase 1, Phase 2, and Phase 3 behavior.

Do not break:

```txt
Login
Roles
Shipments
Parties
Documents
Tasks
Workflow automation
BL Management
Demurrage
Follow-up Log
Alerts
Charges
Reports
Mock AI
Dashboard
Render deployment
```

---

# 2. Phase 3.5 Scope

Implement only these cleanup/admin controls:

```txt
1. Archive / Restore Shipment
2. Deactivate / Reactivate Party
3. Delete Party Permanently only if unused
4. Cancel / Restore Task
5. Delete Task only if manual and safe
6. Hide archived/inactive/cancelled records by default
7. Add filters/toggles for showing archived/inactive/cancelled records
8. Update dashboard counts to exclude archived/cancelled items where appropriate
9. Update README
10. Run smoke tests
```

---

# 3. Strict Non-Goals

Do **not** implement these in Phase 3.5:

```txt
OpenAI API
Real AI/LLM integration
Email parsing
Gmail API
Google Drive API upload
AWS S3
Courier automation
Celery
Redis
Invoice PDF generation
Payment gateway
Accounting integration
New Phase 4 features
New Phase 5 features
```

Do not change the financial rule already implemented in Phase 3:

```txt
Cancelled charges stay in DB and are excluded from active totals.
```

---

# 4. Git Workflow

Before coding:

```bash
git status
git log --oneline -5
```

Make sure working tree is clean.

Create branch:

```bash
git checkout -b phase-3-5-admin-cleanup
```

If branch already exists:

```bash
git checkout phase-3-5-admin-cleanup
```

---

# 5. Core Design Rules

## 5.1 Do Not Hard Delete Important Operational History

Never blindly hard-delete:

```txt
Shipments
Used parties
Auto-generated workflow tasks
Charges already handled as cancelled in Phase 3
```

Reason:

```txt
Shipments are linked to documents, tasks, charges, BL, demurrage, follow-ups, and reports.
Parties are linked to shipments, charges, and follow-ups.
Auto-generated tasks are part of workflow history.
```

---

## 5.2 Hide, Do Not Clutter

Normal screens should show only active data.

Use filters/toggles for old data:

```txt
Active only = default
Include Archived = optional
Include Inactive = optional
Include Cancelled = optional
```

---

# 6. Shipment Archive / Restore

## 6.1 Backend Model Changes

Update `Shipment` model.

Add fields:

```txt
is_archived boolean default false
archived_at nullable datetime
archived_by nullable FK to users.id
archive_reason nullable text
```

Rules:

```txt
Archived shipments remain in database.
Do not delete linked documents, tasks, charges, BL, demurrage, follow-ups, or alerts.
Archived shipments should be hidden from normal lists and dashboard counts by default.
```

---

## 6.2 Backend Shipment Routes

Add routes:

```txt
PATCH /api/shipments/{shipment_id}/archive
PATCH /api/shipments/{shipment_id}/restore
```

### PATCH /api/shipments/{shipment_id}/archive

Input body:

```json
{
  "reason": "Wrong duplicate shipment created"
}
```

Behavior:

```txt
Validate shipment exists.
Only ADMIN can archive.
Set is_archived = true.
Set archived_at = current datetime.
Set archived_by = current user id.
Set archive_reason = provided reason.
Do not delete linked records.
Return updated shipment.
```

### PATCH /api/shipments/{shipment_id}/restore

Behavior:

```txt
Validate shipment exists.
Only ADMIN can restore.
Set is_archived = false.
Clear archived_at, archived_by, and archive_reason if appropriate.
Return updated shipment.
```

---

## 6.3 Shipment List Filtering

Update:

```txt
GET /api/shipments
```

Add query parameter:

```txt
include_archived=false by default
```

Default behavior:

```txt
GET /api/shipments should return only non-archived shipments.
```

If:

```txt
include_archived=true
```

Then return both active and archived shipments.

Optional additional query:

```txt
archived_only=true
```

If implemented, it should return only archived shipments.

---

## 6.4 Dashboard Rules for Archived Shipments

Archived shipments should not count in:

```txt
Live Shipments
Pending Tasks
Future Bookings
Completed Shipments This Month
Recent Shipments active list
Active financial summaries if those are designed for active operations
Mock AI active shipment answers
```

Important:

```txt
Historical reports may still include archived shipments if reporting endpoint intentionally includes all historical records.
```

For Phase 3.5, keep simple:

```txt
Operational dashboard excludes archived shipments.
Financial reports can still include charges unless route specifically says active only.
```

---

## 6.5 Frontend Shipment UI

Update shipment detail page:

```txt
Show Archive Shipment button for ADMIN only.
Ask for archive reason before archiving.
If shipment is archived, show Archived badge.
If shipment is archived, show Restore Shipment button for ADMIN only.
Hide Archive/Restore buttons for STAFF and VIEW_ONLY.
```

Use words:

```txt
Archive Shipment
Restore Shipment
```

Do not use:

```txt
Delete Shipment
```

Update shipment list page:

```txt
Hide archived shipments by default.
Add Include Archived toggle or filter if simple.
Archived shipments should show an Archived badge if included.
```

---

# 7. Party Deactivate / Reactivate / Delete If Unused

## 7.1 Backend Model Changes

Update `Party` model.

Add fields:

```txt
is_active boolean default true
deactivated_at nullable datetime
deactivated_by nullable FK to users.id
deactivation_reason nullable text
```

Rules:

```txt
Inactive parties remain in database.
Inactive parties should be hidden from new-selection dropdowns by default.
Old shipments, charges, and follow-ups must still show inactive party names.
```

---

## 7.2 Backend Party Routes

Add routes:

```txt
PATCH /api/parties/{party_id}/deactivate
PATCH /api/parties/{party_id}/reactivate
DELETE /api/parties/{party_id}
```

### PATCH /api/parties/{party_id}/deactivate

Input body:

```json
{
  "reason": "Old vendor no longer used"
}
```

Behavior:

```txt
Validate party exists.
Only ADMIN can deactivate.
Set is_active = false.
Set deactivated_at = current datetime.
Set deactivated_by = current user id.
Set deactivation_reason = provided reason.
Return updated party.
```

### PATCH /api/parties/{party_id}/reactivate

Behavior:

```txt
Validate party exists.
Only ADMIN can reactivate.
Set is_active = true.
Clear deactivated_at, deactivated_by, and deactivation_reason if appropriate.
Return updated party.
```

### DELETE /api/parties/{party_id}

Permanent delete is allowed only if the party is unused.

Before deleting, check references in:

```txt
shipments.exporter_id
shipments.importer_id
charges.party_id
follow_up_logs.party_id
any other table that references party_id
```

If used:

```txt
Do not delete.
Return 400:
"Party is used in existing records. Deactivate it instead."
```

If unused:

```txt
Allow permanent delete.
```

Permissions:

```txt
Only ADMIN can deactivate/reactivate/delete parties.
STAFF cannot remove parties.
VIEW_ONLY cannot remove parties.
```

---

## 7.3 Party List Filtering

Update:

```txt
GET /api/parties
```

Add query parameter:

```txt
include_inactive=false by default
```

Default behavior:

```txt
GET /api/parties should return only active parties.
```

If:

```txt
include_inactive=true
```

Return active and inactive parties.

Optional:

```txt
inactive_only=true
```

If implemented, return inactive parties only.

Dropdown behavior:

```txt
Create shipment dropdown should show active parties only.
Charge party dropdown should show active parties only.
Follow-up party dropdown should show active parties only.
```

Old records should still display inactive party names.

If the frontend needs old linked party names, use either:

```txt
1. Existing joined response if available.
2. Fetch party by ID even if inactive.
3. Include party name in read response where possible.
```

---

## 7.4 Frontend Party UI

Update Parties page:

```txt
Show Deactivate Party button for active parties, ADMIN only.
Show Reactivate Party button for inactive parties, ADMIN only.
Show Delete Permanently button for ADMIN only.
Hide these controls for STAFF and VIEW_ONLY.
```

Use words:

```txt
Deactivate Party
Reactivate Party
Delete Permanently
```

If backend returns 400 on delete:

```txt
Show:
"Party is used in existing records. Deactivate it instead."
```

Normal party page:

```txt
Show active parties by default.
Add Include Inactive toggle or filter if simple.
Inactive parties should show Inactive badge.
```

---

# 8. Task Cancel / Restore / Safe Delete

## 8.1 Backend Model Change

Current Task statuses likely include:

```txt
open
done
```

Add status:

```txt
cancelled
```

Rules:

```txt
open = active pending task
done = completed task
cancelled = task intentionally no longer needed
```

Cancelled tasks should not count as pending.

---

## 8.2 Backend Task Routes

Add routes:

```txt
PATCH /api/tasks/{task_id}/cancel
PATCH /api/tasks/{task_id}/restore
DELETE /api/tasks/{task_id}
```

### PATCH /api/tasks/{task_id}/cancel

Behavior:

```txt
Validate task exists.
ADMIN and STAFF can cancel.
VIEW_ONLY cannot cancel.
Set status = cancelled.
Return updated task.
```

### PATCH /api/tasks/{task_id}/restore

Behavior:

```txt
Validate task exists.
ADMIN and STAFF can restore.
VIEW_ONLY cannot restore.
Set status = open.
Return updated task.
```

### DELETE /api/tasks/{task_id}

Delete only manual tasks.

Rules:

```txt
If task.auto_generated = false:
    allow hard delete.

If task.auto_generated = true:
    block delete with 400:
    "Auto-generated workflow tasks should be cancelled instead of deleted."
```

Permissions:

```txt
ADMIN and STAFF can delete manual tasks.
VIEW_ONLY cannot delete tasks.
```

---

## 8.3 Task List Filtering

Update:

```txt
GET /api/tasks
```

Add query parameter:

```txt
include_cancelled=false by default
```

Default behavior:

```txt
Task list should exclude cancelled tasks.
```

If:

```txt
include_cancelled=true
```

Return cancelled tasks too.

Dashboard:

```txt
Pending Tasks count should include only status = open.
Done and cancelled should not count as pending.
```

Alerts:

```txt
Overdue task alerts should be generated only for status = open.
Cancelled tasks should not create overdue alerts.
```

Mock AI:

```txt
Pending task answers should include only open tasks.
Cancelled tasks should not appear unless user specifically asks for cancelled tasks.
```

---

## 8.4 Frontend Task UI

Update Tasks page and Shipment Detail Tasks tab.

Keep existing:

```txt
Done
Reopen
```

Add:

```txt
Cancel Task
Delete Task
```

Rules:

```txt
Cancel Task visible for ADMIN and STAFF.
Delete Task visible only if task.auto_generated = false.
Do not show Cancel/Delete to VIEW_ONLY.
Cancelled tasks hidden by default.
Add Include Cancelled toggle if simple.
If cancelled tasks are visible, show Cancelled badge.
For cancelled tasks, show Restore/Reopen option for ADMIN and STAFF.
```

User-facing wording:

```txt
Cancel Task
Restore Task
Delete Manual Task
```

Do not show generic delete for auto-generated workflow tasks.

---

# 9. Charges Reminder

Phase 3 already implemented:

```txt
Cancel Charge instead of hard delete.
Cancelled charges stay stored.
Cancelled charges excluded from active P&L/dashboard/report totals.
```

Do not change this behavior except to ensure it still works after Phase 3.5.

---

# 10. Permissions Summary

## ADMIN

Can:

```txt
Archive/restore shipments
Deactivate/reactivate parties
Delete unused parties
Cancel/restore tasks
Delete manual tasks
Use all existing write features
```

## STAFF

Can:

```txt
Cancel/restore tasks
Delete manual tasks if allowed by implementation
Use normal operational features
```

Cannot:

```txt
Archive/restore shipments
Deactivate/reactivate/delete parties
```

## VIEW_ONLY

Can:

```txt
Read dashboard
Read shipments
Read parties
Read tasks
Read documents
Read BL
Read demurrage
Read follow-ups
Read charges/reports
Read mock AI answers
```

Cannot:

```txt
Archive/restore shipments
Deactivate/reactivate/delete parties
Cancel/restore/delete tasks
Any write action
```

---

# 11. API Error Requirements

Return:

```txt
401 for unauthenticated
403 for insufficient permission
404 for missing shipment/party/task
400 for:
- deleting used party
- deleting auto-generated task
- invalid request
```

Do not crash.

Frontend should show readable errors.

---

# 12. README Updates

Update README with:

```txt
Phase 3.5 Admin Cleanup controls
Shipment Archive / Restore
Party Deactivate / Reactivate
Party Delete Permanently only if unused
Task Cancel / Restore
Manual Task Delete
Why hard deletion is avoided
How archived/inactive/cancelled records are hidden by default
Permission rules
```

Add explanation:

```txt
Archive/deactivate keeps history safe while avoiding UI clutter.
```

---

# 13. Testing Requirements

## 13.1 Backend Compile

Run:

```bash
cd backend
source .venv/bin/activate
python -m compileall app
```

Expected:

```txt
No syntax errors.
```

---

## 13.2 Frontend Build

Run:

```bash
cd frontend
npm run build
```

Expected:

```txt
Build passes.
```

---

## 13.3 Shipment Archive Tests

As ADMIN:

```txt
Create or select shipment.
Archive shipment with reason.
Confirm shipment disappears from normal shipment list.
Confirm dashboard active counts exclude archived shipment.
Confirm linked documents/tasks/charges/follow-ups still exist.
Call GET /api/shipments?include_archived=true and confirm shipment appears.
Restore shipment.
Confirm shipment appears in normal list again.
```

As STAFF:

```txt
Try archive shipment.
Expected: 403.
```

As VIEW_ONLY:

```txt
Try archive shipment.
Expected: 403.
```

---

## 13.4 Party Deactivate/Delete Tests

As ADMIN:

```txt
Create unused party.
Delete permanently.
Expected: success.

Create party linked to shipment.
Try delete permanently.
Expected: 400 with message:
"Party is used in existing records. Deactivate it instead."

Deactivate linked party.
Expected: success.

Confirm inactive party disappears from normal party list/dropdowns.
Confirm old shipment still shows inactive party name.

Reactivate party.
Confirm it appears in dropdowns again.
```

As STAFF:

```txt
Try deactivate/reactivate/delete party.
Expected: 403.
```

As VIEW_ONLY:

```txt
Try deactivate/reactivate/delete party.
Expected: 403.
```

---

## 13.5 Task Cancel/Delete Tests

As ADMIN or STAFF:

```txt
Create manual task.
Delete manual task.
Expected: success.

Try deleting auto-generated workflow task.
Expected: 400:
"Auto-generated workflow tasks should be cancelled instead of deleted."

Cancel auto-generated task.
Expected: success.

Confirm cancelled task disappears from default task list.
Confirm cancelled task does not count in dashboard Pending Tasks.

Use include_cancelled=true.
Confirm cancelled task appears with Cancelled badge.

Restore cancelled task.
Confirm task returns to open and appears in pending list.
```

As VIEW_ONLY:

```txt
Try cancel/restore/delete task.
Expected: 403.
```

---

## 13.6 Regression Tests

Confirm existing flows still work:

```txt
Admin login
Shipment creation
Party creation
Document status update
Workflow status update
BL Management
Demurrage
Follow-up Log
Charges
Reports
Dashboard
Mock AI
VIEW_ONLY read/write restrictions
```

---

## 13.7 Security Scan

Run:

```bash
git status
git diff
find . -name ".env" -o -name "node_modules" -o -name ".venv" -o -name "dist"

grep -R "postgresql://" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "JWT_SECRET_KEY=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "DATABASE_URL=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
```

Allowed matches:

```txt
.env.example
README
planning docs
test docs
```

Not allowed:

```txt
Real Neon URL
Real database password
Real JWT secret
Committed .env file
```

---

# 14. Acceptance Criteria

Phase 3.5 is complete only when:

```txt
[ ] Backend compiles
[ ] Frontend builds
[ ] Shipment archive works
[ ] Shipment restore works
[ ] Archived shipments hidden by default
[ ] Archived shipments available with include_archived=true
[ ] Archived shipments excluded from operational dashboard counts
[ ] Linked shipment records are preserved after archive
[ ] Party deactivate works
[ ] Party reactivate works
[ ] Unused party permanent delete works
[ ] Used party permanent delete is blocked
[ ] Inactive parties hidden from dropdowns by default
[ ] Old records still show inactive party names
[ ] Task cancel works
[ ] Task restore works
[ ] Manual task delete works
[ ] Auto-generated task delete is blocked
[ ] Cancelled tasks hidden by default
[ ] Cancelled tasks excluded from pending counts and overdue alerts
[ ] ADMIN permission works
[ ] STAFF restrictions work
[ ] VIEW_ONLY restrictions work
[ ] Phase 1 flows still work
[ ] Phase 2 flows still work
[ ] Phase 3 flows still work
[ ] No OpenAI/email/courier/payment features added
[ ] No real secrets committed
[ ] README updated
```

---

# 15. Final Commit

After implementation and tests:

```bash
git status
git add .
git commit -m "Add safe archive and deactivate controls"
```

Push:

```bash
git push -u origin phase-3-5-admin-cleanup
```

---

# 16. Final Report Required

After implementation, report:

```txt
Backend compile result
Frontend build result
Shipment archive/restore test result
Party deactivate/reactivate/delete test result
Task cancel/delete test result
Permission test result
Regression test result
Secret scan result
Git status
Commit hash
Known limitations
```
