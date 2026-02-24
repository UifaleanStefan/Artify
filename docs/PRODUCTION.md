# Production readiness checklist

Use this before going live and when reviewing the app.

## Required environment

- [ ] **REPLICATE_API_TOKEN** – set and valid
- [ ] **DATABASE_URL** – PostgreSQL, persistent (e.g. Render Postgres)
- [ ] **PUBLIC_BASE_URL** – exact HTTPS URL of the app (e.g. `https://artify.works`)
- [ ] **Email** – at least one of: RESEND_API_KEY, SENDGRID_API_KEY, or SMTP_* (for result and failure emails)

## Security

- [ ] No secrets in repo (use env vars; `.env` in `.gitignore`)
- [ ] App served over HTTPS only (platform or reverse proxy)
- [ ] Security headers are applied (X-Content-Type-Options, X-Frame-Options, etc.) – see `SecurityHeadersMiddleware` in `main.py`
- [ ] Debug routes: consider disabling `/debug/*` in production or protecting them (e.g. by env flag or auth)

## Reliability

- [ ] **Health** – `/health` returns 200; use it for liveness/uptime checks
- [ ] **DB** – migrations/init run on startup; TTL cleanup runs for orders and result images
- [ ] **Replicate** – retries on timeout and rate limit; source images persisted at order creation so redeploys don’t break in-flight orders
- [ ] **Errors** – unhandled exceptions return generic 500 JSON (no stack trace to client); details only in logs

## Operations

- [ ] Logs go to stdout (so Render/host can capture them)
- [ ] Static upload/results dir: use a persistent volume or rely on DB for result images (DB is primary; disk is fallback)
- [ ] Backups: backup PostgreSQL (orders, result blobs if you keep them long term)

## Optional improvements

- **Rate limiting** – add per-IP or per-email limits on `/api/orders` and `/api/upload-image` to reduce abuse
- **Readiness** – add a `/ready` that checks DB connectivity if your platform supports readiness vs liveness
- **Static caching** – serve `/static` with `Cache-Control: public, max-age=…` for JS/CSS (HTML stays no-cache so deploys are picked up)
