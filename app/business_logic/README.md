# Cylestio Monitor - Data Extraction Framework

This module provides a framework for extracting structured data from JSON event records sent by monitoring SDKs. The framework is designed to be simple, modular, and extensible.

## Architecture

The extraction framework is built around these key components:

1. **Event Processor**: Coordinates the application of extractors to events
2. **Extractors**: Individual modules that extract specific types of data from events
3. **Data Models**: SQLAlchemy models that store the extracted data

## Extractors

The following extractors are included:

- **CommonExtractor**: Extracts common fields across all event types (agent, session)
- **TokenUsageExtractor**: Extracts token usage metrics from LLM calls
- **PerformanceExtractor**: Extracts performance metrics (duration, latency)
- **SecurityExtractor**: Extracts security alerts and warnings
- **ModelInfoExtractor**: Extracts information about LLMs and frameworks

## Adding a New Extractor

1. Create a new Python file in the `extractors` directory
2. Implement a class that inherits from `BaseExtractor`
3. Implement the `can_process` and `process` methods
4. Register your extractor in `__init__.py`

Example:

```python
from app.business_logic.extractors.base import BaseExtractor

class MyExtractor(BaseExtractor):
    def can_process(self, event) -> bool:
        return event.event_type == "my_event_type"
        
    async def process(self, event, db_session) -> None:
        # Extract data and save to database
        # ...
```

## Data Flow

1. JSON event records are ingested into the system
2. The `EventProcessor` determines which extractors to apply
3. Each applicable extractor pulls data from the JSON and creates relational records
4. The extracted data is committed to the database

## Best Practices

1. **Keep extractors focused**: Each extractor should handle a specific type of data
2. **Handle variations**: Account for different JSON structures in different event types
3. **Graceful failure**: Log errors but don't let one extractor failure break the whole pipeline
4. **Performance**: Minimize database queries in extractors

## Current Implementation

This is an MVP implementation focused on extracting the most important data for dashboard visualizations:

- Token usage metrics
- Performance metrics
- Model and framework information
- Security alerts

Future enhancements may include more sophisticated content analysis, conversation tracking, and advanced metrics calculation. 