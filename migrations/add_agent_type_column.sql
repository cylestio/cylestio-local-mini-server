-- This script adds agent_type, description, and configuration columns to the agents table
-- if they don't already exist.

-- Note: SQLite doesn't allow checking if a column exists and conditionally adding it in pure SQL.
-- Therefore we must create a safe migration with appropriate error checking in the Python script.

-- Add agent_type column
ALTER TABLE agents ADD COLUMN agent_type VARCHAR DEFAULT NULL;

-- Add description column
ALTER TABLE agents ADD COLUMN description VARCHAR DEFAULT NULL;

-- Add configuration column
ALTER TABLE agents ADD COLUMN configuration JSON DEFAULT NULL;

-- Create index on agent_type column
CREATE INDEX IF NOT EXISTS ix_agents_agent_type ON agents (agent_type); 