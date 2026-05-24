# Codex Implementation Plan — Phase 3 Charges + Reporting

## Purpose

Implement **Phase 3** of the Freight Forwarding AI-Powered Management System.

Phase 1 and Phase 2 are already implemented, tested, committed, and hosted.

Existing hosted app:

```txt
Frontend: https://freight-frontend-u051.onrender.com
Backend:  https://freight-backend-au6c.onrender.com
```

Phase 3 should add the financial layer:

```txt
Charges Module
Payable / Receivable tracking
Per-shipment Profit & Loss
Pending collections
Monthly financial summaries
Reports page
Dashboard financial cards
Mock AI finance questions
```

The goal is to let the freight forwarder clearly see:

```txt
What we have to pay
What we have to collect
What is pending
What is received/paid
How much profit each shipment made
Which shipments have pending collections
Monthly business summary
```

---

# 1. Existing System Context

The app already has:

```txt
React.js + Vite frontend
FastAPI backend
PostgreSQL / Neon database
JWT + bcrypt authentication
Role-based access: ADMIN, STAFF, VIEW_ONLY
Shipment creation for export/import
Shipment code generation
Party directory
Document checklist
Workflow automation
BL Management
Demurrage calculator
Follow-up Log
Improved alerts
Mock AI assistant
Render deployment
```

Preserve all existing Phase 1 and Phase 2 behavior.

Do not break:

```txt
Login
Roles
Shipments
Documents
Tasks
Workflow status
BL Management
Demurrage
Follow-ups
Alerts
Mock AI existing questions
Hosted deployment
```

---

# 2. Phase 3 Scope

Build only these features:

```txt
1. Charges database model
2. Charges API routes
3. Charges tab in Shipment Detail
4. Shipment-wise Profit & Loss summary
5. Pending receivables/payables tracking
6. Dashboard financial cards
7. Reports page
8. Mock AI finance-related database answers
9. README update
10. Phase 3 tests/checklist
```

---

# 3. Strict Phase 3 Non-Goals

Do **not** implement these yet:

```txt
OpenAI API
Real AI / LLM integration
Email parsing
Gmail API
Google Drive API upload
AWS S3
Courier automation
Celery
Redis
Invoice PDF generation
Payment gateway
Accounting software integration
GST invoice automation
Bank reconciliation
Multi-currency exchange-rate automation
Advanced charts if they complicate build
```

Keep Phase 3 focused on **manual financial entry + reports**.

---

# 4. Git Workflow

Before coding:

```bash
git status
git log --oneline -5
```

Make sure working tree is clean.

Create a new branch:

```bash
git checkout -b phase-3-charges-reporting
```

If branch already exists:

```bash
git checkout phase-3-charges-reporting
```

---

# 5. Database Model

## 5.1 Add Charge Model

Create a new SQLAlchemy model:

```txt
Charge
```

Suggested table name:

```txt
charges
```

Fields:

```txt
id
shipment_id
charge_type
direction
amount
currency
party_id
status
invoice_no
date
notes
created_at
updated_at
```

Field details:

```txt
id: primary key
shipment_id: FK to shipments.id, required
charge_type: enum/string
direction: payable / receivable
amount: decimal, required
currency: string, default INR
party_id: FK to parties.id, nullable
status: pending / paid / received / cancelled
invoice_no: string nullable
date: date nullable
notes: text nullable
created_at: datetime
updated_at: datetime
```

Rules:

```txt
Every charge must link to shipment_id.
A charge cannot exist without a shipment.
party_id is optional because sometimes the user may not know the party yet.
amount must be >= 0.
direction controls how it affects P&L.
status controls whether it is pending or settled.
Cancelled charges should not count in totals.
```

---

## 5.2 Charge Type Options

Use these charge types:

```txt
ocean_freight
do_charges
bl_charges
hbl_charges
liner_charges
clearance_charges
courier_charges
agent_charges
demurrage
documentation
handling
transport
other
```

Readable frontend labels:

```txt
Ocean Freight
DO Charges
BL Charges
HBL Charges
Liner Charges
Clearance Charges
Courier Charges
Agent Charges
Demurrage
Documentation
Handling
Transport
Other
```

---

## 5.3 Direction Options

```txt
payable
receivable
```

Meaning:

```txt
payable = money the company must pay to line/agent/CHA/courier/etc.
receivable = money the company must collect from client/importer/exporter/etc.
```

---

## 5.4 Status Options

Use:

```txt
pending
paid
received
cancelled
```

Rules:

```txt
For payable charges:
- pending = not yet paid
- paid = paid to vendor/line/agent

For receivable charges:
- pending = not yet collected from client
- received = collected from client

cancelled = ignored from active totals
```

---

# 6. Backend Schemas

Create:

```txt
backend/app/schemas/charge.py
```

Schemas:

```txt
ChargeCreate
ChargeUpdate
ChargeRead
ShipmentPLSummary
DashboardFinancialSummary
MonthlyReportSummary
```

## 6.1 ChargeCreate

Fields:

```txt
shipment_id
charge_type
direction
amount
currency
party_id
status
invoice_no
date
notes
```

Required:

```txt
shipment_id
charge_type
direction
amount
```

Defaults:

```txt
currency = INR
status = pending
```

---

## 6.2 ChargeUpdate

Allow partial updates:

```txt
charge_type
direction
amount
currency
party_id
status
invoice_no
date
notes
```

---

## 6.3 ChargeRead

Return:

```txt
id
shipment_id
shipment_code if easy
charge_type
direction
amount
currency
party_id
party_name if easy
status
invoice_no
date
notes
created_at
updated_at
```

---

## 6.4 ShipmentPLSummary

Return:

```txt
shipment_id
shipment_code
currency
total_payable
total_receivable
total_paid
total_received
pending_payable
pending_receivable
net_profit
charge_count
multiple_currencies
```

Formula:

```txt
total_payable = sum(payable charges except cancelled)
total_receivable = sum(receivable charges except cancelled)
net_profit = total_receivable - total_payable

pending_payable = sum(payable charges with status pending)
pending_receivable = sum(receivable charges with status pending)

total_paid = sum(payable charges with status paid)
total_received = sum(receivable charges with status received)
```

For Phase 3, default reports can assume INR if most entries are INR.

If multiple currencies exist, return:

```txt
multiple_currencies = true
```

and show a frontend note:

```txt
Multiple currencies are present. Totals are not converted automatically.
```

---

# 7. Backend API Routes

Create route file:

```txt
backend/app/api/routes/charges.py
```

Register it in:

```txt
backend/app/main.py
```

## 7.1 Charge CRUD Routes

Create:

```txt
GET    /api/shipments/{shipment_id}/charges
POST   /api/shipments/{shipment_id}/charges
PATCH  /api/charges/{charge_id}
DELETE /api/charges/{charge_id}
```

Behavior:

```txt
GET:
- list all charges for shipment
- newest first or date desc

POST:
- create charge linked to shipment_id from path
- validate shipment exists

PATCH:
- update charge fields

DELETE:
- hard-delete charge if simple
- or mark cancelled if easier to preserve records
```

Permissions:

```txt
ADMIN and STAFF can create/update/delete.
VIEW_ONLY can read only.
```

---

## 7.2 Shipment P&L Route

Create:

```txt
GET /api/shipments/{shipment_id}/pnl
```

Returns:

```txt
ShipmentPLSummary
```

Use charges linked to that shipment.

---

## 7.3 Dashboard Financial Summary Route

Create:

```txt
GET /api/reports/dashboard-financials
```

Return:

```txt
pending_receivables
pending_payables
this_month_receivables
this_month_payables
this_month_profit
currency
multiple_currencies
```

Suggested rules:

```txt
pending_receivables = all receivable charges with status pending
pending_payables = all payable charges with status pending
this_month_receivables = receivable charges dated this month, excluding cancelled
this_month_payables = payable charges dated this month, excluding cancelled
this_month_profit = this_month_receivables - this_month_payables
```

If charge date is null:

```txt
Use created_at date as fallback.
```

---

## 7.4 Reports Routes

Create route file:

```txt
backend/app/api/routes/reports.py
```

Routes:

```txt
GET /api/reports/monthly
GET /api/reports/pending-receivables
GET /api/reports/pending-payables
GET /api/reports/shipment-pnl
```

### GET /api/reports/monthly

Query params:

```txt
year optional
month optional
```

Return:

```txt
month
year
shipment_count
completed_shipments
total_receivable
total_payable
net_profit
pending_receivable
pending_payable
currency
multiple_currencies
```

### GET /api/reports/pending-receivables

Return list:

```txt
charge_id
shipment_id
shipment_code
party_name
amount
currency
invoice_no
date
notes
```

### GET /api/reports/pending-payables

Return list:

```txt
charge_id
shipment_id
shipment_code
party_name
amount
currency
invoice_no
date
notes
```

### GET /api/reports/shipment-pnl

Return shipment-wise P&L:

```txt
shipment_id
shipment_code
type
status
total_receivable
total_payable
net_profit
pending_receivable
pending_payable
currency
multiple_currencies
```

---

# 8. Backend Service Logic

Create service file:

```txt
backend/app/services/finance_service.py
```

Responsibilities:

```txt
calculate_shipment_pnl(db, shipment_id)
calculate_dashboard_financials(db)
calculate_monthly_report(db, year, month)
list_pending_receivables(db)
list_pending_payables(db)
list_shipment_pnl(db)
```

Keep formulas in this service rather than duplicating in routes.

---

# 9. Frontend Changes

## 9.1 Add Charges Tab

Update shipment detail tabs:

```txt
Overview
Documents
Tasks
BL Management
Follow-up Log
Demurrage
Charges
```

Charges tab should show:

```txt
P&L summary cards
Charge create/edit form
Charge table
```

---

## 9.2 Charges Tab UI

Create component/section:

```txt
ChargesTab
```

Fields:

```txt
Charge Type dropdown
Direction dropdown: payable / receivable
Amount input
Currency input/dropdown
Party dropdown
Status dropdown
Invoice No input
Date input
Notes textarea
Save button
```

Defaults:

```txt
Currency: INR
Status: pending
Date: today optional
```

Charge table columns:

```txt
Type
Direction
Amount
Currency
Party
Status
Invoice No
Date
Notes
Actions
```

Actions:

```txt
Edit
Delete
Mark Paid if payable
Mark Received if receivable
```

VIEW_ONLY behavior:

```txt
Can view charges and P&L.
Cannot create/edit/delete/mark paid/mark received.
```

---

## 9.3 Shipment P&L Summary UI

At top of Charges tab show cards:

```txt
Total Receivable
Total Payable
Net Profit
Pending Receivable
Pending Payable
```

Visual rules:

```txt
Net Profit positive: normal/success style
Net Profit negative: warning/critical style
Pending Receivable: warning style
Pending Payable: info/warning style
```

---

## 9.4 Dashboard Financial Cards

Update Dashboard page to include:

```txt
Pending Receivables
Pending Payables
This Month Receivables
This Month Payables
This Month Profit
```

Do not remove existing operational cards:

```txt
Live Shipments
Pending Tasks
Future Bookings
Alerts Today
Completed Shipments This Month
```

If layout is crowded, use two sections:

```txt
Operational Summary
Financial Summary
```

---

## 9.5 Reports Page

Add route:

```txt
/reports
```

Add sidebar link:

```txt
Reports
```

Reports page sections:

```txt
Monthly Summary
Pending Receivables
Pending Payables
Shipment-wise P&L
```

Controls:

```txt
Month selector
Year selector
Refresh button
```

Tables:

### Pending Receivables Table

```txt
Shipment Code
Party
Amount
Currency
Invoice No
Date
Notes
```

### Pending Payables Table

```txt
Shipment Code
Party
Amount
Currency
Invoice No
Date
Notes
```

### Shipment-wise P&L Table

```txt
Shipment Code
Type
Status
Total Receivable
Total Payable
Net Profit
Pending Receivable
Pending Payable
```

---

# 10. Mock AI Phase 3 Improvements

Extend existing mock AI route:

```txt
POST /api/ai/ask
```

Add database-rule answers for:

```txt
How much freight is uncollected?
Which shipments have pending receivables?
Which shipments have pending payables?
Show profit for FF-EXP-2026-001
Show P&L for FF-EXP-2026-001
Which shipments are loss-making?
What is this month profit?
```

Rules:

```txt
No OpenAI API.
No API key.
Use database queries only.
Return readable text.
```

---

# 11. Permissions

Maintain:

```txt
ADMIN:
- full read/write

STAFF:
- operational read/write for charges and reports
- cannot manage users unless existing code allows intentionally

VIEW_ONLY:
- read-only access
- can view charges, P&L, reports
- cannot create/update/delete charges
- cannot mark paid/received
```

Backend must enforce this.

Frontend should hide write buttons for VIEW_ONLY where possible, but backend protection is mandatory.

---

# 12. Validation

Backend validation:

```txt
amount must be >= 0
shipment_id must exist
charge_type must be valid
direction must be payable or receivable
status must be valid
party_id must exist if provided
```

Frontend validation:

```txt
Amount required
Amount cannot be negative
Charge type required
Direction required
Status required
```

---

# 13. Error Handling

Backend should return:

```txt
401 unauthenticated
403 insufficient permission
404 missing shipment/charge
400 invalid input
```

Frontend should show readable errors.

Do not crash to blank screen.

---

# 14. README Updates

Update README with:

```txt
Charges module
Payable vs receivable
Shipment P&L formula
Reports page
Dashboard financial cards
Mock AI finance examples
Phase 3 limitations
```

Add limitations:

```txt
No real accounting integration yet.
No invoice PDF generation yet.
No exchange-rate automation yet.
No OpenAI API yet.
No email parsing yet.
```

---

# 15. Testing Requirements

After implementation, run:

## Backend

```bash
cd backend
source .venv/bin/activate
python -m compileall app
uvicorn app.main:app --reload
```

Check:

```txt
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

## Frontend

```bash
cd frontend
npm install
npm run build
npm run dev
```

Check:

```txt
http://127.0.0.1:5173
```

---

# 16. Manual Test Flow

## 16.1 Admin Login

```txt
Login as admin.
Open dashboard.
Open shipments.
Open existing shipment or create new shipment.
```

## 16.2 Create Charges

Create receivable charge:

```txt
Charge Type: ocean_freight
Direction: receivable
Amount: 50000
Currency: INR
Party: importer/exporter
Status: pending
Invoice No: INV-R-001
Date: today
Notes: Freight to collect from client
```

Create payable charge:

```txt
Charge Type: liner_charges
Direction: payable
Amount: 35000
Currency: INR
Party: shipping line
Status: pending
Invoice No: BILL-P-001
Date: today
Notes: Line payment pending
```

Expected P&L:

```txt
Total Receivable: 50000
Total Payable: 35000
Net Profit: 15000
Pending Receivable: 50000
Pending Payable: 35000
```

## 16.3 Mark Paid/Received

Mark receivable as:

```txt
received
```

Expected:

```txt
Pending Receivable decreases.
Total Receivable remains same.
Total Received increases.
```

Mark payable as:

```txt
paid
```

Expected:

```txt
Pending Payable decreases.
Total Payable remains same.
Total Paid increases.
```

---

## 16.4 Reports Page Test

Open:

```txt
/reports
```

Check:

```txt
Monthly summary loads.
Pending receivables table loads.
Pending payables table loads.
Shipment-wise P&L table loads.
Month/year filters work if implemented.
```

---

## 16.5 Dashboard Financial Cards Test

Dashboard should show:

```txt
Pending Receivables
Pending Payables
This Month Receivables
This Month Payables
This Month Profit
```

Expected:

```txt
Values update after charges are created.
Pending values decrease after paid/received.
Profit = receivable - payable.
```

---

## 16.6 Mock AI Finance Test

Ask mock AI:

```txt
How much freight is uncollected?
Which shipments have pending receivables?
Which shipments have pending payables?
Show profit for FF-EXP-2026-001
Which shipments are loss-making?
What is this month profit?
```

Expected:

```txt
Answers come from charges/reports data.
No OpenAI API call.
No API key needed.
```

---

## 16.7 VIEW_ONLY Test

Login as VIEW_ONLY.

Expected read access:

```txt
Charges tab visible
P&L visible
Reports visible
Dashboard financial cards visible
```

Expected blocked write access:

```txt
Cannot create charge
Cannot edit charge
Cannot delete charge
Cannot mark paid
Cannot mark received
```

Backend should return:

```txt
403 Not enough permission
```

---

# 17. Smoke Test Acceptance Criteria

Phase 3 is complete only when:

```txt
[ ] Backend compiles
[ ] Frontend builds
[ ] Existing Phase 1 flows still work
[ ] Existing Phase 2 flows still work
[ ] Charge model/table exists
[ ] Charge CRUD routes work
[ ] Charges tab appears in shipment detail
[ ] Charge create works
[ ] Charge update works
[ ] Charge delete/cancel works
[ ] Mark payable paid works
[ ] Mark receivable received works
[ ] Shipment P&L summary is correct
[ ] Pending receivable calculation is correct
[ ] Pending payable calculation is correct
[ ] Dashboard financial cards load
[ ] Dashboard financial cards update after charges change
[ ] Reports page loads
[ ] Monthly summary works
[ ] Pending receivables report works
[ ] Pending payables report works
[ ] Shipment-wise P&L report works
[ ] Mock AI finance questions work
[ ] VIEW_ONLY can view finance data
[ ] VIEW_ONLY cannot modify finance data
[ ] No OpenAI API added
[ ] No email parsing added
[ ] No Google Drive API upload added
[ ] No Celery/Redis added
[ ] No real secrets committed
[ ] README updated
```

---

# 18. Security and Git Check

Run:

```bash
git status
git diff
```

Check ignored files:

```bash
find . -name ".env" -o -name "node_modules" -o -name ".venv" -o -name "dist"
```

Search for secrets:

```bash
grep -R "postgresql://" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "JWT_SECRET_KEY=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "DATABASE_URL=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
```

Allowed places:

```txt
.env.example
README
Markdown planning/testing docs
```

Not allowed:

```txt
Real Neon URL
Real database password
Real JWT secret
Committed .env file
```

---

# 19. Final Commit

After implementation and tests:

```bash
git status
git add .
git commit -m "Implement phase 3 charges and reporting"
```

Push:

```bash
git push -u origin phase-3-charges-reporting
```

---

# 20. Final Codex Instruction

Implement Phase 3 only.

Do not add OpenAI, Gmail, email parsing, Google Drive API upload, AWS S3, Celery, Redis, invoice PDF generation, payment gateway, or accounting integrations.

Preserve all existing Phase 1 and Phase 2 behavior.

Use normal CSS only.

Use existing backend/frontend coding style.

Make small, safe, testable changes.

After implementation:

```txt
Run backend compile check.
Run frontend build.
Run smoke tests.
Update README.
Commit with:
Implement phase 3 charges and reporting
```

Report clearly:

```txt
What changed
New database tables/fields
New API routes
Frontend pages/tabs added
Tests run
Known limitations
Commit hash
```
