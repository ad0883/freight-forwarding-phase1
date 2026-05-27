# Phase 15 — Exception Engine + Manual Review Center

## Overview

Phase 15 implements the central operational exception layer that ties together workflow errors, validation issues, finance holds, document mismatches, container risks, Gmail suggestion conflicts, overdue tasks, and manual-review cases into one controlled review center.

## Architecture

```
Detection Sources → Exception Engine → Manual Review Center → Human Decision
                                    ↓
                              Audit Trail
```

### Key Principles
- Exception engine organizes and recommends
- Human users decide and act
- All decisions are audited
- No autonomous writes or external actions

## Models

| Table | Purpose |
|-------|---------|
| `exception_cases` | Core exception records with lifecycle |
| `exception_case_links` | Links to related entities (shipments, documents, etc.) |
| `exception_case_comments` | Discussion thread per exception |
| `exception_case_assignments` | Assignment history |
| `exception_case_status_history` | Append-only status audit trail |
| `exception_case_escalations` | Escalation records |
| `exception_case_sla_policies` | Configurable SLA targets |
| `exception_case_watchers` | Notification subscribers |

## Exception Lifecycle

```
open → acknowledged → in_review → resolved
                   ↘ escalated → resolved
                   ↘ waiting_on_* → resolved
                   ↘ dismissed
resolved/dismissed → reopened → (cycle)
```

## Detection Sources

| Source | Creates exceptions for |
|--------|----------------------|
| Validation Issues | Critical/blocking open issues |
| Document Mismatches | Critical mismatches, low confidence |
| Finance Holds | Active credit holds |
| Finance Risks | Open risk records |
| Workflow Logs | Blocked transitions, manual review required |
| Container Risks | Overdue empty returns |
| Gmail Suggestions | Low confidence, manual review status |
| Overdue Tasks | Critical/warning priority overdue tasks |

### Dedupe Policy
- Each detection source generates a stable `dedupe_key`
- Only one active exception per dedupe_key
- Repeated detection runs update `last_seen_at` without creating duplicates
- Resolved/dismissed cases are not duplicated unless the issue reappears

## APIs

### Exception Management
- `GET /api/exceptions` — List with filters
- `POST /api/exceptions` — Create manually
- `GET /api/exceptions/summary` — Dashboard summary
- `GET /api/exceptions/manual-review` — Review queue
- `GET /api/exceptions/my-queue` — My assigned items
- `POST /api/exceptions/run-detection` — Trigger detection scan

### Exception Actions
- `POST /api/exceptions/{id}/acknowledge`
- `POST /api/exceptions/{id}/assign`
- `POST /api/exceptions/{id}/resolve`
- `POST /api/exceptions/{id}/dismiss`
- `POST /api/exceptions/{id}/reopen`
- `POST /api/exceptions/{id}/escalate`
- `POST /api/exceptions/{id}/comments`
- `POST /api/exceptions/{id}/links`

### SLA Policies
- `GET /api/exceptions/sla-policies`
- `PATCH /api/exceptions/sla-policies/{id}`

### Shipment Integration
- `GET /api/shipments/{id}/exceptions`
- `GET /api/shipments/{id}/manual-review`

## Permissions

| Role | Capabilities |
|------|-------------|
| ADMIN | All actions, SLA policy edit, assign, dismiss, escalate |
| STAFF | View, acknowledge, comment, resolve, run detection |
| VIEW_ONLY | Read-only summary/list/detail |

## SLA Defaults

| Severity/Priority | Response | Resolution |
|-------------------|----------|------------|
| Critical / P0 | 30 min | 4 hours |
| High / P1 | 1 hour | 8 hours |
| Medium / P2 | 4 hours | 24 hours |
| Low / P3 | 8 hours | 48 hours |
| Info / P4 | 24 hours | 7 days |

## Audit & Security

- All lifecycle actions create audit log entries
- Metadata is sanitized (no passwords, tokens, secrets)
- Status history is append-only
- AI assistant can read exceptions but cannot mutate them

## How Phase 15 Prepares Phase 16

Phase 15 creates the organized exception layer that Phase 16 (Approval Engine + HOD Governance) will build upon:
- Exceptions are classified and prioritized
- Assignment and escalation workflows are established
- Audit trail is comprehensive
- Phase 16 will add formal approval chains and HOD sign-off on top of this foundation
