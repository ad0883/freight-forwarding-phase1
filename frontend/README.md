# Freight Forwarding Phase 1 Frontend

React + Vite frontend for the Phase 1 freight forwarding MVP.

Phase 2 adds workflow status controls, BL Management, import demurrage tracking, follow-up logs, dashboard pending-task/critical-alert panels, and expanded mock AI prompts.

## Local Setup

```bash
npm install
cp .env.example .env
npm run dev
```

The app runs at `http://localhost:5173` by default.

## QA Account Emails

For automated/local QA users, avoid reserved domains such as `example.com` and
`example.org`; backend email validation may reject them. Use a valid test domain
such as `testmail.dev` for throwaway QA accounts.
