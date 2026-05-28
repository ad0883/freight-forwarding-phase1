# Phase 21 — Tracking Adapters

## Overview

Phase 21 adds a safe adapter framework for external tracking data sources. It enables ingestion, normalization, validation, and display of tracking data from shipping lines, vessel schedules, terminal/CFS/ICD portals, transport GPS providers, and manual tracking sources.

**Core principle: External tracking data is evidence, not truth. Humans approve important state changes.**

## Key Features

- **Tracking Provider Registry**: Manual and mock providers seeded by default; real providers can be added later
- **Adapter Framework**: Pluggable adapter architecture for different tracking sources
- **Watch Items**: Track containers, BLs, bookings, vessels, transport jobs by identifier
- **Tracking Observations**: Normalized tracking events with confidence scoring
- **Status Normalization**: Maps raw external statuses (Gate In, LOADED, etc.) to canonical internal statuses
- **Suggested Updates**: Creates reviewable suggestions for state changes — never auto-applies
- **Tracking Mismatches**: Detects conflicts between external tracking and internal state
- **Sync Runs**: Auditable sync execution with metrics
- **Portal-Safe Visibility**: Customer-safe tracking summary hiding provider/internal details

## Non-Goals (Phase 21)

- Paid AIS provider integration
- Hardcoded shipping line credentials
- Scraping private portals
- Automatic state mutation (shipment/container/transport/customs)
- Automatic ETA overwrite
- Predictive ETA model
- Full world map visualization

## Database Tables

| Table | Purpose |
|-------|---------|
| `tracking_providers` | Provider registry (manual, mock, real) |
| `tracking_adapter_configs` | Provider configuration (no plaintext secrets) |
| `tracking_watch_items` | Items being tracked |
| `tracking_observations` | Raw + normalized tracking data |
| `tracking_events` | Parsed tracking events |
| `tracking_suggested_updates` | Reviewable state change suggestions |
| `tracking_mismatches` | Conflicts between external and internal data |
| `tracking_sync_runs` | Sync execution audit trail |
| `tracking_activity_logs` | Activity log |

## API Endpoints

### Summary & Providers
- `GET /api/tracking/summary` — Dashboard metrics
- `GET /api/tracking/providers` — List providers
- `POST /api/tracking/providers` — Create provider (ADMIN)
- `PATCH /api/tracking/providers/{id}` — Update provider (ADMIN)
- `POST /api/tracking/providers/{id}/configs` — Create adapter config (ADMIN)

### Watch Items
- `GET /api/tracking/watch-items` — List watch items
- `POST /api/tracking/watch-items` — Create watch item
- `POST /api/tracking/watch-items/{id}/pause` — Pause
- `POST /api/tracking/watch-items/{id}/resume` — Resume
- `POST /api/tracking/watch-items/{id}/complete` — Complete
- `POST /api/tracking/watch-items/{id}/run-sync` — Run sync for item

### Observations & Events
- `GET /api/tracking/observations` — List observations
- `POST /api/tracking/observations/manual` — Create manual observation
- `GET /api/tracking/events` — List tracking events

### Suggestions & Mismatches
- `GET /api/tracking/suggestions` — List suggestions
- `POST /api/tracking/suggestions/{id}/approve` — Approve
- `POST /api/tracking/suggestions/{id}/reject` — Reject
- `POST /api/tracking/suggestions/{id}/dismiss` — Dismiss
- `GET /api/tracking/mismatches` — List mismatches
- `POST /api/tracking/mismatches/{id}/resolve` — Resolve

### Sync
- `GET /api/tracking/sync-runs` — List sync runs
- `POST /api/tracking/run-sync` — Run tracking sync

### Shipment Integration
- `GET /api/shipments/{id}/tracking` — Shipment tracking observations
- `POST /api/shipments/{id}/tracking/watch-items` — Create watch for shipment
- `POST /api/shipments/{id}/tracking/run-sync` — Run sync for shipment

### Portal (Customer-Safe)
- `GET /api/portal/shipments/{id}/tracking` — Customer-safe tracking view

## Default Providers

| Key | Type | Description |
|-----|------|-------------|
| `manual_tracking` | manual | Human-entered tracking updates |
| `mock_shipping_line` | shipping_line | Simulated shipping line data |
| `mock_vessel_schedule` | vessel_schedule | Simulated vessel schedule |
| `mock_terminal` | terminal | Simulated terminal/CFS data |
| `mock_transport_gps` | transport_gps | Simulated GPS tracking |

## Status Normalization

External statuses are normalized to canonical internal forms:

| Raw Status | Normalized |
|-----------|-----------|
| Gate In, IN_GATE, Gated In | `gate_in` |
| Gate Out, Out Gate | `gate_out` |
| Loaded, Loaded on Vessel, On Board | `loaded_on_vessel` |
| Discharged, Unloaded | `discharged` |
| Departed, Vessel Departed, Sailed | `departed` |
| Arrived, Vessel Arrived, Berthed | `arrived` |
| Delivered, Cargo Delivered | `delivered` |
| Empty Returned | `empty_returned` |
| In Transit, On Rail, On Road | `in_transit` |

## Security

- Provider credentials stored as `secret_ref` only — never plaintext in DB
- Portal summary hides: provider details, confidence scores, raw status, metadata
- No automatic state mutation — all changes require human review
- Suggestions go through approve/reject/dismiss workflow
- High-risk suggestions can require formal approval (Phase 16 integration)
- Sync runs are auditable with metrics

## Frontend

- Tracking page at `/tracking` with tabs: Watch Items, Observations, Suggestions, Mismatches, Providers, Sync Runs
- Dashboard summary cards for active watches, observations, pending suggestions, mismatches
- Sidebar navigation entry under Operations
