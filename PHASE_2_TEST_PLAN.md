# Phase 2 Test Plan — Freight Forwarding System

## Purpose

Use this file to test the implemented **Phase 2 Tracking & Alerts** features before starting Phase 3.

Phase 2 includes:

```txt
Workflow automation
BL Management tab
Demurrage calculator
Follow-up Log UI
Improved alert rules
Pending tasks improvements
Role permission checks
Mock AI Phase 2 questions
```

Do not start Phase 3 until all important tests pass.

---

## 1. App URLs

```txt
Backend:  http://127.0.0.1:8000
API Docs: http://127.0.0.1:8000/docs
Frontend: http://127.0.0.1:5173
```

---

## 2. Restart Backend

Stop old backend process with `Ctrl + C`.

Run:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Windows PowerShell:

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Expected:

```txt
Backend starts without crash.
http://127.0.0.1:8000 opens.
http://127.0.0.1:8000/docs opens.
No database model/table error.
```

---

## 3. Rebuild and Run Frontend

```bash
cd frontend
npm install
npm run build
npm run dev
```

Expected:

```txt
npm run build passes.
Frontend starts at http://127.0.0.1:5173.
No blank screen.
No missing import error.
```

---

## 4. Basic Login Test

Login as admin:

```txt
Email: admin@example.com
Password: admin123
```

Expected:

```txt
Login succeeds.
Dashboard opens.
Sidebar is visible.
No console crash.
```

---

## 5. Phase 1 Regression Test

### 5.1 Party Test

Go to `/parties`.

Create:

```txt
Name: Phase2 Test Exporter
Type: exporter
Contact Person: Test Contact
Email: phase2exporter@example.com
Phone: 9999999999
Country: India
GSTIN: TESTGSTIN123
```

Expected:

```txt
Party is created.
Party appears in list.
Party can be updated if update UI exists.
```

### 5.2 Export Shipment Creation

Go to `/shipments/new`.

Create export shipment:

```txt
Type: export
Exporter: Phase2 Test Exporter
Shipping Line: MSC
Vessel Name: MSC TEST
Voyage No: V001
Origin Port: INMUN
Destination Port: NLRTM
Container No: TEST1234567
Container Type: 20GP
ETD: any future date
ETA: any future date
Booking Ref: BOOK-PHASE2-EXP
Commodity: Garments
```

Expected:

```txt
Shipment is created.
Shipment code starts with FF-EXP.
Shipment detail page opens.
Default export documents are created.
Initial task is created.
```

### 5.3 Import Shipment Creation

Create import shipment:

```txt
Type: import
Importer: Phase2 Test Exporter or another importer party
Shipping Line: Maersk
Vessel Name: IMPORT TEST
Voyage No: I001
Origin Port: CNSHA
Destination Port: INNSA
Container No: IMP1234567
Container Type: 40GP
ETD: any past/current date
ETA: any future/current date
Booking Ref: BOOK-PHASE2-IMP
Commodity: Chemicals
```

Expected:

```txt
Shipment is created.
Shipment code starts with FF-IMP.
Default import documents are created.
Initial task is created.
```

---

## 6. Shipment Detail Tabs Test

Open an export shipment detail page.

Expected tabs:

```txt
Overview
Documents
Tasks
BL Management
Follow-up Log
Demurrage
```

For export shipment:

```txt
Overview opens.
Documents tab opens.
Tasks tab opens.
BL Management tab opens.
Follow-up Log tab opens.
Demurrage should be hidden or show "not applicable for export".
```

For import shipment:

```txt
Demurrage tab is available and usable.
BL Management tab is available.
Follow-up Log tab is available.
```

---

## 7. Export Workflow Automation Test

Open an export shipment.

Move through these statuses one by one:

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

After each update, check:

```txt
Status changes successfully.
No backend error.
No frontend blank screen.
New next task is created.
Duplicate next tasks are not created when same status is saved again.
```

### Export Side Effect Checks

```txt
SI Submitted:
- SI document should become sent if previously pending.

VGM Filed:
- VGM document should become received/approved if previously pending.

BL Draft Received:
- BL_DRAFT document should become received.
- BL draft received date should be set in BL Management if empty.

BL Approved:
- BL_DRAFT document should become approved.
- BL approval date should be set in BL Management if empty.

Final BL Received:
- FINAL_BL document should become received.
- Final BL date should be set in BL Management if empty.

Docs Collected:
- INVOICE should become received if pending.
- PACKING_LIST should become received if pending.
```

### Export Completion Check

When status becomes `Completed`, check:

```txt
Completed Shipments This Month should increase.
Live/active shipment count should no longer count this shipment if backend excludes completed shipments.
```

---

## 8. Import Workflow Automation Test

Open an import shipment.

Move through these statuses one by one:

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

After each update, check:

```txt
Status changes successfully.
Next task is created.
Duplicate next tasks are not created.
No backend error.
No frontend crash.
```

### Import Side Effect Checks

```txt
Freight Invoice Received:
- FREIGHT_INVOICE document should become received.

BL Surrender Confirmed:
- TELEX_RELEASE should update if applicable.

DO Received:
- DO document should become received.
- do_received_date should be set if the field exists.
- Demurrage start_date should be set to today if empty.

Container Delivered:
- container_delivered_date should be set if the field exists.
- Demurrage should stop/running status should update if implemented.
```

### Import Completion Check

When status becomes `Completed`, check:

```txt
Completed Shipments This Month should increase.
Shipment should no longer appear as active if completed shipments are excluded.
```

---

## 9. BL Management Tab Test

Open BL Management tab for an export shipment.

Fill:

```txt
BL Type: HBL
Draft Received Date: today
Corrections: Correct consignee address and container number.
Approval Date: today
Final BL Date: today
Surrender Done: false
Telex Release: false
Final BL Google Drive Link: https://drive.google.com/test-final-bl
```

Expected:

```txt
Save succeeds.
No error message.
Reload page.
Values remain saved.
File link opens in new tab if UI supports it.
```

Repeat for import shipment:

```txt
BL Type: Telex
Surrender Done: true
Telex Release: true
```

Expected:

```txt
Save succeeds.
Values persist.
```

---

## 10. Demurrage Calculator Test

Open an import shipment.

Go to Demurrage tab.

Set:

```txt
Free Days Allowed: 7
Start Date: today or 5 days ago
Rate Per Day: 1000
Currency: INR
Alert At Days: 3
Container Count: 2
```

Expected computed fields:

```txt
Free Days End Date = Start Date + Free Days Allowed
Days Used = Today - Start Date
Days Remaining = End Date - Today
Demurrage Running = No if days remaining > 0
Total Demurrage Due = 0 if not overdue
Status = within_free_days or expiring_soon
```

### Expiring Soon Test

Set:

```txt
Start Date: 5 days ago
Free Days Allowed: 7
Alert At Days: 3
```

Expected:

```txt
Days Remaining should be around 2.
Status should be expiring_soon.
UI should show warning style if implemented.
```

### Running Demurrage Test

Set:

```txt
Start Date: 10 days ago
Free Days Allowed: 7
Rate Per Day: 1000
Container Count: 2
```

Expected:

```txt
Days Remaining should be negative or 0.
Demurrage Running = Yes.
Total Demurrage Due should be positive.
Example: 3 overdue days * 1000 * 2 = 6000.
Status should be running.
UI should show critical style if implemented.
```

### Export Demurrage Test

Open export shipment Demurrage tab.

Expected:

```txt
Demurrage is hidden or shows:
Demurrage tracking is mainly applicable to import shipments.
```

---

## 11. Follow-Up Log Test

Open shipment detail.

Go to Follow-up Log tab.

Create follow-up:

```txt
Party: select any party
Channel: call
Summary: Called CHA and confirmed document status.
Next Action: Follow up tomorrow.
Status: open
```

Expected:

```txt
Follow-up is saved.
Follow-up appears in list.
Date is shown.
Party is shown if available.
Channel is shown.
Summary is shown.
Next action is shown.
Status is shown.
```

Update follow-up:

```txt
Status: closed
```

Expected:

```txt
Status updates successfully.
Reload page.
Status remains closed.
```

If delete exists:

```txt
Delete follow-up.
```

Expected:

```txt
Follow-up is removed.
No unrelated records are deleted.
```

---

## 12. Dashboard Phase 2 Test

Go to dashboard.

Expected cards:

```txt
Live Shipments
Pending Tasks
Future Bookings
Alerts Today
Completed Shipments This Month
```

Check:

```txt
Pending Tasks count decreases when task is marked done.
Completed Shipments count increases only when shipment status becomes Completed.
Completed Shipments does not increase when only a task is marked done.
```

Check panels:

```txt
Pending Tasks panel appears if implemented.
Critical Alerts / Recent Alerts panel appears if implemented.
Dashboard loads without error.
```

---

## 13. Task Duplicate Test

Open a shipment.

Set workflow status to:

```txt
Container Booked
```

Then save the same status again.

Expected:

```txt
Only one "Send Shipping Instruction" task exists for that shipment.
No duplicate auto-generated task is created.
```

Repeat for:

```txt
BL Draft Received
DO Received
Container Delivered
```

Expected:

```txt
No duplicate auto-generated tasks.
```

---

## 14. Alert Rules Test

Alert rules may run via APScheduler. If there is a manual trigger function or test endpoint, use it. Otherwise restart backend and verify scheduler starts without crashing.

### 14.1 Task Overdue Alert

Create or edit a task:

```txt
status: open
due_date: yesterday
```

Expected:

```txt
One WARNING alert is created.
Running job again should not create duplicate alert.
```

### 14.2 VGM Deadline Warning

For export shipment:

```txt
vgm_cutoff_date: tomorrow
VGM document status: pending
```

Expected:

```txt
WARNING alert is created.
No duplicate on repeated runs.
```

### 14.3 BL/SI Cutoff Warning

For export shipment:

```txt
bl_cutoff_date or si_cutoff_date: tomorrow
SI or BL_DRAFT status: pending
```

Expected:

```txt
WARNING alert is created.
```

### 14.4 Free Days Expiry Alert

For import shipment demurrage:

```txt
days_remaining <= alert_at_days
days_remaining > 0
```

Expected:

```txt
CRITICAL alert is created.
```

### 14.5 Demurrage Started Alert

For import shipment:

```txt
days_remaining <= 0
shipment.status is not Container Delivered / Freight Collected / Completed
```

Expected:

```txt
CRITICAL alert is created.
Demurrage status becomes running.
```

### 14.6 DO Not Collected Alert

For import shipment:

```txt
eta: more than 2 days ago
DO document status: pending
```

Expected:

```txt
CRITICAL alert is created.
```

### 14.7 Freight Invoice Chase Alert

For import shipment:

```txt
eta: within next 3 days
FREIGHT_INVOICE document status: pending
```

Expected:

```txt
WARNING alert is created.
```

---

## 15. Mock AI Phase 2 Test

Go to Mock AI page.

Ask:

```txt
Which shipments have free days expiring?
Which shipments have demurrage running?
Which shipments have BL approval pending?
Which follow-ups are open?
What is the status of FF-EXP-2026-001?
```

Expected:

```txt
Answers come from database rules.
No OpenAI API key is required.
No real OpenAI API call is made.
```

---

## 16. VIEW_ONLY Permission Test

Create or use a VIEW_ONLY user.

As admin, create user from API docs or user management:

```json
{
  "name": "View Only User",
  "email": "viewonly@example.com",
  "password": "view123",
  "role": "VIEW_ONLY"
}
```

Login as:

```txt
viewonly@example.com
view123
```

### VIEW_ONLY Should Read

```txt
Dashboard
Shipment list
Shipment detail
Documents
Tasks
BL Management
Demurrage
Follow-up Log
Alerts
Mock AI
Parties
```

### VIEW_ONLY Should Not Write

Try:

```txt
Create party
Update party
Create shipment
Update shipment
Update workflow status
Update document status
Add Google Drive document link
Create task
Mark task done
Reopen task
Update BL Management
Update Demurrage
Create follow-up
Update follow-up
Delete follow-up
Create user
```

Expected:

```txt
Write actions are hidden or fail gracefully.
Backend returns 403 Not enough permission.
No data is changed.
```

---

## 17. API Docs Test

Open:

```txt
http://127.0.0.1:8000/docs
```

Test important endpoints.

### Auth

```txt
POST /api/auth/login
GET  /api/auth/me
```

### Shipments

```txt
GET   /api/shipments/dashboard
GET   /api/shipments
POST  /api/shipments
GET   /api/shipments/{shipment_id}
PATCH /api/shipments/{shipment_id}
PATCH /api/shipments/{shipment_id}/workflow-status
```

### Documents

```txt
GET   /api/documents/shipment/{shipment_id}
PATCH /api/documents/{document_id}
```

### Tasks

```txt
GET   /api/tasks
POST  /api/tasks
PATCH /api/tasks/{task_id}
```

### BL Management

```txt
GET   /api/shipments/{shipment_id}/bl
PATCH /api/shipments/{shipment_id}/bl
```

### Demurrage

```txt
GET   /api/shipments/{shipment_id}/demurrage
PATCH /api/shipments/{shipment_id}/demurrage
```

### Follow-ups

```txt
GET    /api/shipments/{shipment_id}/followups
POST   /api/shipments/{shipment_id}/followups
PATCH  /api/followups/{followup_id}
DELETE /api/followups/{followup_id}
```

### Alerts

```txt
GET /api/alerts
```

### Mock AI

```txt
POST /api/ai/ask
```

Expected:

```txt
Unauthenticated requests return 401.
VIEW_ONLY write requests return 403.
Invalid IDs return 404.
Invalid workflow status returns 400.
```

---

## 18. Security and Git Review

Run from project root:

```bash
git status
git diff
```

Check ignored files:

```bash
find . -name ".env" -o -name "node_modules" -o -name ".venv" -o -name "dist"
```

Make sure these are not staged:

```txt
backend/.env
frontend/.env
backend/.venv
frontend/node_modules
frontend/dist
.DS_Store
```

Search for leaked secrets:

```bash
grep -R "postgresql://" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "JWT_SECRET_KEY=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "DATABASE_URL=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
```

Acceptable places:

```txt
.env.example
README
Markdown planning/testing docs
```

Not acceptable:

```txt
Real Neon URL
Real database password
Real JWT secret
Committed .env file
```

---

## 19. Backend Compile Check

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

## 20. Frontend Build Check

Run:

```bash
cd frontend
npm run build
```

Expected:

```txt
Build passes.
No JS build error.
No missing import.
```

---

## 21. Test Data Cleanup

After testing, clean temporary records:

```txt
Phase2 Test Exporter
Phase2 Test Importer
Phase2 Test Shipment
Phase2 Test Follow-up
viewonly@example.com if temporary
```

Do not delete real data.

Example cleanup idea:

```python
from app.db.session import SessionLocal
from app.models import Party, Shipment, Task, User, FollowUpLog

db = SessionLocal()

test_parties = db.query(Party).filter(Party.name.ilike("%Phase2 Test%")).all()
test_party_ids = [p.id for p in test_parties]

test_shipments = db.query(Shipment).filter(
    (Shipment.exporter_id.in_(test_party_ids)) |
    (Shipment.importer_id.in_(test_party_ids)) |
    (Shipment.booking_ref.ilike("%PHASE2%"))
).all()

for shipment in test_shipments:
    db.delete(shipment)

for party in test_parties:
    db.delete(party)

test_users = db.query(User).filter(User.email == "viewonly@example.com").all()
for user in test_users:
    db.delete(user)

db.commit()
db.close()
print("Phase 2 test data cleaned.")
```

Only run cleanup if you are sure the records are temporary.

---

## 22. Final Acceptance Checklist

```txt
[ ] Backend starts
[ ] API docs open
[ ] Backend compile passes
[ ] Frontend build passes
[ ] Frontend starts
[ ] Admin login works
[ ] Phase 1 party flow still works
[ ] Phase 1 shipment creation still works
[ ] Export workflow status update works
[ ] Import workflow status update works
[ ] Workflow creates next task
[ ] Workflow avoids duplicate tasks
[ ] Export workflow document side effects work
[ ] Import workflow document side effects work
[ ] Shipment can be marked Completed
[ ] Completed Shipments This Month updates only for completed shipments
[ ] BL Management loads
[ ] BL Management saves
[ ] BL Management persists after reload
[ ] Import Demurrage loads
[ ] Import Demurrage saves
[ ] Demurrage computed fields are correct
[ ] Export demurrage is hidden or marked not applicable
[ ] Follow-up Log creates records
[ ] Follow-up Log lists records
[ ] Follow-up Log updates records
[ ] Alerts list works
[ ] Alert rules do not duplicate alerts
[ ] Mock AI Phase 2 questions work
[ ] VIEW_ONLY can read
[ ] VIEW_ONLY cannot write
[ ] No OpenAI API added
[ ] No charges module added
[ ] No courier module added
[ ] No email parser added
[ ] No Celery/Redis added
[ ] No real secrets committed
[ ] Test data cleaned or clearly identified
[ ] README updated if needed
```

---

## 23. Final Commit

After all tests pass:

```bash
git status
git add .
git commit -m "Verify phase 2 tracking and alerts"
```

If implementation was not committed yet:

```bash
git add .
git commit -m "Implement phase 2 tracking and alerts"
```

Push:

```bash
git push
```

If on feature branch:

```bash
git push -u origin phase-2-tracking-alerts
```

---

## 24. Report Format

After testing, report results like this:

```txt
Phase 2 Test Result

Backend:
- Health check:
- API docs:
- Compile:

Frontend:
- Dev server:
- Production build:

Phase 1 regression:
- Party flow:
- Shipment creation:
- Dashboard:

Phase 2:
- Export workflow:
- Import workflow:
- BL Management:
- Demurrage:
- Follow-up Log:
- Alerts:
- Mock AI:

Permissions:
- Admin:
- Staff:
- View Only:

Security:
- .env ignored:
- No real secrets:
- Git status:

Final result:
- Passed / Failed
- Commit:
- Notes:
```
