# Phase 14 — Finance + Credit Control

Phase 14 strengthens the finance layer with structured invoice/payment
control, party credit profiles, credit holds, aging buckets, FX rate
snapshots, finance risk records, and advisory release controls. The
existing Phase 3 charges/P&L flow continues unchanged.

## Architecture

```
charges (Phase 3, untouched)
   └─ optional links ──▶ finance_invoice_lines ──▶ finance_invoices
                                                         │
                                                         ▼
                                                finance_payment_allocations
                                                         ▲
                                                         │
                                                  finance_payments

party_credit_profiles ──▶ credit_hold_records ──▶ release checks (advisory)

finance_aging_snapshots, fx_rate_snapshots, finance_risk_records, finance_adjustments
```

All operations create operational events and audit logs. Critical risks
fan out to notifications and validation issues with deduplication.

## Models (new)

| Table | Purpose |
| --- | --- |
| `finance_invoices` | Receivable/payable invoices with totals + status |
| `finance_invoice_lines` | Per-line breakdown, optionally linked to a charge |
| `finance_payments` | Internal payment receipts/vendor payments (no bank/gateway) |
| `finance_payment_allocations` | Allocates payments to invoices/charges/shipments |
| `party_credit_profiles` | Credit limit, credit days, hold preferences |
| `credit_hold_records` | Active/resolved credit holds (advisory) |
| `finance_aging_snapshots` | Cached aging buckets |
| `fx_rate_snapshots` | Manual FX rates (no live fetch) |
| `finance_risk_records` | Open finance risks with deduping |
| `finance_adjustments` | Waivers/discounts/write-offs (manual review) |

Migration: `phase14_finance_credit` (chains after `phase13_doc_intel`).

## Backend services

* `finance_invoice_service.py` — create/update/cancel/list invoices and recompute totals from allocations.
* `payment_service.py` — record payments, allocate to invoices/charges/shipments, prevent over-allocation, propagate to invoice paid/outstanding.
* `credit_control_service.py` — credit profiles, party outstanding, credit risk evaluation, hold create/refresh/resolve/waive.
* `finance_aging_service.py` — bucket calculation (not_due/0-30/31-60/61-90/90+) per party and overall.
* `fx_service.py` — FX rate snapshots and conversions; missing rates surface as risks.
* `release_control_service.py` — advisory release checks (`release_final_bl`, `release_do`, `dispatch_documents`, `mark_export_completed`, `mark_import_completed`, `extend_credit`).
* `finance_risk_service.py` — finance risk creation/resolution with notifications + validation issues.
* `finance_overview_service.py` — finance overview totals and shipment finance summary.

## API

Prefix `/api/finance` (see `app/api/routes/finance_control.py`).

Highlights:
* `GET /finance/overview` — KPIs for the finance dashboard.
* `POST /finance/invoices`, `POST /finance/invoices/from-charge/{id}`, `POST /finance/invoices/{id}/cancel`.
* `POST /finance/payments`, `POST /finance/payments/{id}/allocate`, `POST /finance/payments/{id}/cancel`.
* `GET /finance/credit-profiles`, `PATCH /finance/parties/{id}/credit-profile`.
* `GET /finance/holds`, `POST /finance/holds/{id}/resolve`, `POST /finance/holds/{id}/waive`.
* `GET /finance/aging`, `POST /finance/aging/snapshot`.
* `GET /finance/risks`, `POST /finance/risks/{id}/resolve`, `POST /finance/refresh-party/{id}`, `POST /finance/refresh-shipment/{id}`.
* `GET /finance/fx-rates`, `POST /finance/fx-rates`.

Shipment-scoped:
* `GET /shipments/{id}/finance-summary`
* `GET /shipments/{id}/release-checks`
* `POST /shipments/{id}/finance-refresh`

## Permissions

| Action | Roles |
| --- | --- |
| List / read finance data | Any authenticated role |
| Create/update invoices, payments, allocations, FX rates, snapshots, refresh risks, resolve holds | `ADMIN`, `STAFF` |
| Cancel invoice/payment, waive hold, manage credit profile | `ADMIN` only |
| `VIEW_ONLY` | Read-only access; cannot mutate |

## Credit-control logic

For each refresh per party (also called per shipment via `refresh_shipment_finance_risks`):

1. Compute receivable outstanding from open invoices.
2. Compute overdue amount (due-date in the past).
3. If `hold_on_limit_exceeded` and outstanding > limit → critical hold + risk.
4. Else if outstanding ≥ `warning_threshold_percent` of limit → warning risk only.
5. If `hold_on_overdue` and overdue > 0 → warning hold + risk.
6. Negative shipment P&L from existing charges → margin warning risk.

Holds and risks deduplicate via deterministic keys, so repeated refreshes
don't generate duplicate notifications.

## Aging buckets

`not_due`, `0-30`, `31-60`, `61-90`, `90+` — based on invoice `due_date`
relative to today. Only invoices in open statuses
(`draft`, `issued`, `partially_paid`, `overdue`, `disputed`, `on_hold`) are
included.

## Release control

Advisory only. Phase 14 never performs an external release. The check returns
`allowed=false` with a list of blocking holds when:
* The shipment has any active hold whose `blocked_action` matches the requested action (or is null = applies to all).
* The associated party has any active hold matching the same rule.

When blocked, a critical `release_blocked` finance risk is recorded.

## FX

Only manual snapshots are supported in Phase 14. `convert_amount` walks the
nearest snapshot; if missing in either direction it returns `None`, and the
caller (e.g. payment-currency mismatch) can record a `missing_fx_rate` risk.

## Validation rules (new)

`finance_invoice_missing_party`, `finance_invoice_negative_amount`,
`finance_payment_overallocated`, `finance_payment_currency_mismatch`,
`finance_invoice_overdue`, `finance_receivable_overdue`,
`finance_payable_overdue`, `finance_credit_limit_warning`,
`finance_credit_limit_exceeded`, `finance_missing_fx_rate`,
`finance_negative_margin_warning`, `finance_release_blocked_credit_hold`,
`finance_demurrage_invoice_mismatch`, `finance_detention_invoice_mismatch`.

Default behavior: enabled, non-blocking.

## Notifications

Created for receivable/payable overdue, credit warning/exceeded, release
blocked, unallocated payments, invoice disputes, negative margin, missing FX.
Dedupe keys are deterministic (e.g. `finance_release_blocked:{shipment_id}:{action_key}`).

## Events / Audit

Operational events: `finance.invoice_created`, `finance.invoice_updated`,
`finance.invoice_cancelled`, `finance.payment_created`, `finance.payment_allocated`,
`finance.payment_cancelled`, `finance.credit_profile_updated`, plus the
hold/risk lifecycle ones described in the plan. Audit logs are sanitized and
contain only allowlisted metadata fields.

## AI assistant

Read-only. New intent `finance_control_summary` produces an overview of
receivable/payable totals, overdue, active holds, open risks. AI cannot
create invoices, mark payments, waive holds, or release documents.

## Frontend

* `/finance` — Overview, Receivables, Payables, Payments, Credit Control,
  Holds, Aging, FX Rates, Risks tabs.
* Shipment detail → new **Finance** tab using `ShipmentFinancePanel`
  with summary, holds, release checks, and risk list.
* Dashboard widget: receivable/payable overdue, holds, open risks,
  unallocated payments, negative margin shipments.

## Limitations

* No bank/payment gateway, no e-invoice/e-way bill, no PDF generation.
* No automatic release of OBL/DO/documents.
* No autonomous AI finance decisions.
* Tax handling is metadata only; tax filing is out of scope.

## Roadmap into Phases 15+

* Phase 15 will introduce an exception engine that consumes the finance risk
  records produced here.
* Phase 16/17 will layer an approval engine and HOD/bot governance on top of
  the manual `finance_adjustment` table seeded in this phase.
