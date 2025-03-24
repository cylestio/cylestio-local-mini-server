-- Create agents table with all required columns
CREATE TABLE IF NOT EXISTS agents (
    id INTEGER NOT NULL, 
    agent_id VARCHAR NOT NULL, 
    last_seen DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
    first_seen DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
    llm_provider VARCHAR,
    agent_type VARCHAR,
    description VARCHAR,
    configuration JSON,
    PRIMARY KEY (id)
);

-- Create indexes for agents table
CREATE UNIQUE INDEX IF NOT EXISTS ix_agents_agent_id ON agents (agent_id);
CREATE INDEX IF NOT EXISTS ix_agents_agent_type ON agents (agent_type);

-- Create events table
CREATE TABLE IF NOT EXISTS events (
    id INTEGER NOT NULL, 
    timestamp DATETIME NOT NULL, 
    level VARCHAR NOT NULL, 
    agent_id VARCHAR NOT NULL, 
    event_type VARCHAR NOT NULL, 
    channel VARCHAR NOT NULL, 
    direction VARCHAR, 
    session_id VARCHAR, 
    relationship_id VARCHAR, 
    data JSON, 
    duration_ms FLOAT, 
    caller_file VARCHAR, 
    caller_line INTEGER, 
    caller_function VARCHAR, 
    is_processed BOOLEAN NOT NULL DEFAULT 0, 
    alert VARCHAR, 
    PRIMARY KEY (id), 
    FOREIGN KEY(agent_id) REFERENCES agents (agent_id)
);

-- Create indexes for events table
CREATE INDEX IF NOT EXISTS ix_events_timestamp ON events (timestamp);
CREATE INDEX IF NOT EXISTS ix_events_level ON events (level);
CREATE INDEX IF NOT EXISTS ix_events_agent_id ON events (agent_id);
CREATE INDEX IF NOT EXISTS ix_events_event_type ON events (event_type);
CREATE INDEX IF NOT EXISTS ix_events_channel ON events (channel);
CREATE INDEX IF NOT EXISTS ix_events_direction ON events (direction);
CREATE INDEX IF NOT EXISTS ix_events_session_id ON events (session_id);
CREATE INDEX IF NOT EXISTS ix_events_relationship_id ON events (relationship_id);
CREATE INDEX IF NOT EXISTS ix_events_duration_ms ON events (duration_ms);
CREATE INDEX IF NOT EXISTS ix_events_is_processed ON events (is_processed);
CREATE INDEX IF NOT EXISTS ix_events_alert ON events (alert);

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER NOT NULL, 
    session_id VARCHAR NOT NULL, 
    agent_id VARCHAR NOT NULL, 
    start_time DATETIME NOT NULL, 
    end_time DATETIME, 
    total_events INTEGER DEFAULT 0 NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(agent_id) REFERENCES agents (agent_id)
);

-- Create indexes for sessions table
CREATE UNIQUE INDEX IF NOT EXISTS ix_sessions_session_id ON sessions (session_id);
CREATE INDEX IF NOT EXISTS ix_sessions_agent_id ON sessions (agent_id);
CREATE INDEX IF NOT EXISTS ix_sessions_start_time ON sessions (start_time);
CREATE INDEX IF NOT EXISTS ix_sessions_end_time ON sessions (end_time); 