# Deployment

LiRa is designed to run on a single organisation-owned server via Docker Compose,
behind Caddy which terminates HTTPS automatically.

## Architecture

```
Internet ──HTTPS──▶ Caddy ──▶ /api/*  → backend (FastAPI, :8000)
                          └──▶ /*      → frontend (Next.js, :3000)
                                          backend ──▶ Postgres, /data/uploads
```

Only Caddy is exposed to the network (ports 80/443). In a hardened deployment,
remove the `ports:` entries for `backend` and `frontend` in `docker-compose.yml`
so they are reachable only on the internal Docker network.

## Steps

1. **Provision** a Linux server with Docker + Docker Compose and a DNS record
   pointing your hostname (e.g. `work.example.com`) at it. Open ports 80 and 443.

2. **Configure** environment:
   ```bash
   cp .env.example .env
   ```
   Set at least:
   - `ENVIRONMENT=production`
   - `APP_DOMAIN=work.example.com`  (used by Caddy for automatic TLS)
   - `APP_BASE_URL=https://work.example.com`  (used in invite/reset emails)
   - `SECRET_KEY=<64+ random chars>`  (`python -c "import secrets;print(secrets.token_urlsafe(48))"`)
   - `COOKIE_SECURE=true`
   - `POSTGRES_PASSWORD=<strong password>`
   - `CORS_ORIGINS=https://work.example.com`
   - SMTP settings (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`)
   - `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` — the first administrator
     (created only if the database has no users).

3. **Launch**:
   ```bash
   docker compose up -d --build
   ```
   The backend container runs migrations and seeds reference data on start. Caddy
   obtains a Let's Encrypt certificate for `APP_DOMAIN` automatically.

4. **Verify**: `https://work.example.com/api/health` returns `{"status":"ok"}`.
   Sign in as the bootstrap admin and invite your team.

## Updating

```bash
git pull
docker compose up -d --build
```

Migrations run automatically on backend start. Review new migrations before
deploying to production.

## Scaling notes

For ~10 users the single-node setup is ample. To grow toward 100+ users:
- Give Postgres more resources / move it to a managed instance (change `DATABASE_URL`).
- Run multiple backend replicas behind Caddy (the app is stateless apart from the
  DB and the shared `/data/uploads` volume — mount that volume on shared storage).
- Add Redis + a background worker if email volume grows (the notification
  abstraction already isolates delivery).

## Security checklist

- [ ] `SECRET_KEY` is long and random, not the default.
- [ ] `COOKIE_SECURE=true` and the site is served over HTTPS only.
- [ ] `backend`/`frontend` ports are not published to the public network.
- [ ] Strong `POSTGRES_PASSWORD`; database not exposed externally.
- [ ] SMTP credentials set so invitations/resets are delivered.
- [ ] Regular backups configured (see [backup-restore.md](backup-restore.md)).
- [ ] `.env` is never committed and has restricted file permissions.
