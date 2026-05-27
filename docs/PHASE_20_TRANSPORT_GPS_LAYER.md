# Phase 20 — Transport + GPS Layer

## Overview

Phase 20 adds the transport coordination and GPS/vehicle movement layer to the Freight Forwarding system. This enables tracking of inland movement, transporter assignment, pickup/delivery jobs, vehicle details, driver details, container movement, location updates, trip milestones, delays, POD/empty return coordination, and transport exceptions.

## Key Features

- **Transport Job Lifecycle**: Create, assign, track, and close transport jobs linked to shipments
- **Transporter Assignment**: Link transport jobs to transporter parties
- **Vehicle & Driver Capture**: Register vehicles and drivers with validity tracking
- **Pickup/Delivery Milestones**: Auto-seeded milestone templates per job type
- **Container Movement Tracking**: Link containers to transport jobs with movement roles
- **Manual GPS/Location Updates**: Record location updates from manual/driver call/transporter sources
- **POD/Delivery Proof Tracking**: Upload and track transport documents (LR, POD, gate pass, etc.)
- **Empty Return Coordination**: Track empty container return status and milestones
- **Transport Exceptions**: Create and resolve transport-specific exceptions (delays, breakdowns, etc.)
- **Portal-Safe Visibility**: Customer-safe transport summary hiding internal cost/driver details

## Non-Goals (Phase 20)

- Live GPS provider API integration (Phase 21)
- SIM/device tracking integration
- FASTag / E-way bill integration
- Map provider billing
- Automatic route optimization
- Driver mobile app
- WhatsApp/SMS driver bot
- External transporter portal
- Predictive ETA engine

## Database Tables

| Table | Purpose |
|-------|---------|
| `transport_jobs` | Main transport job records |
| `transport_job_containers` | Container-to-job linkage |
| `transport_vehicles` | Vehicle registry |
| `transport_drivers` | Driver registry |
| `transport_milestones` | Job milestone tracking |
| `transport_location_updates` | Manual/GPS location records |
| `transport_documents` | Transport document references |
| `transport_exceptions` | Transport-specific exceptions |
| `transport_activity_logs` | Activity audit trail |
| `transport_charge_refs` | Links to finance/charges module |

## API Endpoints

### Transport Jobs
- `GET /api/transport` — List transport jobs
- `POST /api/transport` — Create transport job
- `GET /api/transport/summary` — Transport dashboard summary
- `GET /api/transport/{job_id}` — Get job detail
- `PATCH /api/transport/{job_id}` — Update job
- `POST /api/transport/{job_id}/assign-transporter` — Assign transporter
- `POST /api/transport/{job_id}/assign-vehicle-driver` — Assign vehicle/driver
- `POST /api/transport/{job_id}/status` — Update status
- `POST /api/transport/{job_id}/close` — Close job

### Milestones
- `GET /api/transport/{job_id}/milestones` — List milestones
- `POST /api/transport/milestones/{milestone_id}/complete` — Complete milestone

### Locations
- `GET /api/transport/{job_id}/locations` — List location updates
- `POST /api/transport/{job_id}/locations` — Add location update

### Vehicles & Drivers
- `GET /api/transport/vehicles` — List vehicles
- `POST /api/transport/vehicles` — Create vehicle
- `PATCH /api/transport/vehicles/{vehicle_id}` — Update vehicle
- `GET /api/transport/drivers` — List drivers
- `POST /api/transport/drivers` — Create driver
- `PATCH /api/transport/drivers/{driver_id}` — Update driver

### Documents
- `GET /api/transport/{job_id}/documents` — List transport documents
- `POST /api/transport/{job_id}/documents` — Create transport document

### Exceptions
- `GET /api/transport/exceptions` — List all transport exceptions
- `POST /api/transport/exceptions` — Create exception
- `GET /api/transport/exceptions/{exception_id}` — Get exception detail
- `POST /api/transport/exceptions/{exception_id}/resolve` — Resolve exception

### Shipment Integration
- `GET /api/shipments/{shipment_id}/transport` — List shipment transport jobs
- `POST /api/shipments/{shipment_id}/transport` — Create job for shipment
- `GET /api/shipments/{shipment_id}/transport-summary` — Shipment transport summary

### Portal (Customer-Safe)
- `GET /api/portal/shipments/{shipment_id}/transport` — Customer-safe transport view

## Job Types

| Type | Description |
|------|-------------|
| `export_pickup` | Factory/warehouse pickup for export |
| `import_delivery` | Port to consignee delivery |
| `empty_container_pickup` | Empty container from yard |
| `empty_container_return` | Return empty to yard |
| `factory_stuffing` | Stuffing at factory |
| `port_gate_in` | Transport to port gate-in |
| `port_gate_out` | Transport from port gate-out |
| `domestic_transfer` | General domestic movement |

## Status Flow

```
planned → transporter_assigned → vehicle_assigned → driver_assigned →
pickup_scheduled → at_pickup → picked_up → in_transit →
at_gate → gated_in/gated_out → at_delivery → delivered →
empty_return_pending → empty_returned → closed
```

Special statuses: `delayed`, `on_hold`, `cancelled`

## Security

- Driver personal data (phone, license) hidden from portal users
- Internal transporter cost/margin not exposed to customers
- No automatic delivery confirmation without human evidence
- No automatic empty return closure without verification
- Transport layer coordinates and records; humans verify milestones

## Frontend

- Transport page at `/transport` with tabs: Jobs, Exceptions, Vehicles, Drivers
- Dashboard summary cards for active jobs, in-transit, delayed, empty return pending
- Sidebar navigation entry under Operations
