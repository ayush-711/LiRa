# Troubleshooting

## The stack won't start

- **`docker compose up` fails on Postgres health**: check `POSTGRES_*` values in
  `.env` are consistent; remove a corrupt volume with `docker compose down -v`
  (⚠️ deletes data) only in development.
- **Backend exits during migrations**: view logs with
  `docker compose logs backend`. A common cause is a bad `DATABASE_URL` override or
  Postgres not yet ready — the compose healthcheck should prevent the latter.

## Can't sign in

- **No admin account**: in production the first admin is created only if
  `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` are set and there are no
  users. Set them and restart the backend.
- **"Account temporarily locked"**: too many failed logins. Wait
  `LOGIN_LOCKOUT_MINUTES`, or clear `locked_until`/`failed_login_count` for the
  user in the database.
- **Login returns but you're bounced back to /login**: the session cookie isn't
  sticking. In production ensure `COOKIE_SECURE=true` **and** HTTPS; over plain
  HTTP a secure cookie is dropped by the browser.

## CSRF errors (403 CSRF_FAILED)

The SPA reads the `lira_csrf` cookie and sends it as `X-CSRF-Token`. If you see
this, the cookie is missing — sign in again. Server-to-server clients should use
`Authorization: Bearer` instead of cookies.

## Emails aren't sending

- If `SMTP_HOST` is empty, emails are **logged to the backend console** instead of
  sent (development behaviour). Set SMTP settings to send real mail.
- Check `docker compose logs backend` for `Failed to send email` lines. Email
  failures never block the underlying action (assignment, invite, etc.).

## Invitations / reset links don't work

- Links use `APP_BASE_URL`; make sure it matches the URL users actually visit.
- Tokens are single-use and expire (`INVITATION_EXPIRE_HOURS`,
  `PASSWORD_RESET_EXPIRE_HOURS`). Re-issue if expired.

## Attachments fail to upload

- Check the file type is in the allowlist and under `MAX_UPLOAD_SIZE_MB`.
- Ensure the `uploads` volume is writable; the backend writes under
  `UPLOAD_ROOT` (`/data/uploads`).

## Board drag does nothing / reverts

- Viewers are read-only by design. Otherwise a revert with a toast means the
  server rejected the move — check backend logs; the board reloads authoritative
  state automatically.

## Frontend can't reach the API in local dev

- `npm run dev` proxies `/api` to `http://localhost:8000` (see `next.config.mjs`).
  Ensure the backend is running there, or set `BACKEND_INTERNAL_URL`.

## Useful commands

```bash
docker compose logs -f backend         # tail backend logs
docker compose exec backend alembic current   # current migration
docker compose exec postgres psql -U lira -d lira   # DB shell
```
