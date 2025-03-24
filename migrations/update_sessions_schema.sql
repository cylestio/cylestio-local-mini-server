-- Add new columns to the sessions table
ALTER TABLE sessions ADD COLUMN total_tokens INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE sessions ADD COLUMN total_requests INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE sessions ADD COLUMN total_responses INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE sessions ADD COLUMN avg_latency_ms INTEGER DEFAULT NULL;
ALTER TABLE sessions ADD COLUMN session_metadata JSON DEFAULT NULL; 