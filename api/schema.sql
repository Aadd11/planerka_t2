CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(32) UNIQUE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    registered BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    full_name TEXT NOT NULL,
    alliance TEXT NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'employee',
    employee_category VARCHAR(64) NOT NULL DEFAULT 'adult',
    weekly_norm_hours DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(128) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS collection_periods (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    alliance TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    deadline TIMESTAMPTZ NOT NULL,
    is_open BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS schedule_entries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period_id INTEGER NOT NULL REFERENCES collection_periods(id) ON DELETE CASCADE,
    day DATE NOT NULL,
    status VARCHAR(128) NOT NULL,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_schedule_user_period_day UNIQUE (user_id, period_id, day)
);

CREATE TABLE IF NOT EXISTS schedule_submissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period_id INTEGER NOT NULL REFERENCES collection_periods(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    submitted_at TIMESTAMPTZ,
    employee_comment TEXT,
    manager_comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_submission_user_period UNIQUE (user_id, period_id)
);

CREATE TABLE IF NOT EXISTS schedule_templates (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    work_days INTEGER NOT NULL,
    rest_days INTEGER NOT NULL,
    shift_start VARCHAR(5) NOT NULL,
    shift_end VARCHAR(5) NOT NULL,
    has_break BOOLEAN NOT NULL DEFAULT FALSE,
    break_start VARCHAR(5),
    break_end VARCHAR(5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
