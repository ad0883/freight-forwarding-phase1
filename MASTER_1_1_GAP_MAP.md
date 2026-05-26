# Master 1.1 Gap Map

Date: 2026-05-26

Scope: Phase 8 architecture alignment map. This document records current capability against the Master 1.1 target and does not implement later-phase features.

| Master 1.1 Module | Current Status | Existing App Feature | Gap | Target Phase |
| --- | --- | --- | --- | --- |
| Organizations / users / roles / permissions | Partially built | Global users, ADMIN/STAFF/VIEW_ONLY, Phase 8 default organization foundation | No memberships, tenant switching, org-scoped roles, or strict tenant isolation | Phase 8 foundation, later governance phase |
| Parties / contacts | Partially built | Parties with lifecycle controls and references from shipments/charges/follow-ups | No rich contact model, portal identity, or relationship graph | Later party/portal phase |
| Shipments | Built | Export/import shipment CRUD, workflow status, archive/restore | No organization-scoped shipment ownership yet | Existing plus future tenancy phase |
| Shipment graph | Partially built | Shipment links to documents, tasks, BL, demurrage, charges, follow-ups, alerts | No generalized graph/event model | Phase 9+ |
| Containers | Partially built | Shipment-level container number/type | No multi-container entity or lifecycle | Later container phase |
| Container events | Missing | None | No milestone/event stream | Phase 9+ |
| Documents | Built | Default checklists, status, URL, notes | No native upload/storage | Later document phase |
| Document versions | Missing | None | No version table/history | Later document phase |
| OCR extractions | Missing | None | No OCR pipeline | Later AI/document phase |
| Charges | Built | Payable/receivable charges, cancelled exclusions, P&L | No invoice/tax/accounting integration | Existing plus finance phase |
| Invoices | Missing | Charge invoice number only | No invoice entity or PDF generation | Later finance phase |
| Payments | Missing | Paid/received charge statuses | No payment records/gateway reconciliation | Later finance phase |
| Credit control | Partially built | Pending receivable report | No credit limits, aging workflows, or dunning | Later finance phase |
| FX rates | Missing | Mixed-currency flag only | No conversion or rate table | Later finance phase |
| Tasks | Built | Manual/auto tasks, cancel/restore/delete guardrails | No SLA engine | Existing plus Phase 9+ |
| Events | Planned | Phase 8 placeholder event service | No persistent event table or emitters | Phase 9 |
| Workflow states | Partially built | Shipment workflow status and side effects | No formal transition engine | Phase 9+ |
| Exceptions | Missing | Alerts/notifications only | No exception entity/escalation workflow | Later operations phase |
| Approvals | Missing | BL approval dates only | No approval engine | Later governance phase |
| Emails | Built | Gmail read-only connection, cache, suggestions | No send/modify Gmail behavior by design | Existing plus later automation phase |
| Email threads | Partially built | Cached Gmail thread id | No thread timeline UI/model | Later email phase |
| Email attachments | Partially built | Attachment presence flag | No attachment ingestion/storage | Later email/document phase |
| Coordination logs | Partially built | Follow-up logs | No generalized coordination timeline | Later operations phase |
| Customs status | Missing | CHA party type only | No customs status model | Later customs phase |
| Transport movements | Missing | None | No transport movement model | Later transport phase |
| Tracking events | Missing | None | No adapter/event ingestion | Later tracking phase |
| Notifications | Built | Internal notifications, rules, daily summary, unread state | No push/email/SMS delivery | Existing plus delivery phase |
| Audit logs | Built | Write/admin/export audit logs | No org-scoped audit filtering | Future governance phase |
| Bot actions | Planned | Read-only AI assistant, Phase 8 event placeholders | No autonomous writes by design | Later bot phase |
| Bot performance | Missing | AI interaction logs only | No evaluation metrics | Later AI operations phase |
| Rule definitions | Planned | Notification rules, Phase 8 rule base placeholder | No general rule engine | Phase 9+ |
| SLA tracker | Missing | Due dates and overdue notifications | No SLA policy model | Later operations phase |
| Exporter portal | Missing | None | No external portal or scoped access | Later portal phase |
| Importer portal | Missing | None | No external portal or scoped access | Later portal phase |
| CHA/customs layer | Missing | CHA party records only | No customs workflow portal | Later customs phase |
| Transport/GPS layer | Missing | None | No GPS/driver tracking | Later transport phase |
| Control tower | Partially built | Dashboard, reports, alerts, notifications | No multi-tenant control tower or event cockpit | Later control tower phase |
| Predictive intelligence | Missing | Read-only fallback/LLM summaries | No predictive models | Later intelligence phase |

## Phase 8 Notes

- The default organization is a compatibility foundation, not full tenant isolation.
- Future schema changes should use Alembic rather than startup-only compatibility patches.
- Event, validation, and rule engine placeholders are intentionally not wired into production behavior yet.
