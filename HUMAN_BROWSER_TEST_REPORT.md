# Human Browser Test Report

## Scope

- Playwright e2e setup for the React + FastAPI app.
- Coverage includes login/logout for `ADMIN`, `STAFF`, and `VIEW_ONLY`, dashboard, shipments, shipment detail tabs, QA shipment creation, workflow transitions visibility, QA container creation, TXT document upload, document intelligence, Finance page presence, view-only mutation restrictions, and mobile sidebar behavior.

## How To Run

```bash
cd frontend
npm run test:e2e:headed
```

Required environment variables can be placed in your shell or in ignored `frontend/.env.e2e`:

```env
E2E_BASE_URL=http://127.0.0.1:5173
E2E_ADMIN_EMAIL=
E2E_ADMIN_PASSWORD=
E2E_STAFF_EMAIL=
E2E_STAFF_PASSWORD=
E2E_VIEW_EMAIL=
E2E_VIEW_PASSWORD=
```

The tests use `VITE_API_BASE_URL` when set, otherwise local runs derive `http://127.0.0.1:8000/api` from `E2E_BASE_URL`.

## Latest Run

Passed on local isolated e2e backend.

Command run from `frontend`:

```bash
npm run test:e2e:headed
```

Result:

```text
13 passed (18.4s)
```

Notes:

- The run used a temporary SQLite-backed FastAPI instance on `http://127.0.0.1:8001/api`.
- No secrets were committed. Runtime credentials were supplied through process env only and are intentionally not recorded here.
- HTML report output is generated under ignored `frontend/playwright-report`.
