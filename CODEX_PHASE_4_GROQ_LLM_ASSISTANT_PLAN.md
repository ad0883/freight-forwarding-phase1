# Codex Implementation Plan — Phase 4 Groq LLM Assistant

## Purpose

Implement **Phase 4** of the Freight Forwarding AI-Powered Management System.

Phase 4 upgrades the existing rule-based/mock AI assistant into a real **Groq-powered LLM assistant**.

The assistant should help users ask natural-language questions about:

```txt
Shipments
Tasks
Documents
Workflow status
BL Management
Demurrage
Follow-ups
Charges
Reports
Pending receivables/payables
Shipment P&L
Operational risks
Suggested next actions
```

Phase 4 must preserve all existing Phase 1, Phase 2, Phase 3, and Phase 3.5 behavior.

Existing hosted app:

```txt
Frontend: https://freight-frontend-u051.onrender.com
Backend:  https://freight-backend-au6c.onrender.com
```

---

# 1. Existing System Context

The app already has:

```txt
React.js + Vite frontend
FastAPI backend
PostgreSQL / Neon database
JWT + bcrypt authentication
Role-based access: ADMIN / STAFF / VIEW_ONLY

Phase 1:
- Login
- Users and roles
- Shipment creation
- Party directory
- Document checklist
- Basic tasks
- Dashboard
- Mock AI

Phase 2:
- Workflow automation
- BL Management
- Demurrage
- Follow-up Log
- Better alerts

Phase 3:
- Charges
- Shipment P&L
- Reports
- Dashboard financial cards
- Mock AI finance questions

Phase 3.5:
- Shipment archive/restore
- Party deactivate/reactivate/delete-if-unused
- Task cancel/restore/delete-manual
- Archived/inactive/cancelled filtering
```

Preserve all existing behavior.

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
Archive/deactivate/cancel controls
Dashboard
Render deployment
```

---

# 2. Phase 4 Goal

Replace or upgrade the current rule-based mock AI assistant with a real Groq-backed LLM assistant.

The assistant must be:

```txt
Database-aware
Read-only by default
Safe for business records
Grounded in app data
Clear when data is missing
Able to suggest next actions
Unable to directly modify/delete/archive records in Phase 4
```

Core design rule:

```txt
The LLM must not directly access the database.

The backend should:
1. Receive the user question.
2. Detect intent with deterministic logic.
3. Fetch only relevant data from the database.
4. Build a safe summarized context.
5. Send only that context to Groq.
6. Return a structured response to the frontend.
```

---

# 3. Strict Phase 4 Non-Goals

Do **not** implement these in Phase 4:

```txt
OpenAI API as the primary provider
Gmail API
Email parsing
Automatic email replies
Google Drive API upload
AWS S3 upload
Direct document OCR
Payment gateway
Invoice PDF generation
Accounting integration
Celery
Redis
Autonomous database writes
AI executing archive/delete/cancel actions
AI creating shipments automatically
AI modifying charges automatically
AI sending messages/emails
```

The AI can suggest actions, but it must not perform write actions.

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
git checkout -b phase-4-groq-llm-assistant
```

If branch exists:

```bash
git checkout phase-4-groq-llm-assistant
```

---

# 5. Groq Integration Design

Use Groq from the backend only.

Do not expose the Groq API key to the frontend.

Groq supports an OpenAI-compatible API endpoint:

```txt
https://api.groq.com/openai/v1
```

For Phase 4, use Groq as the default provider.

Add backend environment variables:

```env
AI_PROVIDER=groq
AI_ENABLED=true
GROQ_API_KEY=your_groq_api_key
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
AI_TIMEOUT_SECONDS=30
AI_MAX_CONTEXT_ROWS=30
AI_LOG_INTERACTIONS=true
```

Optional future OpenAI compatibility variables may exist, but do not make OpenAI primary:

```env
OPENAI_API_KEY=
OPENAI_MODEL=
```

Rules:

```txt
GROQ_API_KEY must only exist in backend .env or Render backend environment variables.
Never put GROQ_API_KEY in frontend .env.
Never commit GROQ_API_KEY.
If AI_ENABLED=false or GROQ_API_KEY is missing, fallback to the existing mock/rule-based AI behavior.
```

---

# 6. Backend Dependencies

Use the OpenAI-compatible client approach for Groq.

Add dependency if not already installed:

```txt
openai
```

Update:

```txt
backend/requirements.txt
```

Do not add LangChain, LangGraph, vector databases, or heavy agent frameworks in Phase 4.

Keep implementation simple, inspectable, and controllable.

---

# 7. Backend Files to Add / Update

Add:

```txt
backend/app/services/ai_context_service.py
backend/app/services/llm_service.py
backend/app/schemas/ai.py
```

Update:

```txt
backend/app/api/routes/ai.py
backend/app/core/config.py
backend/requirements.txt
backend/.env.example
README.md
```

Optional if simple:

```txt
backend/app/models/ai_log.py
```

If logging adds too much complexity, skip the model and mention it in limitations.

---

# 8. AI Context Builder

Create:

```txt
backend/app/services/ai_context_service.py
```

Its job:

```txt
Accept user question.
Detect intent using deterministic rules.
Fetch only relevant data.
Build summarized context.
Limit row count.
Exclude archived/cancelled/inactive data by default.
Return structured context for LLM.
```

Do not dump whole database tables.

## 8.1 Supported Intents

Support these intents:

```txt
general_dashboard_summary
shipment_status
shipment_detail
workflow_next_action
pending_tasks
overdue_tasks
bl_pending
demurrage_risk
open_followups
charges_summary
pending_receivables
pending_payables
shipment_profit
monthly_profit
loss_making_shipments
archived_shipments
inactive_parties
cancelled_tasks
unknown
```

Use simple keyword/regex logic.

Shipment code regex:

```txt
FF-EXP-2026-001
FF-IMP-2026-001
```

Suggested regex:

```python
r"\bFF-[A-Z]+-\d{4}-\d+\b"
```

---

## 8.2 Context Row Limits

Default:

```txt
AI_MAX_CONTEXT_ROWS=30
```

Specific limits:

```txt
Max 1 shipment detail when shipment code is specified
Max 10 high-risk shipments
Max 10 pending receivables
Max 10 pending payables
Max 10 overdue tasks
Max 10 open follow-ups
```

If there are more results, summarize:

```txt
Showing top 10 of 42 matching records.
```

---

## 8.3 Visibility Rules

Default AI context should exclude:

```txt
Archived shipments
Cancelled tasks
Cancelled charges
Inactive parties from suggestion/dropdown-style answers
```

But if the user explicitly asks:

```txt
Show archived shipments
Show inactive parties
Show cancelled tasks
```

then include that specific data.

Historical financial reports may still include archived shipments if existing report behavior does so.

---

## 8.4 Context Should Include Only Useful Fields

For shipments:

```txt
shipment_code
type
status
origin_port
dest_port
etd
eta
shipping_line
is_archived
```

For tasks:

```txt
title
status
due_date
priority
shipment_code
auto_generated
```

For documents:

```txt
doc_type
status
shipment_code
```

For BL:

```txt
bl_type
draft_received
approval_date
final_bl_date
surrender_done
telex_release
shipment_code
```

For demurrage:

```txt
shipment_code
free_days
start_date
days_remaining
status
total_demurrage_due
```

For follow-ups:

```txt
shipment_code
party_name
channel
summary
next_action
status
date
```

For charges/P&L:

```txt
shipment_code
total_receivable
total_payable
pending_receivable
pending_payable
net_profit
currency
multiple_currencies
```

---

# 9. LLM Service

Create:

```txt
backend/app/services/llm_service.py
```

Responsibilities:

```txt
Read AI settings.
Create Groq-compatible client.
Call Groq using the OpenAI-compatible base_url.
Send system instructions + summarized context + user question.
Return structured response.
Handle timeout/errors.
Fallback to rule-based mock if disabled or failed.
```

Client example pattern:

```python
from openai import OpenAI

client = OpenAI(
    api_key=settings.groq_api_key,
    base_url=settings.groq_base_url,
)
```

Use chat completions or compatible call style supported by the installed SDK.

Recommended model default:

```txt
llama-3.3-70b-versatile
```

---

# 10. LLM System Instructions

The LLM must receive strong instructions.

Use a system prompt like:

```txt
You are a freight forwarding operations assistant.

Answer only using the provided application context.
If the answer is not present in context, say that the system does not have enough data.
Do not invent shipment statuses, parties, ports, dates, financial amounts, charges, BL details, demurrage values, or task information.
Do not claim an action was performed.
You cannot modify records, archive shipments, deactivate parties, cancel tasks, edit charges, send emails, or upload files.
You may suggest next actions, but they are recommendations only.
For operational risks, mark priority as critical, warning, info, or none.
Keep answers concise, practical, and business-focused.
```

---

# 11. Structured AI Response

Create schemas:

```txt
AIAskRequest
AIAskResponse
AIDataPoint
AISuggestedAction
```

Request shape:

```json
{
  "question": "Which shipments have demurrage running?",
  "shipment_id": null,
  "shipment_code": null
}
```

Response shape:

```json
{
  "answer": "Two import shipments have demurrage running...",
  "priority": "warning",
  "suggested_actions": [
    "Follow up with CHA for DO handover",
    "Check container delivery status"
  ],
  "data_points": [
    {
      "label": "Shipment",
      "value": "FF-IMP-2026-003"
    }
  ],
  "used_llm": true,
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "fallback_used": false
}
```

Priority values:

```txt
critical
warning
info
none
```

Rules:

```txt
Frontend must render the answer even if suggested_actions or data_points are empty.
If Groq fails, fallback_used=true.
If AI is disabled, used_llm=false and fallback_used=true.
```

---

# 12. API Routes

Preserve existing route:

```txt
POST /api/ai/ask
```

Do not break existing frontend calls.

Update behavior:

```txt
If AI_ENABLED=true and GROQ_API_KEY exists:
    Build context.
    Call Groq.
    Return AIAskResponse.

If AI_ENABLED=false, GROQ_API_KEY missing, or Groq fails:
    Use current mock/rule-based fallback.
```

Add:

```txt
GET /api/ai/examples
GET /api/ai/status
```

## 12.1 GET /api/ai/examples

Return suggested prompts:

```txt
What shipments need attention today?
Which tasks are overdue?
Which shipments have demurrage running?
Which BL approvals are pending?
Which follow-ups are open?
How much freight is uncollected?
Which shipments have pending receivables?
Which shipments have pending payables?
Which shipments are loss-making?
Show profit for FF-EXP-2026-001.
What is the next action for FF-IMP-2026-001?
Show archived shipments.
Show inactive parties.
Show cancelled tasks.
```

## 12.2 GET /api/ai/status

Return:

```json
{
  "ai_enabled": true,
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "fallback_available": true
}
```

Do not expose API keys.

---

# 13. Fallback Behavior

Keep existing mock/rule-based behavior.

Fallback should support at least:

```txt
Which tasks are pending?
Which shipments have BL approval pending?
Show shipment status.
Which shipments have free days expiring?
Which shipments have demurrage running?
Which follow-ups are open?
Which shipments have pending receivables?
Which shipments have pending payables?
Show profit for FF-EXP-2026-001.
Which shipments are loss-making?
What is this month profit?
```

If LLM fails, return response like:

```txt
The LLM service is unavailable right now, so I used rule-based fallback data.
```

---

# 14. Optional AI Interaction Logging

If simple, add model:

```txt
AIInteractionLog
```

Fields:

```txt
id
user_id
question
answer
used_llm
provider
model
fallback_used
priority
created_at
```

Rules:

```txt
Do not store GROQ_API_KEY.
Do not store raw full database context.
Question and answer are enough for Phase 4.
```

If this adds too much work, skip it and mention limitation.

---

# 15. Frontend Changes

Update existing AI page.

Route remains:

```txt
/ai
```

Rename UI from:

```txt
Mock AI Assistant
```

to:

```txt
AI Assistant
```

Add:

```txt
Chat-like UI
Example prompt buttons
AI status indicator
Fallback mode indicator
Priority badge
Suggested actions section
Data points section
Loading state
Readable error state
```

Example prompt buttons:

```txt
What shipments need attention today?
Which tasks are overdue?
Which shipments have demurrage running?
Which BL approvals are pending?
Which follow-ups are open?
How much freight is uncollected?
Which shipments have pending receivables?
Which shipments have pending payables?
Which shipments are loss-making?
Show profit for FF-EXP-2026-001.
What is the next action for FF-IMP-2026-001?
```

If response includes:

```txt
suggested_actions
```

show them as a list.

If response includes:

```txt
data_points
```

show them as compact rows/cards.

If fallback is used, show:

```txt
Fallback mode used
```

---

# 16. Permissions

All authenticated users can ask read-only AI questions.

Role behavior:

```txt
ADMIN: can ask all read-only questions
STAFF: can ask all read-only questions
VIEW_ONLY: can ask all read-only questions
```

Since Phase 4 does not perform writes, VIEW_ONLY can use the assistant.

Do not include data that the user should not normally read.

No unauthenticated AI access.

---

# 17. Safety Rules

The assistant must never say:

```txt
I archived the shipment.
I deleted the party.
I updated the charge.
I marked the task done.
I sent the email.
I uploaded the file.
```

Because Phase 4 does not perform writes.

It may say:

```txt
Suggested action: archive duplicate shipment after review.
Suggested action: follow up with CHA.
Suggested action: mark charge received if payment has arrived.
Suggested action: upload the BL to Drive and paste the link.
```

All actions are recommendations only.

---

# 18. Error Handling

Handle:

```txt
Missing GROQ_API_KEY
AI_ENABLED=false
Groq timeout
Groq API error
Context builder finds no data
Question too broad
Unknown shipment code
User unauthenticated
Invalid request body
```

Expected behavior:

```txt
No backend crash.
No frontend blank screen.
Return useful fallback answer.
```

Examples:

```txt
"I could not find shipment FF-EXP-2026-999 in the system."

"The LLM service is unavailable right now, so I used rule-based fallback data."

"The system does not have enough data to answer this."
```

---

# 19. README Updates

Update README with:

```txt
Phase 4 Groq LLM assistant overview
Backend-only Groq API key setup
AI_PROVIDER
AI_ENABLED
GROQ_API_KEY
GROQ_BASE_URL
GROQ_MODEL
Fallback mode
Supported question examples
Safety rule: AI is read-only in Phase 4
Limitations
Render backend environment variable setup
```

Add backend env variables:

```env
AI_PROVIDER=groq
AI_ENABLED=true
GROQ_API_KEY=your_groq_api_key
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
AI_TIMEOUT_SECONDS=30
AI_MAX_CONTEXT_ROWS=30
AI_LOG_INTERACTIONS=true
```

Warnings:

```txt
Never put GROQ_API_KEY in frontend env variables.
Never commit backend .env.
Never expose API keys in API responses.
```

---

# 20. Local Testing

## 20.1 Backend Compile

```bash
cd backend
source .venv/bin/activate
python -m compileall app
```

Expected:

```txt
No syntax errors.
```

## 20.2 Frontend Build

```bash
cd frontend
npm run build
```

Expected:

```txt
Build passes.
```

## 20.3 Run Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

## 20.4 Run Frontend

```bash
cd frontend
npm run dev
```

---

# 21. AI Smoke Tests

## 21.1 Fallback Test

Set:

```env
AI_ENABLED=false
```

Expected:

```txt
Existing fallback/mock answers still work.
No Groq key needed.
```

Ask:

```txt
Which tasks are pending?
Which shipments have BL approval pending?
Show shipment status.
Which shipments have pending receivables?
```

---

## 21.2 Groq LLM Test

Set:

```env
AI_ENABLED=true
AI_PROVIDER=groq
GROQ_API_KEY=valid_key
GROQ_MODEL=llama-3.3-70b-versatile
```

Ask:

```txt
What shipments need attention today?
Which tasks are overdue?
Which shipments have demurrage running?
Which BL approvals are pending?
Which follow-ups are open?
How much freight is uncollected?
Which shipments have pending receivables?
Which shipments have pending payables?
Show profit for FF-EXP-2026-001.
Which shipments are loss-making?
What is the next action for FF-IMP-2026-001?
```

Expected:

```txt
Answer uses real database context.
No invented shipment codes.
No invented financial amounts.
No write action performed.
Response includes suggested actions when useful.
```

---

## 21.3 Failure Test

Test with invalid Groq key or temporarily unavailable service.

Expected:

```txt
No backend crash.
Fallback response is returned.
fallback_used=true.
```

---

# 22. Regression Tests

Confirm existing flows still work:

```txt
Login
Dashboard
Shipments
Workflow status update
Documents
Tasks
BL Management
Demurrage
Follow-up Log
Charges
Reports
Archive/restore shipment
Deactivate/reactivate party
Cancel/restore task
VIEW_ONLY restrictions
```

---

# 23. Security Tests

Run:

```bash
git status
git diff

find . -name ".env" -o -name "node_modules" -o -name ".venv" -o -name "dist"

grep -R "GROQ_API_KEY" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "OPENAI_API_KEY" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
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
Real GROQ_API_KEY
Real Neon URL
Real JWT secret
Committed .env
```

---

# 24. Acceptance Criteria

Phase 4 is complete only when:

```txt
[ ] Backend compiles
[ ] Frontend builds
[ ] GROQ_API_KEY is backend-only
[ ] AI_ENABLED=false fallback works
[ ] AI_ENABLED=true Groq answers work
[ ] AI answers use database context
[ ] AI does not invent shipment codes or finance amounts
[ ] AI does not perform write actions
[ ] Existing mock/rule-based fallback remains available
[ ] AI page shows examples
[ ] AI page shows answer, priority, suggested actions, and data points
[ ] Unknown shipment code handled gracefully
[ ] Groq timeout/error handled gracefully
[ ] VIEW_ONLY can ask read-only questions
[ ] Existing Phase 1 flows still work
[ ] Existing Phase 2 flows still work
[ ] Existing Phase 3 flows still work
[ ] Existing Phase 3.5 flows still work
[ ] README updated
[ ] No real secrets committed
```

---

# 25. Deployment Notes

Do not deploy until tests pass locally.

For Render backend environment variables, add:

```env
AI_PROVIDER=groq
AI_ENABLED=true
GROQ_API_KEY=your_groq_api_key
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
AI_TIMEOUT_SECONDS=30
AI_MAX_CONTEXT_ROWS=30
AI_LOG_INTERACTIONS=true
```

Redeploy backend first.

Frontend usually only needs redeploy if UI changed.

Do not add Groq variables to frontend Render service.

---

# 26. Final Commit

After implementation and tests:

```bash
git status
git add .
git commit -m "Implement phase 4 Groq LLM assistant"
```

Push:

```bash
git push -u origin phase-4-groq-llm-assistant
```

---

# 27. Final Report Required

After implementation, report:

```txt
Backend compile result
Frontend build result
AI fallback test result
Groq API test result
Database-grounding test result
VIEW_ONLY AI permission result
Regression test result
Secret scan result
Git status
Commit hash
Known limitations
```
