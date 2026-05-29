# Master 1.1 Release Checklist

## Checklist Metadata

| Field | Value |
|-------|-------|
| Date | 2026-05-29 |
| Certified Commit | 4c0d74c |
| Certified Branch | main |
| Original QA Branch | phase-25-master-1-1-completion-certification |
| Target | Internal Pilot |

---

## Pre-Deployment Checklist

### Infrastructure

| Item | Status | Notes |
|------|--------|-------|
| Render deploy configuration | ✅ | FastAPI + Uvicorn |
| Neon PostgreSQL provisioned | ✅ | Production database |
| Alembic migration path verified | ✅ | Single head, upgrade succeeds |
| Environment variables configured | ⬜ | Must set before deploy |
| HTTPS enabled | ✅ | Render provides TLS |
| Domain configured | ⬜ | Configure if custom domain needed |

### Environment Variables (Required for Production)

| Variable | Set | Critical |
|----------|-----|----------|
| DATABASE_URL | ⬜ | 🔴 Required |
| JWT_SECRET_KEY | ⬜ | 🔴 Required (strong random value) |
| ADMIN_EMAIL | ⬜ | 🔴 Required |
| ADMIN_PASSWORD | ⬜ | 🔴 Required (strong password) |
| BACKEND_CORS_ORIGINS | ⬜ | 🔴 Required (production frontend URL) |
| AI_ENABLED | ⬜ | Optional (false if no Groq key) |
| GROQ_API_KEY | ⬜ | Optional (for AI features) |
| GMAIL_ENABLED | ⬜ | Optional (false if no Google credentials) |
| GOOGLE_CLIENT_ID | ⬜ | Optional (for Gmail) |
| GOOGLE_CLIENT_SECRET | ⬜ | Optional (for Gmail) |
| GOOGLE_REDIRECT_URI | ⬜ | Optional (production callback URL) |
| TOKEN_ENCRYPTION_KEY | ⬜ | Optional (for Gmail token encryption) |
| FRONTEND_BASE_URL | ⬜ | Required (production frontend URL) |
| DOCUMENT_STORAGE_BACKEND | ⬜ | Default: database |

### Security

| Item | Status | Notes |
|------|--------|-------|
| No secrets in repository | ✅ | Verified by security scan |
| JWT secret is strong | ⬜ | Must set before deploy |
| Admin password is strong | ⬜ | Must set before deploy |
| CORS restricted to production | ⬜ | Must configure |
| .env not committed | ✅ | In .gitignore |
| uploaded_documents not committed | ✅ | In .gitignore |
| client_secret*.json not committed | ✅ | In .gitignore |

### Database

| Item | Status | Notes |
|------|--------|-------|
| Alembic current = latest head | ✅ | phase24_enterprise_govern |
| Migration chain intact | ✅ | 21 migrations |
| Default admin created on startup | ✅ | Automatic |
| Default organization created | ✅ | Automatic |
| Seed data (rules, policies, bots, etc.) | ✅ | Automatic on startup |
| Backup plan documented | ⬜ | Neon provides snapshots |

### Frontend

| Item | Status | Notes |
|------|--------|-------|
| Build passes | ✅ | `npm run build` succeeds |
| Bundle size acceptable | ✅ | 530KB (slightly over warning) |
| API base URL configured | ⬜ | Must point to production backend |
| Static hosting configured | ⬜ | Render static site or CDN |

### Application

| Item | Status | Notes |
|------|--------|-------|
| Health endpoint responds | ✅ | GET / returns status:ok |
| Admin user exists | ✅ | Created on startup |
| Default organization exists | ✅ | Created on startup |
| Scheduler jobs configured | ✅ | 3 jobs (alerts, notifications, summary) |
| Gmail read-only scope | ✅ | Only gmail.readonly |
| AI fallback works without key | ✅ | Returns rule-based responses |

---

## Post-Deployment Verification

| Step | Command/Action | Expected |
|------|---------------|----------|
| 1. Health check | `GET /` | `{"status": "ok"}` |
| 2. Login | `POST /api/auth/login` | Returns JWT token |
| 3. Dashboard | `GET /api/shipments` | Returns empty list or data |
| 4. Alembic check | `alembic current` | Shows phase24_enterprise_govern |
| 5. Create shipment | `POST /api/shipments` | Returns shipment with code |
| 6. Control tower | `GET /api/control-tower/summary` | Returns summary object |
| 7. Enterprise health | `GET /api/enterprise/health` | Returns health status |

---

## Rollback Plan

1. If migration fails: Restore Neon database from snapshot
2. If app fails to start: Check environment variables, review logs
3. If critical bug found: Revert to previous deployment on Render
4. Database backup: Neon provides point-in-time recovery

---

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Developer | — | — | ⬜ |
| QA | Automated (Phase 25) | 2026-05-29 | ✅ |
| Security | Automated (Phase 25) | 2026-05-29 | ✅ |
| Product | — | — | ⬜ |
