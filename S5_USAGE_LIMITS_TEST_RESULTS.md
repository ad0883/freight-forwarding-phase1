# S5 Usage Limits Test Results

## Backend Enforcements:
- Shipments creation: 403 USAGE_LIMIT_REACHED when `shipments_per_month` limit is met.
- Document versions upload: 403 USAGE_LIMIT_REACHED when `document_uploads_per_month` limit is met.
- AI Ask: 403 USAGE_LIMIT_REACHED when `ai_requests_per_month` limit is met.
- User creation: 403 USAGE_LIMIT_REACHED when `users` limit is met.
- Tracking Sync: 403 USAGE_LIMIT_REACHED when `tracking_syncs_per_month` limit is met.
- Predictive Run: 403 USAGE_LIMIT_REACHED when `predictive_runs_per_month` limit is met.
- Portal Account Creation: Blocked when limit reached.

## Frontend UI Warnings:
- **Dashboard / UsageLimitsPage:** Shows all usage limits with bars highlighting warnings (yellow) and blocks (red).
- **CreateShipmentPage:** Displays banner when near limit or reached. Button is disabled when reached.
- **ShipmentDetailPage (Document Upload):** Displays banner inside the upload modal when near limit or reached. Button is disabled when reached.
- **MockAiPage:** Displays banner when near limit or reached. Input and button are disabled when reached.
- **UsersAdminPage:** Displays banner when near limit or reached. Button is disabled when reached.

## Permissions
- Usage summary API requires authentication.
- Limits only applied to organization scoped users.

## Data integrity
- No data is deleted when limits are reached. Users simply cannot create more records until the limit resets or is increased.
