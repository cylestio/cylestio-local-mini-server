# Cylestio Monitor - Database Schema

This document describes the database schema design for the Cylestio Monitor telemetry processing system.

## Entity-Relationship Diagram

The database schema consists of the following main entities and their relationships:

```
Agent (1) ---- (*) Event
Agent (1) ---- (*) Conversation
Session (1) ---- (*) Conversation

Event (1) ---- (0/1) TokenUsage
Event (1) ---- (*) PerformanceMetric
Event (1) ---- (*) SecurityAlert
Event (1) ---- (*) ContentAnalysis 
Event (1) ---- (0/1) FrameworkDetails
Event (1) ---- (0/1) ModelDetails
Event (1) ---- (0/1) PromptDetails
Event (1) ---- (0/1) ResponseDetails
Event (1) ---- (*) CallStack

Conversation (1) ---- (*) ConversationTurn
ConversationTurn (0/1) ---- (1) Event (request)
ConversationTurn (0/1) ---- (1) Event (response)
```

## Event Types and Their Related Tables

Different event types populate different tables in the database schema:

### LLM_call_start Events
- **agents**: Basic agent information
- **events**: Core event data
- **sessions**: Session tracking
- **security_alerts**: If suspicious content is detected
- **model_details**: If model information is available

### LLM_call_finish Events
- **agents**: Basic agent information
- **events**: Core event data
- **sessions**: Session tracking
- **token_usage**: Token consumption metrics
- **performance_metrics**: Response time measurements
- **model_details**: If model information is available

### monitor_init Events
- **agents**: Basic agent information
- **events**: Core event data
- **sessions**: Session tracking
- **framework_details**: Information about the monitoring framework

### Other Event Types
- **conversation_turns** and **conversations**: Only populated from conversation events
- **content_analysis**: Only populated from content analysis events
- **call_stack**: Only populated from events with call stack information 
- **prompt_details**: Only populated from events with detailed prompt information
- **response_details**: Only populated from events with detailed response information

## Core Tables

### Agent
- Represents an AI agent that is being monitored
- Contains basic information about the agent, such as ID, provider, and type
- Has one-to-many relationships with events and conversations

### Event
- Central table for all telemetry events
- Contains core fields like timestamp, level, event type, and channel
- Stores the raw JSON data and links to normalized data in other tables
- Acts as the hub in a hub-and-spoke model for all event-related data

### Session
- Represents a user session or interaction period
- Contains session metadata and aggregated metrics
- Has one-to-many relationship with conversations

## Data Tables

### TokenUsage
- Stores token usage metrics from LLM calls
- Tracks input, output, and cached tokens
- Supports dashboard metrics for token consumption

### PerformanceMetric
- Contains performance data points like latency and duration
- Used for tracking system performance over time

### SecurityAlert
- Stores security-related alerts and warnings
- Indicates potential security issues in LLM usage

### ContentAnalysis
- Holds content analysis results and metrics
- Used for tracking content quality and conformance

### FrameworkDetails
- Contains information about the LLM frameworks used
- Tracks framework versions, components, and types

## Enhanced Data Tables

### ModelDetails
- Stores detailed information about LLM models
- Includes model configuration, capabilities, and behavior
- Supports filtering and analysis by model characteristics

### PromptDetails
- Contains information about prompts sent to LLMs
- Tracks prompt structure, system messages, and context
- Enables prompt effectiveness analysis

### ResponseDetails
- Stores detailed information about LLM responses
- Tracks features like citations, function calls, and stop reasons
- Supports response quality metrics and analysis

### CallStack
- Contains information about the application call stack
- Enables tracing of code paths that triggered LLM calls
- Supports hierarchical representations of call paths

### Conversation/ConversationTurn
- Models multi-turn conversations with AI agents
- Links related request and response events
- Tracks conversation metrics and turns

## Indexing Strategy

The schema uses the following indexing strategy to optimize query performance:

1. **Primary Keys**: All tables have integer primary keys for efficient joins
2. **Foreign Keys**: All tables with relationships have indexed foreign keys
3. **Frequently Queried Columns**: Columns used in filtering, grouping, or sorting are indexed:
   - `timestamp` in Event table
   - `agent_id` across multiple tables
   - `event_type` in Event table
   - `model_name` in ModelDetails
   - `function_name` in ResponseDetails
   - Categorical fields used for filtering (`level`, `channel`, etc.)
4. **Compound Indexes**: In the full implementation, consider adding compound indexes for common query patterns

## Query Examples

Here are examples of how to query the schema for common dashboard metrics:

1. Token usage by agent over time:
```sql
SELECT 
    e.agent_id, 
    DATE_TRUNC('day', e.timestamp) as day, 
    SUM(tu.input_tokens) as total_input_tokens,
    SUM(tu.output_tokens) as total_output_tokens
FROM events e
JOIN token_usage tu ON e.id = tu.event_id
GROUP BY e.agent_id, day
ORDER BY e.agent_id, day;
```

2. Response latency by model:
```sql
SELECT 
    md.model_name,
    AVG(e.duration_ms) as avg_latency,
    COUNT(*) as call_count
FROM events e
JOIN model_details md ON e.id = md.event_id
WHERE e.event_type = 'model_response'
GROUP BY md.model_name
ORDER BY avg_latency DESC;
```

3. Security alerts by severity:
```sql
SELECT 
    sa.severity,
    COUNT(*) as alert_count
FROM security_alerts sa
GROUP BY sa.severity
ORDER BY 
    CASE 
        WHEN sa.severity = 'critical' THEN 1
        WHEN sa.severity = 'high' THEN 2
        WHEN sa.severity = 'medium' THEN 3
        WHEN sa.severity = 'low' THEN 4
        ELSE 5
    END;
```

4. Most active conversations:
```sql
SELECT 
    c.conversation_id,
    c.agent_id,
    c.turn_count,
    c.total_tokens_used
FROM conversations c
ORDER BY c.turn_count DESC
LIMIT 10;
``` 