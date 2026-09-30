# LiRa — Architecture

## 1. Overview

LiRa is a **modular monolith**: a single FastAPI backend and a single Next.js
frontend, backed by PostgreSQL and local file storage, deployed behind a Caddy
reverse proxy that terminates HTTPS. No microservices, no message brokers, no
Kubernetes. The design keeps a small operational footprint for ~10 users while
leaving clean extension points to grow to 100+.

```
                Internet
                   │  HTTPS
                   ▼
             ┌───────────┐
             │   Caddy    │  (TLS, security headers, routing)
             └─────┬──────┘
        /api/* │        │ /*
               ▼        ▼
        ┌──────────┐  ┌──────────┐
        │ Backend   │  │ Frontend │
        │ FastAPI   │  │ Next.js  │
        └────┬──────┘  └──────────┘
             │
     ┌───────┴────────┐
     ▼                ▼
┌──────────┐   ┌──────────────┐
│ Postgres │   │ File storage │  (/data/uploads)
└──────────┘   └──────────────┘
```

### Backend layering

Route handlers stay thin. Business logic lives in services; data access in
repositories. This prevents duplicated business rules and keeps handlers testable.

```
api/         FastAPI routers — HTTP concerns, dependency wiring, no business logic
schemas/     Pydantic request/response models (the API contract)
services/    Business logic, authorization checks, transactions, orchestration
repositories/  SQLAlchemy queries — the only place that talks to the ORM
models/      SQLAlchemy ORM entities
core/        config, security, logging, errors, dependencies
auth/        password hashing, JWT, invitation tokens
notifications/  channel abstraction (email now; slack/webhook later)
storage/     safe local file storage
audit/       audit log + activity event helpers
```

## 2. Data model (ER)

```
users ──< project_members >── projects ──< issues
  │                              │            │
  │                              │            ├──< comments
  │                              │            ├──< attachments
  │                              │            ├──< issue_labels >── labels
  │                              │            ├──< activity_events
  │                              │            └──< issue_relationships >── issues (self)
  │
  ├──< notifications
  ├──< notification_preferences (1:1)
  ├──< audit_logs (actor)
  ├──< invitations (created_by)
  └──< password_reset_tokens

reference tables: issue_statuses, issue_types, issue_priorities
```

Key relationships:

- **users ↔ projects** is many-to-many through `project_members`, which also
  carries a per-project role (`manager` | `member`).
- **issues.parent_id → issues.id** models subtasks (self-referential).
- **issue_relationships** stores directed links (`blocks`, `relates_to`) between
  two issues with a uniqueness + no-self constraint.
- **issue statuses/types/priorities** are stored rows (not enums hard-coded
  everywhere) so workflows can be extended; each issue references them by id.
- Issue keys (`DOC-124`) are generated transactionally from a per-project
  `issue_counter` column using `SELECT ... FOR UPDATE`.

See [database.md](database.md) for columns and indexes.

## 3. Roles & permission matrix

Two levels of role:

- **Global role** on `users`: `admin`, `project_manager`, `member`, `viewer`.
- **Project role** on `project_members`: `manager`, `member` (who may create/assign
  within a project). Admins bypass project membership.

Visibility in V1 is **global**: every authenticated non-deactivated user can *read*
every project and issue. Membership governs *write* actions.

| Action | Admin | Project Manager¹ | Member¹ | Viewer |
|---|:--:|:--:|:--:|:--:|
| View projects / issues / board | ✅ | ✅ | ✅ | ✅ |
| Global search | ✅ | ✅ | ✅ | ✅ |
| Create project | ✅ | ❌ | ❌ | ❌ |
| Edit / archive project | ✅ | ✅ (managed) | ❌ | ❌ |
| Manage project members | ✅ | ✅ (managed) | ❌ | ❌ |
| Create issue | ✅ | ✅ (member) | ✅ (member) | ❌ |
| Edit issue / change status / assign | ✅ | ✅ (member) | ✅ (member) | ❌ |
| Comment | ✅ | ✅ | ✅ (member) | ❌ |
| Upload attachment | ✅ | ✅ | ✅ (member) | ❌ |
| Manage labels / issue types | ✅ | ✅ (project labels) | ❌ | ❌ |
| Invite / deactivate users, assign roles | ✅ | ❌ | ❌ | ❌ |
| View audit log | ✅ | ❌ | ❌ | ❌ |

¹ "managed" = the project the user is a manager of. "member" = a project they
belong to (as manager or member). Every mutation is authorized **server-side**;
the frontend only hides controls for UX.

## 4. Frontend route map

```
/login
/invite/[token]
/forgot-password  /reset-password/[token]
/dashboard
/my-issues
/notifications
/projects
/projects/[key]                 → overview
/projects/[key]/board
/projects/[key]/issues          (list view, bulk ops, saved views)
/projects/[key]/activity
/projects/[key]/settings
/issues/[key]                   (full issue page; drawer used inline elsewhere)
/team
/settings                       (account + notification prefs)
/admin/users
/admin/audit
```

## 5. API module map

Base path `/api`. Consistent JSON errors, pagination, filtering, sorting.

```
/auth            login, logout, me, refresh, forgot/reset password
/invitations     create, list, accept(token), revoke
/users           list, get, patch, deactivate  (admin-guarded where needed)
/projects        CRUD, archive, members
/issues          CRUD, archive, filter/sort/search, relationships, subtasks
/issues/{id}/comments
/issues/{id}/attachments        + /attachments/{id} (authenticated download)
/issues/{id}/activity
/labels          CRUD
/meta            statuses, types, priorities (reference data)
/notifications   list, read, read-all, preferences
/audit-logs      admin only, filterable
/dashboard       aggregated operational metrics + throughput
/search          global search (Postgres full-text)
/saved-views     named, reusable issue filters
/ws              WebSocket live updates
```

Full endpoint list: [api.md](api.md).

## 6. Notification abstraction

`NotificationService` builds an in-app `notifications` row and dispatches to
registered `NotificationChannel`s. V1 ships `EmailNotificationChannel` (SMTP,
templated, sent on a background task so a mail failure never fails the request).
`SlackNotificationChannel` / `WebhookNotificationChannel` can be registered later
without touching call sites.

## 6b. Realtime & background jobs

**Realtime** (`app/realtime/`): domain services call `publish(event)`; a
`ConnectionManager` fans it out to connected WebSocket clients. Services never
import WebSocket types, and publishing is a no-op when nobody is listening, so
realtime stays strictly additive — the REST API remains the source of truth and
the UI treats events as cache-invalidation hints.

**Due-date reminders** (`app/services/reminders.py`): an asyncio loop started in
the FastAPI lifespan scans daily for open, assigned issues that are due soon or
overdue and notifies the assignee. `issues.last_due_reminder_on` makes it
idempotent across restarts.

Both are deliberately in-process (no Celery/Redis) to keep the footprint small.
Both assume **one backend replica**; scaling out requires Redis pub/sub for
realtime and a leader lock for the reminder job. The in-memory auth rate limiter
has the same constraint.

## 7. Security posture

Argon2 password hashing · JWT in httpOnly+Secure+SameSite cookies · CSRF
double-submit token on mutations · server-side RBAC on every mutation · Pydantic
input validation · SQLAlchemy parameterized queries (no string SQL) · per-IP auth
rate limiting + per-account failed-login lockout · safe file uploads (size/MIME/extension checks,
path-traversal-proof storage, authenticated download) · security headers + HTTPS
at the proxy · secrets only via env. See [deployment.md](deployment.md).

## 8. Phase plan & status

- **Phase 0** Architecture — this document ✅
- **Phase 1** Foundation: repo, docker-compose, config, DB, migrations, health, logging
- **Phase 2** Auth & users: login/logout, JWT, invitations, password reset, RBAC
- **Phase 3** Projects: CRUD, archive, members, overview, activity
- **Phase 4** Issues: CRUD, keys, statuses/types/priorities, labels, subtasks, relationships, comments, attachments
- **Phase 5** Views: Kanban, list, my-issues, search, filters, bulk ops, saved views
- **Phase 6** Notifications & audit
- **Phase 7** Dashboard & polish: command palette, shortcuts, empty/loading/error states
- **Phase 8** Production: HTTPS, backups, docs

Each phase keeps the system runnable.
