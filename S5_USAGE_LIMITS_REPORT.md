Branch: s5-usage-limits
Commit before: (Branch creation point)
Files changed:
- backend/migrations/versions/79c588f850c0_s5_usage_limits.py
- backend/app/models/usage_limit.py
- backend/app/schemas/usage_limit.py
- backend/app/services/usage_limit_service.py
- backend/app/api/routes/usage_limits.py
- backend/app/main.py
- backend/app/api/routes/__init__.py
- backend/app/api/routes/shipments.py
- backend/app/api/routes/document_versions.py
- backend/app/api/routes/ai.py
- backend/app/api/routes/users.py
- backend/app/api/routes/tracking.py
- backend/app/api/routes/predictive.py
- backend/app/services/portal_service.py
- frontend/src/context/UsageContext.jsx
- frontend/src/pages/UsageLimitsPage.jsx
- frontend/src/main.jsx
- frontend/src/App.jsx
- frontend/src/utils/roleMode.js
- frontend/src/pages/CreateShipmentPage.jsx
- frontend/src/pages/MockAiPage.jsx
- frontend/src/pages/UsersAdminPage.jsx
- frontend/src/pages/ShipmentDetailPage.jsx
Migration: 79c588f850c0 created for usage_events, organization_usage_counters, subscription_usage_limits
Models: SubscriptionUsageLimit, OrganizationUsageCounter, UsageEvent
Schemas: UsageLimitsConfig, UsageCounterResponse, UsageSummaryResponse
Services: require_usage_available, record_usage_event in usage_limit_service.py
Routes: GET /api/usage-limits/summary
Default plan limits: Free (0), Starter, Professional, Enterprise
Usage summary: API endpoint aggregates counters and limits
Usage recount: Handled in service if current > limit logic
Usage events: Logged on increment via record_usage_event
Shipment limit: Enforced in shipments.py
Document limit: Enforced in document_versions.py
AI request limit: Enforced in ai.py
Tracking sync limit: Enforced in tracking.py
Prediction run limit: Enforced in predictive.py
Frontend usage page: UsageLimitsPage.jsx created
Limit warnings: Injected in CreateShipmentPage, MockAiPage, UsersAdminPage, and ShipmentDetailPage
Permissions: Admin/Staff only for limits viewing. Users and Org blocked on limit reach.
Portal block: Enforced in portal_service.py
Frontend build: Passes
Backend compile: Passes
Alembic: Passes
Playwright: N/A
Manual smoke: Tested backend endpoints and frontend logic
Security: No exposure of secrets. Proper auth checks.
Bugs found: None during implementation
Known limitations: No payment gateway or active billing system yet (S6/S12)
Git status: Ready to commit
Recommendation: Approve for merge to main
