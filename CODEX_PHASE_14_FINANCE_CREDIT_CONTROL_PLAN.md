# CODEX_PHASE_14_FINANCE_CREDIT_CONTROL_PLAN.md

# Phase 14 — Finance + Credit Control Expansion

## Purpose

Implement **Phase 14** for the Freight Forwarding / EXIM Operational Intelligence System.

Phase 13 added document intelligence, OCR/text extraction, document classification, extracted fields, mismatches, and review-only document intelligence suggestions. Phase 14 now strengthens the finance layer so the system can control receivables, payables, credit risk, payment holds, release controls, FX snapshots, and finance aging.

The goal is:

```txt
Move beyond basic charges/P&L into finance control.
Track receivables and payables with aging.
Track payments and allocations.
Maintain customer credit profiles.
Detect credit-limit and overdue-payment risk.
Create shipment/document release holds when finance risk exists.
Record FX snapshots for multi-currency calculations.
Prepare tax/GST/TDS metadata without becoming full accounting software.
Keep finance decisions reviewable, auditable, and rule-driven.
```

Phase 14 must preserve the existing charges/P&L/reporting behavior while adding stronger finance and credit-control modules beside it.

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
Phase 9.1    Gmail automation cleanup/dedupe/account scoping
Phase 10     Strong export/import state machines
Phase 11     Container lifecycle + demurrage/detention separation
Phase 12     Document upload + versioning foundation
Phase 13     Document intelligence + OCR + mismatch validation
```

Current stack:

```txt
Frontend: React + Vite
Backend: FastAPI
Database: PostgreSQL / Neon
Migrations: Alembic
Auth: JWT + bcrypt
Roles: ADMIN / STAFF / VIEW_ONLY
Finance base: charges, P&L, reports
Documents: upload/versioning/intelligence
Containers: lifecycle + demurrage/detention separation
Workflow: export/import state machine
Events/validation: operational event + rule/validation issue foundation
AI: Groq read-only assistant
Gmail: read-only OAuth + review-based suggestions
```

Preserve all existing behavior:

```txt
Login
Users/admin management
Dashboard
Shipments
Parties
Tasks
Charges
P&L reports
Existing charge create/cancel/payment flows
Document upload/versioning
Document intelligence
BL management
Demurrage
Containers
Container exposure
Workflow states
Follow-ups
Legacy alerts
Notifications
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

Master 1.1 requires the finance layer to cover:

```txt
receivables
payables
credit control
client outstanding
vendor outstanding
payment holds
release controls
multi-currency FX snapshots
GST/TDS preparation
margin/P&L accuracy
vendor reconciliation
client payment follow-up
waiver/special rate handling
demurrage/detention finalization
```

Phase 14 implements the first structured finance-control layer.

Later phases will add:

```txt
Phase 15: exception engine + manual review center
Phase 16: approval engine + HOD bot governance
Phase 17: bot governance + learning system
```

So Phase 14 must create finance risk signals and holds, but should not implement a full HOD approval engine yet.

---

# 3. Strict Non-Goals

Do **not** implement in Phase 14:

```txt
Payment gateway
Bank integration
Accounting software integration
Tally/Zoho/QuickBooks sync
Invoice PDF generation
E-invoice / e-way bill filing
GST return filing
TDS return filing
Automatic payment approval
Automatic BL/DO/document release
Autonomous AI finance decisions
Full approval engine / HOD bot
Exporter/importer portal
CHA/customs portal
Transport/GPS
Tracking provider adapters
n8n
WhatsApp/SMS
Gmail send/modify/delete/archive
```

Phase 14 may prepare fields and workflows for these, but must not build them yet.

---

# 4. Safety Rules

Phase 14 may:

```txt
create finance invoice records
create payment records
allocate payments to invoices/charges
compute receivable/payable aging
compute party outstanding
compute shipment finance summary
create credit risk records
create finance holds/release blocks
create notifications and validation issues
record finance events and audit logs
show finance dashboard widgets
let users manually clear/resolve finance risks
```

Phase 14 must not automatically:

```txt
mark invoices paid without explicit user action
approve payment waivers
release OBL/DO/documents
override credit holds
send collection emails
send vendor payment emails
create real bank transactions
file taxes
create invoice PDFs
push data to accounting software
```

Default policy:

```txt
Finance control is advisory/blocking inside the app.
Real-world financial action requires explicit user confirmation.
Sensitive finance actions should create audit logs and manual-review signals.
```

---

# 5. Git Workflow

Start from updated `main` after Phase 13 is merged/deployed/stable.

```bash
git status
git log --oneline -8

git checkout main
git pull origin main
git checkout -b phase-14-finance-credit-control
```

Final commit:

```bash
git add .
git commit -m "Implement phase 14 finance credit control"
git push -u origin phase-14-finance-credit-control
```

Do not deploy until tests pass.

---

# 6. Database / Alembic Migration

Use Alembic.

Add migration:

```txt
phase14_finance_credit
```

Revision ID must be <= 32 characters.

The migration must chain after current `main` head, expected:

```txt
phase13_doc_intel
```

or whichever exact current Alembic head exists on `main`.

New tables:

```txt
finance_invoices
finance_invoice_lines
finance_payments
finance_payment_allocations
party_credit_profiles
credit_hold_records
finance_aging_snapshots
fx_rate_snapshots
finance_risk_records
finance_adjustments
```

Optional if safe:

```txt
tax_profiles
tax_withholding_records
```

Rules:

```txt
No table drops
No destructive renames
No data reset
No breaking changes to existing charges table
No automatic migration that changes existing P&L totals
All new fields nullable or safe default
```

Existing charges remain the source for current Phase 3 P&L unless explicitly linked into new finance records.

---

# 7. Backend Models

## 7.1 FinanceInvoice

Table:

```txt
finance_invoices
```

Fields:

```txt
id
organization_id nullable
shipment_id nullable
party_id nullable
invoice_number nullable
invoice_type
direction
status
currency
subtotal_amount
tax_amount
total_amount
paid_amount
outstanding_amount
invoice_date nullable
due_date nullable
credit_days nullable
source
linked_charge_id nullable
created_by_user_id nullable
created_by_name nullable
created_at
updated_at
metadata_json nullable
```

`invoice_type` values:

```txt
customer_invoice
vendor_invoice
freight_invoice
demurrage_invoice
detention_invoice
debit_note
credit_note
reimbursement
other
```

`direction` values:

```txt
receivable
payable
```

`status` values:

```txt
draft
issued
partially_paid
paid
overdue
cancelled
disputed
on_hold
```

Rules:

```txt
Do not auto-create invoice PDFs.
Do not auto-send invoices.
Do not mutate existing charges unless explicit user action.
```

---

## 7.2 FinanceInvoiceLine

Table:

```txt
finance_invoice_lines
```

Fields:

```txt
id
invoice_id
charge_id nullable
description
quantity
unit_price
amount
currency
tax_code nullable
tax_amount nullable
created_at
metadata_json nullable
```

Purpose:

```txt
Represent line-level finance details without replacing existing charges.
```

---

## 7.3 FinancePayment

Table:

```txt
finance_payments
```

Fields:

```txt
id
organization_id nullable
party_id nullable
payment_type
direction
status
currency
amount
unallocated_amount
payment_date nullable
reference_number nullable
method nullable
bank_name nullable
notes nullable
created_by_user_id nullable
created_by_name nullable
created_at
updated_at
metadata_json nullable
```

`payment_type` values:

```txt
receipt
vendor_payment
adjustment
refund
advance
other
```

`direction` values:

```txt
inbound
outbound
```

`status` values:

```txt
draft
posted
partially_allocated
allocated
cancelled
reversed
```

Rules:

```txt
Payments are internal records only.
Do not connect to bank/payment gateway.
```

---

## 7.4 FinancePaymentAllocation

Table:

```txt
finance_payment_allocations
```

Fields:

```txt
id
payment_id
invoice_id nullable
charge_id nullable
shipment_id nullable
allocated_amount
currency
allocated_at
allocated_by_user_id nullable
allocated_by_name nullable
notes nullable
created_at
metadata_json nullable
```

Rules:

```txt
Allocation updates invoice paid/outstanding amounts.
Allocation must not change real bank state.
Cancelled/reversed payments should not count.
```

---

## 7.5 PartyCreditProfile

Table:

```txt
party_credit_profiles
```

Fields:

```txt
id
organization_id nullable
party_id
credit_limit
credit_currency
credit_days
is_credit_allowed
hold_on_overdue
hold_on_limit_exceeded
warning_threshold_percent
status
created_at
updated_at
metadata_json nullable
```

`status` values:

```txt
active
suspended
manual_review
inactive
```

Defaults:

```txt
credit_limit = 0
credit_days = 0
is_credit_allowed = true
hold_on_overdue = true
hold_on_limit_exceeded = true
warning_threshold_percent = 80
```

---

## 7.6 CreditHoldRecord

Table:

```txt
credit_hold_records
```

Fields:

```txt
id
party_id nullable
shipment_id nullable
hold_type
severity
status
reason
trigger_source
current_outstanding nullable
credit_limit nullable
overdue_amount nullable
blocked_action nullable
created_at
created_by_user_id nullable
created_by_name nullable
resolved_at nullable
resolved_by_user_id nullable
resolved_by_name nullable
resolution_notes nullable
metadata_json nullable
```

`hold_type` values:

```txt
credit_limit_exceeded
overdue_payment
manual_finance_hold
document_release_hold
do_release_hold
obl_release_hold
shipment_completion_hold
```

`status` values:

```txt
active
acknowledged
resolved
waived
dismissed
```

`blocked_action` examples:

```txt
release_final_bl
release_do
dispatch_documents
mark_shipment_completed
extend_credit
```

Rules:

```txt
Holds should block or warn only inside app workflows.
No external release action should happen automatically.
Waiver/resolution is manual and audited.
```

---

## 7.7 FinanceAgingSnapshot

Table:

```txt
finance_aging_snapshots
```

Fields:

```txt
id
party_id nullable
shipment_id nullable
direction
currency
snapshot_date
not_due_amount
bucket_0_30
bucket_31_60
bucket_61_90
bucket_90_plus
total_outstanding
overdue_amount
created_at
metadata_json nullable
```

`direction` values:

```txt
receivable
payable
```

Purpose:

```txt
Cache/report aging summaries.
```

---

## 7.8 FxRateSnapshot

Table:

```txt
fx_rate_snapshots
```

Fields:

```txt
id
base_currency
quote_currency
rate
rate_date
source
is_manual
created_by_user_id nullable
created_by_name nullable
created_at
metadata_json nullable
```

Rules:

```txt
Manual FX snapshot is allowed.
Do not fetch live FX rates unless explicitly implemented using a configured provider.
Do not make internet calls from backend without configuration.
```

---

## 7.9 FinanceRiskRecord

Table:

```txt
finance_risk_records
```

Fields:

```txt
id
party_id nullable
shipment_id nullable
risk_type
severity
status
message
recommended_action nullable
related_invoice_id nullable
related_payment_id nullable
related_hold_id nullable
created_at
resolved_at nullable
resolved_by_user_id nullable
resolved_by_name nullable
metadata_json nullable
```

Risk types:

```txt
receivable_overdue
payable_overdue
credit_limit_warning
credit_limit_exceeded
unallocated_payment
invoice_dispute
margin_negative
missing_fx_rate
release_blocked
```

---

## 7.10 FinanceAdjustment

Table:

```txt
finance_adjustments
```

Fields:

```txt
id
invoice_id nullable
charge_id nullable
shipment_id nullable
adjustment_type
direction
amount
currency
reason
status
created_by_user_id nullable
created_by_name nullable
approved_by_user_id nullable
approved_by_name nullable
created_at
approved_at nullable
metadata_json nullable
```

`adjustment_type` values:

```txt
waiver
discount
write_off
round_off
correction
credit_note
debit_note
```

`status` values:

```txt
draft
pending_review
approved
rejected
applied
cancelled
```

Rules:

```txt
In Phase 14, approval can be manual/simple.
Full HOD approval engine comes later.
```

---

# 8. Backend Services

## 8.1 finance_invoice_service.py

Functions:

```python
create_invoice_from_charge(db, charge_id, user, invoice_data=None)
create_invoice(db, data, user)
update_invoice(db, invoice_id, data, user)
cancel_invoice(db, invoice_id, user, reason=None)
recalculate_invoice_totals(db, invoice_id)
list_invoices(db, filters, user)
get_invoice(db, invoice_id, user)
```

Responsibilities:

```txt
create invoice lines
calculate subtotal/tax/total/outstanding
link charge if applicable
record operational events
record audit logs
create validation issues for risky values
```

---

## 8.2 payment_service.py

Functions:

```python
create_payment(db, data, user)
allocate_payment(db, payment_id, allocations, user)
cancel_payment(db, payment_id, user, reason=None)
recalculate_payment_allocation(db, payment_id)
list_payments(db, filters, user)
get_payment(db, payment_id, user)
```

Responsibilities:

```txt
track internal payments
allocate to invoices/charges
update invoice paid/outstanding
record events/audit logs
prevent over-allocation
```

---

## 8.3 credit_control_service.py

Functions:

```python
get_or_create_credit_profile(db, party_id, user=None)
update_credit_profile(db, party_id, data, user)
calculate_party_outstanding(db, party_id, direction="receivable")
evaluate_credit_risk(db, party_id, shipment_id=None)
create_or_refresh_credit_hold(db, risk, user=None)
resolve_credit_hold(db, hold_id, user, notes=None)
waive_credit_hold(db, hold_id, user, notes=None)
```

Responsibilities:

```txt
calculate outstanding
check credit limit
check overdue invoices
create credit holds
create finance risk records
create notifications
create validation issues
```

---

## 8.4 finance_aging_service.py

Functions:

```python
calculate_aging_for_party(db, party_id, direction="receivable", as_of_date=None)
calculate_aging_summary(db, direction="receivable", as_of_date=None)
create_aging_snapshot(db, party_id=None, shipment_id=None, direction="receivable")
```

Aging buckets:

```txt
not due
0-30
31-60
61-90
90+
```

---

## 8.5 fx_service.py

Functions:

```python
create_fx_rate_snapshot(db, data, user)
get_fx_rate(db, base_currency, quote_currency, rate_date=None)
convert_amount(db, amount, from_currency, to_currency, rate_date=None)
```

Rules:

```txt
If rate missing, create finance risk / validation issue.
Do not silently guess FX rate.
```

---

## 8.6 finance_risk_service.py

Functions:

```python
create_finance_risk(db, data, user=None)
resolve_finance_risk(db, risk_id, user, notes=None)
list_finance_risks(db, filters, user)
refresh_shipment_finance_risks(db, shipment_id, user=None)
refresh_party_finance_risks(db, party_id, user=None)
```

---

# 9. Charge Integration

Existing charges must continue to work.

Phase 14 should add optional finance linkage:

```txt
charge -> finance_invoice_line -> finance_invoice
charge -> payment_allocation if paid/received
```

Rules:

```txt
Do not change existing charge totals.
Do not change existing P&L report logic unless adding optional enhanced finance summary.
Existing charge statuses remain supported.
Cancelled charges remain excluded from P&L as currently implemented.
```

Add safe actions:

```txt
Create invoice from charge
Link charge to invoice
Allocate payment to charge/invoice
View finance status from charge detail
```

---

# 10. Demurrage / Detention Integration

Phase 11 exposure remains advisory.

Phase 14 may add:

```txt
Finalize demurrage estimate into finance invoice draft
Finalize detention estimate into finance invoice draft
```

Rules:

```txt
No automatic invoice creation.
User must explicitly click finalise/create invoice.
Finalized finance record should link back to container_demurrage_record or container_detention_record if available.
```

If linkage is too risky, create only placeholder fields and docs.

---

# 11. Document Intelligence Integration

Phase 13 OCR can detect freight invoice amounts and mismatches.

Phase 14 may:

```txt
show document intelligence finance suggestions in finance review
compare invoice OCR amount against finance invoice/charge
create finance mismatch risk
```

Do not auto-create finance invoices from OCR.

---

# 12. Release Control

Add app-level release controls for sensitive actions.

Initial blocked actions:

```txt
release_final_bl
release_do
dispatch_documents
mark_export_completed
mark_import_completed
```

Add service:

```txt
backend/app/services/release_control_service.py
```

Functions:

```python
check_release_allowed(db, shipment_id, action_key, user)
create_release_hold_if_needed(db, shipment_id, action_key, reason, user=None)
list_release_holds(db, filters, user)
```

Rules:

```txt
If active credit hold exists for shipment/party, release action should warn/block inside app.
Do not perform real external release.
Do not auto-clear holds.
```

Integrate softly with:

```txt
workflow completion states
document dispatch actions
BL/DO status actions if routes exist
```

If existing route cannot be safely blocked, create validation issue/notification instead.

---

# 13. Backend APIs

Add routes:

```txt
backend/app/api/routes/finance_control.py
```

Prefix:

```txt
/api/finance
```

Routes:

```txt
GET /api/finance/invoices
POST /api/finance/invoices
GET /api/finance/invoices/{invoice_id}
PATCH /api/finance/invoices/{invoice_id}
POST /api/finance/invoices/{invoice_id}/cancel
POST /api/finance/invoices/from-charge/{charge_id}

GET /api/finance/payments
POST /api/finance/payments
GET /api/finance/payments/{payment_id}
POST /api/finance/payments/{payment_id}/allocate
POST /api/finance/payments/{payment_id}/cancel

GET /api/finance/credit-profiles
GET /api/finance/parties/{party_id}/credit-profile
PATCH /api/finance/parties/{party_id}/credit-profile

GET /api/finance/holds
POST /api/finance/holds/{hold_id}/resolve
POST /api/finance/holds/{hold_id}/waive

GET /api/finance/aging
GET /api/finance/parties/{party_id}/aging
POST /api/finance/aging/snapshot

GET /api/finance/risks
POST /api/finance/risks/{risk_id}/resolve
POST /api/finance/refresh-party/{party_id}
POST /api/finance/refresh-shipment/{shipment_id}

GET /api/finance/fx-rates
POST /api/finance/fx-rates
```

Shipment-specific routes:

```txt
GET /api/shipments/{shipment_id}/finance-summary
GET /api/shipments/{shipment_id}/release-checks
POST /api/shipments/{shipment_id}/finance-refresh
```

Permissions:

```txt
ADMIN: all finance actions
STAFF: create/update invoices/payments, allocate, refresh risks, view holds
VIEW_ONLY: read-only finance summaries, no create/update/waive/resolve
```

Sensitive actions:

```txt
waive hold
cancel invoice
cancel payment
create adjustment
```

should require ADMIN or existing high-permission role if available.

---

# 14. Validation Rules

Add Phase 14 rule definitions:

```txt
finance_invoice_missing_party
finance_invoice_negative_amount
finance_payment_overallocated
finance_payment_currency_mismatch
finance_invoice_overdue
finance_receivable_overdue
finance_payable_overdue
finance_credit_limit_warning
finance_credit_limit_exceeded
finance_missing_fx_rate
finance_negative_margin_warning
finance_release_blocked_credit_hold
finance_demurrage_invoice_mismatch
finance_detention_invoice_mismatch
```

Default:

```txt
enabled = true
blocking = false
```

Potential blocking:

```txt
finance_payment_overallocated
finance_release_blocked_credit_hold
```

Only make blocking if tested safely.

---

# 15. Notifications

Create notifications for:

```txt
receivable overdue
payable overdue
credit limit warning
credit limit exceeded
release blocked
unallocated payment
invoice dispute
negative margin
missing FX rate
```

Dedupe keys:

```txt
finance_receivable_overdue:{invoice_id}
finance_payable_overdue:{invoice_id}
finance_credit_limit_warning:{party_id}:{date}
finance_credit_limit_exceeded:{party_id}
finance_release_blocked:{shipment_id}:{action_key}
finance_unallocated_payment:{payment_id}
finance_missing_fx:{from_currency}:{to_currency}:{date}
finance_negative_margin:{shipment_id}
```

Do not duplicate notifications on repeated refresh.

---

# 16. Events / Audit Integration

Operational events:

```txt
finance.invoice_created
finance.invoice_updated
finance.invoice_cancelled
finance.payment_created
finance.payment_allocated
finance.payment_cancelled
finance.credit_profile_updated
finance.credit_hold_created
finance.credit_hold_resolved
finance.credit_hold_waived
finance.aging_snapshot_created
finance.fx_rate_created
finance.risk_created
finance.risk_resolved
finance.release_check_failed
```

Audit logs:

```txt
finance.invoice_create
finance.invoice_update
finance.invoice_cancel
finance.payment_create
finance.payment_allocate
finance.payment_cancel
finance.credit_profile_update
finance.hold_resolve
finance.hold_waive
finance.fx_rate_create
finance.risk_resolve
```

Sanitize metadata.

Do not store payment secrets or bank credentials.

---

# 17. AI Assistant Integration

Update AI read-only context/fallback for:

```txt
Which customers have overdue receivables?
How much is pending from this party?
Show credit risk for this shipment.
Can we release DO for FF-IMP-2026-001?
Which invoices are overdue?
Show payable aging.
Show receivable aging.
What is the outstanding amount for FF-EXP-2026-001?
Which shipments are on finance hold?
```

AI rules:

```txt
AI remains read-only.
AI cannot create invoices.
AI cannot mark payments.
AI cannot waive holds.
AI cannot release documents.
AI cannot override credit control.
AI can explain finance status and recommended next review action.
```

---

# 18. Frontend Changes

## 18.1 Finance Control Page

Add route:

```txt
/finance
```

Sections/tabs:

```txt
Overview
Receivables
Payables
Payments
Credit Control
Holds
Aging
FX Rates
Risks
```

Show:

```txt
total receivables
overdue receivables
total payables
overdue payables
active holds
credit limit warnings
unallocated payments
negative margin alerts
```

---

## 18.2 Shipment Finance Tab

Add or improve shipment detail finance section.

Show:

```txt
shipment invoices
shipment payments
outstanding
P&L summary
finance holds
release checks
linked charges
demurrage/detention finance exposure
```

Actions:

```txt
create invoice from charge
record payment
allocate payment
refresh finance risks
check release allowed
```

Do not break existing charges tab.

---

## 18.3 Party Credit Profile UI

On party detail or finance page:

```txt
credit limit
credit days
currency
outstanding
overdue amount
active holds
status
update credit profile
```

---

## 18.4 Dashboard Widgets

Add widgets:

```txt
Receivables Aging
Payables Aging
Credit Holds
Overdue Finance Items
Unallocated Payments
```

Widgets should fail independently.

---

## 18.5 Reports

Add finance reports without breaking existing reports:

```txt
Receivables Aging Report
Payables Aging Report
Credit Hold Report
Party Outstanding Report
Shipment Finance Summary
```

---

# 19. README / Docs

Update README with:

```txt
Phase 14 finance + credit control
invoice/payment records
payment allocation
aging buckets
credit profiles
credit holds
release controls
FX snapshots
limitations/non-goals
```

Add:

```txt
docs/PHASE_14_FINANCE_CREDIT_CONTROL.md
```

Include:

```txt
Architecture
Models
APIs
Credit control rules
Aging logic
Release control logic
Permissions
Security limits
How Phase 14 prepares Phase 15 exception engine and Phase 16 approval engine
```

---

# 20. Backend Test Plan

Run:

```bash
cd backend
source .venv/bin/activate
python -m compileall app
```

Alembic:

```bash
alembic history
alembic heads
alembic upgrade head
alembic current
```

API smoke:

```txt
Login as ADMIN
Create party
Create shipment
Create receivable invoice
Create payable invoice
Create payment
Allocate payment to invoice
Check outstanding changes
Create/update credit profile
Refresh party finance risk
Generate aging summary
Create FX rate
Check release allowed/blocked
Resolve/waive hold
VIEW_ONLY cannot mutate finance
```

Validation tests:

```txt
negative invoice amount creates issue or is rejected
payment over-allocation blocked
credit limit exceeded creates hold
overdue receivable creates risk/notification
missing FX rate creates risk
release blocked by active credit hold
cancelled invoice excluded from outstanding
cancelled payment excluded from allocation
```

Regression:

```txt
Existing charges still work
Existing P&L totals unchanged
Shipment CRUD still works
Workflow state machine still works
Containers still work
Documents and intelligence still work
Gmail automation still works
AI still works
Events/validation issues still work
Notifications still work
```

---

# 21. Frontend Test Plan

Run:

```bash
cd frontend
npm run build
```

Manual smoke:

```txt
Finance page loads
Create invoice works
Create payment works
Allocate payment works
Credit profile update works
Aging report loads
Shipment finance tab loads
Release check shows hold/warning
Dashboard finance widgets load
VIEW_ONLY cannot mutate finance
Existing pages still load
```

---

# 22. Security Test Plan

Run:

```bash
git status
git diff

find . -name ".env" -o -name "node_modules" -o -name ".venv" -o -name "dist" -o -name "client_secret*.json" -o -name "uploaded_documents"

grep -R "GOOGLE_CLIENT_SECRET" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=uploaded_documents --exclude=".env"
grep -R "GROQ_API_KEY" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=uploaded_documents --exclude=".env"
grep -R "OPENAI_API_KEY" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=uploaded_documents --exclude=".env"
grep -R "postgresql://" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=uploaded_documents --exclude=".env"
grep -R "JWT_SECRET_KEY=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=uploaded_documents --exclude=".env"
grep -R "DATABASE_URL=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=uploaded_documents --exclude=".env"
```

Also inspect finance metadata for:

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
bank credentials
card numbers
UPI secrets
```

No sensitive values should be stored in audit/events/notifications/validation metadata.

---

# 23. Acceptance Criteria

Phase 14 is complete only when:

```txt
[ ] Backend compiles
[ ] Frontend builds
[ ] Alembic migration exists
[ ] FinanceInvoice model/table exists
[ ] FinancePayment model/table exists
[ ] Payment allocation works
[ ] PartyCreditProfile works
[ ] Credit holds work
[ ] Aging summary works
[ ] FX snapshot works
[ ] Release control check works
[ ] Finance risk records work
[ ] Notifications for finance risks work
[ ] Validation issues for finance risks work
[ ] Finance page works
[ ] Shipment finance summary works
[ ] Dashboard finance widgets work
[ ] Existing charges/P&L remain stable
[ ] AI can summarize finance status read-only
[ ] Existing Phase 1–13 features still work
[ ] No secrets or sensitive finance credentials committed/stored
```

---

# 24. Final Commit

After all checks pass:

```bash
git status
git add .
git commit -m "Implement phase 14 finance credit control"
```

Push:

```bash
git push -u origin phase-14-finance-credit-control
```

---

# 25. Final Report Required

After implementation, report:

```txt
Backend compile result
Frontend build result
Alembic migration result
Finance invoice test result
Payment allocation test result
Credit profile/hold test result
Aging summary test result
FX snapshot test result
Release control test result
Notification/validation integration result
AI finance summary test result
Regression test result for Phases 1–13
Secret/finance metadata scan result
Git status
Commit hash
Known limitations
```
