# MASTER_1_1_INTERNAL_PILOT_PLAN_FOR_CLAUDE.md

# Freight Forwarding Operational Intelligence System
# Master 1.1 Internal Pilot Plan for Claude

## Purpose

Use this plan with Claude/Codex to run a controlled **Master 1.1 Internal Pilot** after completion of Phases 1–25.

The system is certified as:

```txt
Freight Forwarding Operational Intelligence System — Master 1.1 Internal Pilot
```

The goal of this pilot is not to add new features. The goal is to operate the system like a real freight-forwarding firm would use it, find real operational gaps, verify role/security boundaries, and produce a clean post-pilot bug/fix roadmap.

---

# 1. Current System Status

Completed phases:

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

Final certification status:

```txt
Release recommendation: READY FOR INTERNAL PILOT
Critical bugs: 0
High bugs: 0
Medium bugs: 0
Known low issue: bundle size warning only
```

---

# 2. Strict Master 1.1 Pilot Rule

During the pilot, Claude must strictly follow Master 1.1.

Do not add random features.

Do not redesign the system.

Do not start Master 1.2 yet.

Pilot focus:

```txt
real usage
bug discovery
workflow validation
permission validation
security verification
missing field discovery
UX friction
performance observation
data quality issues
release readiness
```

Forbidden during pilot unless explicitly approved:

```txt
new operational modules
new AI autonomy
new external integrations
new GPS vendor
new tracking provider
new customs filing automation
new payment/accounting integration
new portal type
new prediction models
destructive cleanup
production data deletion
```

---

# 3. Pilot Objective

Claude must operate as a **15+ year logistics operations QA lead + product manager + enterprise implementation auditor**.

The pilot should answer:

```txt
Can a real freight-forwarding team use this app daily?
Where does the workflow feel incomplete?
Which fields are missing?
Which pages are confusing?
Which operations are too slow?
Which permissions are risky?
Which reports are useful or not useful?
Which AI/bot outputs are reliable?
Which modules need patching before private beta?
```

The expected outcome is:

```txt
1. Master 1.1 Internal Pilot Report
2. Pilot bugs list
3. Pilot operational gaps list
4. Pilot UX friction list
5. Pilot data model gap list
6. Pilot security/permission findings
7. Master 1.1 Patch Plan
8. Go / No-Go recommendation for Private Beta
```

---

# 4. Pilot Duration

Recommended pilot duration:

```txt
7 to 14 days
```

Minimum pilot duration:

```txt
3 full working days
```

Do not conclude the pilot after only compile/build tests.

The app must be used like a real operations system.

---

# 5. Pilot Users

Use controlled users only.

Recommended users:

```txt
ADMIN user
STAFF / operations user
VIEW_ONLY user
Portal customer user
Optional finance/admin tester
```

Do not allow public users.

Do not onboard external real clients yet unless explicitly approved.

---

# 6. Pilot Data Rules

Use controlled pilot records.

Use prefixes:

```txt
PILOT-
QA-
TEST-
MASTER11-
```

Examples:

```txt
PILOT-EXPORT-001
PILOT-IMPORT-001
PILOT-CUSTOMER-001
PILOT-CHA-001
PILOT-TRANSPORTER-001
PILOT-INVOICE-001
```

Do not test using uncontrolled real customer data unless the user explicitly approves.

Do not delete production/admin/system/configuration data.

Do not print secrets.

Do not open or expose:

```txt
.env
.env.e2e
DATABASE_URL
JWT_SECRET_KEY
Gmail tokens
OAuth secrets
Groq/OpenAI keys
client_secret JSON
uploaded private files
```

---

# 7. Required Pilot Test Scenarios

## 7.1 Export Shipment Pilot Scenario

Create and operate one full export cycle.

Required flow:

```txt
Create exporter party
Create consignee/buyer party
Create CHA party
Create transporter party
Create export shipment
Add container
Add workflow milestones
Upload commercial invoice
Upload packing list
Run document intelligence
Review mismatches/suggestions
Create receivable/payable charge
Check finance release status
Create customs export case
Assign CHA
Complete customs checklist
Add shipping bill / LEO reference
Create transport pickup job
Assign transporter/vehicle/driver
Add manual location update
Complete gate-in milestone
Create tracking watch item
Run mock tracking sync
Check control tower
Run predictive risk
Resolve or record exceptions
Verify approval flow if risky action is attempted
```

Expected result:

```txt
Export shipment can be operated end-to-end.
Invalid transitions are blocked or flagged.
Sensitive overrides require approval/manual review.
AI remains read-only.
No automatic business mutation occurs.
```

---

## 7.2 Import Shipment Pilot Scenario

Create and operate one full import cycle.

Required flow:

```txt
Create importer party
Create shipper/supplier party
Create CHA party
Create transporter party
Create import shipment
Add container
Upload BL/AWB, invoice, packing list
Run document intelligence
Check document mismatches
Create finance charges and release check
Create customs import case
Assign CHA
Add BOE/OOC references
Create transport delivery job
Assign transporter/vehicle/driver
Add manual location update
Complete delivery milestone
Track empty return status
Create tracking watch item
Run mock tracking sync
Check detention/demurrage risk
Check control tower
Run predictive risk
Verify exceptions/approvals if needed
```

Expected result:

```txt
Import shipment can be operated end-to-end.
OOC/customs/finance/empty return risks are visible.
No automatic closure without evidence.
```

---

# 8. Module-by-Module Pilot Checklist

Claude must test and report on each module.

## 8.1 Auth / Users / Roles

Test:

```txt
ADMIN login
STAFF login
VIEW_ONLY login
invalid password
protected route before login
role-based visibility
```

Report:

```txt
pass/fail
bugs
security concerns
UX issues
```

---

## 8.2 Shipments

Test:

```txt
create export shipment
create import shipment
edit shipment
open shipment detail
archive/restore
search/filter
invalid fields
shipment code auto-generation
```

---

## 8.3 Parties

Test:

```txt
create exporter
create importer
create CHA
create transporter
create customer/vendor
edit party
search/filter
inactive status
party links
```

---

## 8.4 Workflow / State Machines

Test:

```txt
valid transition
invalid transition
export state flow
import state flow
workflow logs
approval-triggered sensitive transition
```

---

## 8.5 Containers

Test:

```txt
create container
container lifecycle
demurrage risk
detention risk
empty return
invalid container data
container linked to shipment/transport/tracking
```

---

## 8.6 Documents

Test:

```txt
upload document
upload second version
download
approve/reject
rollback
customer-visible flag
internal document hidden from portal
```

---

## 8.7 Document Intelligence

Test:

```txt
run intelligence
classification
field extraction
mismatch detection
suggestion approve/reject/dismiss
no auto-apply
```

---

## 8.8 Finance / Credit Control

Test:

```txt
create receivable
create payable
create payment
payment allocation
over-allocation block
credit profile
credit hold
release check
aging
FX
P&L totals
cancelled charges excluded
restricted finance visibility
```

---

## 8.9 Gmail

Test:

```txt
Gmail status
connected/disconnected state
read-only scope
no send
no modify
no delete
no archive
suggestion dedupe
account reconnect behavior
```

---

## 8.10 Exceptions / Manual Review

Test:

```txt
run exception detection
dedupe active cases
acknowledge
assign
comment
escalate
resolve
dismiss
reopen
SLA policies
```

---

## 8.11 Approvals / HOD Governance

Test:

```txt
create approval
submit
approve
reject
request changes
cancel
execute approved action
maker-checker blocks own high-risk approval
action lock works
bot action approval
```

---

## 8.12 Bot Governance

Test:

```txt
default bot agents
bot action records
feedback
learning candidates
prompt/rule versions if present
guardrail violations
pause/resume bot
VIEW_ONLY cannot mutate
no autonomous bot action
```

---

## 8.13 Portal

Test:

```txt
portal account
party link
shipment access grant
document visibility
portal request
portal notification
portal cannot see other customers
portal cannot see internal margin/payables/Gmail/audit/bot/internal approval data
```

---

## 8.14 Customs

Test:

```txt
customs case
CHA assignment
milestones
checklist
document requirements
queries/comments
references
duty records
OOC/LEO
portal-safe customs summary
no government filing automation
```

---

## 8.15 Transport

Test:

```txt
transport job
transporter assignment
vehicle
driver
milestones
manual location
POD/LR docs
exceptions
empty return
portal-safe transport summary
no live GPS unless configured
no driver private data leakage
```

---

## 8.16 Tracking

Test:

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

---

## 8.17 Control Tower

Test:

```txt
summary
operations health
risk heatmap
top risks
SLA overdue
map placeholders
ETA/ETD changes
tracking source health
stale data monitor
party performance
drill-down links
widget failure isolation
portal blocked
```

---

## 8.18 Predictive Intelligence

Test:

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

---

## 8.19 Enterprise Governance

Test:

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
cross-org isolation if multi-org test data exists
```

---

# 9. Human-Like Browser QA

Claude must use browser testing if available.

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
page loads
no blank screen
no console-breaking error
forms usable
buttons usable
empty states work
error states work
role restrictions visible
drill-down links work
mobile layout acceptable
```

If browser testing is blocked, report exactly why.

Do not pretend browser testing passed if it did not run.

---

# 10. Security Pilot Checklist

Claude must verify:

```txt
No secrets committed
No secrets in API responses
No portal cross-customer leakage
No portal access to internal APIs
No VIEW_ONLY mutation
No STAFF enterprise-policy mutation
No driver private data leakage to portal
No internal margin/payables leakage
No Gmail token/email body leakage
No bot prompt/rule internals leakage
No approval policy internals leakage
No provider secret leakage
No prediction metadata leakage
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

# 11. AI / Bot Safety Pilot

Test these prompts:

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
Can you mark this shipment complete?
```

Expected:

```txt
AI gives read-only summaries.
AI does not mutate business data.
AI refuses or redirects unsafe actions to manual/approval workflow.
AI explains uncertainty and missing data.
```

---

# 12. Performance / Reliability Pilot

Observe:

```txt
dashboard load time
control tower load time
document dashboard-summary load time
prediction run duration
tracking mock sync duration
enterprise health check duration
frontend route load time
browser console errors
API timeout errors
```

Classify issues:

```txt
critical
high
medium
low
```

Fix critical/high before private beta.

---

# 13. Pilot Bug Severity Rules

Use this severity scale:

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

Pilot exit rule:

```txt
0 critical bugs
0 high bugs
medium bugs fixed or explicitly accepted
low bugs documented
```

---

# 14. Required Output Files

Claude must create these files:

```txt
PILOT_MASTER_1_1_REPORT.md
PILOT_MASTER_1_1_BUGS.md
PILOT_MASTER_1_1_OPERATIONAL_GAPS.md
PILOT_MASTER_1_1_UX_ISSUES.md
PILOT_MASTER_1_1_SECURITY_FINDINGS.md
PILOT_MASTER_1_1_PERFORMANCE_NOTES.md
PILOT_MASTER_1_1_PATCH_PLAN.md
pilot_master_1_1_run.json
```

Do not commit these automatically unless user approves.

---

# 15. Final Pilot Report Format

The final report must include:

```txt
Pilot date range
Branch/commit tested
Environment
Backend compile result
Frontend build result
Alembic result
Browser QA result
Export workflow result
Import workflow result
Module certification summary
Role/permission result
Portal isolation result
Enterprise governance result
AI read-only result
Gmail read-only result
Bot governance result
Predictive no-auto-mutation result
Security scan result
Performance result
Bugs found by severity
Operational gaps
UX issues
Missing fields
Recommended patch list
Private beta readiness
```

Final recommendation must be one of:

```txt
READY FOR PRIVATE BETA
READY FOR INTERNAL PILOT CONTINUATION
NOT READY
```

Do not mark private beta ready if critical/high bugs remain.

---

# 16. Claude Execution Prompt

Use this exact prompt with Claude:

```txt
You are the QA lead, logistics operations auditor, product manager, and enterprise implementation reviewer for my Freight Forwarding Operational Intelligence System.

The system has completed Master 1.1 Phases 1–25 and is certified as READY FOR INTERNAL PILOT.

Your task is to run a real internal pilot simulation, not just compile/build tests.

Strictly follow Master 1.1.
Do not add random features.
Do not start Master 1.2.
Do not mutate or delete real data unless explicitly instructed.
Use only controlled pilot records with prefixes PILOT-, QA-, TEST-, MASTER11-.
Do not print or expose secrets.

Pilot goals:
1. Use the app like a real freight-forwarding team.
2. Run at least one export shipment cycle and one import shipment cycle.
3. Test all major modules from Auth through Enterprise Governance.
4. Verify portal isolation, role permissions, AI read-only behavior, Gmail read-only behavior, bot governance, prediction no-auto-mutation, and enterprise controls.
5. Identify bugs, operational gaps, UX issues, missing fields, slow pages, confusing flows, and security risks.
6. Create a patch plan for Master 1.1 Internal Pilot fixes.
7. Do not recommend Master 1.2 until pilot findings are reviewed.

Required output files:
PILOT_MASTER_1_1_REPORT.md
PILOT_MASTER_1_1_BUGS.md
PILOT_MASTER_1_1_OPERATIONAL_GAPS.md
PILOT_MASTER_1_1_UX_ISSUES.md
PILOT_MASTER_1_1_SECURITY_FINDINGS.md
PILOT_MASTER_1_1_PERFORMANCE_NOTES.md
PILOT_MASTER_1_1_PATCH_PLAN.md
pilot_master_1_1_run.json

Required final recommendation:
READY FOR PRIVATE BETA
or
READY FOR INTERNAL PILOT CONTINUATION
or
NOT READY

Do not claim a test passed unless you actually ran it.
If browser testing is blocked, say exactly why.
If a module cannot be tested due to missing data/user/config, document it clearly.
```

---

# 17. What To Do After Pilot

After Claude finishes, do not immediately build new features.

Next step should be:

```txt
Master 1.1 Internal Pilot Patch
```

Patch categories:

```txt
critical bug fixes
high bug fixes
medium accepted/fixed
UX cleanup
missing fields
performance improvements
permission hardening
documentation updates
```

Only after the patch is stable should you consider:

```txt
Private Beta
```

Only after private beta should you plan:

```txt
Master 1.2 Roadmap
```
