# Phase 18 — Exporter / Importer Portal

## Overview

Customer-scoped portal for exporters/importers to securely view and collaborate on their own shipments without seeing internal freight-forwarder operations.

## Architecture

```
Internal FF System ←→ Portal Access Layer ←→ Customer Portal UI
                          ↓
                   Visibility Filter (anti-leak)
```

## Models (9 tables)

| Table | Purpose |
|-------|---------|
| `portal_accounts` | External user accounts linked to parties |
| `portal_party_links` | Account-to-party relationships |
| `portal_shipment_access` | Explicit shipment access grants |
| `portal_document_access` | Document visibility controls |
| `portal_requests` | Customer queries/requests |
| `portal_request_comments` | Request discussion (with visibility flag) |
| `portal_notifications` | Customer-safe notifications |
| `portal_activity_logs` | Portal usage audit |
| `portal_preferences` | User preferences |

## Security Boundaries

Portal CANNOT see:
- Internal cost/margin/P&L
- Vendor payables
- Gmail cache/tokens
- Audit logs
- Bot governance internals
- Approval policy internals
- Other customers' shipments
- Internal staff notes

Portal CAN see:
- Assigned shipments (code, status, milestones, ETA/ETD)
- Customer-visible documents
- Customer receivable invoices (if enabled)
- Own requests and their status
- Customer-safe notifications

## Access Control

- Shipment access is explicit (granted by ADMIN)
- Party-based access derives from portal_account.party_id
- Document visibility requires `visible_to_customer = true`
- Internal comments have `visible_to_customer = false`

## Permissions

| Role | Access |
|------|--------|
| ADMIN | Full portal management, grant/revoke access |
| Portal User | View assigned shipments, raise requests, comment |
| Internal STAFF | Cannot be portal users (separate concerns) |
