# Private Beta AI Performance Notes

## Summary

15 performance measurements recorded. 3 medium-severity items noted.

---

## Performance Observations

| # | Endpoint/Page | Observed Time | Expected | Severity | Recommendation |
|---|---|---|---|---|---|
| 1 | `/api/tracking/run-sync` | 4.47s | <5s | Low | Acceptable for sync operation |
| 2 | `/api/predictive/run` | 10.22s | <5s | **Medium** | Consider async/background processing |
| 3 | `/api/control-tower/summary` | 6.55s | <3s | **Medium** | Add query caching or pagination |
| 4 | `/api/ai/ask` (attention) | 4.20s | <30s | Low | Good — well within limits |
| 5 | `/api/ai/ask` (delays) | 1.61s | <30s | Low | Excellent |
| 6 | `/api/ai/ask` (demurrage) | 12.39s | <30s | Low | Acceptable for complex query |
| 7 | `/api/enterprise/health` | 1.87s | <3s | Low | Acceptable |
| 8 | `/api/enterprise/organizations` | 0.85s | <3s | Low | Good |
| 9 | `/api/enterprise/roles` | 0.74s | <3s | Low | Good |
| 10 | `/api/enterprise/permissions` | 1.21s | <3s | Low | Good |
| 11 | `/api/enterprise/security-events` | 0.94s | <3s | Low | Good |
| 12 | `/api/enterprise/permissions/matrix` | 0.82s | <3s | Low | Good |
| 13 | `GET /api/containers/risk` | 11.57s | <3s | **Medium** | Consider caching risk calculations |
| 14 | `GET /api/control-tower/summary` | 6.55s | <3s | **Medium** | Same as #3 above |

---

## Performance Classification

| Severity | Count | Items |
|---|---|---|
| **Medium** | 3 | Predictive run (10.2s), Control Tower summary (6.6s), Container risk (11.6s) |
| **Low** | 12 | All within acceptable ranges |
| **Critical** | 0 | None |

---

## Frontend Build Performance

| Metric | Value |
|---|---|
| Build time | 867ms |
| Total modules | 1,670 |
| CSS bundle | 26.80 kB (5.72 kB gzipped) |
| JS bundle | 531.16 kB (131.61 kB gzipped) |
| Bundle warning | JS chunk > 500 kB — consider code-splitting |

---

## Recommendations

1. **Container risk endpoint (11.6s):** Consider adding a cache layer for risk calculations, or pre-computing risk on container status changes.
2. **Control Tower summary (6.6s):** This aggregates many data sources. Consider caching the summary with a 1-minute TTL.
3. **Predictive run (10.2s):** This is a batch computation. Consider running as a background task with progress polling.
4. **Frontend bundle (531 kB):** Use dynamic `import()` for route-level code-splitting to reduce initial load.

All items are **non-blocking** for private beta.
