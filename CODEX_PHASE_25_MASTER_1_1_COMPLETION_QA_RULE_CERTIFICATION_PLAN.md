# CODEX_PHASE_25_MASTER_1_1_COMPLETION_QA_RULE_CERTIFICATION_PLAN.md

# Phase 25 — Master 1.1 Completion QA + Rule Certification

## Purpose

Implement **Phase 25**, the final Master 1.1 completion phase.

Phase 24 added Enterprise Scaling + Multi-Organization Governance. Phase 25 must **not add new product features**. It must certify that the entire EXIM / Freight Forwarding Operational Intelligence System is complete, safe, consistent, testable, governed, and aligned with **Master 1.1**.

The goal:

```txt
Validate the full system end-to-end.

Certify that every phase from Phase 1 to Phase 24 works together safely:
operations, workflow, validation, containers, documents, finance, exceptions, approvals, bot governance, portal, customs, transport, tracking, control tower, predictive intelligence, and enterprise governance.

No final release should happen until Master 1.1 rule certification, security verification, role testing, migration verification, browser QA, API regression, and production readiness checks pass.
```

Phase 25 is the final QA/certification layer.

---

# 1. Current Completed Roadmap

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
Phase 9.1    Gmail cleanup/dedupe/account scoping
Phase 10     Strong export/import state machines
Phase 11     Container lifecycle + demurrage/detention
Phase 12     Document upload + versioning
Phase 13     Document intelligence + OCR + mismatch validation
Phase 14     Finance + credit control
Phase 15     Exception engine + manual review center
Phase 16     Approval engine + HOD governance
Phase 17     Bot governance + learning system
Phase 18     Exporter / Importer portal
Phase 19     CHA / Customs coordination
Phase 20     Transport + GPS layer
Phase 21     Tracking adapters
Phase 22     Full Control Tower Dashboard + Master 1.1 alignment
Phase 23     Predictive Intelligence
Phase 24     Enterprise Scaling + Multi-Organization Governance
Phase 25     Master 1.1 Completion QA + Rule Certification
```

---

# 2. Strict Master 1.1 Rule

Strictly follow Master 1.1.

Phase 25 must not create random new functionality.

Allowed:

```txt
QA
certification
rule validation
workflow validation
security validation
role validation
migration verification
browser testing
API regression
release readiness
documentation
bug fixing
hardening
```

Not allowed:

```txt
new modules
new AI autonomy
new prediction models
new portals
new tracking providers
new GPS integrations
new customs filing automation
new payments/accounting integration
new maps
new external webhooks
new WhatsApp/SMS automation
```

---

# 3. Git Workflow

Start from clean `main` after Phase 24 is committed, pushed, migrated, and smoke-tested.

```bash
cd /Users/akbroc/Desktop/freight-forwarding-phase1

git status
git checkout main
git pull origin main
git checkout -b phase-25-master-1-1-completion-certification
```

Final commit:

```bash
git add .
git commit -m "Complete Master 1.1 QA and rule certification"
git push -u origin phase-25-master-1-1-completion-certification
```

Merge only after all certification checks pass:

```bash
git checkout main
git pull origin main
git merge phase-25-master-1-1-completion-certification
git push origin main
```

---

# 4. Phase 25 Deliverables

Create these files:

```txt
docs/MASTER_1_1_COMPLETION_CERTIFICATION.md
docs/MASTER_1_1_FINAL_QA_REPORT.md
docs/MASTER_1_1_SECURITY_CERTIFICATION.md
docs/MASTER_1_1_RULE_CERTIFICATION.md
docs/MASTER_1_1_RELEASE_CHECKLIST.md
docs/MASTER_1_1_KNOWN_LIMITATIONS.md
```

If a docs folder does not exist, create it.

Also create optional machine-readable output:

```txt
master_1_1_certification_run.json
```

Do not commit temporary browser reports unless intentionally useful and sanitized.

---

# 5. Backend Certification

Run:

```bash
cd backend
source .venv/bin/activate

python -m compileall app
.venv/bin/alembic history
.venv/bin/alembic heads
.venv/bin/alembic current
.venv/bin/alembic upgrade head
```

Expected:

```txt
Backend compiles with 0 errors.
Alembic has one head.
Current revision equals latest Phase 24 head.
Upgrade head succeeds from current DB.
```

If fresh DB testing is available, also test:

```txt
fresh database -> alembic upgrade head -> app imports -> startup works
```

---

# 6. Frontend Certification

Run:

```bash
cd frontend
npm run build
npm run test:e2e
```

If headed browser is available:

```bash
npm run test:e2e:headed
```

Expected:

```txt
Frontend build passes.
Browser tests pass or failures are documented and classified.
No critical UI crash.
No protected route leakage.
```

---

# 7. Route / API Certification

Generate and inspect route list.

Required modules must still have registered routes:

```txt
auth/users
shipments
parties
tasks/followups
workflow
containers
documents
document intelligence
finance
gmail
exceptions/manual review
approvals
bot governance
portal
customs
transport
tracking
control tower
predictive
enterprise
ai
notifications
alerts
```

Check:

```txt
No duplicate route conflict
Static routes appear before dynamic /{id} routes
No important route shadowing
All route imports clean
```

Special route-ordering checks:

```txt
/api/exceptions/sla-policies before /api/exceptions/{id}
/api/approvals/policies before /api/approvals/{id}
/api/approvals/action-locks before /api/approvals/{id}
/api/approvals/bot-actions before /api/approvals/{id}
/api/customs/queries before /api/customs/{case_id}
/api/transport/vehicles before /api/transport/{job_id}
/api/tracking/providers before dynamic tracking IDs if any
/api/predictive/models before /api/predictive/models/{id}
/api/enterprise/health before dynamic organization routes
```

---

# 8. Master 1.1 Architecture Certification

Certify these architecture layers:

```txt
Operational system
Intelligence system
Workflow engine
Validation/rule engine
Exception engine
Approval/HOD governance
Bot governance
External party access
Control tower
Predictive intelligence
Enterprise governance
Final QA/certification
```

For each layer, report:

```txt
Implemented: yes/no
Files/APIs involved
Test result
Known limitation
Master 1.1 alignment status
```

---

# 9. Workflow + Rule Certification

Certify deterministic rules before AI.

## Export workflow

Test:

```txt
Create export shipment
Container lifecycle
Document upload/checklist
Document intelligence
Finance/release check
Customs export case / LEO status
Transport pickup/gate-in
Tracking watch item
Exceptions if required data missing
Approval if risky override
Control Tower shows status
Predictive risk can run
```

Expected:

```txt
Invalid transitions blocked or flagged.
Sensitive overrides require approval/manual review.
AI does not mutate state.
```

## Import workflow

Test:

```txt
Create import shipment
Container lifecycle
Document upload/checklist
Document intelligence
Finance/release check
Customs import case / OOC status
Transport delivery/empty return
Tracking watch item
Exceptions if missing/overdue
Approval if risky override
Control Tower shows status
Predictive risk can run
```

Expected:

```txt
Invalid transitions blocked or flagged.
OOC/customs/finance/empty return risks visible.
No automatic closure without evidence.
```

---

# 10. Module Certification Checklist

Certify each module:

## 10.1 Auth / Users / Roles

```txt
ADMIN login works
STAFF login works
VIEW_ONLY login works
invalid login blocked
protected routes blocked before login
role restrictions enforced
```

## 10.2 Shipments

```txt
create export
create import
open detail
edit safe fields
archive/restore
invalid data blocked
shipment code auto-generation works
```

## 10.3 Parties

```txt
create exporter/importer/customer/vendor/CHA/transporter
edit party
search/filter
party links work
inactive behavior safe
```

## 10.4 Workflow

```txt
valid transitions work
invalid transitions blocked/flagged
export/import state machines consistent
sensitive transitions require review/approval where applicable
```

## 10.5 Containers

```txt
container create
container lifecycle
demurrage risk
detention risk
empty return status
invalid container data blocked/flagged
```

## 10.6 Documents

```txt
upload
versioning
download
approve/reject
rollback
customer-visible flag
internal document hidden from portal
```

## 10.7 Document Intelligence

```txt
classification
field extraction
mismatch detection
suggestions
approve/reject/dismiss suggestion
no auto-apply without explicit user action
```

## 10.8 Finance / Credit Control

```txt
receivables
payables
payments
allocation
over-allocation blocked
credit profile
credit hold
release check
aging
FX
P&L excludes cancelled items
restricted finance hidden from unauthorized roles
```

## 10.9 Gmail

```txt
Gmail status
read-only scope preserved
no send
no modify
no delete
no archive
suggestions dedupe
account disconnect/reconnect scoped correctly
```

## 10.10 Exceptions / Manual Review

```txt
detect exceptions
dedupe active cases
acknowledge
assign
comment
escalate
resolve
dismiss
reopen
SLA policies safe
```

## 10.11 Approvals / HOD Governance

```txt
create approval
submit
approve
reject
request changes
cancel
execute safe action
maker-checker blocks own high-risk approval
action locks work
policy routes work
```

## 10.12 Bot Governance

```txt
default bot agents seeded
action records
feedback
learning candidates
prompt/rule versioning if present
guardrail violations
pause/resume bot
VIEW_ONLY cannot mutate
no autonomous bot action
```

## 10.13 Portal

```txt
portal account
party link
shipment access grant
document visibility
portal request
portal notification
portal cannot see other customers
portal cannot see margin/payables/Gmail/audit/bot/internal approval data
```

## 10.14 Customs

```txt
customs case
CHA assignment
milestones
checklist
document requirements
queries/comments
references
duty records
OOC/LEO status
portal-safe customs summary
no government filing automation
```

## 10.15 Transport

```txt
transport job
transporter assignment
vehicle/driver
milestones
manual location
POD/LR docs
exceptions
empty return
portal-safe transport summary
no live GPS unless configured
no driver private data leakage
```

## 10.16 Tracking

```txt
providers seeded
watch items
manual observation
mock sync
normalization
suggestions
mismatches
sync runs
portal-safe tracking summary
no plaintext provider secrets
no automatic state mutation
```

## 10.17 Control Tower

```txt
summary
operations
risk heatmap real-data based
top risks
SLA overdue
map readiness placeholders
ETA/ETD changes
tracking source health
stale data monitor
party performance
drill-down links
widget failure isolation
portal blocked
```

## 10.18 Predictive Intelligence

```txt
models seeded
prediction run
prediction records
explanations
recommendations
outcomes
feedback
control tower predictive summary
no automatic mutation
portal blocked/safely scoped
```

## 10.19 Enterprise Governance

```txt
default organization
admin membership
roles seeded
permission policies seeded
permission matrix
health checks
security events
audit exports
data retention policies
portal blocked
VIEW_ONLY cannot mutate
cross-org isolation checked
```

---

# 11. Security Certification

Run secret scan excluding local env/build artifacts:

```bash
grep -R "GOOGLE_CLIENT_SECRET" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=playwright-report --exclude-dir=test-results --exclude-dir=uploaded_documents --exclude=".env" --exclude=".env.e2e" || true
grep -R "GROQ_API_KEY" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=playwright-report --exclude-dir=test-results --exclude-dir=uploaded_documents --exclude=".env" --exclude=".env.e2e" || true
grep -R "OPENAI_API_KEY" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=playwright-report --exclude-dir=test-results --exclude-dir=uploaded_documents --exclude=".env" --exclude=".env.e2e" || true
grep -R "postgresql://" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=playwright-report --exclude-dir=test-results --exclude-dir=uploaded_documents --exclude=".env" --exclude=".env.e2e" || true
grep -R "DATABASE_URL=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=playwright-report --exclude-dir=test-results --exclude-dir=uploaded_documents --exclude=".env" --exclude=".env.e2e" || true
grep -R "JWT_SECRET_KEY=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=playwright-report --exclude-dir=test-results --exclude-dir=uploaded_documents --exclude=".env" --exclude=".env.e2e" || true
```

Also inspect API responses/logs for:

```txt
password
token
secret
DATABASE_URL
JWT
Gmail token
OAuth token
raw email body
raw file bytes
provider API key
driver license/phone exposed to portal
internal notes exposed to portal
margin/payables exposed to unauthorized role
bot prompt/rule internals exposed to unauthorized role
approval policy internals exposed to unauthorized role
cross-org shipment/finance/portal data
```

Expected:

```txt
No secrets committed.
No sensitive payload leakage.
Portal and VIEW_ONLY restrictions enforced.
```

---

# 12. AI / Bot Certification

Certify:

```txt
AI is read-only by default
AI does not mutate business data
AI does not approve/reject/resolve/dismiss/apply
AI can summarize only allowed context
Bot actions remain proposals unless approved
Bot governance tracks actions/feedback/guardrails
Prediction recommendations do not auto-apply
Gmail remains read-only
```

Test AI prompts:

```txt
What needs attention today?
Which shipments are likely delayed?
Which containers risk demurrage?
Which customs cases are delayed?
Which approvals are blocking release?
Which bots need review?
Can you approve this request?
Can you release this document?
Can you send this Gmail?
```

Expected:

```txt
AI answers read-only summaries.
AI refuses or redirects mutation to proper manual/approval workflow.
```

---

# 13. Role / Permission Certification

Test these roles:

```txt
ADMIN
STAFF
VIEW_ONLY
portal/customer user
```

Expected:

```txt
ADMIN:
  can manage all internal modules and enterprise governance

STAFF:
  can perform operational work but not enterprise/admin-only policy actions

VIEW_ONLY:
  can read allowed summaries but cannot mutate

portal/customer:
  can access only portal-safe data and assigned shipments
  cannot access internal routes
```

Blocked route groups for portal:

```txt
/api/control-tower/*
/api/predictive/*
/api/enterprise/*
/api/bot-governance/*
/api/approvals/policies
/api/audit/*
internal finance/payables/margin endpoints
```

---

# 14. Browser Human-Like QA

Use Playwright and manual click-through.

Required pages:

```txt
Login
Dashboard
Shipments
Parties
Workflow
Containers
Documents
Document Intelligence
Finance
Gmail
Manual Review
Approvals
Bot Governance
Portal
Customs
Transport
Tracking
Control Tower
Predictive
Enterprise
AI Assistant
Settings/Admin
```

For each page check:

```txt
loads
no blank screen
no console-breaking error
buttons/forms usable
role restrictions visible
empty state works
error state works
mobile layout usable enough
drill-down links work
```

---

# 15. Performance / Reliability Certification

Check:

```txt
dashboard endpoints respond
control tower does not freeze
document summary does not timeout
prediction run is bounded
tracking mock sync is bounded
enterprise health check is bounded
widgets fail independently
frontend build bundle acceptable
no obvious N+1 endpoint issue for dashboard/control tower
```

If a performance issue is found:

```txt
classify severity
fix if high/critical
document if low/non-blocking
```

---

# 16. Production Readiness Checklist

Verify:

```txt
Render deploy succeeds
Neon database migration succeeds
alembic current = latest phase
environment variables configured
CORS configured
Gmail read-only credentials safe
Groq/AI key only in env
JWT secret only in env
uploaded_documents ignored/not committed
frontend dist ignored/not committed
playwright reports ignored/not committed
test data cleanup script safe
backup/recovery plan documented
admin user exists
default organization exists
```

---

# 17. Required Final Reports

Create:

```txt
docs/MASTER_1_1_COMPLETION_CERTIFICATION.md
docs/MASTER_1_1_FINAL_QA_REPORT.md
docs/MASTER_1_1_SECURITY_CERTIFICATION.md
docs/MASTER_1_1_RULE_CERTIFICATION.md
docs/MASTER_1_1_RELEASE_CHECKLIST.md
docs/MASTER_1_1_KNOWN_LIMITATIONS.md
```

Each report must include:

```txt
date
commit hash
branch
test environment
pass/fail status
bugs found
bugs fixed
known limitations
release recommendation
```

---

# 18. Known Limitations Section

Document honestly.

Expected possible limitations:

```txt
No real paid AIS/live vessel API yet unless separately integrated
No real GPS provider integration yet
No ICEGATE/customs filing automation
No payment gateway/accounting sync
No public tracking page
Predictive intelligence is deterministic/rule-based, not ML-trained
Maps may be placeholder/readiness-only
Enterprise multi-org enforcement may be foundation-level if existing tables are not fully organization_id scoped
```

These are acceptable if documented because they match phased Master 1.1 scope.

---

# 19. Bug Severity Rules

Classify bugs:

```txt
Critical:
  data leakage, auth bypass, destructive mutation, migration failure, app cannot start

High:
  wrong finance totals, portal cross-customer leak, approval bypass, workflow corruption

Medium:
  module partially broken, important UI blocked, role issue with limited scope

Low:
  cosmetic bug, slow widget, missing empty state, non-blocking UX issue
```

Release rule:

```txt
0 critical bugs
0 high bugs
medium bugs must be fixed or explicitly accepted
low bugs can be documented
```

---

# 20. Acceptance Criteria

Phase 25 is complete only when:

```txt
[ ] Backend compile passes
[ ] Frontend build passes
[ ] Alembic single head confirmed
[ ] Fresh migration path confirmed if possible
[ ] API regression passes
[ ] Browser QA passes or documented
[ ] All core modules tested
[ ] Export workflow certified
[ ] Import workflow certified
[ ] Portal isolation certified
[ ] Enterprise governance certified
[ ] AI read-only behavior certified
[ ] Gmail read-only behavior certified
[ ] Bot governance certified
[ ] Prediction no-auto-mutation certified
[ ] Control Tower real-data risk certified
[ ] Security scan passes
[ ] No critical/high bugs remain
[ ] Final reports created
[ ] Release recommendation written
```

---

# 21. Final Commit

After all certification reports are created and issues are fixed:

```bash
git status
git add docs README.md backend/app frontend/src
git commit -m "Complete Master 1.1 QA and rule certification"
```

If certification also required test fixes, include those changed files.

Push:

```bash
git push -u origin phase-25-master-1-1-completion-certification
```

Merge:

```bash
git checkout main
git pull origin main
git merge phase-25-master-1-1-completion-certification
git push origin main
```

---

# 22. Final Output Required From Codex

At completion, Codex must report:

```txt
Backend compile result
Frontend build result
Alembic head/current result
API regression result
Browser QA result
Export workflow certification
Import workflow certification
Module certification summary
Role/permission certification
Portal isolation certification
Enterprise governance certification
AI read-only certification
Gmail read-only certification
Bot governance certification
Prediction no-auto-mutation certification
Security scan result
Performance/reliability result
Bugs found by severity
Bugs fixed
Known limitations
Final release recommendation
Git status
Commit hash
```

Final release recommendation must be one of:

```txt
READY FOR INTERNAL PILOT
READY FOR PRIVATE BETA
READY FOR PRODUCTION RELEASE
NOT READY
```

Do not mark production-ready if critical/high bugs remain.
