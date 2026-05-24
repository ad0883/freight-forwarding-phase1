# Codex Implementation Plan — Phase 6 Production Hardening & Polish

## Purpose

Implement **Phase 6** of the Freight Forwarding AI-Powered Management System.

Phase 6 is not a new freight module. It is a **production hardening and polish phase**.

The app already has major functionality:

```txt
Phase 1: Core freight system
Phase 2: Workflow, BL, demurrage, follow-ups, alerts
Phase 3: Charges, P&L, reports
Phase 3.5: Archive/deactivate/cancel cleanup controls
Phase 4: Groq LLM assistant
Phase 5: Gmail email automation with reviewable suggestions
```

Now the goal is to make the system safer, clearer, easier to manage, and more reliable for real use.

Phase 6 should add:

```txt
Audit logs
User management UI
Change password
Better error/loading/empty states
Safer admin controls
Data export/backup helpers
Health/status page
Dashboard/filter polish
Mobile responsiveness improvements
README/deployment documentation cleanup
```

---

# 1. Existing System Context

The system currently has:

```txt
React.js + Vite frontend
FastAPI backend
PostgreSQL / Neon database
JWT + bcrypt authentication
Render hosting
Groq LLM assistant
Gmail read-only automation
Google Drive pasted links only
Role-based access: ADMIN / STAFF / VIEW_ONLY
```

Existing hosted app:

```txt
Frontend: https://freight-frontend-u051.onrender.com
Backend:  https://freight-backend-au6c.onrender.com
```

Preserve all existing Phase 1/2/3/3.5/4/5 behavior.

Do not break:

```txt
Login
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
Groq AI Assistant
Gmail Email Automation
Dashboard
Render deployment
```

---

# 2. Phase 6 Scope

Implement only production hardening and polish:

```txt
1. Audit Logs
2. User Management UI
3. Change Password
4. Better loading/error/empty states
5. Backup/export tools
6. Health/status page
7. Safer dashboard/filter polish
8. Mobile responsiveness improvements
9. Test-data cleanup helpers
10. README/deployment guide cleanup
```

---

# 3. Strict Non-Goals

Do **not** implement these in Phase 6:

```txt
New Gmail features
Gmail send/reply/delete/archive
Google Drive API upload
AWS S3 upload
OCR
Courier tracking
Invoice PDF generation
Accounting integration
Payment gateway
Celery / Redis
Multi-tenant billing
Native mobile app
New LLM agent actions
Autonomous AI writes
```

The system should remain controlled and review-based.

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
git checkout -b phase-6-production-hardening
```

If branch already exists:

```bash
git checkout phase-6-production-hardening
```

---

# 5. Audit Logs

## 5.1 Goal

Add an audit trail for important business actions.

The system should record who did what, when, and to which record.

Examples:

```txt
Admin archived shipment FF-EXP-2026-001
Staff applied Gmail suggestion to create charge INR 35000
Admin deactivated party ABC Textiles
Staff marked task done
Admin cancelled charge
Staff updated document status
Admin changed user role
```

---

## 5.2 Backend Model

Add model:

```txt
AuditLog
```

Table:

```txt
audit_logs
```

Fields:

```txt
id
actor_user_id nullable
actor_name
actor_email
actor_role
action
entity_type
entity_id nullable
entity_label nullable
description
metadata_json nullable
ip_address nullable
user_agent nullable
created_at
```

Examples:

```txt
action = shipment.archive
entity_type = shipment
entity_label = FF-EXP-2026-001

action = party.deactivate
entity_type = party
entity_label = ABC Textiles

action = email_suggestion.apply
entity_type = email_suggestion
entity_label = Suggestion #12

action = charge.create
entity_type = charge
entity_label = INR 35000 payable
```

---

## 5.3 Audit Service

Add:

```txt
backend/app/services/audit_service.py
```

Function:

```txt
record_audit_log(db, actor_user, action, entity_type, entity_id=None, entity_label=None, description=None, metadata=None, request=None)
```

Rules:

```txt
Audit failure should not crash the business action.
If audit logging fails, log server error but do not block the action.
Never store secrets, access tokens, refresh tokens, API keys, passwords, or JWTs in metadata.
```

---

## 5.4 Actions to Audit

Add audit logs to important actions:

```txt
user.create
user.update
user.role_change
password.change
shipment.create
shipment.update
shipment.archive
shipment.restore
workflow.status_update
party.create
party.update
party.deactivate
party.reactivate
party.delete
task.create
task.update
task.done
task.reopen
task.cancel
task.restore
task.delete
document.update
bl.update
demurrage.update
followup.create
followup.update
followup.delete
charge.create
charge.update
charge.cancel
charge.mark_paid
charge.mark_received
email.connect
email.disconnect
email.scan
email_suggestion.apply
email_suggestion.reject
```

For AI questions, do not store hidden context. If logging AI is already implemented, store only the visible question/answer and safe metadata.

---

## 5.5 Audit API Routes

Create:

```txt
backend/app/api/routes/audit.py
```

Routes:

```txt
GET /api/audit-logs
GET /api/audit-logs/{audit_log_id}
```

Query filters:

```txt
action optional
entity_type optional
entity_id optional
actor_user_id optional
date_from optional
date_to optional
search optional
limit default 50
offset default 0
```

Permissions:

```txt
ADMIN only can view audit logs.
```

---

## 5.6 Frontend Audit Logs Page

Add route:

```txt
/audit-logs
```

Add sidebar link:

```txt
Audit Logs
```

Show only to:

```txt
ADMIN
```

Page UI:

```txt
Filter by action
Filter by entity type
Search box
Date range
Audit table
```

Table columns:

```txt
Date/Time
Actor
Action
Entity
Description
```

Detail drawer/modal:

```txt
Full description
Metadata JSON pretty view
IP/user agent if available
```

---

# 6. User Management UI

## 6.1 Goal

Add a proper admin UI for users instead of relying on API docs.

Add page:

```txt
/users
```

Visible to:

```txt
ADMIN only
```

Features:

```txt
List users
Create user
Edit user name/role/active status
Reset user password manually
Deactivate/reactivate user if backend supports it
```

Do not allow an admin to accidentally remove their own admin access.

---

## 6.2 Backend Checks

Confirm or add routes if missing:

```txt
GET /api/users
POST /api/users
PATCH /api/users/{user_id}
PATCH /api/users/{user_id}/password-reset
PATCH /api/users/{user_id}/deactivate
PATCH /api/users/{user_id}/reactivate
```

Rules:

```txt
ADMIN only.
Cannot deactivate the only active ADMIN.
Cannot change the only active ADMIN to non-admin.
Never return password hash.
```

---

## 6.3 Frontend User Page

Columns:

```txt
Name
Email
Role
Active
Created At
Actions
```

Actions:

```txt
Create User
Edit Role
Deactivate
Reactivate
Reset Password
```

Create user form:

```txt
Name
Email
Password
Role: ADMIN / STAFF / VIEW_ONLY
```

Reset password:

```txt
New password
Confirm new password
```

---

# 7. Change Password

## 7.1 Goal

Users should be able to change their own password without admin.

Add route:

```txt
POST /api/auth/change-password
```

Input:

```json
{
  "current_password": "old",
  "new_password": "new"
}
```

Rules:

```txt
Authenticated users only.
Verify current password.
Hash new password with existing bcrypt logic.
Do not log password values.
Return success.
```

Add frontend page:

```txt
/settings
```

Fields:

```txt
Current password
New password
Confirm password
```

Show success/error messages.

---

# 8. Better Error / Loading / Empty States

Add consistent components:

```txt
LoadingState
ErrorState
EmptyState
ConfirmDialog
```

Use them in major pages:

```txt
Dashboard
Shipments
Parties
Tasks
Reports
Charges
Email Automation
AI Assistant
Audit Logs
Users
```

Examples:

```txt
No shipments yet. Create your first shipment.
No charges yet. Add receivable/payable charges.
No Gmail suggestions pending.
No audit logs found for this filter.
Unable to load reports. Retry.
```

---

# 9. Confirmation Dialogs for Risky Actions

Add confirmation UI for:

```txt
Archive Shipment
Restore Shipment
Deactivate Party
Reactivate Party
Delete Party Permanently
Cancel Task
Delete Manual Task
Cancel Charge
Apply Gmail Suggestion
Force Apply Gmail Suggestion
Reset User Password
Deactivate User
```

Confirm dialogs should explain what will happen.

---

# 10. Backup / Export Tools

## 10.1 Goal

Add simple export endpoints for admin.

Do not implement full DB backup.

Add CSV exports:

```txt
GET /api/exports/shipments.csv
GET /api/exports/parties.csv
GET /api/exports/charges.csv
GET /api/exports/tasks.csv
GET /api/exports/audit-logs.csv
```

Permissions:

```txt
ADMIN only.
```

Frontend page:

```txt
/admin/tools
```

Section:

```txt
Export Data
```

Buttons:

```txt
Download Shipments CSV
Download Parties CSV
Download Charges CSV
Download Tasks CSV
Download Audit Logs CSV
```

Never export:

```txt
Gmail access tokens
Refresh tokens
Password hashes
API keys
JWT secrets
```

---

# 11. Health / Status Page

## 11.1 Backend Health

Add or improve:

```txt
GET /api/health
GET /api/health/details
```

`/api/health` can be public simple:

```json
{
  "status": "ok"
}
```

`/api/health/details` ADMIN only:

```json
{
  "database": "ok",
  "gmail_enabled": true,
  "ai_enabled": true,
  "provider": "groq",
  "environment": "production",
  "version": "phase-6"
}
```

Do not expose secrets.

---

## 11.2 Frontend Status Page

Add:

```txt
/status
```

Visible to:

```txt
ADMIN
```

Show:

```txt
Backend status
Database status
AI enabled/disabled
Gmail enabled/disabled
Current app version/phase
```

---

# 12. Dashboard / Filter Polish

Improve dashboard and list filters:

```txt
Shipments:
- Active
- Completed
- Archived
- All

Parties:
- Active
- Inactive
- All

Tasks:
- Open
- Done
- Cancelled
- All

Charges:
- Pending
- Paid/Received
- Cancelled
- All
```

Keep default clean:

```txt
Active/non-cancelled records only.
```

Add small labels:

```txt
Showing active shipments only
Include archived
Include inactive
Include cancelled
```

---

# 13. Mobile Responsiveness

Improve layout for smaller screens.

Focus on:

```txt
Sidebar collapse
Dashboard cards wrapping
Tables horizontal scroll
Forms full width
Shipment detail tabs scroll horizontally
Email Automation tables readable
Reports tables readable
```

Do not redesign the whole UI.

Use existing CSS patterns.

---

# 14. Test Data Cleanup Helper

Add admin-only cleanup helper for obvious test data.

Route:

```txt
POST /api/admin/cleanup-test-data
```

Input:

```json
{
  "dry_run": true
}
```

Rules:

```txt
ADMIN only.
Dry run by default.
Only target records containing clear markers:
- Codex Test
- Phase2 Test
- Phase3 Test
- INV-TEST
- TEST123
- Test Exporter
```

Response:

```json
{
  "dry_run": true,
  "would_delete": {
    "shipments": 2,
    "parties": 3,
    "charges": 1
  }
}
```

Recommended Phase 6 safe version:

```txt
Implement dry-run only first.
Do not delete real data.
```

---

# 15. README / Deployment Guide Cleanup

Update README with:

```txt
Current feature list by phase
Local setup
Render deployment
Environment variables
Neon database setup
Groq setup
Gmail setup
Google OAuth redirect URIs
Security notes
Role permissions
Backup/export notes
Known limitations
Troubleshooting
```

Add troubleshooting sections:

```txt
Render not showing recent changes
Gmail OAuth access blocked
Gmail token_exchange_failed
Frontend refresh Not Found
CORS error
Database columns missing
Groq fallback mode active
```

---

# 16. Backend Tests / Smoke Tests

Run:

```bash
cd backend
source .venv/bin/activate
python -m compileall app
```

Manual API smoke:

```txt
Login
GET /api/health
GET /api/health/details as ADMIN
GET /api/audit-logs as ADMIN
POST /api/auth/change-password
GET /api/users as ADMIN
Export CSV endpoints
```

---

# 17. Frontend Build

Run:

```bash
cd frontend
npm run build
```

Manual UI smoke:

```txt
Dashboard
Shipments
Parties
Tasks
Documents
Charges
Reports
AI Assistant
Email Automation
Audit Logs
Users
Settings
Status
Admin Tools
```

---

# 18. Security Tests

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
Committed backend/.env
Committed client_secret*.json
Password hashes in exports
Gmail tokens in responses
```

---

# 19. Acceptance Criteria

Phase 6 is complete only when:

```txt
[ ] Backend compiles
[ ] Frontend builds
[ ] AuditLog model exists
[ ] Important actions create audit logs
[ ] Audit Logs page works for ADMIN
[ ] User Management UI works for ADMIN
[ ] Change Password works
[ ] Risky actions have confirmation dialogs
[ ] Loading/error/empty states improved
[ ] Export CSV endpoints work
[ ] Health/status endpoints work
[ ] Status page works
[ ] Dashboard/list filters are clearer
[ ] Basic mobile responsiveness is improved
[ ] README/deployment guide updated
[ ] No existing Phase 1 behavior broken
[ ] No existing Phase 2 behavior broken
[ ] No existing Phase 3 behavior broken
[ ] No existing Phase 3.5 behavior broken
[ ] No existing Phase 4 behavior broken
[ ] No existing Phase 5 behavior broken
[ ] No real secrets committed
```

---

# 20. Final Commit

After implementation and tests:

```bash
git status
git add .
git commit -m "Implement phase 6 production hardening"
```

Push:

```bash
git push -u origin phase-6-production-hardening
```

---

# 21. Final Report Required

After implementation, report:

```txt
Backend compile result
Frontend build result
Audit log test result
User management test result
Change password test result
Export/backup test result
Health/status test result
UI polish test result
Regression test result
Secret scan result
Git status
Commit hash
Known limitations
```
