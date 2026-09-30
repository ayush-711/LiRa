# Feature inventory, limitations & roadmap

## Feature inventory

### Auth & access
- Invitation-only registration (hashed, single-use, expiring tokens)
- Email/password login with Argon2 hashing, failed-login lockout
- **Per-IP rate limiting** on auth endpoints (complements per-account lockout)
- Session JWT in httpOnly + SameSite cookies; CSRF double-submit on mutations
- Password reset (no user enumeration)
- Four global roles + per-project roles; server-side authorization on every mutation

### Projects
- Create (admin), edit, **archive and restore**, members with roles, overview stats, activity
- Transactional, per-project issue-key generation (`DOC-124`)

### Issues
- Full CRUD, archive; type, status, priority, assignee, reporter, labels, due date, **estimate**
- Subtasks with progress; relationships (blocks / blocked-by / relates-to)
- **Markdown** descriptions and comments (rendered, with write/preview toggle)
- Comments with **@mention autocomplete** that inserts server-resolvable handles
- Attachments (safe local storage, authenticated download)
- Inline editing; immutable activity feed
- **Bulk operations**: multi-select → status / priority / assignee / add label / archive

### Views
- Kanban board with drag-and-drop, optimistic updates, per-column quick-create, filters
- List view with search, filter, sort, pagination, bulk selection
- **Saved views** — name and reuse a set of filters; optionally share with the team
- My Issues (bucketed: overdue / urgent / in-progress / ready-for-QA / upcoming / completed)
- Global search + ⌘K command palette; keyboard shortcuts with a **`?` help dialog**

### Operations
- Dashboard: overview, personal, issues-by-status, project progress, recent activity,
  **throughput** (issues completed per week, 8-week window)
- Team page with workload stats
- In-app + email notifications with per-user preferences; pluggable channels
- **Due-date reminders** — daily job emails assignees about due-soon/overdue issues,
  idempotent via `issues.last_due_reminder_on`
- **Live updates over WebSocket** — board/issue/comment/notification changes propagate
  without a refresh
- Admin audit log (filterable, paginated); user & invitation management

### Interface
- Warm "Japandi" design system with **light / dark / system** themes (no-flash, persisted)
- Responsive down to mobile, including a **slide-over navigation drawer**
- Empty, loading and error states throughout

### Platform
- FastAPI modular monolith; Next.js frontend; PostgreSQL; Alembic migrations
- **PostgreSQL full-text search** (GIN index, stemming) with ILIKE fallback
- Docker Compose + Caddy (automatic HTTPS); structured logging; health check
- **CI** (GitHub Actions): backend tests, frontend typecheck/unit/build, E2E

## Testing

| Suite | Count | What it covers |
|-------|------:|----------------|
| Backend (`pytest`) | 29 | Auth & lockout, permissions matrix, full acceptance workflow, issue-key sequencing, bulk ops, saved views, project restore, rate limiting, due-date reminders |
| Frontend unit (`vitest`) | 21 | Date/overdue logic, formatting, Markdown rendering + XSS escaping, mention autocomplete |
| E2E (`playwright`) | 6 | Login (success + failure), create issue → comment → status change → activity, search, shortcuts, theme persistence |

Backend tests run on in-memory SQLite (no services needed); E2E runs against a
live `docker compose` stack.

## Counting semantics
Open = not Done & not archived · Completed = Done · Overdue = past due & not Done
& not archived. Centralised in `app/services/issue_rules.py` and `dashboard_service`.

## Known limitations
- **Realtime is single-process.** The WebSocket manager fans out in-memory, so
  running multiple backend replicas would need Redis pub/sub. Same for the
  due-date reminder job (it would run once per replica) and the in-memory rate
  limiter. All three are documented at their call sites.
- **Visibility is global** — every authenticated user can read all projects and
  issues, per the original requirement. Private projects are an extension point.
- **No WYSIWYG editor.** Markdown is rendered properly now, but authoring is a
  textarea with preview rather than a rich-text surface.
- **Email delivery is fire-and-forget** — failures are logged, not retried.
- **Avatar upload** isn't implemented (initials are generated instead); the
  `avatar_url` field exists and is rendered when set.
- **Accessibility** is good on labels, focus states and semantics, but modals do
  not yet trap focus, and the custom dropdowns are not full ARIA comboboxes.

## Roadmap
- Focus trapping + full ARIA combobox semantics for dropdowns
- Avatar upload; per-project custom workflows (`issue_statuses.project_id` reserved)
- Private projects / restricted issues
- Redis-backed realtime, reminders and rate limiting for multi-replica deployments
- OAuth / SSO (auth layer is isolated in `app/auth`)
- Slack / Teams channels (the `NotificationChannel` abstraction already exists)
- Cycles/sprints — deliberately **not** built; see note below

### Why cycles/sprints aren't here
The original brief explicitly said not to build complex sprint planning unless it
was naturally useful, and imposing a cadence needs your team's actual process.
What's shipped instead is the process-neutral half: an optional `estimate` field
and a throughput chart, which give delivery signal without forcing a ritual. If
you do work in cycles, that's a deliberate next step rather than an oversight.
