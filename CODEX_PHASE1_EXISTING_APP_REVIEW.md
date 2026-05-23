# Codex Review Plan — Existing Phase 1 Freight Forwarding MVP

## Purpose

Review the existing Phase 1 Freight Forwarding MVP before final GitHub push and deployment.

The app has already been tested end-to-end with:

```txt
Backend: http://127.0.0.1:8000
API docs: http://127.0.0.1:8000/docs
Frontend: http://127.0.0.1:5173
API smoke suite: 36 passed / 0 failed
```

The goal of this review is not to build Phase 2.

The goal is to inspect, clean, secure, and finalize the existing Phase 1 implementation.

---

## Current Phase 1 Status

The following features are already working:

```txt
Backend health check: pass
API docs: pass
CORS from http://localhost:5173: pass
Admin login: pass
/api/auth/me: pass
Admin user listing: pass
Admin can create VIEW_ONLY user: pass
VIEW_ONLY login: pass
VIEW_ONLY can read parties: pass
VIEW_ONLY cannot create parties: pass
Party create/list/update: pass
Export shipment create: pass
Import shipment create: pass
Shipment code generation: pass
FF-EXP-2026-001
FF-IMP-2026-001
Shipment list/detail/update: pass
Export default documents: pass, 9 created
Import default documents: pass, 8 created
Document status + Google Drive URL update: pass
Task list: pass
Initial shipment task creation: pass
Mark task done: pass
Reopen task: pass
Manual task creation: pass
Dashboard summary: pass
Alerts list: pass
Mock AI pending tasks: pass
Mock AI BL pending: pass
Mock AI shipment status: pass
Frontend production build: pass
API smoke suite result: 36 passed / 0 failed
```

Important note:

```txt
The .env CORS parsing bug was fixed.
The following files are modified and may not be committed yet:

backend/app/core/config.py
backend/app/main.py
```

Codex test created temporary database records with names like:

```txt
Codex Test Exporter...
Codex Test Importer...
Codex manual follow-up...
```

Review and clean these if they are still present.

---

# Review Tasks for Codex

## 1. Git and Secret Safety Review

Check the repository for accidental secret exposure.

Run:

```bash
git status
find . -name ".env" -o -name "node_modules" -o -name ".venv"
```

Confirm these are not staged or committed:

```txt
backend/.env
frontend/.env
backend/.venv
frontend/node_modules
frontend/dist
```

Check `.gitignore` includes:

```gitignore
backend/.env
frontend/.env
backend/.venv/
frontend/node_modules/
frontend/dist/
__pycache__/
*.pyc
.DS_Store
```

Search for leaked secrets:

```bash
grep -R "postgresql://" . --exclude-dir=node_modules --exclude-dir=.venv --exclude=".env"
grep -R "JWT_SECRET_KEY=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude=".env"
grep -R "DATABASE_URL=" . --exclude-dir=node_modules --exclude-dir=.venv --exclude=".env"
```

Acceptable places:

```txt
.env.example
README.md
Documentation files
```

Not acceptable:

```txt
Real DATABASE_URL committed in source
Real JWT_SECRET_KEY committed in source
Real Neon password committed in source
```

If any real secret is found, remove it and replace it with placeholder text.

---

## 2. Review the CORS Fix

Inspect these files:

```txt
backend/app/core/config.py
backend/app/main.py
```

Run:

```bash
git diff backend/app/core/config.py backend/app/main.py
```

Confirm:

```txt
BACKEND_CORS_ORIGINS supports comma-separated values.
Spaces after commas do not break parsing.
CORS uses settings.cors_origins.
No hardcoded localhost-only value remains.
The backend still supports local frontend:
http://localhost:5173
http://127.0.0.1:5173
```

Expected local CORS env example:

```env
BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Expected Render production example:

```env
BACKEND_CORS_ORIGINS=https://your-frontend.onrender.com
```

If the CORS parsing is correct, keep the fix.

---

## 3. Authentication Review

Review these files:

```txt
backend/app/api/routes/auth.py
backend/app/api/deps.py
backend/app/core/security.py
backend/app/models/user.py
```

Confirm:

```txt
Passwords are hashed using bcrypt.
Plain passwords are never stored.
JWT tokens are created using JWT_SECRET_KEY.
Protected routes require a valid token.
Disabled users cannot access protected routes.
The default admin is created only when no admin exists.
```

Default development admin:

```txt
Email: admin@example.com
Password: admin123
```

Important:

```txt
This default password is acceptable for local development only.
For production, README should clearly tell the user to change ADMIN_PASSWORD before first deployment.
```

---

## 4. Role and Permission Review

Review these files:

```txt
backend/app/api/deps.py
backend/app/api/routes/users.py
backend/app/api/routes/parties.py
backend/app/api/routes/shipments.py
backend/app/api/routes/documents.py
backend/app/api/routes/tasks.py
```

Confirm these permissions:

```txt
ADMIN:
- can create/list users
- can create/update parties
- can create/update shipments
- can update documents
- can create/update tasks

STAFF:
- can create/update parties
- can create/update shipments
- can update documents
- can create/update tasks
- should not create/list users unless intentionally allowed

VIEW_ONLY:
- can read parties
- can read shipments
- can read documents
- can read tasks
- can read alerts
- cannot create/update parties
- cannot create/update shipments
- cannot update documents
- cannot create/update tasks
- cannot create/list users
```

If any VIEW_ONLY write access exists, fix it.

---

## 5. Database Model Review

Review these models:

```txt
backend/app/models/user.py
backend/app/models/party.py
backend/app/models/shipment.py
backend/app/models/document.py
backend/app/models/task.py
backend/app/models/alert.py
backend/app/models/followup.py
```

Confirm these tables exist:

```txt
users
parties
shipments
documents
tasks
alerts
follow_up_logs
```

Confirm these relationships:

```txt
documents.shipment_id -> shipments.id
tasks.shipment_id -> shipments.id
alerts.shipment_id -> shipments.id when shipment-specific
follow_up_logs.shipment_id -> shipments.id
shipments.exporter_id -> parties.id
shipments.importer_id -> parties.id
shipments.created_by -> users.id
```

Core project rule:

```txt
No shipment-related document, task, alert, or follow-up should be disconnected from a shipment unless intentionally global.
```

---

## 6. Shipment Code Review

Review:

```txt
backend/app/services/shipment_service.py
backend/app/api/routes/shipments.py
```

Confirm shipment codes generate like this:

```txt
Export: FF-EXP-YYYY-NNN
Import: FF-IMP-YYYY-NNN
```

Examples:

```txt
FF-EXP-2026-001
FF-IMP-2026-001
```

Confirm:

```txt
Export and import counters are separate.
Year is included.
NNN is zero-padded.
shipment_code is unique.
```

Also check possible race-condition risk:

```txt
If two shipments are created at the exact same time, duplicate shipment_code may occur.
```

For Phase 1, this can be documented as acceptable, but note it as a future improvement.

---

## 7. Default Document Checklist Review

Review:

```txt
backend/app/services/shipment_service.py
```

Confirm export shipment creates exactly 9 default documents:

```txt
BOOKING_CONFIRMATION
SI
VGM
BL_DRAFT
FINAL_BL
INVOICE
PACKING_LIST
COO
AWB
```

Confirm import shipment creates exactly 8 default documents:

```txt
PRE_ALERT
ARRIVAL_NOTICE
MBL
HBL
FREIGHT_INVOICE
DO
BOE
TELEX_RELEASE
```

Confirm:

```txt
Documents are linked using shipment_id.
Documents are not duplicated accidentally.
Default status is pending.
Google Drive link can be saved in file_url.
```

---

## 8. Task Module Review

Review:

```txt
backend/app/models/task.py
backend/app/api/routes/tasks.py
backend/app/services/shipment_service.py
frontend/src/pages/TasksPage.jsx
frontend/src/pages/ShipmentDetailPage.jsx
```

Confirm:

```txt
Initial export task is created:
Book container with shipping line

Initial import task is created:
Track ETA updates from line
```

Confirm task operations:

```txt
List tasks
Create manual task
Mark done
Reopen task
Set priority
Set due date
```

Confirm:

```txt
Tasks are linked to shipment_id.
VIEW_ONLY cannot create or update tasks.
```

---

## 9. Alert Module Review

Review:

```txt
backend/app/models/alert.py
backend/app/api/routes/alerts.py
backend/app/services/alert_service.py
```

Confirm:

```txt
GET /api/alerts works.
APScheduler starts with backend.
Daily alert check runs at 7:00 AM.
Open tasks with due_date before today create warning alerts.
Duplicate overdue alerts are avoided.
```

For Phase 1, only this basic alert rule is required.

Do not add full demurrage alerts yet.

---

## 10. Mock AI Review

Review:

```txt
backend/app/api/routes/ai.py
frontend/src/pages/MockAiPage.jsx
```

Confirm mock AI supports:

```txt
Which tasks are pending?
Which shipments have BL approval pending?
Show shipment status.
```

Confirm:

```txt
No OpenAI API key is required.
No real OpenAI API call is made.
AI answers are based on simple backend/database rules.
```

Do not implement OpenAI in Phase 1.

---

## 11. Frontend Review

Review these files:

```txt
frontend/src/api/client.js
frontend/src/App.jsx
frontend/src/components/Layout.jsx
frontend/src/components/ProtectedRoute.jsx
frontend/src/pages/LoginPage.jsx
frontend/src/pages/DashboardPage.jsx
frontend/src/pages/ShipmentsPage.jsx
frontend/src/pages/CreateShipmentPage.jsx
frontend/src/pages/ShipmentDetailPage.jsx
frontend/src/pages/PartiesPage.jsx
frontend/src/pages/TasksPage.jsx
frontend/src/pages/MockAiPage.jsx
frontend/src/styles/global.css
```

Manually test these routes:

```txt
/login
/
/shipments
/shipments/new
/shipments/:id
/parties
/tasks
/ai
```

Confirm:

```txt
Login works.
Logout works.
Sidebar active state works.
Dashboard loads without blank screen.
Shipment table handles empty state.
Party table handles empty state.
Create shipment form works.
Document status dropdown updates.
Google Drive link can be added.
Google Drive link opens in new tab.
Task done/reopen works.
Mock AI shows readable answer.
Frontend does not use Tailwind CSS.
```

Check responsive behavior:

```txt
Open browser dev tools.
Test mobile/narrow width.
Sidebar and tables should not break badly.
Horizontal scroll is acceptable for tables.
```

---

## 12. API Review

Open:

```txt
http://127.0.0.1:8000/docs
```

Review and test:

```txt
POST /api/auth/login
GET  /api/auth/me
GET  /api/users
POST /api/users
GET  /api/shipments/dashboard
GET  /api/shipments
POST /api/shipments
GET  /api/shipments/{id}
PATCH /api/shipments/{id}
GET  /api/documents/shipment/{shipment_id}
PATCH /api/documents/{document_id}
GET  /api/tasks
POST /api/tasks
PATCH /api/tasks/{task_id}
GET  /api/parties
POST /api/parties
PATCH /api/parties/{party_id}
GET  /api/alerts
POST /api/ai/ask
```

Confirm:

```txt
Protected routes return 401 without token.
VIEW_ONLY write attempts return 403.
Invalid IDs return 404.
Bad login returns 401.
```

---

## 13. Test Data Cleanup

Check database for temporary test records.

Remove records with names like:

```txt
Codex Test Exporter...
Codex Test Importer...
Codex manual follow-up...
```

Also remove:

```txt
temporary export shipments created by smoke tests
temporary import shipments created by smoke tests
temporary VIEW_ONLY users if not needed
```

Keep only:

```txt
admin user
real parties
real shipments
```

If safe, create a cleanup script or provide SQL/Python commands to delete only Codex test data.

Do not delete real user data.

---

## 14. README Review

Review and improve README files.

README should explain:

```txt
Local backend setup
Local frontend setup
Neon DATABASE_URL setup
JWT_SECRET_KEY setup
Default admin login
Google Drive document-link workflow
Render backend deployment
Render frontend deployment
GitHub push commands
Phase 1 features
Phase 1 limitations
```

Add clear warning:

```txt
Never commit backend/.env or frontend/.env.
Change ADMIN_PASSWORD before production deployment.
```

---

## 15. Phase Boundary Review

Do not build or expand these in this review:

```txt
Charges module
Demurrage calculator
BL management tab
Courier module
Gmail/email parser
OpenAI API
Google Drive API upload
Celery
Redis
```

If any of these are half-built, either:

```txt
1. Remove incomplete UI/routes, or
2. Clearly mark them as future Phase 2/3 placeholders without breaking Phase 1.
```

Do not start Phase 2 in this review.

---

## 16. Build and Run Checks

Run backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Check:

```txt
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

Run frontend:

```bash
cd frontend
npm install
npm run dev
```

Check:

```txt
http://127.0.0.1:5173
```

Run production build:

```bash
cd frontend
npm run build
```

Expected:

```txt
Build passes without errors.
```

---

## 17. Final Git Review

Before committing:

```bash
git status
git diff
```

Confirm:

```txt
No .env files staged.
No node_modules staged.
No .venv staged.
No real secrets staged.
Only intended source/docs files changed.
```

Commit CORS fix if not committed:

```bash
git add backend/app/core/config.py backend/app/main.py
git commit -m "Fix backend CORS config parsing"
```

Commit final review changes:

```bash
git add .
git commit -m "Finalize tested phase 1 MVP"
```

If nothing changed:

```txt
No commit required.
```

---

# Final Acceptance Checklist

Phase 1 review is complete only when:

```txt
[ ] No real secrets are committed
[ ] .env files are ignored
[ ] CORS parsing fix is reviewed
[ ] CORS works locally
[ ] Backend starts successfully
[ ] API docs open successfully
[ ] Frontend starts successfully
[ ] Frontend production build passes
[ ] Admin login works
[ ] VIEW_ONLY read works
[ ] VIEW_ONLY write is blocked
[ ] Party create/list/update works
[ ] Export shipment create works
[ ] Import shipment create works
[ ] Shipment code generation works
[ ] Export default documents = 9
[ ] Import default documents = 8
[ ] Document status update works
[ ] Google Drive file_url update works
[ ] Task list works
[ ] Task done/reopen works
[ ] Manual task creation works
[ ] Dashboard summary works
[ ] Alerts list works
[ ] Mock AI pending tasks works
[ ] Mock AI BL pending works
[ ] Mock AI shipment status works
[ ] Test records are removed or clearly identified
[ ] README is updated
[ ] Phase 2 features are not accidentally added
```

---

# Final Instruction for Codex

Perform this review carefully.

Do not start Phase 2.

Do not add OpenAI, demurrage, charges, BL management, email parsing, Google Drive API, Celery, or Redis.

Only review, clean, secure, fix small Phase 1 issues, update README if needed, and commit the final tested Phase 1 MVP.

If you find problems, fix them.

If you find no problems, report that Phase 1 is ready for GitHub push and Render deployment.
