# Backend Verification Report

Date: 2026-04-26

## Scope

- Read project context from:
  - `README.md`
  - `api/README.md`
  - `api/DEPLOY.md`
  - `presentation.md`
- Reworked backend tests to exercise the API through HTTP instead of direct route calls.
- Covered all implemented API endpoints in `api/app.py` and `api/routes_*.py`.
- Verified the suite inside Docker only.

## Test Command

```bash
docker compose exec backend python -m pytest tests/test_backend.py
```

## Result

- Status: passed
- Total tests: 12
- Result: `12 passed`

## What Was Added

- Full HTTP-level endpoint coverage for:
  - `GET /health`
  - `POST /auth/register`
  - `POST /auth/login`
  - `POST /auth/verify`
  - `GET /auth/me`
  - `GET /periods/current`
  - `POST /periods`
  - `POST /periods/{period_id}/close`
  - `GET /periods/current/stats`
  - `GET /periods/current/submissions`
  - `GET /periods/history`
  - `GET /schedules/me`
  - `PUT /schedules/me`
  - `POST /schedules/me/submit`
  - `POST /schedules/validate`
  - `GET /schedules/by-user/{user_id}`
  - `GET /manager/schedules`
  - `GET /manager/comments`
  - `POST /manager/comments`
  - `GET /manager/coverage`
  - `GET /admin/users`
  - `PUT /admin/users/{user_id}/verify`
  - `PUT /admin/users/{user_id}/role`
  - `PUT /admin/users/{user_id}/alliance`
  - `DELETE /admin/users/{user_id}`
  - `GET /export/schedule`
  - `GET /templates`
  - `POST /templates`
  - `DELETE /templates/{template_id}`

## Fixes Made

### 1. `/auth/verify` SQLite datetime bug

Problem:
- verification token expiration comparison crashed with `TypeError: can't compare offset-naive and offset-aware datetimes`

Cause:
- SQLite returned naive datetime values, while the code compared them to `datetime.now(timezone.utc)`.

Fix:
- normalized naive `expires_at` values to UTC before comparison in `api/routes_auth.py`.

### 2. `/schedules/me/submit` invalid error payload

Problem:
- invalid schedule submit could crash while building the `400` response because `date` objects in validation details were not JSON-serializable.

Fix:
- switched validation serialization to `model_dump(..., mode="json")` in `api/routes_schedule.py`.

### 3. Docker test bootstrap

Problem:
- tests failed inside Docker because the backend container uses production-like env defaults and rejected the short test JWT secret during app import.

Fix:
- updated `api/tests/conftest.py` to force:
  - `APP_ENV=test`
  - a long enough `JWT_SECRET_KEY`

## Files Changed

- `api/routes_auth.py`
- `api/routes_schedule.py`
- `api/tests/conftest.py`
- `api/tests/test_backend.py`

## Residual Notes

- Test output still contains dependency deprecation warnings from:
  - SQLAlchemy timestamp defaults using `datetime.utcnow()`
  - `python-jose`
  - `python-multipart` import path inside Starlette
- These warnings do not currently break the API, but they should be cleaned up before future dependency upgrades.
