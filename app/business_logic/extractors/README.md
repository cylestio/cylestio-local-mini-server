# Cylestio Monitor Extraction Framework

The Extraction Framework is a core component of the Cylestio Monitor system that provides utilities and classes for extracting structured data from JSON telemetry events.

## Overview

The framework consists of:

1. **BaseExtractor** - Base class providing common extraction utilities
2. **ExtractorRegistry** - Registry for managing and discovering extractors
3. **Utility Functions** - Helper functions for JSON navigation and data conversion

## Using BaseExtractor

The `BaseExtractor` class provides the foundation for all extractors. It offers methods for safely extracting data from nested JSON structures, performing type conversions, and handling errors.

### Creating a Custom Extractor

To create a custom extractor:

```python
from app.business_logic.extractors import BaseExtractor, extractor_registry

class MyCustomExtractor(BaseExtractor):
    def can_process(self, event) -> bool:
        # Determine if this extractor can process the given event
        return event.event_type in ["my_event_type_1", "my_event_type_2"]
        
    async def process(self, event, db_session) -> None:
        # Extract data from the event
        user_id = self.safe_extract(event.data, "user.id")
        timestamp = self.extract_and_convert(event.data, "timestamp", datetime)
        
        # Process the extracted data
        # ...
        
        # Save to database
        # ...

# Register the extractor
extractor_registry.register(MyCustomExtractor())
```

### Key BaseExtractor Methods

- **safe_extract(data, path, default=None)** - Safely extract a value from nested JSON using a dot-notation path or list of keys
- **multi_path_extract(data, paths, default=None)** - Try multiple paths to extract a value
- **convert_value(value, target_type, default=None)** - Convert a value to a target type with error handling
- **extract_and_convert(data, path, target_type, default=None)** - Extract and convert a value in one step
- **get_list_item(data_list, index, default=None)** - Safely get an item from a list by index
- **extract_nested_structures(data, path, process_fn)** - Extract and process a nested structure

## ExtractorRegistry

The `ExtractorRegistry` manages all registered extractors and provides methods to access them.

### Registering Extractors

```python
from app.business_logic.extractors import extractor_registry

# Register an extractor
extractor_registry.register(MyExtractor())

# Register for a specific event type
extractor_registry.register_for_event_type("custom_event", MyExtractor())
```

### Using the Registry

```python
# Get all registered extractors
all_extractors = extractor_registry.get_all_extractors()

# Get extractors for a specific event
applicable_extractors = extractor_registry.get_extractors_for_event(event)

# Get an extractor by name
extractor = extractor_registry.get_extractor_by_name("MyExtractor")
```

## Utility Functions

The framework includes utility functions for common JSON operations:

- **find_paths_with_key(data, target_key)** - Find all paths to a specific key
- **find_values_by_key(data, target_key)** - Find all values for a specific key
- **flatten_json(data, delimiter='.')** - Flatten a nested JSON into a flat dictionary
- **normalize_string(value)** - Normalize a string value (lowercase, trim whitespace)
- **extract_datetime(value)** - Extract and parse a datetime from various formats
- **extract_numeric_values(text)** - Extract all numeric values from a text string
- **merge_dictionaries(dict1, dict2, overwrite=True)** - Merge two dictionaries recursively
- **extract_schema_fields(data, schema_fields)** - Extract fields based on a schema mapping
- **get_nested_value(data, path, default=None)** - Get a value using a dot-notation path

## Example: Handling JSON Variations

The framework is designed to handle variations in JSON structure. For example:

```python
# Try multiple possible paths for a field
value = self.multi_path_extract(
    event.data, 
    ["response.text", "response.content", "response.message"]
)

# Extract based on a schema mapping
schema = {
    "user_name": ["user.name", "user.username", "username"],
    "user_id": ["user.id", "user_id", "id"],
    "timestamp": "timestamp"
}
extracted = extract_schema_fields(event.data, schema)
```

## Error Handling

The framework provides built-in error handling with logging:

```python
# Safe method that will handle errors and log them
success, error = self.safe_process(event, db_session)
if not success:
    # Handle error
    pass
```

## Best Practices

1. **Always handle potential None values** - Use default values or handle None cases explicitly
2. **Use type conversion utilities** - For safe type conversion with error handling
3. **Try multiple paths for important fields** - To handle variations in JSON structure
4. **Log extraction failures** - For easier debugging
5. **Keep extractors focused** - Each extractor should handle a specific aspect of the data

## Adding New Extractors to the System

1. Create a new file in `app/business_logic/extractors/`
2. Define your extractor class extending `BaseExtractor`
3. Implement the `can_process()` and `process()` methods
4. Register your extractor in `app/business_logic/extractors/__init__.py`

By following these guidelines, your extractors will integrate seamlessly with the broader Cylestio Monitor system. 