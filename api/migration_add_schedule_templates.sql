-- Migration: Add schedule_templates table
-- Date: 2026-04-05

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
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schedule_templates_user_id ON schedule_templates(user_id);
