# Master 1.1 Pilot Patch Plan

## Patch Priority

### P0 — Must Fix Before Private Beta

| ID | Category | Description | Effort |
|----|----------|-------------|--------|
| PATCH-001 | Bug Fix | Fix enterprise/organizations 500 (OrgRead schema missing `status` field) | Small |
| PATCH-002 | Browser QA | Run full Playwright browser QA suite | Medium |

### P1 — Should Fix Before Private Beta

| ID | Category | Description | Effort |
|----|----------|-------------|--------|
| PATCH-003 | Performance | Add caching for control tower summary (60s TTL) | Small |
| PATCH-004 | Performance | Make tracking sync async (background job) | Medium |
| PATCH-005 | UX | Add frontend loading states for slow operations (AI, control tower, predictions) | Small |
| PATCH-006 | Documentation | Document correct API routes for containers (via shipment), documents (via document-versions), tracking watch items | Small |

### P2 — Nice to Have

| ID | Category | Description | Effort |
|----|----------|-------------|--------|
| PATCH-007 | Performance | Optimize shipment creation (defer audit/events) | Medium |
| PATCH-008 | Performance | Pre-warm AI context on startup | Small |
| PATCH-009 | UX | Add date range filtering to shipment list | Small |
| PATCH-010 | Performance | Optimize startup seed operations (skip if already seeded) | Small |
| PATCH-011 | Frontend | Code splitting to reduce bundle below 500KB | Medium |
| PATCH-012 | Security | Add rate limiting on auth endpoints | Small |

---

## Patch Execution Order

```
1. PATCH-001 (fix OrgRead schema) — immediate
2. PATCH-003 (control tower caching) — same session
3. PATCH-005 (frontend loading states) — same session
4. PATCH-006 (API documentation) — same session
5. PATCH-002 (browser QA) — after fixes
6. PATCH-004 (async tracking) — if time permits
7. Remaining P2 items — after pilot continuation
```

---

## PATCH-001 Detail: Fix OrgRead Schema

**File:** `backend/app/schemas/enterprise.py` (or equivalent)

**Problem:** `OrgRead` Pydantic model requires `status` field but `Organization` SQLAlchemy model doesn't have it.

**Fix Options:**
1. Add `status: Optional[str] = "active"` to OrgRead (make optional with default)
2. Add `status` column to Organization model + Alembic migration

**Recommended:** Option 1 (no migration needed, backward compatible)

---

## PATCH-003 Detail: Control Tower Caching

**Problem:** Control tower summary queries all modules on every request (~7s)

**Fix:** Add in-memory cache with 60-second TTL using existing `warm_dashboard_cache` pattern.

---

## PATCH-004 Detail: Async Tracking Sync

**Problem:** Tracking sync blocks for 30+ seconds

**Fix:** Return sync job ID immediately, process in background, allow polling for status.

---

## Post-Patch Verification

After applying patches:
1. Re-run pilot test script
2. Verify 0 critical/high bugs
3. Verify enterprise/organizations returns 200
4. Verify control tower < 2s (cached)
5. Run Playwright browser QA
6. If all pass → READY FOR PRIVATE BETA

---

## Timeline Estimate

| Phase | Duration |
|-------|----------|
| P0 patches | 1 day |
| P1 patches | 2-3 days |
| Browser QA | 1 day |
| Verification | 1 day |
| **Total to Private Beta** | **5-7 days** |
