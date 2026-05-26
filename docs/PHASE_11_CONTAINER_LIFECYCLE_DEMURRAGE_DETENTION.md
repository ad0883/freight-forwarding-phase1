# Phase 11: Container Lifecycle + Demurrage / Detention Separation

Phase 11 elevates containers to first-class operational entities, supports
multi-container shipments, and separates demurrage from detention. Estimates
are advisory and never auto-create payable/receivable charges.

## Architecture

```
Shipment
  └── Container (1..N)
         ├── ContainerEvent (append-only)
         ├── ContainerDemurrageRecord (current snapshot)
         └── ContainerDetentionRecord (current snapshot)
DemurrageDetentionRule  (free-day / rate defaults)
```

Container changes flow through:

```
user / system action
  -> container_service (create / update / transition / event)
     -> Phase 9 OperationalEvent (container.created/updated/event_added/...)
     -> Phase 9 ValidationIssue when broken state detected
     -> AuditLog
     -> demurrage_detention_service (refresh exposure)
       -> upsert ContainerDemurrageRecord / ContainerDetentionRecord
       -> Phase 7 Notification (deduped) for risk
```

## State chains

Export: `CONTAINER_PLANNED -> EMPTY_RELEASED -> EMPTY_PICKUP_SCHEDULED ->
EMPTY_PICKED_UP -> ARRIVED_AT_FACTORY -> STUFFING_STARTED ->
STUFFING_COMPLETED -> SEALED -> DISPATCHED_TO_PORT -> GATE_IN ->
LOADED_ON_VESSEL -> DEPARTED -> CLOSED`.

Import: `EXPECTED_ON_VESSEL -> ARRIVED_AT_PORT -> DISCHARGED -> DO_RECEIVED ->
CLEARED_FOR_DELIVERY -> GATE_OUT -> OUT_FOR_DELIVERY -> DELIVERED ->
DE_STUFFED_IF_APPLICABLE -> EMPTY_RETURN_PENDING -> EMPTY_RETURNED -> CLOSED`.

`POST /api/containers/{id}/transition` accepts any of these statuses, records
a corresponding `ContainerEvent`, and pushes the matching date field if it is
unset.

## Demurrage vs detention

- Demurrage tracks port/CFS dwell. Window = `discharge_date or expected_arrival_date`
  to `delivery_date or gate_out_date`.
- Detention tracks usage outside terminal. Window =
  `delivery_date or gate_out_date` to `empty_return_date`.
- Each engine reads `demurrage_free_days` / `detention_free_days` overrides on
  the container, falls back to a `DemurrageDetentionRule`, then to a global
  default (7 days, INR 50/day).
- `chargeable_days = max(0, days_used - free_days)`.
- `estimated_amount = chargeable_days * rate_per_day`.
- Status is `running` when the window is still open and chargeable, `estimated`
  otherwise, `not_applicable` when the window has not started.

The two engines never share state. Demurrage and detention amounts are
recorded in separate tables and never auto-converted into Phase 3 charges.

## APIs

| Method | Path | Roles | Purpose |
| --- | --- | --- | --- |
| GET | `/api/containers` | any auth | list containers (filter by `shipment_id`) |
| GET | `/api/containers/statuses` | any auth | canonical status catalog |
| GET | `/api/containers/risk` | any auth | recent containers with non-zero risk |
| POST | `/api/containers/backfill-from-shipments` | ADMIN | dry-run (default) or apply legacy backfill |
| GET | `/api/containers/{id}` | any auth | detail incl. exposure |
| PATCH | `/api/containers/{id}` | ADMIN, STAFF | update fields |
| DELETE | `/api/containers/{id}` | ADMIN | soft-delete (preserves events) |
| GET | `/api/containers/{id}/events` | any auth | append-only event log |
| POST | `/api/containers/{id}/events` | ADMIN, STAFF | record event |
| POST | `/api/containers/{id}/transition` | ADMIN, STAFF | move to new status |
| GET | `/api/containers/{id}/exposure` | any auth | refresh + return exposure |
| POST | `/api/containers/{id}/refresh-exposure` | ADMIN, STAFF | refresh exposure (audited) |
| GET | `/api/shipments/{id}/containers` | any auth | shipment's containers w/ exposure |
| POST | `/api/shipments/{id}/containers` | ADMIN, STAFF | add container to shipment |
| GET | `/api/shipments/{id}/container-exposure` | any auth | aggregated shipment exposure |
| POST | `/api/shipments/{id}/refresh-container-exposure` | ADMIN, STAFF | refresh shipment-wide exposure |

Permissions:
- ADMIN: all routes including hard delete (replaced by soft-delete when events exist).
- STAFF: create, update, transition, refresh, add events.
- VIEW_ONLY: read state and timeline.

## Validation rules (non-blocking by default)

- `container_number_format_warning`
- `container_duplicate_active_warning`
- `container_loaded_before_gate_in_warning`
- `import_container_delivered_before_do_warning`
- `empty_return_before_delivery_warning`
- `gate_in_after_cutoff_warning`
- `partial_delivery_supported_info`

Each broken state writes/refreshes a Phase 9 `ValidationIssue` scoped to
`entity_type=container, entity_id=<container_id>`.

## Notifications

Risk notifications use deterministic dedupe keys:

- `container_demurrage_running:{container_id}`
- `container_detention_running:{container_id}`
- `container_empty_return_overdue:{container_id}`
- `container_demurrage_warning:{container_id}:{date}`
- `container_detention_warning:{container_id}:{date}`
- `container_lifecycle_broken:{container_id}:{rule_key}`

Refreshing exposure repeatedly does not duplicate active notifications.

## Backfill

`POST /api/containers/backfill-from-shipments` (ADMIN) accepts
`{ "dry_run": bool }`. Dry-run returns candidate shipments parsed from the
legacy `shipment.container_no` field and their notes. Apply mode creates
containers via the standard service so events, audit logs, and validation
checks all run. Existing container records are never overwritten.

## Future Phase 12

Phase 12 will introduce transport, GPS, and external tracking adapters that
emit `ContainerEvent` rows from third-party data. The Phase 11 container model
already supports the `source` enum for `tracking`, `transport`, `line`, and
`cha`, so Phase 12 plugs into the same append-only event stream.
