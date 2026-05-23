# Freight Forwarding Phase 1 MVP

Phase 1 implementation of a freight forwarding operations system with a FastAPI backend, PostgreSQL database, and React + Vite frontend.

## Features

- JWT login with default admin creation
- Role-ready backend permissions for `ADMIN`, `STAFF`, and `VIEW_ONLY`
- Export and import shipment creation
- Auto-generated shipment IDs such as `FF-EXP-2026-001`
- Default document checklist per shipment
- Google Drive URL storage in document `file_url`
- Party directory
- Task list with done/reopen flow
- APScheduler overdue-task alert foundation
- Mock AI assistant with rule-based database answers

## Backend Local Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `backend/.env` with a valid PostgreSQL connection string:

```env
DATABASE_URL=postgresql://username:password@host/dbname?sslmode=require
```

Run the API:

```bash
uvicorn app.main:app --reload
```

API docs are available at `http://localhost:8000/docs`.

Default development login:

```txt
admin@example.com
admin123
```

Use that password for local development only. Change `ADMIN_PASSWORD` before the first production deploy.

## Frontend Local Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The frontend runs at `http://localhost:5173`.

## Neon Setup

1. Create a Neon PostgreSQL project.
2. Copy the pooled or direct connection string.
3. Paste it into `backend/.env` as `DATABASE_URL`.
4. Keep `sslmode=require` in the URL for Neon.

Never commit `backend/.env` or `frontend/.env`. They are ignored by git and should stay local or in your hosting provider's environment settings.

## Document Link Workflow

Phase 1 stores document links only. Upload files manually to Google Drive, copy the share URL, then paste it into the document `file_url` field in the shipment Documents tab.

## Phase 1 Limitations

Phase 1 intentionally does not include OpenAI API calls, real file uploads, Google Drive API upload, S3, Celery, Redis, charges, demurrage, BL management, courier tracking, reports, or email/Gmail parsing.

Shipment codes are unique in the database, but the current counter-based generator can race if two shipments of the same type are created at exactly the same time. Use single-user/admin workflows for Phase 1; replace this with a database sequence before high-concurrency production use.

## Render Deployment

Backend web service:

```txt
Root directory: backend
Build command: pip install -r requirements.txt
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Backend environment variables:

```env
DATABASE_URL=your_neon_postgres_url
JWT_SECRET_KEY=your_secret_key
BACKEND_CORS_ORIGINS=https://your-frontend.onrender.com
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE_SECONDS=1800
AUTO_CREATE_TABLES=true
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-this-password
```

For production speed, use Neon's pooled connection URL, deploy the backend in the same or nearest region as the database, and run without `--reload`.
Set a long random `JWT_SECRET_KEY`, and change `ADMIN_PASSWORD` before the service starts for the first time.

Frontend static site:

```txt
Root directory: frontend
Build command: npm install && npm run build
Publish directory: dist
```

Frontend environment variable:

```env
VITE_API_BASE_URL=https://your-backend.onrender.com/api
```

## GitHub Push

```bash
git init
git add .
git commit -m "Initial freight forwarding phase 1 MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/freight-forwarding-phase1.git
git push -u origin main
```
