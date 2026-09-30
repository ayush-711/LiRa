# Local development setup

## Option A — Docker (recommended)

Requirements: Docker + Docker Compose.

```bash
cp .env.example .env      # edit SECRET_KEY and passwords
docker compose up --build
```

This starts Postgres, the backend (which runs migrations + seeds reference data
and a bootstrap admin), the frontend, and Caddy. Open:

- App: http://localhost
- API docs: http://localhost/api/docs (or http://localhost:8000/api/docs)

Seed sample data (optional):

```bash
docker compose exec backend python -m app.scripts.seed_dev_data
```

Default development admin: `admin@lira.local` / `Admin123!`
Sample users (after seeding): `rahul@lira.local`, `priya@lira.local`,
`aman@lira.local` — all with password `Password123!`.

## Option B — Run services directly

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate       # Windows: .venv\Scripts\activate ; macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Point at a local Postgres (or use docker compose up postgres)
export POSTGRES_HOST=localhost POSTGRES_PORT=5432 \
       POSTGRES_USER=lira POSTGRES_PASSWORD=lira POSTGRES_DB=lira

alembic upgrade head
python -m app.scripts.seed_reference
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000, proxies /api to http://localhost:8000
```

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest                 # uses an in-memory SQLite DB, no Postgres needed
```

## Common commands

| Task | Command |
|------|---------|
| New migration | `alembic revision --autogenerate -m "message"` |
| Apply migrations | `alembic upgrade head` |
| Seed reference data | `python -m app.scripts.seed_reference` |
| Seed dev data | `python -m app.scripts.seed_dev_data` |
| Backend tests | `pytest` |
| Frontend typecheck | `npm run typecheck` |
| Frontend unit tests | `npm test` |
| End-to-end tests | `npm run e2e` (needs the stack running) |
