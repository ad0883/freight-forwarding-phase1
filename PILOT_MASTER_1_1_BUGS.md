# Master 1.1 Pilot Bugs

## Bug Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 0 |
| Medium | 1 |
| Low | 4 |

---

## Medium Bugs

### BUG-M001: Enterprise /organizations endpoint returns 500

- **Module:** Enterprise Governance
- **Endpoint:** GET /api/enterprise/organizations
- **Error:** `pydantic_core.ValidationError: 1 validation error for OrgRead - status: Field required`
- **Root Cause:** `OrgRead` Pydantic schema requires a `status` field but the `Organization` SQLAlchemy model does not have this column.
- **Impact:** Cannot list organizations via API. Enterprise governance partially broken.
- **Fix:** Either add `status` column to Organization model + migration, or make `status` optional in `OrgRead` schema with a default value.
- **Blocking:** No (other enterprise endpoints work: health, roles, permissions, security-events, data-retention)

---

## Low Bugs

### BUG-L001: Frontend bundle size warning

- **Module:** Frontend
- **Detail:** JS bundle is 530KB (Vite warns at 500KB threshold)
- **Impact:** Slightly longer initial load on slow connections
- **Fix:** Code splitting with dynamic imports

### BUG-L002: Server startup slow (~60s)

- **Module:** Backend / Startup
- **Detail:** Application startup takes ~60 seconds due to Neon DB latency + all seed operations running sequentially
- **Impact:** Cold starts are slow; not blocking for operation
- **Fix:** Parallelize seed operations or make them conditional (skip if already seeded)

### BUG-L003: AI first-call latency (22s)

- **Module:** AI Assistant
- **Detail:** First AI call takes ~22 seconds (Groq cold start + context building). Subsequent calls ~1.5s.
- **Impact:** First user interaction with AI feels slow
- **Fix:** Add loading indicator in frontend; consider warming AI on startup

### BUG-L004: Tracking sync duration (30s)

- **Module:** Tracking
- **Detail:** Mock tracking sync takes ~30 seconds
- **Impact:** User waits long for sync results
- **Fix:** Optimize sync logic or add async background processing

---

## Pilot Exit Assessment

| Criterion | Status |
|-----------|--------|
| 0 critical bugs | ✅ PASS |
| 0 high bugs | ✅ PASS |
| Medium bugs fixed or accepted | ⚠️ 1 medium - needs fix |
| Low bugs documented | ✅ PASS |

**Verdict:** Fix BUG-M001 before Private Beta. Low bugs acceptable for pilot.
