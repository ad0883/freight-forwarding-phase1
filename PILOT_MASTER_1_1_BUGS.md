# Master 1.1 Pilot Bugs

## Bug Summary

| Severity | Count | Status |
|----------|-------|--------|
| Critical | 0 | — |
| High | 0 | — |
| Medium | 1 | ✅ FIXED |
| Low | 4 | ⚠️ MITIGATED |

---

## Medium Bugs

### BUG-M001: Enterprise /organizations endpoint returns 500 — ✅ FIXED

- **Module:** Enterprise Governance
- **Endpoint:** GET /api/enterprise/organizations
- **Error:** `pydantic_core.ValidationError: OrgRead - status: Field required`
- **Root Cause:** `OrgRead` Pydantic schema required `status: str` but the `Organization` SQLAlchemy model uses `is_active: bool` and `org_type: str` (not `status` or `organization_type`).
- **Fix Applied:** Added `OrgRead.from_org()` class method that maps `is_active` → `status` ("active"/"inactive") and `org_type` → `organization_type`. Made `status` default to "active".
- **File Changed:** `backend/app/api/routes/enterprise.py`
- **Verification:** GET /api/enterprise/organizations now returns 200 with correct data.
- **No migration required.** No access control changes. ADMIN-only restriction preserved.

---

## Low Bugs — Mitigated

### BUG-L001: Frontend bundle size warning — ACCEPTED

- **Detail:** JS bundle is 531KB (Vite warns at 500KB)
- **Status:** Accepted for internal pilot. Code splitting deferred to future optimization.

### BUG-L002: Server startup slow (~60s) — DOCUMENTED

- **Detail:** Neon DB latency + sequential seed operations
- **Status:** Documented. Not blocking. Seeds are idempotent and only slow on cold start.

### BUG-L003: AI first-call latency (~22s) — MITIGATED

- **Detail:** Groq cold start + context building
- **Mitigation:** Frontend now shows "first response may take 15–20 seconds while the AI warms up" message on first call.
- **File Changed:** `frontend/src/pages/MockAiPage.jsx`

### BUG-L004: Tracking sync duration (~30s) — MITIGATED

- **Detail:** Mock sync processes all watch items sequentially
- **Mitigation:** Added sync button with disabled state during sync, shows "Syncing — may take up to 30s..." to prevent duplicate clicks and set user expectations.
- **File Changed:** `frontend/src/pages/TrackingPage.jsx`

---

## Additional Improvements Applied

| Area | Improvement | File |
|------|-------------|------|
| Control Tower | Better loading label | ControlTowerPage.jsx |
| Enterprise | Resilient loading (Promise.allSettled) + retry button | EnterprisePage.jsx |
| Predictive | Better loading label + retry button | PredictivePage.jsx |
| Tracking | Better loading label + retry button + sync button | TrackingPage.jsx |
| AI Assistant | Cold-start warning on first message | MockAiPage.jsx |

---

## Pilot Exit Assessment

| Criterion | Status |
|-----------|--------|
| 0 critical bugs | ✅ PASS |
| 0 high bugs | ✅ PASS |
| Medium bugs fixed | ✅ PASS (BUG-M001 fixed) |
| Low bugs documented/mitigated | ✅ PASS |

**Verdict:** Pilot exit criteria met. Private Beta requires full browser QA and deployment smoke test.
