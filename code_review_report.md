# Code Review Report

Date: 2026-04-26
Scope: backend API implementation under `api/`

## Findings

### 1. `GET` endpoints mutate persistent state by auto-creating submissions

Severity: high

Files:
- [api/routes_schedule.py](/home/aadd/development/planerka_t2/api/routes_schedule.py:49)
- [api/routes_manager.py](/home/aadd/development/planerka_t2/api/routes_manager.py:77)
- [api/routes_export.py](/home/aadd/development/planerka_t2/api/routes_export.py:75)
- [api/schedule_service.py](/home/aadd/development/planerka_t2/api/schedule_service.py:119)

Why it matters:
- `get_or_create_submission()` is called from read paths such as `GET /schedules/me`, `GET /manager/schedules`, `GET /manager/comments`, and `GET /export/schedule`.
- That means simply viewing a schedule or exporting data inserts `schedule_submissions` rows with `draft` status.
- This violates HTTP semantics for `GET`, makes analytics depend on reads, and can create misleading audit/history artifacts. A manager opening a dashboard should not change employee workflow state.

Impact:
- Hidden DB writes from read-only traffic.
- Draft submissions appear even when an employee never started a schedule.
- Future reporting and admin investigations will not be able to distinguish “never touched” from “viewed by someone else”.

Recommendation:
- Split submission loading into `get_submission()` for read endpoints and only create rows during write operations such as `PUT /schedules/me` or `POST /schedules/me/submit`.

### 2. Employee updates can delete manager day comments on omitted days

Severity: high

File:
- [api/routes_schedule.py](/home/aadd/development/planerka_t2/api/routes_schedule.py:82)

Why it matters:
- `_persist_schedule()` deletes all existing `ScheduleEntry` rows for the user and period before recreating them from `payload.days`.
- Manager day comments are preserved only for days present in the incoming payload.
- If the client sends a partial schedule update or simply omits a previously commented day, that day row is deleted and the manager’s comment disappears.

Impact:
- Employees can unintentionally erase manager feedback.
- The business rule “employee cannot edit manager comments” is only partially enforced. They cannot overwrite a preserved comment on the same day, but they can still remove it by omission.

Recommendation:
- Either require full-period replacement explicitly and reject partial payloads, or merge updates day-by-day without deleting untouched entries.
- If full replacement remains, preserve manager-comment-only entries when rebuilding the schedule.

### 3. Coverage calculation overcounts the final hour of each segment

Severity: medium

File:
- [api/routes_manager.py](/home/aadd/development/planerka_t2/api/routes_manager.py:223)

Why it matters:
- Coverage buckets are built with `range(start_hour, end_hour + 1)`.
- For a segment `09:00-11:00`, this counts `09:00`, `10:00`, and `11:00`.
- In normal interval semantics, the employee works until 11:00, not through the entire 11:00-12:00 bucket.

Impact:
- Hourly staffing is overstated by one bucket at every segment boundary.
- Manager decisions based on `coverage` can be wrong, especially around opening/closing hours.

Recommendation:
- Use end-exclusive bucketing.
- If the endpoint is intended to show “active at the start of the hour”, use `range(start_hour, end_hour)`.
- If partial-hour precision matters, derive buckets from minute overlap instead of integer hour boundaries.

### 4. Admin “current stats/submissions” endpoints are effectively scoped to the admin’s own alliance

Severity: medium

File:
- [api/routes_periods.py](/home/aadd/development/planerka_t2/api/routes_periods.py:112)
- [api/routes_periods.py](/home/aadd/development/planerka_t2/api/routes_periods.py:156)

Why it matters:
- `GET /periods/current/stats` and `GET /periods/current/submissions` are available to `admin`, but both hardcode filtering by `current_user.alliance`.
- Admin therefore cannot inspect another alliance’s current open period unless their own user record happens to be assigned to that same alliance.

Impact:
- Admin role is broader in the rest of the codebase than in these endpoints.
- This creates inconsistent behavior relative to `/periods/history`, `/schedules/by-user/{user_id}`, and export access.

Recommendation:
- Either make these endpoints manager-only, or add explicit alliance/period selection for admins and document the intended scope.

### 5. Startup schema creation bypasses migration discipline

Severity: medium

File:
- [api/app.py](/home/aadd/development/planerka_t2/api/app.py:42)

Why it matters:
- `Base.metadata.create_all(bind=engine)` runs on every app startup.
- The project also documents Alembic-based deployment.
- Running `create_all()` in production-like environments undermines migration control and can hide missing migrations during development while still failing to apply real schema changes in production.

Impact:
- Drift between ORM models and the real database schema can go unnoticed.
- Deployments may appear healthy in one environment and fail in another depending on startup order and existing tables.

Recommendation:
- Remove `create_all()` from app startup.
- Keep schema management in migrations and test setup only.

### 6. Template inputs are only range-checked, not time-validated

Severity: medium

File:
- [api/schemas.py](/home/aadd/development/planerka_t2/api/schemas.py:238)

Why it matters:
- `ScheduleTemplateCreate` validates `workDays` and `restDays`, but `shiftStart`, `shiftEnd`, `breakStart`, and `breakEnd` are plain strings.
- Invalid values like `99:99`, `ab:cd`, or a break range outside the shift are accepted.

Impact:
- Invalid template data can be persisted and later break client assumptions or any future template-application feature.

Recommendation:
- Add time-format validators and cross-field checks:
  - valid `HH:MM`
  - `shiftStart < shiftEnd`
  - if `hasBreak`, require both break fields and validate them inside the shift

### 7. Open-period uniqueness is enforced only in application code, not at the data layer

Severity: medium

Files:
- [api/routes_periods.py](/home/aadd/development/planerka_t2/api/routes_periods.py:65)
- [api/models.py](/home/aadd/development/planerka_t2/api/models.py:79)

Why it matters:
- `create_period()` closes existing open periods before inserting a new one, but there is no database constraint preventing two concurrent requests from creating multiple open periods for the same alliance.

Impact:
- Race conditions can violate the core invariant “one active period per alliance”.
- Downstream endpoints that rely on `.first()` over open periods will become nondeterministic.

Recommendation:
- Add a partial unique index for `(alliance)` where `is_open = true` in PostgreSQL.
- Keep the application-side close-then-create logic as secondary protection.

## Coverage Notes

Reviewed areas:
- auth
- schedule persistence and validation
- periods
- manager workflows
- admin workflows
- export
- templates
- app startup/configuration

Test status observed during review:
- Docker test suite passes for the current HTTP coverage.
- The issues above are primarily semantic/state-management problems rather than already-failing test scenarios.

## Suggested Next Steps

1. Remove write side effects from all `GET` endpoints.
2. Fix schedule persistence so manager comments on omitted days cannot be erased.
3. Correct coverage bucket semantics and add a regression test around segment boundaries.
4. Clarify admin scope for current-period analytics endpoints.
5. Move schema lifecycle entirely to migrations.
6. Add schema-level validation for template time fields.
