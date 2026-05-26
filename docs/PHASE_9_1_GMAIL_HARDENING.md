# Phase 9.1: Gmail Automation Hardening & Cleanup

Phase 9.1 fixes data-hygiene issues in Gmail automation without changing scopes
or moving away from the review-based suggestion model. It is purely additive on
top of Phase 9 and prepares Gmail to coexist with the Phase 10 state machine.

## Scope

- Backend tightens scoping, dedupe, classifier, and field validation.
- New endpoints surface dismiss/delete/bulk-reject/cleanup actions.
- Frontend gives bulk-select, reject, dismiss, delete, and one-click cleanup.
- Gmail remains read-only. Phase 9.1 never sends, modifies, deletes, archives,
  or labels Gmail messages.

## Account scoping

- `email_connections.gmail_account_email` and `gmail_account_id` capture the
  authenticated Gmail profile email and a stable hash-based id.
- `email_message_cache` and `email_suggestions` carry `user_id` and
  `gmail_account_email`. Listings default to the connected account so messages
  cached against a previously connected account do not leak.
- Disconnect records `disconnected_at` and `last_cleanup_at` on the connection.

## Deduplication

- Cached emails: unique on `(connection_id, gmail_message_id)` plus
  `(user_id, gmail_account_email, gmail_message_id)`. Subject hash is stored
  for diagnostics. Repeat scans update the existing row.
- Suggestions: unique on
  `(email_message_id, suggestion_type, shipment_id, extracted_data_hash)` where
  `extracted_data_hash` is a stable SHA-256 of the canonicalised payload.
  Repeat scans skip duplicates instead of creating new rows.

## Classifier and field validation

- Non-freight senders (IRCTC, Shopify/Amazon order shipped, newsletters,
  promos, travel, social) classify as `unknown` unless a freight term or
  shipment code is present.
- Booking-confirmation, BL-draft, arrival-notice, freight-invoice,
  delivery-order and pre-alert classifiers require freight anchors before
  emitting suggestions.
- BL number validation rejects token-like and high-entropy strings.
- Booking ref, vessel/voyage, ports, and amounts go through bespoke validators.
- If no shipment matches and confidence is below `0.7`, no operational
  suggestion is created. The cached email status flips to `manual_review` or
  `ignored` instead.

## Endpoints

| Method | Path | Roles | Purpose |
| --- | --- | --- | --- |
| GET | `/api/email/status` | ADMIN, STAFF | now also reports pending and cached counts |
| POST | `/api/email/scan` | ADMIN, STAFF | dedupe-aware; returns `duplicates_skipped` |
| POST | `/api/email/disconnect` | ADMIN, STAFF | accepts `{ "clear_cache": bool }` |
| POST | `/api/email/cleanup` | ADMIN, STAFF | hide cached emails + dismiss pending suggestions for a target account |
| POST | `/api/email/suggestions/bulk-reject` | ADMIN, STAFF | bulk reject given pending suggestion ids |
| POST | `/api/email/suggestions/clear-pending` | ADMIN, STAFF | reject by filters: low_confidence, no_shipment, suggestion_type, older_than, gmail_account_email, current_account_only |
| PATCH | `/api/email/suggestions/{id}/reject` | ADMIN, STAFF | reject (alias of POST) |
| PATCH | `/api/email/suggestions/{id}/dismiss` | ADMIN, STAFF | dismiss without business changes |
| DELETE | `/api/email/suggestions/{id}` | ADMIN | hard delete; blocked when status = `applied` |
| GET | `/api/email/messages` | ADMIN, STAFF | adds `current_account_only`, `include_hidden` query params |
| GET | `/api/email/suggestions` | ADMIN, STAFF | adds `current_account_only`, `include_low_confidence` query params |

## Permissions

- ADMIN: scan, list, review, apply, reject, dismiss, delete, bulk-reject,
  clear-pending, cleanup.
- STAFF: scan, list, review, apply, reject, dismiss, bulk-reject,
  clear-pending, cleanup. STAFF cannot hard-delete suggestions.
- VIEW_ONLY: blocked across all Gmail endpoints (403).

## Events / audit / safety

- Apply and reject continue to emit the existing operational events.
- Disconnect, cleanup, dismiss, delete, bulk-reject, clear-pending each emit a
  sanitized audit log row. None store Gmail tokens, OAuth codes, raw email
  bodies, API keys, JWTs, `DATABASE_URL`, or other secrets.
- Phase 9.1 cleanup hides cached emails and rejects pending suggestions only.
  Charges, tasks, documents, BL records, and demurrage created by previous
  Apply runs are preserved.

## Migration

Run `alembic upgrade head` to apply `phase9_1_gmail_cleanup`. The migration
adds nullable columns and idempotent indexes. Existing email_connections,
email_message_cache, and email_suggestions rows are preserved.
