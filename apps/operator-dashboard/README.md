# Operator Dashboard

Minimal React + Vite dashboard for operators monitoring field activity.

## Pages

- Active events
- Event history
- Device status
- Live stream placeholder

## Run

```bash
npm install
npm run dev
```

## Backend Switch

The dashboard uses the FastAPI gateway by default.

1. Copy `.env.example` to `.env`
2. Point `VITE_API_BASE_URL` to the gateway host
3. Use `VITE_USE_MOCK_API=true` only when you intentionally want offline mock data

Event pages poll `/events` every few seconds. In local development, evidence
images under `datasets/evidence` are exposed through the dashboard dev server at
`/local-evidence` so gateway event payloads can display local annotated frames.
