# Backup & restore

LiRa's durable state is in two places:

1. **PostgreSQL** — all application data.
2. **Uploaded files** — the `uploads` Docker volume (mounted at `/data/uploads`).

Plus your **`.env`** (secrets/config) which should be backed up securely and
separately (e.g. a password manager or secrets vault), never in the same place as
the data.

## Backing up

### Database

```bash
# Dump to a timestamped file on the host
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > backup-db-$(date +%F).sql.gz
```

### Uploaded files

```bash
# Archive the uploads volume
docker run --rm -v lira_uploads:/data -v "$PWD":/backup alpine \
  tar czf /backup/backup-uploads-$(date +%F).tar.gz -C /data .
```

(Replace `lira_uploads` with the actual volume name from `docker volume ls` if your
Compose project name differs.)

### Automate

Add a cron job on the host running the two commands nightly and copying the
resulting archives off-box (rsync/S3/etc.). Keep at least 7 daily + 4 weekly copies.

## Restoring

Restore into a fresh stack (Postgres empty).

### Database

```bash
gunzip -c backup-db-YYYY-MM-DD.sql.gz \
  | docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

If restoring into a brand-new database, create it first and ensure migrations are
at the same revision as the backup (the dump includes the schema, so you can skip
`alembic upgrade` when restoring a full dump).

### Uploaded files

```bash
docker run --rm -v lira_uploads:/data -v "$PWD":/backup alpine \
  sh -c "cd /data && tar xzf /backup/backup-uploads-YYYY-MM-DD.tar.gz"
```

### Verify

- `GET /api/health` → ok
- Sign in; open a project, an issue, and download an attachment.

## Where data lives (quick reference)

| Data | Location |
|------|----------|
| Application data | Postgres volume `pgdata` |
| Attachments | Docker volume `uploads` → `/data/uploads` |
| TLS certificates | Docker volume `caddy_data` |
| Secrets/config | `.env` on the host (back up separately) |
