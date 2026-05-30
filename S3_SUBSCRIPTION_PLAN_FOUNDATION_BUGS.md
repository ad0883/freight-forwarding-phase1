# S3_SUBSCRIPTION_PLAN_FOUNDATION_BUGS

No severe bugs found during development.

### Minor Issues Handled
1. **Alembic Autogenerate Interference**: 
   - *Issue*: FastAPI's `AUTO_CREATE_TABLES` runs sequentially on application reload. Because the server was running with `--reload`, it instantly detected new models and created tables *before* Alembic autogenerate could capture the state diff, causing `alembic` to complain that the tables already existed. 
   - *Resolution*: Dropped tables manually from the DB via script, generated an empty Alembic revision manually, populated the DDL via SQLAlchemy Operations, and executed `alembic upgrade head` cleanly.

2. **UI Navigation Isolation**:
   - *Issue*: Subscriptions UI must only be visible to Admins.
   - *Resolution*: Strictly encapsulated under `ProtectedRoute` for `['ADMIN']` and explicitly blocked rendering in the `SubscriptionsPage.jsx` load loop for non-Admins.

### Outstanding Considerations
- No active gating in this release. Billing mode is pure `manual`. Future updates (S4 Feature Gating) will begin attaching limits based on `metadata_json` schemas in `subscription_plans`.
