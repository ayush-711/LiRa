# API reference

Base path: `/api`. Interactive docs (OpenAPI/Swagger): `/api/docs`.

## Conventions

- **Auth**: session JWT in an httpOnly cookie (set on login/invite-accept). A
  readable `lira_csrf` cookie must be echoed in the `X-CSRF-Token` header on every
  mutating request (POST/PATCH/DELETE). API clients may instead send
  `Authorization: Bearer <access_token>` (bypasses CSRF).
- **Errors**: always `{"error": {"code": "...", "message": "...", "details"?: ...}}`.
- **Pagination**: list endpoints that can grow take `limit` (≤200) and `offset`,
  and return `{items, total, limit, offset}`.
- **Timestamps**: ISO-8601 UTC.

## Auth
| Method | Path | Notes |
|---|---|---|
| POST | `/auth/login` | `{email, password}` → sets cookies, returns `{user, csrf_token}` |
| POST | `/auth/logout` | clears cookies |
| GET | `/auth/me` | current user |
| POST | `/auth/forgot-password` | `{email}` — always 200 (no enumeration) |
| POST | `/auth/reset-password` | `{token, new_password}` |

## Invitations (admin)
`POST /invitations` · `GET /invitations` · `GET /invitations/{token}` (public info)
· `POST /invitations/{token}/accept` · `POST /invitations/{id}/revoke`

## Users
`GET /users` (with workload stats) · `GET /users/{id}` ·
`PATCH /users/{id}/role` (admin) · `POST /users/{id}/deactivate|reactivate` (admin)
· `PATCH /account/profile` · `POST /account/password` ·
`GET|PATCH /account/notification-preferences`

## Projects
`GET|POST /projects` · `GET|PATCH /projects/{key}` · `POST /projects/{key}/archive`
· `GET /projects/{key}/stats` · `POST /projects/{key}/unarchive` (admin) · `GET|POST /projects/{key}/members` ·
`DELETE /projects/{key}/members/{user_id}` · `GET /projects/{key}/activity` ·
`GET /projects/{key}/board`

## Issues
`GET /issues` (filter/sort/paginate) · `POST /issues` · `GET|PATCH /issues/{key}` ·
`POST /issues/{key}/move` · `POST /issues/{key}/archive` · `GET /issues/{key}/subtasks`
· `POST /issues/bulk` — apply one change to up to 100 issues; each is authorized,
activity-logged and audited individually, and per-issue failures are returned in
`failed[]` rather than aborting the batch.

**Filters** on `GET /issues`: `project`, `assignee` (csv ids), `reporter`, `status`,
`priority`, `type`, `label`, `parent_id`, `mine`, `unassigned`, `overdue`,
`due_before`, `search`, `include_archived`, `include_subtasks`, `sort`
(`updated|created|due|key|title`), `order` (`asc|desc`), `limit`, `offset`.

## Comments / Activity
`GET|POST /issues/{key}/comments` · `PATCH|DELETE /comments/{id}` ·
`GET /issues/{key}/activity`

## Relationships
`GET|POST /issues/{key}/relationships` · `DELETE /relationships/{id}`

## Attachments
`GET|POST /issues/{key}/attachments` · `GET /attachments/{id}/download` (authenticated)
· `DELETE /attachments/{id}`

## Labels / Meta
`GET|POST /labels` · `PATCH /labels/{id}` · `GET /meta` (statuses, types, priorities)

## Views
`GET /my-issues` (grouped buckets)

## Notifications
`GET /notifications` · `GET /notifications/unread-count` ·
`POST /notifications/{id}/read` · `POST /notifications/read-all`

## Saved views
`GET /saved-views[?project_id=]` (own + shared) · `POST /saved-views` ·
`PATCH|DELETE /saved-views/{id}` (owner only)

## Realtime
`WS /api/ws` — authenticated via the session cookie (or `?token=`). Emits
`issue.created|updated|moved|archived`, `comment.added`, `notification`.
Events are **cache-invalidation hints**: clients refetch over REST rather than
trusting the payload, so a dropped or duplicated event can't corrupt state.
Send `ping` to keep the connection warm.

## Dashboard / Search / Audit
`GET /dashboard` (includes 8-week `throughput`) · `GET /search?q=` (PostgreSQL
full-text with stemming; ILIKE fallback) · `GET /audit-logs` (admin; filter by
`actor_id`, `action`, `entity_type`, `date_from`, `date_to`)

## Example error
```json
{ "error": { "code": "ISSUE_NOT_FOUND", "message": "Issue DOC-124 was not found" } }
```
