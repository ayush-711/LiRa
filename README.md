# LiRa — Internal Work Management Platform

LiRa is a clean, modern, internal work-management app (a simpler Linear/Jira for a
small team). It provides projects, issues, a Kanban board, list and "My
Issues" views, comments, attachments, subtasks, issue relationships, labels,
notifications, search, audit logs and role-based access — invitation-only, self-hostable.

- **Frontend:** Next.js (App Router) · React · TypeScript · Tailwind · shadcn/ui · TanStack Query · dnd-kit
- **Backend:** Python · FastAPI · Pydantic v2 · SQLAlchemy 2 (async) · Alembic · PostgreSQL
- **Deploy:** Docker Compose behind Caddy (automatic HTTPS)

## Quick start (development)

```bash
cp .env.example .env          # then edit secrets
docker compose up --build     # starts postgres, backend, frontend, caddy
docker compose exec backend python -m app.scripts.seed_dev_data   # optional sample data
```

Then open http://localhost (Caddy) — or the frontend directly at http://localhost:3000
and the API docs at http://localhost:8000/docs.

Default seeded admin (dev only): `admin@lira.local` / `Admin123!`

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/architecture.md](docs/architecture.md) | System architecture, ER model, permission matrix, route/API maps, phase plan |
| [docs/setup.md](docs/setup.md) | Local development setup |
| [docs/deployment.md](docs/deployment.md) | Production deployment + HTTPS |
| [docs/database.md](docs/database.md) | Schema, migrations, indexes |
| [docs/api.md](docs/api.md) | REST API reference |
| [docs/backup-restore.md](docs/backup-restore.md) | Backup & restore procedures |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues |
| [docs/feature-inventory.md](docs/feature-inventory.md) | Feature list, known limitations, roadmap |

The **permission matrix** and **ER diagram** live in
[docs/architecture.md](docs/architecture.md#3-roles--permission-matrix) and
[docs/database.md](docs/database.md#er-diagram).

## Repository layout

```
/backend     FastAPI modular monolith (api, services, repositories, models, ...)
/frontend    Next.js app
/infra       Caddy reverse-proxy config
/docs        Documentation
docker-compose.yml
.env.example
```

See [docs/architecture.md](docs/architecture.md) for the full picture.
