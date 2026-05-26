# Phase 9: Event System + Validation / Rule Engine Foundation

Phase 9 turns the Phase 8 placeholders into a working operational-brain layer:

- Operational events are recorded for representative business actions.
- Validation rules run deterministic, read-only checks against each event.
- Failed checks produce reviewable validation issues.
- Critical issues create deduped internal notifications.

The full Master 1.1 path remains the goal. Phase 9 only delivers the foundation.

## Architecture

```
Operational action -> record_operational_event() -> OperationalEvent row
                                              |
                                              v
                         run_validation_for_event() -> RuleResult[]
                                              |
                                              v
                  create_validation_issues_from_results() -> ValidationIssue rows
                                              |
                                              v
                  create_critical_notifications_for_issues() -> Notification rows
```

Phase 9 stays beside the existing flows. It does not replace shipment, task,
charge, document, BL, or Gmail behaviour.

## Models

### OperationalEvent (`operational_events`)

| field | purpose |
| --- | --- |
| event_type | shipment.created, task.cancelled, etc. |
| entity_type / entity_id / entity_label | scope of the event |
| shipment_id | optional shipment association |
| actor_user_id / actor_name / actor_email / actor_role | safe actor capture |
| source | user, system, gmail, ai, scheduler, workflow, finance, notification |
| correlation_id / request_id | request-trace metadata |
| previous_state_json / new_state_json / metadata_json | sanitized snapshots |
| validation_status | not_checked, passed, warning, failed, manual_review_required |

### RuleDefinition (`rule_definitions`)

Holds rule metadata. Each entry has a unique `rule_key`. Phase 9 seeds default
rules on startup. Rule editing is admin-only and `rule_key` cannot be changed.

### ValidationIssue (`validation_issues`)

| field | purpose |
| --- | --- |
| event_id | event that produced the issue |
| rule_key | rule that flagged the issue |
| entity_type / entity_id / entity_label | scope of the issue |
| shipment_id | optional shipment association |
| severity | info, warning, critical |
| status | open, acknowledged, resolved, dismissed |
| message / recommended_action | human readable guidance |
| metadata_json | non-sensitive extra data |

## APIs

| Method | Path | Roles | Purpose |
| --- | --- | --- | --- |
| GET | `/api/events` | ADMIN, STAFF | list operational events with filters |
| GET | `/api/events/{id}` | ADMIN, STAFF | event detail |
| GET | `/api/validation-issues` | ADMIN, STAFF | filtered issue list |
| GET | `/api/validation-issues/{id}` | ADMIN, STAFF | issue detail |
| PATCH | `/api/validation-issues/{id}/acknowledge` | ADMIN, STAFF | acknowledge issue |
| PATCH | `/api/validation-issues/{id}/resolve` | ADMIN, STAFF | resolve issue |
| PATCH | `/api/validation-issues/{id}/dismiss` | ADMIN, STAFF | dismiss issue |
| GET | `/api/rules` | ADMIN, STAFF | rule list |
| PATCH | `/api/rules/{id}` | ADMIN | rule update |

## Default rules

Shipment: `shipment_missing_required_fields`, `shipment_invalid_type`,
`shipment_archived_write_warning`, `shipment_duplicate_code`.

Task: `task_missing_title`, `task_due_date_in_past_warning`,
`task_cancelled_write_warning`.

Charge: `charge_negative_amount`, `charge_direction_status_mismatch`,
`charge_cancelled_write_warning`, `charge_missing_currency`.

Document: `document_missing_type`, `document_status_invalid`,
`document_missing_url_warning`.

BL: `bl_final_without_draft_warning`, `bl_approved_without_draft_warning`,
`bl_missing_number_warning`.

Gmail: `gmail_suggestion_missing_shipment`, `gmail_suggestion_low_confidence`.

Organization / auth: `user_missing_organization_warning`.

All Phase 9 rules ship with `is_blocking=false` and `is_enabled=true`. The
`is_blocking` flag captures intent for Phase 10 - Phase 9 does not enforce
blocking anywhere.

## Notification integration

When a validation issue is created with `severity=critical`, Phase 9 creates an
internal notification with:

- `category=system`
- `priority=critical`
- `title=Manual review required`
- `action_url=/validation-issues`
- `dedupe_key=validation_issue:{rule_key}:{entity_type}:{entity_id}`

Repeated runs do not duplicate notifications for the same unchanged issue.

## Safety limits

- Recording an event must never break the original business action.
- Event metadata is sanitized via an allowlist style (sensitive keys are
  redacted, large strings truncated, complex objects coerced to strings).
- Phase 9 cannot mutate shipments, tasks, charges, documents, BL records,
  parties, users, Gmail records, or external systems.
- Rule editing is admin-only. STAFF can read but not change rule state.
- Validation issues are reviewable signals. The user retains full control of
  status transitions.

## Future Phase 10 transition

Phase 10 will introduce real export/import state machines, container lifecycle
events, and rule blocking enforcement. Phase 9 stays compatible: events,
validation issues, and rule keys remain stable. New state-machine events plug
into the same emitter pattern.
