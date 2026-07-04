# SplitFare Deployment Guide

This guide prepares the current mock Release Candidate for production-like deployment. It does not enable real suppliers or real booking.

## Frontend: Vercel

Recommended settings:

- Framework preset: Next.js
- Root directory: `frontend`
- Build command: `npm run build`
- Output: Next.js default / standalone handled by Vercel

Environment variables:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-backend.example.com
NEXT_PUBLIC_APP_ENV=production
```

Do not add supplier tokens or backend secrets to `NEXT_PUBLIC_*`.

## Backend: Render

Recommended settings:

- Root directory: `backend`
- Runtime: Docker
- Health check path: `/health`

Environment variables:

```text
APP_ENV=production
APP_VERSION=0.1.0
API_BASE_URL=https://your-backend.example.com
FRONTEND_ORIGIN=https://your-frontend.vercel.app
ENABLE_MOCK_SUPPLIER=true
LOG_LEVEL=INFO
RATE_LIMIT_REQUESTS_PER_MINUTE=120
DATABASE_URL=
REDIS_URL=
```

## Backend: Fly.io

Use the backend Dockerfile:

```powershell
cd backend
fly launch
fly secrets set APP_ENV=production FRONTEND_ORIGIN=https://your-frontend.vercel.app ENABLE_MOCK_SUPPLIER=true
fly deploy
```

Set `/health` as the health check path in Fly config.

## Backend: Railway

Recommended settings:

- Service root: `backend`
- Builder: Dockerfile
- Health check path: `/health`
- Public networking enabled for the API service

Set the same backend environment variables shown in the Render section.

## CORS

Local development uses localhost origins. Production must set `FRONTEND_ORIGIN` to the exact frontend URL, for example:

```text
FRONTEND_ORIGIN=https://splitfare.example.com,https://splitfare-preview.vercel.app
```

Do not use wildcard CORS in production.

## Mock/live mode

`ENABLE_MOCK_SUPPLIER=true` keeps the deterministic mock supplier enabled. Setting it to `false` switches the app into live-mode shape, but this RC does not include a real supplier integration by default, so searches may return empty results unless a future adapter is enabled.

## Health check

`GET /health` returns:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "mode": "mock",
  "timestamp": "2026-07-05T00:00:00+00:00"
}
```

## Local Docker compose

```powershell
docker compose up -d --build
```

The compose stack exposes:

- Frontend: <http://localhost:8080>
- Backend: <http://localhost:8000>
- Health: <http://localhost:8000/health>

## Production safety

- `debug=true` search responses are ignored in production.
- Global errors use a stable `{ "error": { "code", "message", "requestId" } }` format.
- Raw stack traces are not returned when `APP_ENV=production`.
- Search has a basic per-client in-memory rate limit.
- All supplier API keys must remain backend-only.
