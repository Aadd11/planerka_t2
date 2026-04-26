# API Documentation

This document reflects the backend behavior verified on 2026-04-26.

Base URL in local Docker setup:

```text
http://localhost:8000
```

## Authentication

- Protected endpoints use `Authorization: Bearer <token>`.
- `manager` and `admin` routes also require the user to be verified.
- `admin` bypasses role restrictions enforced by `require_role(...)`.

## Roles

- `employee`
- `manager`
- `admin`

## Core Domain Notes

- Group scoping is implemented through the `alliance` field.
- A schedule is stored per user and per collection period.
- Schedule day types:
  - `work`
  - `day_off`
  - `vacation`
  - `holiday`
  - `unavailable`
- Submission statuses:
  - `draft`
  - `submitted`

## System

### `GET /health`

- Auth: no
- Response: service health status and current app environment

Example response:

```json
{
  "status": "ok",
  "env": "production"
}
```

## Auth

### `POST /auth/register`

- Auth: no
- Purpose: create a new employee account
- Request body:

```json
{
  "full_name": "Ivan Ivanov",
  "email": "ivan@example.com",
  "password": "password123",
  "alliance": "Retail East",
  "employeeCategory": "adult"
}
```

- Rules:
  - password must be at least 8 characters
  - password must not exceed 72 bytes
  - duplicate email returns `400`
- Response: created user
- Important:
  - new users are created with `role=employee`
  - new users are created with `isVerified=false`
  - a verification token row is created in the database, but the raw token is not returned by this endpoint

### `POST /auth/login`

- Auth: no
- Purpose: obtain a bearer token
- Accepted formats:
  - JSON: `{ "email": "...", "password": "..." }`
  - form data: `username` or `email`, plus `password`
- Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

- Errors:
  - `400` for wrong credentials
  - `400` if form payload is missing both identity and password

### `POST /auth/verify`

- Auth: no
- Purpose: confirm a user account by verification token
- Request body:

```json
{
  "token": "raw-verification-token"
}
```

- Response: verified user object
- Errors:
  - `400` invalid token
  - `400` expired token
- Important:
  - token storage is hashed in the database
  - the raw token must come from an out-of-band source because `/auth/register` does not return it

### `GET /auth/me`

- Auth: bearer token
- Purpose: return current authenticated user
- Response: current user profile

## Periods

### `GET /periods/current`

- Auth: authenticated active user
- Purpose: return the current open period for the user’s `alliance`
- Response:
  - current period object
  - `null` if the user has no alliance or no open period for that alliance

### `POST /periods`

- Auth: verified `manager` or `admin`
- Purpose: create a new collection period
- Request body:

```json
{
  "name": "May 2026",
  "alliance": "Retail East",
  "periodStart": "2026-05-01",
  "periodEnd": "2026-05-14",
  "deadline": "2026-04-30T18:00:00Z"
}
```

- Rules:
  - `manager` may only create a period for their own `alliance`
  - if `alliance` is omitted, the current user’s `alliance` is used
  - creating a new open period closes previous open periods for the same alliance
- Response: created period with computed `holidays`

### `POST /periods/{period_id}/close`

- Auth: verified `manager` or `admin`
- Purpose: close a period
- Rules:
  - `manager` may close only periods of their own `alliance`
- Errors:
  - `404` period not found
  - `403` manager has no access to that period

### `GET /periods/current/stats`

- Auth: verified `manager` or `admin`
- Purpose: statistics for the current open period of the current user’s `alliance`
- Response:

```json
{
  "totalEmployees": 0,
  "submittedCount": 0,
  "pendingCount": 0
}
```

- Notes:
  - counts only verified employees
  - if there is no open period, all counters are zero

### `GET /periods/current/submissions`

- Auth: verified `manager` or `admin`
- Purpose: split employees into `submitted` and `pending` for the current open period
- Response shape:

```json
{
  "submitted": [],
  "pending": []
}
```

- Notes:
  - employees without a submission row are treated as `draft`
  - pending list includes non-submitted employees

### `GET /periods/history`

- Auth: verified `manager` or `admin`
- Purpose: list past and current periods
- Scope:
  - `admin` sees all periods
  - `manager` sees only periods of their own `alliance`

## Schedules

### `GET /schedules/me`

- Auth: verified user
- Query:
  - optional `period_id`
- Purpose: return the current user’s schedule bundle
- Response includes:
  - `user`
  - `period`
  - `submission`
  - `entries`
  - `validation`

- Notes:
  - if `period_id` is omitted, only an open period is accepted
  - a draft submission row is auto-created if missing

### `PUT /schedules/me`

- Auth: verified user
- Query:
  - optional `period_id`
- Purpose: save schedule as draft
- Request body:

```json
{
  "employeeComment": "Can work mornings",
  "days": {
    "2026-05-04": {
      "dayType": "work",
      "segments": [
        { "start": "09:00", "end": "13:00" }
      ]
    },
    "2026-05-05": {
      "dayType": "day_off",
      "segments": []
    }
  }
}
```

- Behavior:
  - existing entries for the user and period are replaced
  - submission status is reset to `draft`
  - existing manager day comments are preserved
  - user cannot overwrite manager day comments through this endpoint

### `POST /schedules/me/submit`

- Auth: verified user
- Query:
  - optional `period_id`
- Purpose: submit the schedule after backend validation
- Success response: same bundle shape as `GET /schedules/me`
- Errors:
  - `400` if validation contains errors

Error shape:

```json
{
  "detail": {
    "message": "График не отправлен: есть ошибки валидации.",
    "validation": {
      "isValid": false,
      "summary": {
        "totalHours": 0,
        "weeklyHours": {},
        "daysOffCount": {}
      },
      "issues": []
    }
  }
}
```

### `POST /schedules/validate`

- Auth: verified user
- Purpose: validate a candidate schedule without saving it
- Request body:

```json
{
  "periodId": 1,
  "employeeCategory": "adult",
  "days": {
    "2026-05-04": {
      "dayType": "work",
      "segments": [
        { "start": "09:00", "end": "12:00" },
        { "start": "13:00", "end": "18:00" }
      ]
    }
  }
}
```

- Validation covers:
  - date inside period
  - valid time format
  - start earlier than end
  - no overlapping segments
  - work day must have segments
  - non-work day must not have segments
  - weekly norms
  - daily norms for minors
  - night work restrictions for minors
  - minimum days off
  - empty schedule detection

### `GET /schedules/by-user/{user_id}`

- Auth: verified `manager` or `admin`
- Query:
  - optional `period_id`
- Purpose: return another user’s schedule bundle
- Rules:
  - `manager` may access only employees from the same `alliance`
  - `admin` may access any user
- Errors:
  - `404` user not found
  - `403` cross-group access denied

## Manager

### `GET /manager/schedules`

- Auth: verified `manager` or `admin`
- Query:
  - optional `period_id`
- Purpose: return the schedule matrix for a period
- Response:
  - `period`
  - `items[]`, each item containing `user`, `submission`, `entries`, `validation`

- Scope:
  - `manager` sees verified employees from their own `alliance`
  - `admin` sees verified employees only for the selected period’s `alliance`

### `GET /manager/comments`

- Auth: verified `manager` or `admin`
- Query:
  - `user_id`
  - `period_id`
- Purpose: return manager schedule-level and day-level comments for one employee
- Response:

```json
{
  "userId": 12,
  "periodId": 3,
  "scheduleComment": "Overall note",
  "dayComments": {
    "2026-05-04": "Cover lunch peak"
  }
}
```

### `POST /manager/comments`

- Auth: verified `manager` or `admin`
- Purpose: create or update a manager comment
- Request body for schedule-level comment:

```json
{
  "userId": 12,
  "periodId": 3,
  "comment": "Overall note"
}
```

- Request body for day-level comment:

```json
{
  "userId": 12,
  "periodId": 3,
  "date": "2026-05-04",
  "comment": "Cover lunch peak"
}
```

- Notes:
  - if a day entry does not exist, the endpoint creates one with `dayType=unavailable`
  - day comment date must be inside the period

### `GET /manager/coverage`

- Auth: verified `manager` or `admin`
- Query:
  - `day`
  - optional `period_id`
- Purpose: hourly coverage for a selected day
- Response:
  - `day`
  - `periodId`
  - `buckets[]` for `00:00` through `23:00`

Bucket shape:

```json
{
  "hour": "09:00",
  "count": 2,
  "users": ["Alice", "Bob"]
}
```

- Error:
  - `400` if the requested day is outside the selected period

## Admin

### `GET /admin/users`

- Auth: verified `manager` or `admin`
- Query filters:
  - `verified`
  - `alliance`
  - `role`
- Scope:
  - `manager` sees only users from their own `alliance`
  - `admin` may filter by any `alliance`
- Error:
  - `403` if called by an ordinary employee

### `PUT /admin/users/{user_id}/verify`

- Auth: verified `admin`
- Purpose: mark a user as verified
- Errors:
  - `404` user not found

### `PUT /admin/users/{user_id}/role`

- Auth: verified `admin`
- Purpose: change user role
- Request body:

```json
{
  "role": "manager"
}
```

- Errors:
  - `404` user not found

### `PUT /admin/users/{user_id}/alliance`

- Auth: verified `admin`
- Purpose: change user group
- Request body:

```json
{
  "alliance": "Retail West"
}
```

- Notes:
  - for employees, weekly norm hours are recalculated from `employee_category`

### `DELETE /admin/users/{user_id}`

- Auth: verified `admin`
- Purpose: delete a user
- Response: `204 No Content`
- Errors:
  - `404` user not found

## Export

### `GET /export/schedule`

- Auth: verified `manager` or `admin`
- Query:
  - optional `period_id`
- Purpose: export schedule data to Excel
- Response:
  - file download
  - MIME type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

- Scope:
  - `manager` may export only their own `alliance`
  - `admin` may export any period

## Templates

### `GET /templates`

- Auth: verified user
- Purpose: list current user’s templates

### `POST /templates`

- Auth: verified user
- Purpose: create a reusable schedule template
- Request body:

```json
{
  "name": "2/2 Day Shift",
  "workDays": 2,
  "restDays": 2,
  "shiftStart": "09:00",
  "shiftEnd": "18:00",
  "hasBreak": true,
  "breakStart": "13:00",
  "breakEnd": "14:00"
}
```

- Validation:
  - `workDays` from 1 to 7
  - `restDays` from 0 to 7

### `DELETE /templates/{template_id}`

- Auth: verified user
- Purpose: delete one of the current user’s templates
- Response: `204 No Content`
- Errors:
  - `404` template not found or does not belong to the current user

## Common Error Patterns

- `401` invalid or missing bearer token
- `403` unverified user or insufficient role
- `404` missing user, period, or template
- `400` business rule violation or invalid workflow state

## Verified Docker Test Command

```bash
docker compose exec backend python -m pytest tests/test_backend.py
```
