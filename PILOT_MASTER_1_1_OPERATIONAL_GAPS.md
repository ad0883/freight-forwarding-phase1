# Master 1.1 Pilot Operational Gaps

## Summary

These are operational gaps discovered during the internal pilot — areas where a real freight-forwarding team would encounter friction or missing functionality within the Master 1.1 scope.

---

## GAP-001: Document Upload Route Discoverability

- **Area:** Documents
- **Issue:** Document upload is via `/api/document-versions/upload` or `/api/shipments/{id}/document-versions/upload`, not the more intuitive `/api/documents/upload`
- **Impact:** API consumers may try the wrong endpoint
- **Recommendation:** Add a redirect or alias at `/api/documents/upload` → document-versions upload, or document clearly in API docs

## GAP-002: Container Creation Only via Shipment Sub-Route

- **Area:** Containers
- **Issue:** Containers can only be created via `POST /api/shipments/{id}/containers`, not directly via `POST /api/containers`
- **Impact:** Minor confusion for API consumers; `/api/containers` is GET-only
- **Recommendation:** Document clearly; this is acceptable design (containers belong to shipments)

## GAP-003: Tracking Watch Item Requires tracking_identifier

- **Area:** Tracking
- **Issue:** Watch items require `tracking_identifier` field (not just shipment_id + reference). The field name isn't immediately obvious.
- **Impact:** API consumers may not know what value to provide
- **Recommendation:** Add API documentation or validation message explaining expected format

## GAP-004: Portal Account Requires full_name (Not password)

- **Area:** Portal
- **Issue:** Portal account creation requires `email` + `full_name` fields. Password is not set during creation (likely uses invite/reset flow).
- **Impact:** Different from typical user creation flow; needs documentation
- **Recommendation:** Document the portal onboarding flow clearly

## GAP-005: No Bulk Operations

- **Area:** All Modules
- **Issue:** No bulk create/update/delete endpoints for shipments, parties, charges, etc.
- **Impact:** Operations teams managing 50+ shipments daily would need to make individual API calls
- **Recommendation:** Consider bulk endpoints in Master 1.2 for high-volume operations

## GAP-006: No Shipment Search/Filter by Date Range

- **Area:** Shipments
- **Issue:** Shipment list doesn't appear to support date range filtering (ETD/ETA range)
- **Impact:** Operations teams need to find shipments by sailing date
- **Recommendation:** Add date range query parameters

## GAP-007: No Dashboard Refresh/Cache Control

- **Area:** Dashboard / Control Tower
- **Issue:** Control tower summary takes 7+ seconds. No explicit cache refresh mechanism for users.
- **Impact:** Users may see stale data or wait too long
- **Recommendation:** Add cache TTL indicator and manual refresh button

---

## Severity Assessment

| Gap | Severity | Blocking for Pilot? |
|-----|----------|-------------------|
| GAP-001 | Low | No |
| GAP-002 | Low | No |
| GAP-003 | Low | No |
| GAP-004 | Low | No |
| GAP-005 | Medium | No (single-user pilot) |
| GAP-006 | Medium | No |
| GAP-007 | Low | No |

None of these gaps are blocking for the internal pilot. They should be addressed in the Master 1.1 Patch Plan or deferred to Master 1.2.
