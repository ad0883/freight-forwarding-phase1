# CODEX_PHASE_6_1_DIRECT_LOGIN_USER_MANAGEMENT_PLAN.md

# Phase 6.1 — Direct Frontend Login & Admin User Management

## Purpose

Implement **Phase 6.1** for the Freight Forwarding AI-Powered Management System.

Most Phase 6 production hardening work is already completed. This patch should focus only on the remaining user-authentication and admin-user-management gap.

The goal is:

```txt
All users should login directly from the frontend.
ADMIN should manage users from the frontend.
No normal user should need Swagger /docs for login or user creation.
```

Supported roles:

```txt
ADMIN
STAFF
VIEW_ONLY
```

---

# 1. Current System Context

The app already has:

```txt
React.js + Vite frontend
FastAPI backend
PostgreSQL / Neon database
JWT + bcrypt authentication
Render hosting
Role-based access
Freight core system
Workflow/BL/demurrage/follow-ups
Charges and reports
Archive/deactivate/cancel controls
Groq AI Assistant
Gmail Email Automation
Production hardening features from Phase 6
```

Hosted app:

```txt
Frontend: https://freight-frontend-u051.onrender.com
Backend:  https://freight-backend-au6c.onrender.com
```

Preserve all existing behavior from previous phases.

Do not modify unrelated modules.

---

# 2. Scope

Implement only:

```txt
1. Direct frontend login for all roles
2. Admin User Management UI
3. Settings / Change Password page if missing or incomplete
4. Role-based sidebar visibility
5. Route protection for admin-only pages
6. Required backend user/auth API support
7. Safe audit logs for user/auth actions
```

---

# 3. Strict Non-Goals

Do **not** implement:

```txt
New Gmail features
New AI features
Google Drive upload
S3 upload
OCR
Invoice PDF generation
Payment gateway
n8n
Celery/Redis
Courier tracking
Accounting integration
Any unrelated freight feature
Any production demo-login buttons
```

Do not redo completed Phase 6 modules such as:

```txt
Audit logs
Health/status
CSV exports
Admin tools
Cleanup dry-run
Dashboard hardening
Gmail automation
Groq assistant
Reports
Charges
```

Only touch them if necessary for user/auth integration.

---

# 4. Git Workflow

Before coding:

```bash
git status
git log --oneline -5
```

Create branch:

```bash
git checkout -b phase-6-1-direct-login-user-management
```

If branch already exists:

```bash
git checkout phase-6-1-direct-login-user-management
```

Final commit:

```bash
git add .
git commit -m "Implement direct login and user management"
```

Push:

```bash
git push -u origin phase-6-1-direct-login-user-management
```

---

# 5. Backend Requirements

## 5.1 Keep Existing Login

Keep existing route:

```txt
POST /api/auth/login
```

The frontend login page should use it.

The form uses:

```txt
email
password
```

If backend internally expects OAuth2 form fields:

```txt
username
password
```

then frontend should send:

```txt
username = email
password = password
```

Do not break existing login behavior.

---

## 5.2 First Admin From Environment

Keep first admin auto-creation from backend environment variables:

```env
ADMIN_NAME=Admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your_secure_password
```

This creates the first ADMIN.

After that, ADMIN can create/manage users from the frontend.

---

## 5.3 User APIs

Ensure backend supports these routes:

```txt
GET /api/users
POST /api/users
PATCH /api/users/{user_id}
PATCH /api/users/{user_id}/password-reset
PATCH /api/users/{user_id}/deactivate
PATCH /api/users/{user_id}/reactivate
```

If some already exist, reuse and polish them.

Permissions:

```txt
ADMIN only
```

No STAFF or VIEW_ONLY access.

---

## 5.4 User Creation

ADMIN can create users with:

```txt
name
email
password
role
```

Allowed roles:

```txt
ADMIN
STAFF
VIEW_ONLY
```

Rules:

```txt
Email must be unique.
Password must be hashed with existing bcrypt logic.
Never return password_hash in API responses.
Created user can login directly from frontend /login.
```

---

## 5.5 User Update

ADMIN can update:

```txt
name
role
is_active
```

Rules:

```txt
Prevent changing the only active ADMIN to STAFF or VIEW_ONLY.
Prevent deactivating the only active ADMIN.
Prevent an admin from accidentally removing their own final admin access.
Never return password_hash.
```

---

## 5.6 Password Reset

ADMIN can reset any user's password.

Route:

```txt
PATCH /api/users/{user_id}/password-reset
```

Input:

```json
{
  "new_password": "new-password"
}
```

Rules:

```txt
Hash new password.
Do not log password.
Do not return password.
Do not store password in audit metadata.
```

---

## 5.7 Deactivate / Reactivate User

Routes:

```txt
PATCH /api/users/{user_id}/deactivate
PATCH /api/users/{user_id}/reactivate
```

Rules:

```txt
Deactivated user cannot login.
Cannot deactivate the only active ADMIN.
Cannot deactivate yourself if you are the only active ADMIN.
Reactivated user can login again.
```

---

## 5.8 Change Password

Add or polish:

```txt
POST /api/auth/change-password
```

Input:

```json
{
  "current_password": "old-password",
  "new_password": "new-password"
}
```

Permissions:

```txt
Any authenticated user
```

Rules:

```txt
Verify current password.
Hash new password using existing bcrypt logic.
Do not log current password.
Do not log new password.
Return success message.
```

---

## 5.9 Auth Me

Ensure:

```txt
GET /api/auth/me
```

returns current user data:

```txt
id
name
email
role
is_active
created_at
```

Never return:

```txt
password_hash
tokens
secrets
```

---

# 6. Audit Logging

Use existing audit log system if present.

Add safe audit logs for:

```txt
user.create
user.update
user.role_change
user.password_reset
user.deactivate
user.reactivate
auth.change_password
```

Sensitive data rule:

```txt
Never audit passwords.
Never audit password hashes.
Never audit JWTs.
Never audit raw request bodies.
Never audit API keys.
Never audit secrets.
Never audit tokens.
```

For password change/reset, store only:

```txt
action happened
actor user
target user
timestamp
safe description
```

---

# 7. Frontend Requirements

## 7.1 Login Page

Keep or create:

```txt
/login
```

One login page for all roles.

Form fields:

```txt
Email
Password
```

Behavior:

```txt
Submit credentials to backend.
Store auth token using current auth mechanism.
Fetch /api/auth/me after login.
Redirect to /dashboard.
Show readable error if credentials are wrong.
Show readable error if user is inactive.
```

Do not add production quick-login/demo-login buttons:

```txt
Login as Admin
Login as Staff
Login as View Only
```

---

## 7.2 App Load Auth Check

On app load:

```txt
If token exists, call /api/auth/me.
If valid, set current user.
If invalid/expired, clear token and redirect to /login.
```

---

## 7.3 Role-Based Sidebar

Show sidebar links based on role.

### ADMIN

```txt
Dashboard
Shipments
Parties
Tasks
Reports
AI Assistant
Email Automation
Users
Audit Logs
Status
Admin Tools
Settings
```

### STAFF

```txt
Dashboard
Shipments
Parties
Tasks
Reports
AI Assistant
Email Automation
Settings
```

### VIEW_ONLY

```txt
Dashboard
Shipments
Parties
Tasks
Reports
AI Assistant
Settings
```

Rules:

```txt
Hide /users from STAFF and VIEW_ONLY.
Hide /audit-logs from STAFF and VIEW_ONLY.
Hide /status from STAFF and VIEW_ONLY.
Hide /admin/tools from STAFF and VIEW_ONLY.
Hide Email Automation from VIEW_ONLY.
```

---

## 7.4 Route Protection

If unauthorized user manually opens restricted route:

```txt
/users
/audit-logs
/status
/admin/tools
/email for VIEW_ONLY
```

show:

```txt
403 / Not allowed
```

Do not show a blank page.

---

# 8. Users Page

Add or polish route:

```txt
/users
```

Visible to:

```txt
ADMIN only
```

## 8.1 User List

Show columns:

```txt
Name
Email
Role
Active
Created At
Actions
```

## 8.2 Actions

ADMIN can:

```txt
Create user
Edit name
Change role
Deactivate user
Reactivate user
Reset password
```

## 8.3 Create User Form

Fields:

```txt
Name
Email
Password
Role
```

Allowed roles:

```txt
ADMIN
STAFF
VIEW_ONLY
```

## 8.4 Edit User

Fields:

```txt
Name
Role
Active status
```

Rules:

```txt
Show clear warning if trying to demote/deactivate only active ADMIN.
Backend must enforce this even if frontend misses it.
```

## 8.5 Reset Password

Fields:

```txt
New password
Confirm new password
```

Rules:

```txt
Do not show/store password after reset.
Show success message only.
```

---

# 9. Settings Page

Add or polish route:

```txt
/settings
```

Visible to:

```txt
All authenticated users
```

Show current user:

```txt
Name
Email
Role
Active status
```

Change password form:

```txt
Current password
New password
Confirm new password
```

Validation:

```txt
New password and confirm password must match.
Current password required.
Show readable error on wrong current password.
Show success message after change.
```

---

# 10. UI States

Use existing shared components if present.

Add readable states for:

```txt
Loading users
User list empty
User creation failed
Password reset failed
Change password failed
Permission denied
Login failed
```

No blank screens.

---

# 11. Testing

## 11.1 Backend Compile

Run:

```bash
cd backend
source .venv/bin/activate
python -m compileall app
```

Expected:

```txt
No syntax errors.
```

---

## 11.2 Frontend Build

Run:

```bash
cd frontend
npm run build
```

Expected:

```txt
Build passes.
```

---

## 11.3 Direct Login Tests

Test from frontend `/login`:

```txt
ADMIN can login.
STAFF can login.
VIEW_ONLY can login.
Inactive user cannot login.
Invalid password shows readable error.
Expired/invalid token redirects to login.
```

---

## 11.4 Admin User Management Tests

As ADMIN:

```txt
Open /users.
Create STAFF user.
Create VIEW_ONLY user.
Created STAFF logs in directly from /login.
Created VIEW_ONLY logs in directly from /login.
Edit user name.
Change user role.
Reset user password.
User logs in with reset password.
Deactivate user.
Deactivated user cannot login.
Reactivate user.
Reactivated user can login.
```

Protection tests:

```txt
Cannot deactivate only active ADMIN.
Cannot demote only active ADMIN.
Never return password_hash.
```

---

## 11.5 Role Permission Tests

STAFF:

```txt
Can login.
Can see allowed sidebar.
Cannot see /users link.
Manual /users access shows 403.
Cannot call admin user APIs.
```

VIEW_ONLY:

```txt
Can login.
Can see allowed sidebar.
Cannot see /users link.
Manual /users access shows 403.
Cannot perform write actions.
Cannot access Email Automation if policy hides it.
```

---

## 11.6 Change Password Tests

For any authenticated user:

```txt
Open /settings.
Wrong current password fails.
New password mismatch fails.
Correct current password works.
Old password no longer works.
New password works.
```

---

## 11.7 Audit Tests

Confirm audit logs exist for:

```txt
user.create
user.update
user.role_change
user.password_reset
user.deactivate
user.reactivate
auth.change_password
```

Confirm audit logs do not contain:

```txt
password
password_hash
JWT
token
secret
raw request body
```

---

## 11.8 Regression Tests

Verify existing features still work:

```txt
Dashboard
Shipments
Parties
Tasks
Documents
Workflow
BL
Demurrage
Follow-ups
Charges
Reports
AI Assistant
Email Automation
Audit Logs
Status
Admin Tools
```

---

## 11.9 Secret Scan

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
Password hashes in API responses
Sensitive values in audit metadata
```

---

# 12. Acceptance Criteria

Complete only when:

```txt
[ ] Backend compiles
[ ] Frontend builds
[ ] Direct frontend login works for ADMIN
[ ] Direct frontend login works for STAFF
[ ] Direct frontend login works for VIEW_ONLY
[ ] ADMIN can create users from /users
[ ] Created users can login from /login
[ ] ADMIN can edit users
[ ] ADMIN can reset passwords
[ ] Reset user can login with new password
[ ] ADMIN can deactivate/reactivate users
[ ] Deactivated user cannot login
[ ] Only active ADMIN cannot be deactivated
[ ] Only active ADMIN cannot be demoted
[ ] STAFF cannot access /users
[ ] VIEW_ONLY cannot access /users
[ ] Settings page works
[ ] Change password works
[ ] Audit logs created for user/auth actions
[ ] Audit logs contain no sensitive data
[ ] No password_hash returned
[ ] Existing Phase 1–6 features still work
[ ] No real secrets committed
```

---

# 13. Final Commit

After all checks pass:

```bash
git status
git add .
git commit -m "Implement direct login and user management"
```

Push:

```bash
git push -u origin phase-6-1-direct-login-user-management
```

---

# 14. Final Report Required

After implementation, report:

```txt
Backend compile result
Frontend build result
Direct login test result
Admin user management test result
Change password test result
Role permission test result
Audit safety test result
Regression test result
Secret scan result
Git status
Commit hash
Known limitations
```
