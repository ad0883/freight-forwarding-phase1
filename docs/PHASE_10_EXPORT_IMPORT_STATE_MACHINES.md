# Phase 10: Strong Export / Import State Machines

Phase 10 adds controlled lifecycle states to export and import shipments. State
transitions are validated, event-logged, auditable, and capable of generating
manual-review issues without breaking existing shipment behaviour.

## Architecture

```
User action -> /api/workflow/.../transition
            -> get_or_infer_state()
            -> get_transition_definition()
            -> permission + sensitivity checks
            -> Phase 9 OperationalEvent (workflow.transition_requested)
            -> apply | block | manual_review
            -> WorkflowTransitionLog row
            -> AuditLog entry
            -> Notification (only for manual review / critical)
            -> Shipment.workflow_state update if applied
```

Phase 10 leaves existing shipment status fields (`status`, `workflow_status`)
unchanged. The `workflow_state` column is additive and nullable.

## Tables

- `workflow_state_definitions` - canonical state catalog per flow.
- `workflow_transition_definitions` - allowed transitions and sensitivity flags.
- `workflow_transition_logs` - one row per transition attempt.

Plus shipment columns added by Phase 10:

- `workflow_state` (nullable, indexed)
- `workflow_state_updated_at` (nullable)
- `workflow_state_reason` (nullable)
- `manual_review_required` (boolean, default false)
- `manual_review_reason` (nullable)

## States

Phase 10 seeds the canonical export and import state lists from the plan.
Branch states (`CUSTOMS_QUERY_IF_ANY`, `EXAMINATION_IF_ANY`,
`BL_CORRECTION_IF_ANY`) are excluded from the linear chain and reachable via
explicit branch transitions only. Sensitive states (`BL_APPROVED`,
`FINAL_BL_RECEIVED`, `PAYMENT_RECEIVED`, `FREIGHT_PAID`, `IMPORT_COMPLETED`,
`EXPORT_COMPLETED`) require ADMIN role plus explicit `confirm_sensitive=true`.

## APIs

| Method | Path | Roles | Purpose |
| --- | --- | --- | --- |
| GET | `/api/workflow/states` | any auth | list state definitions |
| GET | `/api/workflow/transitions` | any auth | list transition definitions |
| GET | `/api/workflow/shipments/{id}/state` | any auth | current or inferred state |
| GET | `/api/workflow/shipments/{id}/available-transitions` | any auth | next transitions with permission flags |
| POST | `/api/workflow/shipments/{id}/transition` | ADMIN, STAFF | request a transition |
| GET | `/api/workflow/shipments/{id}/timeline` | any auth | transition history |

The transition response shape:

```json
{
  "shipment_id": 1,
  "flow_type": "export",
  "from_state": "BL_DRAFT_PENDING",
  "to_state": "BL_DRAFT_RECEIVED",
  "status": "applied",
  "manual_review_required": false,
  "validation_status": "passed",
  "log_id": 42,
  "event_id": 99
}
```

When blocked or routed to manual review:

```json
{
  "status": "blocked",
  "detail": "No active transition is defined from CONTAINER_PLANNED to EXPORT_COMPLETED.",
  "manual_review_required": false,
  "validation_status": "failed",
  "validation_issue_id": 17,
  "log_id": 43
}
```

## Permissions

- ADMIN: every workflow action.
- STAFF: non-sensitive transitions only. Sensitive transitions return 403.
- VIEW_ONLY: read state and timeline. Transitions return 403.
- Archived shipments are blocked outright via
  `workflow_archived_shipment_transition_block`.

## Validation / rule integration

Phase 10 adds rule definitions to the Phase 9 rule engine:

- `workflow_invalid_transition`
- `workflow_missing_required_state_data`
- `workflow_sensitive_transition_requires_confirmation`
- `workflow_completed_shipment_transition_warning`
- `workflow_archived_shipment_transition_block`
- `workflow_import_do_without_free_days_warning`
- `workflow_export_bl_approval_without_draft_warning`
- `workflow_payment_state_without_charge_warning`

All ship as non-blocking by default. Critical issues create deduped
notifications with `dedupe_key=workflow_manual_review:{rule_key}:shipment:{id}`.

## Frontend

- Shipment detail adds a `Workflow` tab with current state, available
  transitions, and the workflow timeline. Existing tabs stay intact.
- Sensitive transitions surface a confirmation dialog before applying.
- Dashboard adds a `Workflow Control` widget summarising flagged shipments,
  recent blocked/manual-review transitions, and shipments with no workflow
  state. The widget fails independently and does not break the dashboard.

## How Phase 10 prepares Phase 11 container lifecycle

Phase 11 will introduce container-level state (gate-in, gate-out, return,
detention). The Phase 10 model already separates definitions, transitions, and
logs by flow type, leaving room to add a `container` flow without disturbing
existing shipment logic. The `is_blocking` flag on rules and the sensitivity
contract on transitions also feed Phase 11's stricter approval engine.
