# Freight Forwarding Phase 1 Backend

FastAPI backend for the Phase 1 freight forwarding MVP.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `DATABASE_URL` in `.env` with a PostgreSQL connection string, then run:

```bash
uvicorn app.main:app --reload
```

API docs open at `http://localhost:8000/docs`.

## Default Admin

The app creates the first admin on startup when no admin exists:

```txt
admin@example.com
admin123
```
