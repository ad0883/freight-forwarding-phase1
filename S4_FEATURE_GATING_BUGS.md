# S4 — Known Bugs and Limitations

## Known Bugs
1. **ModuleNotFoundError on Initial Depactorization**: The implementation incorrectly referenced `app.api.dependencies` instead of the existing `app.api.deps` which triggered a failure in Uvicorn upon reload. This was resolved promptly.
2. **ImportError in Dependencies**: The initial auth injection used `get_current_active_user` instead of `get_current_user`. Fixed before finalizing testing.

## Limitations & Edge Cases
1. **Portal User Evaluation**: Currently, the system bypasses strict feature evaluation for Portal users because they lack an intrinsic organizational SaaS plan structure in the standard layout. Complex gating of portal-side feature variations (e.g. standard tracking vs white-labeled tracking) is deferred to future requirements.
2. **Frontend Caching**: If a plan assignment is updated server-side, the frontend will not immediately show/hide the sidebar features until the React `FeatureContext` reloads (or page is fully refreshed). Real-time websocket pushes for feature toggles are not implemented.
