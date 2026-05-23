# Codex Implementation Plan — Phase 1 Freight Forwarding System

## Project Overview

You are building **Phase 1** of a **Freight Forwarding AI-Powered Management System**.

The goal of Phase 1 is to build the core operational foundation:

- User login and roles
- Shipment creation for export and import
- Shipment list dashboard
- Basic document checklist per shipment
- Manual data entry
- Party directory/contact book
- Basic tasks
- Basic alerts
- Mock AI assistant

Every major record must be connected back to a shipment wherever applicable.

The most important system rule is:

> Every shipment gets a unique Shipment ID, and all documents, tasks, alerts, and shipment-related records must link back to that shipment.

---

## 1. Selected Tech Stack

### Frontend

```txt
React.js + Vite
React Router
Axios
Normal CSS
```

Do not use Tailwind CSS.

### Backend

```txt
Python + FastAPI
SQLAlchemy ORM
PostgreSQL
JWT authentication
bcrypt password hashing
APScheduler
```

### Database

```txt
PostgreSQL on Neon Free
```

### File Handling

```txt
Google Drive links only for Phase 1
```

Do not implement real file upload yet.

The user will manually upload files to Google Drive, copy the share link, and paste it into the system.

### AI

```txt
Mock AI assistant first
```

Do not connect OpenAI API in Phase 1.

The mock AI assistant should answer simple database-based questions.

### Hosting Target

```txt
Render free hosting
GitHub repository
```

---

## 2. Phase 1 Scope

Build only these features:

```txt
User login + roles
Shipment creation for Export and Import
Shipment list dashboard
Basic document checklist per shipment
Manual data entry
Party directory/contact book
Basic task module
Basic alert module
Mock AI assistant
Google Drive file_url field for documents
```

---

## 3. Phase 1 Non-Goals

Do not build these in Phase 1:

```txt
Real OpenAI API integration
Real Google Drive API upload
AWS S3
Celery
Redis
Full demurrage calculator
Charges and P&L module
BL management module
Courier tracking module
Email parsing
Gmail API
Reports module
Advanced workflow automation
Docker
Kubernetes
```

Only create database/model foundations where useful.

---

## 4. Recommended Repository Structure

Create this structure:

```txt
freight-forwarding-system/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── shipments.py
│   │   │   │   ├── parties.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── alerts.py
│   │   │   │   └── ai.py
│   │   │   └── deps.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   │
│   │   ├── db/
│   │   │   └── session.py
│   │   │
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── shipment.py
│   │   │   ├── party.py
│   │   │   ├── document.py
│   │   │   ├── task.py
│   │   │   ├── alert.py
│   │   │   └── followup.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── shipment.py
│   │   │   ├── party.py
│   │   │   ├── document.py
│   │   │   ├── task.py
│   │   │   └── alert.py
│   │   │
│   │   ├── services/
│   │   │   ├── shipment_service.py
│   │   │   └── alert_service.py
│   │   │
│   │   └── main.py
│   │
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js
│   │   │
│   │   ├── components/
│   │   │   ├── Layout.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   │
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── ShipmentsPage.jsx
│   │   │   ├── CreateShipmentPage.jsx
│   │   │   ├── ShipmentDetailPage.jsx
│   │   │   ├── PartiesPage.jsx
│   │   │   ├── TasksPage.jsx
│   │   │   └── MockAiPage.jsx
│   │   │
│   │   ├── styles/
│   │   │   └── global.css
│   │   │
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── package.json
│   ├── index.html
│   ├── .env.example
│   └── README.md
│
├── .gitignore
└── README.md
```

---

# 5. Backend Implementation Plan

## 5.1 FastAPI Setup

Create a FastAPI app with:

```txt
CORS enabled
/api prefix for all routes
Health check route at /
Automatic API docs at /docs
Environment variable loading from .env
```

Required backend packages:

```txt
fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
pydantic-settings
python-jose[cryptography]
passlib[bcrypt]
python-multipart
email-validator
apscheduler
```

---

## 5.2 Backend Environment Variables

Create `backend/.env.example`:

```env
PROJECT_NAME=Freight Forwarding Phase 1 API
ENVIRONMENT=development

DATABASE_URL=postgresql://username:password@host/dbname?sslmode=require

JWT_SECRET_KEY=change-this-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

AUTO_CREATE_TABLES=true

ADMIN_NAME=Admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
```

---

# 6. Backend Database Models

## 6.1 User Model

Create model:

```txt
id
name
email
hashed_password
role
is_active
created_at
```

Allowed roles:

```txt
ADMIN
STAFF
VIEW_ONLY
```

Role meaning:

```txt
ADMIN: Full access
STAFF: Operational create/update access
VIEW_ONLY: Read-only access
```

---

## 6.2 Party Model

Create model:

```txt
id
name
type
contact_person
email
phone
country
gstin
created_at
```

Allowed party types:

```txt
exporter
importer
cha
overseas_ff
line
courier
buyer
other
```

---

## 6.3 Shipment Model

Create model:

```txt
id
shipment_code
type
status
exporter_id
importer_id
shipping_line
vessel_name
voyage_no
origin_port
dest_port
container_no
container_type
etd
eta
bl_number
booking_ref
commodity
created_at
created_by
```

Allowed shipment types:

```txt
export
import
```

Allowed container types:

```txt
20GP
40GP
40HC
LCL
```

Shipment code format:

```txt
Export: FF-EXP-YYYY-NNN
Import: FF-IMP-YYYY-NNN
```

Example:

```txt
FF-EXP-2026-001
FF-IMP-2026-001
```

---

## 6.4 Document Model

Create model:

```txt
id
shipment_id
doc_type
status
date_received
date_sent
file_url
notes
is_required
created_at
```

Allowed statuses:

```txt
pending
received
sent
approved
not_required
```

For Phase 1, `file_url` stores a Google Drive link.

---

## 6.5 Task Model

Create model:

```txt
id
shipment_id
title
description
assigned_to
due_date
priority
status
auto_generated
created_at
```

Allowed priorities:

```txt
critical
warning
info
```

Allowed statuses:

```txt
open
done
```

---

## 6.6 Alert Model

Create model:

```txt
id
shipment_id
title
message
priority
is_read
created_at
```

Allowed priorities:

```txt
critical
warning
info
```

---

## 6.7 FollowUpLog Model

Create this model now, even if the full UI comes later:

```txt
id
shipment_id
party_id
channel
summary
next_action
status
logged_by
date
```

Allowed channels:

```txt
email
call
whatsapp
meeting
```

Allowed statuses:

```txt
open
closed
```

---

# 7. Backend API Routes

## 7.1 Auth Routes

Create:

```txt
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

Login should return:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

Use:

```txt
bcrypt for password hashing
JWT for token creation
OAuth2PasswordBearer for protected routes
```

When the app starts, auto-create a default admin if no admin exists:

```txt
Email: admin@example.com
Password: admin123
Role: ADMIN
```

---

## 7.2 User Routes

Create:

```txt
GET  /api/users
POST /api/users
```

Permissions:

```txt
Only ADMIN can create/list users.
```

---

## 7.3 Party Routes

Create:

```txt
GET   /api/parties
POST  /api/parties
PATCH /api/parties/{party_id}
```

Permissions:

```txt
ADMIN and STAFF can create/update.
VIEW_ONLY can only read.
```

---

## 7.4 Shipment Routes

Create:

```txt
GET   /api/shipments/dashboard
GET   /api/shipments
POST  /api/shipments
GET   /api/shipments/{shipment_id}
PATCH /api/shipments/{shipment_id}
```

When creating a shipment:

```txt
1. Generate shipment_code automatically.
2. Save shipment.
3. Create default document checklist.
4. Create first auto-generated task.
```

---

## 7.5 Default Export Documents

For export shipment, create these documents automatically:

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

---

## 7.6 Default Import Documents

For import shipment, create these documents automatically:

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

---

## 7.7 Initial Auto-Generated Tasks

For export shipment:

```txt
Book container with shipping line
```

For import shipment:

```txt
Track ETA updates from line
```

---

## 7.8 Document Routes

Create:

```txt
GET   /api/documents/shipment/{shipment_id}
PATCH /api/documents/{document_id}
```

Allow updating:

```txt
status
date_received
date_sent
file_url
notes
is_required
```

---

## 7.9 Task Routes

Create:

```txt
GET   /api/tasks
POST  /api/tasks
PATCH /api/tasks/{task_id}
```

Allow:

```txt
Create manual task
Mark task done
Reopen task
Change priority
Change due date
```

---

## 7.10 Alert Routes

Create:

```txt
GET /api/alerts
```

Phase 1 only needs read/list alerts.

---

## 7.11 Mock AI Route

Create:

```txt
POST /api/ai/ask
```

Input:

```json
{
  "question": "Which tasks are pending?"
}
```

Output:

```json
{
  "answer": "..."
}
```

The mock AI should support simple rule-based questions:

```txt
Which tasks are pending?
Which shipments have BL approval pending?
Show shipment status.
```

Do not use OpenAI API in Phase 1.

---

# 8. APScheduler Alert Logic

Add a basic daily job using APScheduler.

Run every day at:

```txt
7:00 AM
```

Phase 1 alert rule:

```txt
If task.status = open and task.due_date < today:
    create warning alert
```

Avoid duplicate alerts by checking if an alert for the same overdue task already exists.

Do not implement full demurrage logic in Phase 1.

---

# 9. Frontend Implementation Plan

## 9.1 React Setup

Use:

```txt
Vite
React Router
Axios
Normal CSS
```

Frontend environment:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

Do not use Tailwind.

---

## 9.2 Login Page

Route:

```txt
/login
```

Features:

```txt
Email field
Password field
Login button
Store JWT token in localStorage
Redirect to dashboard after login
Show error if login fails
```

Default dev login:

```txt
admin@example.com
admin123
```

---

## 9.3 Protected Layout

Create sidebar layout with links:

```txt
Dashboard
Shipments
Parties
Tasks
Mock AI
Logout
```

If no JWT token exists, redirect user to login.

---

## 9.4 Dashboard Page

Route:

```txt
/
```

Show summary cards:

```txt
Live Shipments
Pending Tasks
Future Bookings
Alerts Today
Completed This Month
```

Below cards, show shipment table:

```txt
Shipment ID
Type
Shipping Line
ETD
ETA
Status
```

Right side or bottom panel:

```txt
Recent alerts
```

---

## 9.5 Shipments Page

Route:

```txt
/shipments
```

Features:

```txt
Shipment table
Search box
Create shipment button
Click shipment row to open detail page
```

Columns:

```txt
Shipment ID
Type
Shipping Line
Origin
Destination
Commodity
Status
```

---

## 9.6 Create Shipment Page

Route:

```txt
/shipments/new
```

Form fields:

```txt
type
exporter_id
importer_id
shipping_line
vessel_name
voyage_no
origin_port
dest_port
container_no
container_type
etd
eta
booking_ref
commodity
```

After creating shipment:

```txt
Redirect to /shipments/{id}
```

---

## 9.7 Shipment Detail Page

Route:

```txt
/shipments/:id
```

Tabs for Phase 1:

```txt
Overview
Documents
Tasks
```

### Overview Tab

Show:

```txt
shipment_code
type
status
shipping_line
vessel_name
voyage_no
origin_port
dest_port
container_no
container_type
etd
eta
booking_ref
commodity
```

### Documents Tab

Show document checklist table:

```txt
Document Type
Status dropdown
File link
Notes
Add/Edit Link button
```

The Add/Edit Link button should allow the user to paste a Google Drive URL and save it to `file_url`.

### Tasks Tab

Show:

```txt
Task title
Description
Priority
Status
Mark done/reopen button
```

---

## 9.8 Parties Page

Route:

```txt
/parties
```

Features:

```txt
Create party form
Party list table
```

Party fields:

```txt
name
type
contact_person
email
phone
country
gstin
```

---

## 9.9 Tasks Page

Route:

```txt
/tasks
```

Features:

```txt
List all tasks
Show shipment_id
Show due date
Show priority
Show status
Mark done/reopen
```

---

## 9.10 Mock AI Page

Route:

```txt
/ai
```

Features:

```txt
Chat-like UI
Question input
Answer box
Calls POST /api/ai/ask
```

Example prompts shown in UI:

```txt
Which tasks are pending?
Which shipments have BL approval pending?
Show shipment status.
```

---

# 10. Styling Requirements

Use clean material-style UI with normal CSS.

Design style:

```txt
Left sidebar
White cards
Soft shadows
Rounded corners
Blue primary color
Responsive layout
Clean tables
Simple badges for status and priority
```

Do not use:

```txt
Tailwind CSS
Bootstrap
Heavy animation libraries
```

---

# 11. Acceptance Criteria

Codex must finish Phase 1 only when all of these work:

```txt
1. Backend starts with:
   uvicorn app.main:app --reload

2. API docs open at:
   http://localhost:8000/docs

3. Default admin can login:
   admin@example.com / admin123

4. Frontend starts with:
   npm run dev

5. Login works from React frontend.

6. Party can be created.

7. Export shipment can be created.

8. Import shipment can be created.

9. Shipment code is auto-generated correctly:
   FF-EXP-YYYY-001
   FF-IMP-YYYY-001

10. Default documents are created automatically for new shipment.

11. Default initial task is created automatically for new shipment.

12. Shipment detail page shows Overview, Documents, and Tasks tabs.

13. Document status can be updated.

14. Google Drive link can be pasted into document file_url.

15. Task can be marked done/reopened.

16. Dashboard summary cards load real data.

17. Mock AI assistant answers simple database-based questions.

18. Code has no Tailwind dependency.

19. README explains local setup, Neon setup, Render setup, and GitHub push.
```

---

# 12. Commands Codex Should Run

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

For Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Frontend Build Check

```bash
cd frontend
npm run build
```

---

## Git Check

```bash
git status
```

---

## Final Commit

```bash
git add .
git commit -m "Implement phase 1 freight forwarding MVP"
```

---

# 13. Render Deployment Notes

## Backend Render Web Service

Root directory:

```txt
backend
```

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Environment variables:

```env
DATABASE_URL=your_neon_postgres_url
JWT_SECRET_KEY=your_secret_key
BACKEND_CORS_ORIGINS=https://your-frontend.onrender.com
AUTO_CREATE_TABLES=true
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-this-password
```

---

## Frontend Render Static Site

Root directory:

```txt
frontend
```

Build command:

```bash
npm install && npm run build
```

Publish directory:

```txt
dist
```

Environment variable:

```env
VITE_API_BASE_URL=https://your-backend.onrender.com/api
```

---

# 14. GitHub Push Commands

From the project root:

```bash
git init
git add .
git commit -m "Initial freight forwarding phase 1 MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/freight-forwarding-phase1.git
git push -u origin main
```

---

# 15. Final Copy-Paste Prompt for Codex

Use this exact prompt in Codex:

```txt
Implement Phase 1 of the Freight Forwarding AI-Powered Management System in this repository.

Follow the implementation plan below exactly.

Build a React.js + Vite frontend and Python FastAPI backend with PostgreSQL support.

Use JWT + bcrypt for authentication.

Use SQLAlchemy models for:
- User
- Party
- Shipment
- Document
- Task
- Alert
- FollowUpLog

Build these Phase 1 features:
- Login with default admin
- Role-ready backend: ADMIN, STAFF, VIEW_ONLY
- Shipment creation for export/import
- Auto shipment code generation
- Shipment list dashboard
- Basic document checklist per shipment
- Google Drive file_url field for documents
- Manual data entry
- Party directory
- Tasks module
- Basic APScheduler overdue-task alert logic
- Mock AI assistant with simple database-rule responses

Do not implement:
- OpenAI API
- real file upload
- Google Drive API
- S3
- Celery
- Redis
- charges module
- demurrage calculator
- email parsing
- Gmail API
- full BL management

Use normal CSS only. Do not use Tailwind.

After implementation:
- Add .env.example files.
- Add setup instructions in README.
- Run backend dependency install if possible.
- Run frontend npm install/build if possible.
- Fix any errors.
- Commit the final working code with message:
  "Implement phase 1 freight forwarding MVP"

Acceptance criteria:
- Backend runs with uvicorn app.main:app --reload.
- Frontend runs with npm run dev.
- Admin can login with admin@example.com / admin123.
- User can create parties.
- User can create export/import shipments.
- Shipment code is auto-generated.
- Default document checklist is created.
- Initial task is created.
- Dashboard cards show real counts.
- Shipment detail has Overview, Documents, and Tasks tabs.
- Document status and Google Drive link can be updated.
- Tasks can be marked done/reopened.
- Mock AI answers pending task/status/BL pending questions.
```

---

# 16. Recommended Phase 2 After Phase 1

After Phase 1 is stable, continue with Phase 2:

```txt
Export workflow step automation
Import workflow step automation
BL management tab
Demurrage calculator
Follow-up log UI
Alert priority rules
More complete role permission handling
```

Do not start Phase 2 until Phase 1 acceptance criteria are fully working.
