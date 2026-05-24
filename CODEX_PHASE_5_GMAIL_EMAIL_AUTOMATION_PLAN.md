# Codex Implementation Plan — Phase 5 Gmail / Email Automation

## Purpose

Implement **Phase 5** of the Freight Forwarding AI-Powered Management System.

Phase 5 adds **Gmail / Email Automation** to help users process freight-related emails.

The system should be able to:

```txt
Connect Gmail
Read freight-related emails
Detect booking confirmations
Detect BL drafts
Detect arrival notices
Detect freight invoices
Detect DO / delivery order emails
Detect pre-alerts
Extract useful shipment fields
Extract possible charge fields
Suggest updates to shipments/documents/tasks/charges
Let the user review everything before saving
```

Important rule:

```txt
Email automation must not directly update business records without user confirmation.
```

The AI/email parser can suggest updates, but the user must click approve/save.

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
- Shipments
- Parties
- Documents
- Tasks
- Dashboard

Phase 2:
- Workflow automation
- BL Management
- Demurrage
- Follow-up Log
- Alerts

Phase 3:
- Charges
- Shipment P&L
- Reports
- Dashboard financial cards

Phase 3.5:
- Shipment archive/restore
- Party deactivate/reactivate/delete-if-unused
- Task cancel/restore/delete-manual
- Archived/inactive/cancelled filtering

Phase 4:
- Groq LLM assistant
- Database-grounded read-only answers
- Fallback AI mode
```

Existing hosted app:

```txt
Frontend: https://freight-frontend-u051.onrender.com
Backend:  https://freight-backend-au6c.onrender.com
```

Preserve all existing Phase 1/2/3/3.5/4 behavior.

---

# 2. Phase 5 Goal

Build a safe email automation layer that helps freight users turn emails into **reviewable suggestions**.

The system should:

```txt
Read Gmail messages after user connects Gmail.
Search for freight-related emails.
Classify email type.
Extract structured data.
Match email to an existing shipment if possible.
Create suggested updates.
Show suggestions in the UI.
Require user approval before applying changes.
Log approved/rejected suggestions.
```

The system should not:

```txt
Auto-update shipments without review
Auto-create charges without review
Auto-send replies
Auto-delete emails
Auto-forward emails
Auto-upload files to Google Drive
```

---

# 3. Strict Phase 5 Non-Goals

Do **not** implement these in Phase 5:

```txt
Auto-reply emails
Auto-send emails
Auto-forward emails
Auto-delete/archive Gmail messages
Auto-create shipments without confirmation
Auto-update documents without confirmation
Auto-create charges without confirmation
Google Drive upload
AWS S3 upload
OCR for attachments
Invoice PDF generation
Accounting integration
Courier automation
Payment gateway
Celery / Redis background queues
Autonomous AI agents
```

Phase 5 should be:

```txt
Read email → Extract data → Suggest update → User approves → Save
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
git checkout -b phase-5-gmail-email-automation
```

If branch exists:

```bash
git checkout phase-5-gmail-email-automation
```

---

# 5. Gmail Integration Design

Use Gmail API through backend only.

Frontend should never receive:

```txt
Google client secret
Refresh token
Access token
```

Backend owns OAuth flow and token storage.

Recommended backend env variables:

```env
GMAIL_ENABLED=true
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://your-backend.onrender.com/api/email/oauth/callback
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly
EMAIL_MAX_RESULTS=20
EMAIL_LOOKBACK_DAYS=30
```

Local development:

```env
GOOGLE_REDIRECT_URI=http://localhost:8000/api/email/oauth/callback
```

Important:

```txt
Use read-only Gmail scope in Phase 5.
Do not request send/modify/delete scopes.
Do not store Google secrets in frontend.
Do not commit any Google secrets.
```

Preferred Gmail scope for Phase 5:

```txt
https://www.googleapis.com/auth/gmail.readonly
```

---

# 6. Backend Dependencies

Add dependencies only if needed:

```txt
google-api-python-client
google-auth
google-auth-oauthlib
google-auth-httplib2
cryptography
```

Update:

```txt
backend/requirements.txt
```

Do not add heavy workflow engines.

Do not add Celery/Redis.

---

# 7. Backend Models

Add these models.

## 7.1 EmailConnection

Table:

```txt
email_connections
```

Fields:

```txt
id
user_id
provider
email_address
access_token_encrypted
refresh_token_encrypted
token_expiry
scopes
is_active
created_at
updated_at
```

Rules:

```txt
provider = gmail
One active Gmail connection per user for Phase 5 is enough.
Tokens must not be stored as plain text if encryption helper exists.
If encryption is not implemented yet, add a clear TODO and avoid logging token values.
```

Preferred: implement app-level encryption using an env variable.

Add env:

```env
TOKEN_ENCRYPTION_KEY=your_fernet_key
```

If encryption is too much for this phase, store tokens with strong warning in README and do not log them. Prefer encryption if practical.

---

## 7.2 EmailMessageCache

Table:

```txt
email_message_cache
```

Fields:

```txt
id
connection_id
gmail_message_id
thread_id
subject
sender
recipients
snippet
body_preview
received_at
has_attachments
classification
matched_shipment_id
processed_status
created_at
updated_at
```

Classification values:

```txt
booking_confirmation
bl_draft
arrival_notice
freight_invoice
delivery_order
pre_alert
general_followup
unknown
```

Processed status values:

```txt
new
suggested
approved
rejected
ignored
```

Rules:

```txt
Do not store full raw email body if not necessary.
Store snippet/body_preview enough for review.
Avoid storing attachments in Phase 5.
```

---

## 7.3 EmailSuggestion

Table:

```txt
email_suggestions
```

Fields:

```txt
id
email_message_id
shipment_id nullable
suggestion_type
confidence
extracted_data_json
status
reviewed_by nullable
reviewed_at nullable
applied_at nullable
created_at
updated_at
```

Suggestion types:

```txt
update_shipment
update_document
update_bl
update_demurrage
create_charge
create_followup
create_task
unknown
```

Status values:

```txt
pending
approved
rejected
applied
ignored
```

Rules:

```txt
Suggestions are not business-record changes yet.
They become real changes only after user approves.
```

---

# 8. Backend Schemas

Add:

```txt
backend/app/schemas/email.py
```

Schemas:

```txt
EmailConnectionRead
EmailMessageRead
EmailScanRequest
EmailScanResponse
EmailSuggestionRead
EmailSuggestionApplyRequest
EmailSuggestionRejectRequest
```

## 8.1 EmailScanRequest

Fields:

```txt
query optional
lookback_days optional default 30
max_results optional default 20
```

Default Gmail search query can be:

```txt
newer_than:30d (booking OR "BL draft" OR "arrival notice" OR "freight invoice" OR "delivery order" OR pre-alert OR shipment)
```

## 8.2 EmailSuggestionRead

Return:

```txt
id
email_message_id
shipment_id
shipment_code if matched
suggestion_type
classification
confidence
extracted_data_json
status
created_at
```

---

# 9. Backend Services

Add:

```txt
backend/app/services/gmail_service.py
backend/app/services/email_parser_service.py
backend/app/services/email_suggestion_service.py
backend/app/services/token_crypto_service.py
```

---

## 9.1 gmail_service.py

Responsibilities:

```txt
Build Gmail OAuth URL
Handle OAuth callback
Store/refresh tokens
Search Gmail messages
Read selected Gmail message metadata/body
Return normalized message data
```

Phase 5 Gmail access should be read-only.

Functions:

```txt
get_authorization_url(user_id)
handle_oauth_callback(code, state)
search_messages(connection, query, max_results)
get_message(connection, gmail_message_id)
normalize_message(raw_message)
```

Do not:

```txt
Send emails
Delete emails
Modify labels
Archive messages
Download attachments automatically
```

---

## 9.2 token_crypto_service.py

Responsibilities:

```txt
Encrypt Gmail access/refresh tokens before storing.
Decrypt tokens only when calling Gmail API.
Never log decrypted tokens.
```

Use:

```txt
cryptography.fernet.Fernet
```

If TOKEN_ENCRYPTION_KEY is missing:

```txt
Do not crash app startup.
Email connection should fail with readable error:
TOKEN_ENCRYPTION_KEY is required for Gmail connections.
```

---

## 9.3 email_parser_service.py

Responsibilities:

```txt
Classify email type
Extract structured fields
Detect possible shipment code
Detect possible BL number
Detect possible container number
Detect ETA/ETD
Detect charge amount/currency
Detect document status changes
Detect follow-up/next action
```

Use deterministic parsing first.

Use existing Groq LLM only as optional extraction helper if safe and already configured.

Default should work without Groq.

Classification keywords:

```txt
booking_confirmation:
- booking confirmation
- booking ref
- vessel
- voyage
- ETD

bl_draft:
- BL draft
- bill of lading draft
- draft BL
- HBL
- MBL

arrival_notice:
- arrival notice
- ETA
- IGM
- destination arrival

freight_invoice:
- freight invoice
- invoice amount
- payable
- due amount
- total amount

delivery_order:
- delivery order
- DO
- delivery order ready
- DO release

pre_alert:
- pre-alert
- pre alert
- prealert
- documents attached
```

Extracted fields can include:

```txt
shipment_code
booking_ref
bl_number
container_no
vessel_name
voyage_no
origin_port
dest_port
etd
eta
invoice_no
amount
currency
party_name
document_type
document_status
next_action
```

Confidence scoring:

```txt
0.9 if shipment_code exact match found
0.7 if booking_ref/container_no match found
0.5 if only subject/type match found
0.3 if weak guess
```

---

## 9.4 email_suggestion_service.py

Responsibilities:

```txt
Match email to shipment
Create pending suggestions
Apply approved suggestion
Reject suggestion
Avoid duplicates
```

Matching logic:

```txt
1. Match shipment_code if present.
2. Match booking_ref if present.
3. Match container_no if present.
4. Match bl_number if present.
5. If no confident match, leave shipment_id null and require manual selection.
```

Suggestion examples:

### Booking Confirmation

Suggest:

```txt
update_shipment:
- booking_ref
- vessel_name
- voyage_no
- etd
- shipping_line
```

### BL Draft

Suggest:

```txt
update_document:
- BL_DRAFT status = received

update_bl:
- draft_received = today
- bl_type if found
- file_url remains manual Drive link
```

### Arrival Notice

Suggest:

```txt
update_shipment:
- eta
- status maybe ETA Tracking Active

create_task:
- Follow up for DO / clearance
```

### Freight Invoice

Suggest:

```txt
create_charge:
- direction = payable
- charge_type = ocean_freight or liner_charges
- amount
- currency
- invoice_no
- status = pending
```

### Delivery Order

Suggest:

```txt
update_document:
- DO status = received

update_demurrage:
- start_date = today if empty

update_shipment:
- status = DO Received
```

### Pre-alert

Suggest:

```txt
update_document:
- PRE_ALERT status = received

create_followup:
- summary based on email
```

---

# 10. Backend API Routes

Create:

```txt
backend/app/api/routes/email.py
```

Register it in:

```txt
backend/app/main.py
```

## 10.1 Connection Routes

```txt
GET  /api/email/status
GET  /api/email/oauth/start
GET  /api/email/oauth/callback
POST /api/email/disconnect
```

### GET /api/email/status

Return:

```json
{
  "connected": true,
  "provider": "gmail",
  "email_address": "user@example.com"
}
```

### GET /api/email/oauth/start

Return:

```json
{
  "auth_url": "https://accounts.google.com/..."
}
```

Frontend opens this URL.

### GET /api/email/oauth/callback

Handle OAuth callback.

After successful connection, redirect to frontend email page:

```txt
https://your-frontend.onrender.com/email?connected=true
```

Use env:

```env
FRONTEND_BASE_URL=https://freight-frontend-u051.onrender.com
```

### POST /api/email/disconnect

Deactivate connection.

Do not delete old cached email suggestions by default.

---

## 10.2 Email Scan Routes

```txt
POST /api/email/scan
GET  /api/email/messages
GET  /api/email/messages/{message_id}
```

### POST /api/email/scan

Input:

```json
{
  "query": "",
  "lookback_days": 30,
  "max_results": 20
}
```

Behavior:

```txt
Require connected Gmail.
Search Gmail.
Fetch basic message data.
Classify messages.
Cache messages.
Create suggestions.
Return scan summary.
```

Response:

```json
{
  "scanned": 12,
  "cached": 12,
  "suggestions_created": 5
}
```

### GET /api/email/messages

List cached messages.

Query params:

```txt
classification optional
processed_status optional
shipment_id optional
```

### GET /api/email/messages/{message_id}

Return full cached message and suggestions.

---

## 10.3 Suggestion Routes

```txt
GET  /api/email/suggestions
PATCH /api/email/suggestions/{suggestion_id}
POST /api/email/suggestions/{suggestion_id}/apply
POST /api/email/suggestions/{suggestion_id}/reject
```

### GET /api/email/suggestions

Query params:

```txt
status=pending
shipment_id optional
suggestion_type optional
```

### PATCH /api/email/suggestions/{suggestion_id}

Allow user to edit suggestion before applying.

Editable:

```txt
shipment_id
extracted_data_json
confidence maybe not editable
```

### POST /api/email/suggestions/{suggestion_id}/apply

Apply suggestion to actual business records.

This is the only point where DB changes happen.

Require user confirmation.

Allowed roles:

```txt
ADMIN and STAFF can apply suggestions.
VIEW_ONLY can read only.
```

Apply behavior depends on suggestion_type.

Rules:

```txt
Do not overwrite existing non-empty fields unless user explicitly confirms overwrite.
If conflict exists, return conflict details and require force=true.
```

Input:

```json
{
  "force": false
}
```

### POST /api/email/suggestions/{suggestion_id}/reject

Set status = rejected.

---

# 11. Permissions

## ADMIN

Can:

```txt
Connect Gmail
Scan emails
View messages
View suggestions
Edit suggestions
Apply suggestions
Reject suggestions
Disconnect Gmail
```

## STAFF

Can:

```txt
Connect own Gmail
Scan emails
View messages
View suggestions
Edit suggestions
Apply suggestions
Reject suggestions
```

## VIEW_ONLY

Cannot access Gmail automation in Phase 5.

Recommended Phase 5 simple rule:

```txt
Only ADMIN and STAFF can use Gmail automation.
VIEW_ONLY cannot access email automation pages or endpoints.
```

---

# 12. Frontend Changes

Add route:

```txt
/email
```

Add sidebar link:

```txt
Email Automation
```

Only show to:

```txt
ADMIN
STAFF
```

Hide from:

```txt
VIEW_ONLY
```

---

## 12.1 Email Automation Page

Sections:

```txt
Connection Status
Scan Controls
Cached Emails
Pending Suggestions
Suggestion Detail / Review
```

### Connection Status

Show:

```txt
Connected Gmail account
Connect Gmail button
Disconnect button
```

### Scan Controls

Fields:

```txt
Search query
Lookback days
Max results
Scan button
```

Default query help text:

```txt
booking OR "BL draft" OR "arrival notice" OR "freight invoice" OR "delivery order" OR pre-alert
```

### Cached Emails Table

Columns:

```txt
Received Date
From
Subject
Classification
Matched Shipment
Status
Suggestions
Open
```

### Pending Suggestions Table

Columns:

```txt
Type
Shipment
Confidence
Extracted Summary
Status
Actions
```

Actions:

```txt
Review
Apply
Reject
```

### Suggestion Review

Show:

```txt
Original email snippet/body preview
Extracted data
Matched shipment
Editable shipment selection if no match
Conflict warnings
Apply button
Reject button
```

---

# 13. Suggestion Apply Behavior

Implement safe apply logic.

## 13.1 update_shipment

Can update fields like:

```txt
booking_ref
bl_number
container_no
vessel_name
voyage_no
origin_port
dest_port
etd
eta
shipping_line
status
```

Rules:

```txt
Do not overwrite non-empty values unless force=true.
Return conflict if existing value differs.
```

---

## 13.2 update_document

Can update document status:

```txt
BL_DRAFT
FINAL_BL
PRE_ALERT
ARRIVAL_NOTICE
FREIGHT_INVOICE
DO
```

Rules:

```txt
Only update status if document exists.
If document missing, create it only if shipment_id exists and user confirms.
No file upload; file_url remains manual Drive link.
```

---

## 13.3 update_bl

Can update:

```txt
draft_received
approval_date
final_bl_date
bl_type
surrender_done
telex_release
```

Rules:

```txt
Do not overwrite user-entered date unless force=true.
```

---

## 13.4 update_demurrage

Can update:

```txt
start_date
free_days maybe if found
```

Rules:

```txt
Only for import shipments.
Do not overwrite existing values unless force=true.
```

---

## 13.5 create_charge

Can create pending charge:

```txt
direction
charge_type
amount
currency
party_id optional
invoice_no
date
notes
```

Rules:

```txt
Require shipment_id.
Require amount.
Default status = pending.
Require user approval.
```

---

## 13.6 create_followup

Can create follow-up log:

```txt
channel = email
summary
next_action
status = open
party_id optional
date
```

---

## 13.7 create_task

Can create task:

```txt
title
description
due_date
priority
status = open
auto_generated = true
```

Use `auto_generated=true` because email suggested it.

---

# 14. Duplicate Prevention

Avoid duplicate cached messages:

```txt
connection_id + gmail_message_id unique
```

Avoid duplicate suggestions:

```txt
email_message_id + suggestion_type + shipment_id unique if practical
```

Avoid duplicate charges from same invoice:

```txt
same shipment_id
same invoice_no
same amount
same direction
```

If duplicate suspected:

```txt
Return warning instead of auto-creating.
```

---

# 15. Security and Privacy

Rules:

```txt
Never log Gmail access token.
Never log Gmail refresh token.
Never return tokens to frontend.
Never expose GOOGLE_CLIENT_SECRET.
Do not store full raw email unnecessarily.
Do not download attachments in Phase 5.
Do not send email content to Groq unless explicitly needed for extraction and only after stripping unnecessary personal data.
```

For Phase 5, prefer deterministic parser first.

If using Groq for extraction:

```txt
Send only subject + snippet/body preview.
Never send attachments.
Never include tokens.
```

---

# 16. README Updates

Update README with:

```txt
Phase 5 Gmail automation overview
Google OAuth setup
Required backend env variables
Gmail readonly scope
How scan works
Suggestion review/apply flow
Safety rule: no automatic DB updates
Limitations
Render environment setup
```

Add env docs:

```env
GMAIL_ENABLED=true
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://freight-backend-au6c.onrender.com/api/email/oauth/callback
FRONTEND_BASE_URL=https://freight-frontend-u051.onrender.com
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly
EMAIL_MAX_RESULTS=20
EMAIL_LOOKBACK_DAYS=30
TOKEN_ENCRYPTION_KEY=your_fernet_key
```

Warnings:

```txt
Never put Google client secret in frontend env.
Never commit backend .env.
Only use gmail.readonly in Phase 5.
```

---

# 17. Local Testing

## 17.1 Backend Compile

```bash
cd backend
source .venv/bin/activate
python -m compileall app
```

## 17.2 Frontend Build

```bash
cd frontend
npm run build
```

## 17.3 Run Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

## 17.4 Run Frontend

```bash
cd frontend
npm run dev
```

---

# 18. API Smoke Tests

Without Gmail credentials:

```txt
GET /api/email/status should work and show connected=false.
POST /api/email/scan should return helpful error: Gmail is not connected.
No backend crash.
```

With Gmail credentials:

```txt
GET /api/email/oauth/start returns auth_url.
OAuth callback stores connection.
POST /api/email/scan scans messages.
GET /api/email/messages returns cached messages.
GET /api/email/suggestions returns suggestions.
Apply suggestion updates DB only after explicit apply.
Reject suggestion marks rejected.
```

---

# 19. UI Smoke Tests

Test:

```txt
Email Automation sidebar link appears for ADMIN/STAFF.
VIEW_ONLY does not see email automation link.
Connect Gmail button appears.
Scan controls appear after connection.
Cached email table loads.
Pending suggestions table loads.
Suggestion review works.
Apply updates only after clicking apply.
Reject works.
Errors are readable.
```

---

# 20. Regression Tests

Confirm existing flows still work:

```txt
Login
Dashboard
Shipments
Documents
Tasks
Workflow
BL Management
Demurrage
Follow-up Log
Charges
Reports
AI Assistant
Archive/restore shipment
Deactivate/reactivate party
Cancel/restore task
VIEW_ONLY restrictions
```

---

# 21. Security Tests

Run:

```bash
git status
git diff

find . -name ".env" -o -name "node_modules" -o -name ".venv" -o -name "dist"

grep -R "GOOGLE_CLIENT_SECRET" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
grep -R "GOOGLE_CLIENT_ID" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude=".env"
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
Real Google secret
Real Groq key
Real Neon URL
Real JWT secret
Committed .env
```

---

# 22. Acceptance Criteria

Phase 5 is complete only when:

```txt
[ ] Backend compiles
[ ] Frontend builds
[ ] Gmail env settings added only to backend docs/examples
[ ] Email status endpoint works without Gmail connected
[ ] OAuth start endpoint returns auth_url
[ ] OAuth callback stores connection
[ ] Gmail scan works when connected
[ ] Cached messages list works
[ ] Email classification works
[ ] Suggestions are created
[ ] Suggestions require review
[ ] Apply suggestion updates DB only after user confirmation
[ ] Reject suggestion works
[ ] No automatic DB updates from email scan
[ ] VIEW_ONLY cannot use Gmail automation writes
[ ] ADMIN/STAFF can scan/apply
[ ] No send/delete/modify Gmail scope used
[ ] No Gmail tokens exposed to frontend
[ ] Existing Phase 1 flows still work
[ ] Existing Phase 2 flows still work
[ ] Existing Phase 3 flows still work
[ ] Existing Phase 3.5 flows still work
[ ] Existing Phase 4 AI still works
[ ] README updated
[ ] No real secrets committed
```

---

# 23. Deployment Notes

Do not deploy until local tests pass.

Render backend environment variables:

```env
GMAIL_ENABLED=true
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://freight-backend-au6c.onrender.com/api/email/oauth/callback
FRONTEND_BASE_URL=https://freight-frontend-u051.onrender.com
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly
EMAIL_MAX_RESULTS=20
EMAIL_LOOKBACK_DAYS=30
TOKEN_ENCRYPTION_KEY=your_fernet_key
```

Google Cloud Console OAuth redirect URI must include:

```txt
https://freight-backend-au6c.onrender.com/api/email/oauth/callback
```

Local redirect URI:

```txt
http://localhost:8000/api/email/oauth/callback
```

Frontend usually only needs redeploy because `/email` UI is added.

Do not add Google secrets to frontend Render service.

---

# 24. Final Commit

After implementation and tests:

```bash
git status
git add .
git commit -m "Implement phase 5 Gmail email automation"
```

Push:

```bash
git push -u origin phase-5-gmail-email-automation
```

---

# 25. Final Report Required

After implementation, report:

```txt
Backend compile result
Frontend build result
Gmail disconnected-mode test result
OAuth URL test result
Gmail live scan test result if credentials available
Email classification test result
Suggestion review/apply test result
VIEW_ONLY restriction result
Regression test result
Secret scan result
Git status
Commit hash
Known limitations
```
