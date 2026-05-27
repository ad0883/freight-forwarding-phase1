# Phase 19 — CHA / Customs Coordination

## Overview

Customs coordination layer that tracks customs cases, CHA assignment, document readiness, filing milestones, queries, references, duty/payment records, and OOC/LEO status. Coordinates without directly filing customs entries.

## Models (10 tables)

| Table | Purpose |
|-------|---------|
| `customs_cases` | Core customs case per shipment |
| `customs_case_milestones` | Filing lifecycle milestones |
| `customs_checklist_items` | Pre-filing checklist |
| `customs_document_requirements` | Required documents per case |
| `customs_queries` | Customs/CHA queries |
| `customs_query_comments` | Query discussion with visibility |
| `customs_party_assignments` | CHA and party roles |
| `customs_duty_records` | Duty assessment/payment tracking |
| `customs_reference_numbers` | SB/BOE/OOC/LEO references |
| `customs_activity_logs` | Audit trail |

## Customs Case Lifecycle

```
not_started → documents_pending → ready_for_cha → sent_to_cha → filed
→ assessment_pending → duty_pending → examination_pending
→ ooc_received (import) / leo_received (export) → cleared → closed
```

## Auto-Seeded Templates

**Export milestones:** documents_received → cha_assigned → shipping_bill_filed → leo_received → closed

**Import milestones:** pre_alert_received → cha_assigned → boe_filed → duty_paid → ooc_received → closed

**Export documents:** Commercial Invoice, Packing List, BL/AWB, Shipping Bill, IEC, GST, AD Code

**Import documents:** Commercial Invoice, Packing List, BL/AWB, Bill of Entry, IEC, GST, Insurance

## Security

- No direct ICEGATE/customs portal filing
- No government credentials stored
- Portal customers see only customer-safe customs status
- Internal CHA notes hidden from portal
- Duty records are reference-only (no payment gateway)
