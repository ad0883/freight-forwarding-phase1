# S5 Usage Limits Bugs

During implementation, no critical bugs were found in the existing system. 

Minor issues found and resolved:
1. UUID vs Integer Primary Keys: Attempted to use UUIDs for usage limit tables initially, which caused foreign key mismatch with the `organizations` table that uses Integer IDs. Resolved by adhering strictly to Integer primary keys for `organization_id` and model `id`.
2. Missing Auth Context: The initial frontend architecture didn't have an `AuthContext.jsx` exposing a `user` object directly. Resolved by extracting the `access_token` from `localStorage` in `UsageContext.jsx` to fetch the usage limits summary.
3. Import Error on Backend Startup: `OrganizationMembership` was mistakenly imported in `usage_limit_service.py` but the model doesn't exist. Switched to use the `User` model to calculate the number of users in an organization.
4. Import Error on Backend Startup: `get_db` was imported from `app.core.database` instead of `app.api.deps` in `usage_limits.py`. Updated the import path.
5. Import Error on Backend Startup: `get_current_active_user` and `require_admin` were imported from `app.api.dependencies` (a module that doesn't exist) instead of using `get_current_user` and `require_roles` from `app.api.deps`. Fixed the imports and dependency injections.

No ongoing bugs known.
