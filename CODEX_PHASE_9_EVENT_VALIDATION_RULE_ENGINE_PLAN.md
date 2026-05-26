# CODEX_PHASE_9_EVENT_VALIDATION_RULE_ENGINE_PLAN.md

# Phase 9 — Event System + Validation / Rule Engine Foundation

## Purpose

Implement **Phase 9** for the Freight Forwarding / EXIM Operational Intelligence System.

Phase 8 added Alembic, default organization groundwork, Master 1.1 gap map, and placeholder event/rule/validation service structure. Phase 9 turns those placeholders into the first real operational-brain layer.

Goal:

```txt
Every important operational action creates an event.
Every event can be checked by deterministic validation/rule logic.
Validation failures create reviewable issues/notifications.
The system begins detecting wrong, missing, duplicate, stale, or risky operational data.
```

Phase 9 should sit beside existing workflows. It must not replace existing shipment/task/charge/document behavior yet.

---

## 1. Current System Context

Completed foundation:

```txt
Phase 1      FF Core base
Phase 2      Workflow, BL, demurrage, follow-ups, alerts
Phase 3      Charges, P&L, reports
Phase 3.5    Safe cleanup controls
Phase 4      Groq AI assistant
Phase 5      Gmail read-only email automation
Phase 6      Production hardening
Phase 6.1    Direct login + admin user management
Phase 7      Notifications / workflow reminder base
Phase 8      Alembic + organization foundation + Master 1.1 gap map
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
Alembic setup
```

---

## 2. Master 1.1 Alignment

Master 1.1 expects the operating brain to follow:

```txt
Event → identity check → validation rules → workflow state check → task/notification engine → approval if needed → database update → audit log
```

Phase 9 implements the first production version of:

```txt
Operational events
Rule definitions
Validation checks
Validation issues
Manual-review signal
Event audit trail
Read-only AI context for operational issues
```

Full export/import state machines come in Phase 10. Full exception engine, approval engine, and HOD bot come later.

---

## 3. Strict Non-Goals

Do **not** implement in Phase 9:

```txt
Full export/import state machine replacement
Container lifecycle
Document upload/versioning/OCR
Exporter/importer portal
CHA/customs layer
Transport/GPS
Tracking adapters
Full exception engine
Approval engine
HOD bot
Autonomous AI writes
n8n
WhatsApp/SMS
Payment gateway
Invoice PDFs
Gmail send/modify/delete/archive
Strict tenant filtering of operational records
```

---

## 4. Safety Rules

Phase 9 may:

```txt
record operational events
run validation checks
create validation issues
create internal notifications
show manual-review warnings
provide AI read-only summaries
```

Phase 9 must not automatically:

```txt
change shipment status
change document status
change BL status
change task status
change charge status
change party status
approve payments
release BL/DO/documents
send emails
delete records
override user actions
```

Default rule:

```txt
All new validation checks are non-blocking warnings unless explicitly configured and tested.
```

---

## 5. Git Workflow

Start from updated `main` after Phase 8 is safely merged/deployed.

```bash
git status
git log --oneline -8

git checkout main
git pull origin main
git checkout -b phase-9-event-validation-rule-engine
```

Final commit:

```bash
git add .
git commit -m "Implement phase 9 event validation rule engine"
git push -u origin phase-9-event-validation-rule-engine
```

Do not deploy until tests pass.

---

# 6. Database / Alembic Requirements

Use Alembic for Phase 9 schema changes.

Add migration:

```txt
phase9_event_validation_foundation
```

Create tables:

```txt
operational_events
rule_definitions
validation_issues
```

Migration rules:

```txt
No data reset
No table drops
No destructive renames
Safe indexes
Safe nullable columns where needed
```

Keep existing startup compatibility/create_all transition behavior untouched unless absolutely required.

---

# 7. Backend Models

## 7.1 OperationalEvent

Add model:

```txt
OperationalEvent
```

Table:

```txt
operational_events
```

Fields:

```txt
id
event_type
entity_type
entity_id nullable
entity_label nullable
shipment_id nullable
actor_user_id nullable
actor_name nullable
actor_email nullable
actor_role nullable
source
correlation_id nullable
request_id nullable
previous_state_json nullable
new_state_json nullable
metadata_json nullable
validation_status
created_at
```

Suggested `source` values:

```txt
user
system
gmail
ai
scheduler
workflow
finance
notification
```

Suggested `validation_status` values:

```txt
not_checked
passed
warning
failed
manual_review_required
```

Never store:

```txt
passwords
password_hash
JWTs
Gmail access/refresh tokens
OAuth codes
API keys
DB URLs
raw request bodies
authorization headers
```

---

## 7.2 RuleDefinition

Add model:

```txt
RuleDefinition
```

Table:

```txt
rule_definitions
```

Fields:

```txt
id
rule_key
name
description
entity_type nullable
event_type nullable
severity
is_enabled
is_blocking
created_at
updated_at
```

Suggested severities:

```txt
info
warning
critical
```

Defaults:

```txt
is_enabled = true
is_blocking = false
```

Seed default rule definitions idempotently.

---

## 7.3 ValidationIssue

Add model:

```txt
ValidationIssue
```

Table:

```txt
validation_issues
```

Fields:

```txt
id
event_id nullable
rule_key
entity_type
entity_id nullable
entity_label nullable
shipment_id nullable
severity
status
message
recommended_action nullable
metadata_json nullable
created_at
acknowledged_at nullable
acknowledged_by nullable
resolved_at nullable
resolved_by nullable
```

Status values:

```txt
open
acknowledged
resolved
dismissed
```

Do not store secrets, raw emails, or raw payloads in `metadata_json`.

---

# 8. Backend Services

## 8.1 event_service.py

Replace the Phase 8 placeholder with a working service.

```python
record_operational_event(
    db,
    event_type,
    entity_type,
    entity_id=None,
    entity_label=None,
    shipment_id=None,
    actor_user=None,
    source="user",
    previous_state=None,
    new_state=None,
    metadata=None,
    request=None,
    correlation_id=None,
    run_validation=True,
)
```

Responsibilities:

```txt
create OperationalEvent
sanitize metadata
capture actor safely
optionally call validation engine
update event.validation_status
return event
```

Event logging failure must not break the original business action unless explicitly called in strict mode.

---

## 8.2 rule_engine/base.py

Implement usable base structures:

```python
@dataclass
class RuleResult:
    passed: bool
    severity: str
    message: str
    rule_key: str
    entity_type: str | None = None
    entity_id: int | None = None
    recommended_action: str | None = None
    metadata: dict | None = None
```

Add helpers:

```python
is_rule_enabled(db, rule_key)
seed_default_rule_definitions(db)
```

---

## 8.3 validation_engine/base.py

Implement validation runner:

```python
run_validation_for_event(db, event) -> list[RuleResult]
create_validation_issues_from_results(db, event, results)
summarize_validation_status(results) -> str
```

The validation runner should execute enabled rules only.

---

## 8.4 validation_engine/checks.py

Initial deterministic checks:

### Shipment checks

```txt
shipment_missing_required_fields
shipment_invalid_type
shipment_archived_write_warning
shipment_duplicate_code
```

### Task checks

```txt
task_missing_title
task_due_date_in_past_warning
task_cancelled_write_warning
```

### Charge checks

```txt
charge_negative_amount
charge_direction_status_mismatch
charge_cancelled_write_warning
charge_missing_currency
```

### Document checks

```txt
document_missing_type
document_status_invalid
document_missing_url_warning
```

### BL checks

```txt
bl_final_without_draft_warning
bl_approved_without_draft_warning
bl_missing_number_warning
```

### Gmail suggestion checks

```txt
gmail_suggestion_missing_shipment
gmail_suggestion_low_confidence
```

### Organization/auth checks

```txt
user_missing_organization_warning
```

Keep Phase 9 checks non-blocking by default.

---

## 8.5 validation_issue_service.py

Add:

```python
list_validation_issues(db, filters, user)
acknowledge_issue(db, issue_id, user)
resolve_issue(db, issue_id, user)
dismiss_issue(db, issue_id, user)
```

Permissions:

```txt
ADMIN and STAFF can list/update.
VIEW_ONLY can read only if existing permission style supports it; otherwise 403.
```

---

# 9. Event Emission Integration

Add event recording to representative actions only.

Minimum event emitters:

```txt
shipment.create
shipment.update
shipment.archive
shipment.restore

party.create
party.update
party.deactivate
party.reactivate

task.create
task.update
task.cancel
task.restore
task.delete

charge.create
charge.update
charge.cancel
charge.mark_paid
charge.mark_received

document.update
bl.update
demurrage.update

email_suggestion.apply
email_suggestion.reject

notification.run_checks
```

Rules:

```txt
Event failure must not break the main action.
Event metadata must be sanitized and allowlisted.
Do not store raw request bodies.
Do not store tokens/secrets.
```

---

# 10. Backend APIs

Add routes:

```txt
backend/app/api/routes/events.py
backend/app/api/routes/validation_issues.py
backend/app/api/routes/rules.py
```

Register:

```txt
/api/events
/api/validation-issues
/api/rules
```

---

## 10.1 Events API

Routes:

```txt
GET /api/events
GET /api/events/{event_id}
```

Filters:

```txt
event_type
entity_type
entity_id
shipment_id
source
validation_status
date_from
date_to
search
limit
offset
```

Permissions:

```txt
ADMIN and STAFF only for Phase 9.
```

---

## 10.2 Validation Issues API

Routes:

```txt
GET /api/validation-issues
GET /api/validation-issues/{issue_id}
PATCH /api/validation-issues/{issue_id}/acknowledge
PATCH /api/validation-issues/{issue_id}/resolve
PATCH /api/validation-issues/{issue_id}/dismiss
```

Filters:

```txt
status
severity
rule_key
entity_type
shipment_id
date_from
date_to
search
limit
offset
```

Permissions:

```txt
ADMIN and STAFF can list/update.
VIEW_ONLY read-only if safe, otherwise 403.
```

---

## 10.3 Rules API

Routes:

```txt
GET /api/rules
PATCH /api/rules/{rule_id}
```

Editable fields:

```txt
is_enabled
is_blocking
severity
description optional
```

Permissions:

```txt
ADMIN can update.
ADMIN/STAFF can read.
```

Do not allow editing `rule_key`.

---

# 11. Notifications Integration

When a validation issue has severity:

```txt
critical
```

create an internal notification:

```txt
Category: system or workflow
Priority: critical
Title: Manual review required
Message: validation issue message
Action URL: /validation-issues
Dedupe key: validation_issue:{rule_key}:{entity_type}:{entity_id}
```

Do not duplicate notifications endlessly.

Do not replace existing notifications or legacy alerts.

---

# 12. Audit Integration

Audit:

```txt
rule.update
validation_issue.acknowledge
validation_issue.resolve
validation_issue.dismiss
```

Optional:

```txt
event.created
```

Do not create noisy audit spam if event volume is high.

---

# 13. AI Assistant Integration

Update AI context/fallback for questions:

```txt
What validation issues exist?
What needs manual review?
What failed validation?
Show broken workflow issues.
What recent events happened?
```

Rules:

```txt
AI remains read-only.
AI cannot resolve issues.
AI cannot update rules.
AI cannot mutate operational records.
```

---

# 14. Frontend Changes

Add pages:

```txt
/events
/validation-issues
/rules
```

Recommended sidebar:

ADMIN:

```txt
Events
Validation Issues
Rules
```

STAFF:

```txt
Events
Validation Issues
```

VIEW_ONLY:

```txt
No rule editing.
Optional read-only Validation Issues if safe.
```

If sidebar is crowded, place these under:

```txt
Admin Tools
Operational Brain
```

---

## 14.1 Events Page

Show:

```txt
Event table
Filters
Event detail drawer/modal
Validation status badge
Entity link when possible
```

Columns:

```txt
Time
Event Type
Entity
Source
Actor
Validation Status
```

---

## 14.2 Validation Issues Page

Show:

```txt
Open issues
Acknowledged issues
Resolved issues
Severity filters
Rule filters
Entity filters
Actions: acknowledge, resolve, dismiss
```

Columns:

```txt
Created
Severity
Rule
Entity
Message
Status
Actions
```

---

## 14.3 Rules Page

ADMIN-only editing page.

Show:

```txt
Rule key
Name
Description
Entity type
Event type
Severity
Enabled toggle
Blocking toggle
```

Warn:

```txt
Blocking rules can affect operations. Keep disabled unless tested.
```

All new rules default to non-blocking.

---

## 14.4 Dashboard Widget

Add widget:

```txt
Validation & Manual Review
```

Show:

```txt
open critical issues
open warning issues
latest 5 validation issues
link to /validation-issues
```

Widget should fail independently if the API call fails.

Do not break existing dashboard cards.

---

# 15. README / Docs

Update README with:

```txt
Phase 9 event system
Operational events
Validation issues
Rule definitions
Non-blocking validation default
Manual-review signals
How this connects to Master 1.1
Events / Validation Issues / Rules pages
```

Add:

```txt
docs/PHASE_9_EVENT_VALIDATION_RULE_ENGINE.md
```

Include:

```txt
Architecture
Models
APIs
Default rules
Safety limits
Future Phase 10 transition to state machines
```

---

# 16. Backend Test Plan

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
```

API smoke:

```txt
Login as ADMIN
Create/update shipment and confirm operational event
Create/update task and confirm operational event
Create/update charge and confirm operational event
Apply/reject Gmail suggestion and confirm event
GET /api/events
GET /api/validation-issues
GET /api/rules
PATCH /api/rules/{id} as ADMIN
PATCH rule as STAFF -> 403
Acknowledge/resolve/dismiss validation issue
```

Validation checks:

```txt
Duplicate shipment code creates issue/warning
Charge direction/status mismatch creates issue if introduced
Archived shipment write creates warning
Gmail suggestion missing shipment creates issue
BL approved without draft creates warning
```

Regression:

```txt
Login
Dashboard
Shipments
Parties
Tasks
Documents
BL
Demurrage
Follow-ups
Alerts
Notifications
Charges
Reports
AI
Gmail automation
Users
Audit logs
Status
Admin tools
Organization foundation
```

---

# 17. Frontend Test Plan

Run:

```bash
cd frontend
npm run build
```

Manual smoke:

```txt
Events page loads
Validation Issues page loads
Rules page loads for ADMIN
STAFF cannot edit rules
Dashboard widget loads
Existing pages still load
Role sidebar remains sane
```

---

# 18. Security Test Plan

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

Also inspect event metadata and validation issue metadata for:

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

# 19. Acceptance Criteria

Phase 9 is complete only when:

```txt
[ ] Backend compiles
[ ] Frontend builds
[ ] Alembic migration exists
[ ] OperationalEvent model/table exists
[ ] RuleDefinition model/table exists
[ ] ValidationIssue model/table exists
[ ] Default rule definitions are seeded
[ ] Representative actions create operational events
[ ] Validation engine runs for representative events
[ ] Validation issues are created for failed checks
[ ] Critical issues create deduped notifications
[ ] Events API works
[ ] Validation Issues API works
[ ] Rules API works
[ ] Admin can update rules
[ ] Staff cannot update rules
[ ] Event failure does not break main business action
[ ] Validation is non-blocking by default
[ ] Dashboard validation widget works
[ ] AI can summarize validation/manual-review issues read-only
[ ] Existing Phase 1–8 features still work
[ ] No secrets committed or stored in event/issue metadata
```

---

# 20. Final Commit

After all checks pass:

```bash
git status
git add .
git commit -m "Implement phase 9 event validation rule engine"
```

Push:

```bash
git push -u origin phase-9-event-validation-rule-engine
```

---

# 21. Final Report Required

After implementation, report:

```txt
Backend compile result
Frontend build result
Alembic migration result
Event API test result
Validation issue API test result
Rules API test result
Representative event emission test result
Validation issue creation test result
Notification integration test result
AI validation summary test result
Role permission test result
Regression test result for Phases 1–8
Secret scan result
Git status
Commit hash
Known limitations
```
