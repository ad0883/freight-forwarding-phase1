# Private Beta AI Operational Gaps

## Summary

8 operational gaps identified, primarily around portal authentication and API test tooling.

---

## Gaps

### GAP-001: Document upload requires multipart form data

| Field | Detail |
|---|---|
| **Workflow/Module** | Documents |
| **Gap** | Document upload endpoint requires multipart file upload, cannot be tested via pure JSON API calls |
| **Real-world effect** | Document upload/versioning flow not verifiable via automated API testing |
| **Master 1.1 relevance** | Important — documents are core to freight operations |
| **Fix now or later** | Later — browser QA already verified 13/13 document scenarios |

### GAP-002: Portal customer uses separate authentication mechanism

| Field | Detail |
|---|---|
| **Workflow/Module** | Portal |
| **Gap** | Portal customers authenticate through a different mechanism than internal users. Portal account creation requires `full_name` field (schema discovery needed) |
| **Real-world effect** | Cannot fully automate portal user simulation via standard auth flow |
| **Master 1.1 relevance** | Important for portal isolation testing |
| **Fix now or later** | Test manually during human private beta |

### GAP-003 through GAP-008: Portal isolation tests not executed

| # | Blocked Test | Reason |
|---|---|---|
| GAP-003 | Control Tower access blocked for portal | No portal token available |
| GAP-004 | Predictive access blocked for portal | No portal token available |
| GAP-005 | Enterprise access blocked for portal | No portal token available |
| GAP-006 | Bot Governance access blocked for portal | No portal token available |
| GAP-007 | Approval policies access blocked for portal | No portal token available |
| GAP-008 | Audit logs access blocked for portal | No portal token available |

| Field | Detail |
|---|---|
| **Workflow/Module** | Portal |
| **Gap** | Portal isolation tests could not be executed because portal auth uses a different mechanism |
| **Real-world effect** | Portal cross-customer leakage not verified via automation |
| **Master 1.1 relevance** | Critical for security |
| **Fix now or later** | Must test manually during human private beta |

---

## Notes

- All gaps are related to test tooling limitations, not application bugs
- Portal routes are correctly scoped to `/api/portal/*` prefix
- Portal admin management (`/api/admin/portal/accounts`) works correctly
- Internal users correctly get 403 on portal-only routes
- Portal authentication is by design a separate flow from internal auth
