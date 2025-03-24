"""
Test module for the core extraction framework.

This module contains tests for the BaseExtractor, ExtractorRegistry,
and extraction utility functions.
"""

import pytest
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.business_logic.extractors.base import (
    BaseExtractor, 
    ExtractorRegistry,
)
from app.business_logic.extractors.utils import (
    find_paths_with_key,
    find_values_by_key,
    flatten_json,
    normalize_string,
    extract_datetime,
    extract_numeric_values,
    merge_dictionaries,
    extract_schema_fields,
    get_nested_value
)


class MockExtractor(BaseExtractor):
    """Mock extractor for testing."""
    
    def __init__(self, event_types=None):
        self.event_types = event_types or ["test_event"]
        self.processed_events = []
        
    def can_process(self, event) -> bool:
        return event.event_type in self.event_types
        
    async def process(self, event, db_session) -> None:
        self.processed_events.append(event)


class TestBaseExtractor:
    """Tests for the BaseExtractor class."""
    
    def test_get_name(self):
        """Test getting the name of an extractor."""
        extractor = MockExtractor()
        assert extractor.get_name() == "MockExtractor"
    
    def test_safe_extract_simple(self):
        """Test safe_extract with a simple dictionary."""
        extractor = MockExtractor()
        data = {"key1": "value1", "key2": {"nested": "value2"}}
        
        assert extractor.safe_extract(data, "key1") == "value1"
        assert extractor.safe_extract(data, "key2.nested") == "value2"
        assert extractor.safe_extract(data, "nonexistent") is None
        assert extractor.safe_extract(data, "nonexistent", "default") == "default"
    
    def test_safe_extract_nested(self):
        """Test safe_extract with a deeply nested dictionary."""
        extractor = MockExtractor()
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "value"
                    }
                }
            }
        }
        
        assert extractor.safe_extract(data, "level1.level2.level3.level4") == "value"
        assert extractor.safe_extract(data, ["level1", "level2", "level3", "level4"]) == "value"
        assert extractor.safe_extract(data, "level1.level2.nonexistent") is None
    
    def test_multi_path_extract(self):
        """Test multi_path_extract with multiple path options."""
        extractor = MockExtractor()
        data = {
            "path1": {"value": "value1"},
            "path3": {"value": "value3"}
        }
        
        paths = ["path1.value", "path2.value", "path3.value"]
        assert extractor.multi_path_extract(data, paths) == "value1"
        
        paths = ["path2.value", "path3.value", "path1.value"]
        assert extractor.multi_path_extract(data, paths) == "value3"
        
        paths = ["nonexistent1", "nonexistent2"]
        assert extractor.multi_path_extract(data, paths) is None
        assert extractor.multi_path_extract(data, paths, "default") == "default"
    
    def test_convert_value(self):
        """Test convert_value with various type conversions."""
        extractor = MockExtractor()
        
        # Test string to int
        assert extractor.convert_value("123", int) == 123
        assert extractor.convert_value("not an int", int) is None
        assert extractor.convert_value("not an int", int, 0) == 0
        
        # Test string to bool
        assert extractor.convert_value("true", bool) is True
        assert extractor.convert_value("yes", bool) is True
        assert extractor.convert_value("false", bool) is False
        assert extractor.convert_value("no", bool) is False
        
        # Test string to datetime
        date_str = "2023-01-01T12:00:00"
        expected_date = datetime(2023, 1, 1, 12, 0, 0)
        assert extractor.convert_value(date_str, datetime) == expected_date
    
    def test_extract_and_convert(self):
        """Test extract_and_convert combining extraction and conversion."""
        extractor = MockExtractor()
        data = {
            "string_value": "123",
            "nested": {"value": "456"}
        }
        
        assert extractor.extract_and_convert(data, "string_value", int) == 123
        assert extractor.extract_and_convert(data, "nested.value", int) == 456
        assert extractor.extract_and_convert(data, "nonexistent", int) is None
        assert extractor.extract_and_convert(data, "nonexistent", int, 0) == 0
    
    def test_get_list_item(self):
        """Test get_list_item with various list operations."""
        extractor = MockExtractor()
        data_list = ["item1", "item2", "item3"]
        
        assert extractor.get_list_item(data_list, 0) == "item1"
        assert extractor.get_list_item(data_list, 2) == "item3"
        assert extractor.get_list_item(data_list, 5) is None
        assert extractor.get_list_item(data_list, 5, "default") == "default"
        assert extractor.get_list_item("not a list", 0, "default") == "default"
    
    def test_extract_nested_structures(self):
        """Test extract_nested_structures with a processing function."""
        extractor = MockExtractor()
        data = {
            "items": [1, 2, 3, 4, 5]
        }
        
        # Process function to sum the items
        process_fn = lambda items: sum(items)
        
        assert extractor.extract_nested_structures(data, "items", process_fn) == 15
        assert extractor.extract_nested_structures(data, "nonexistent", process_fn) is None
        
        # Test with a function that raises an exception
        def failing_fn(items):
            raise ValueError("Test error")
            
        assert extractor.extract_nested_structures(data, "items", failing_fn) is None


class TestExtractorRegistry:
    """Tests for the ExtractorRegistry class."""
    
    def test_register_and_get_all(self):
        """Test registering extractors and getting all extractors."""
        registry = ExtractorRegistry()
        extractor1 = MockExtractor(["type1"])
        extractor2 = MockExtractor(["type2"])
        
        registry.register(extractor1)
        registry.register(extractor2)
        
        extractors = registry.get_all_extractors()
        assert len(extractors) == 2
        assert extractor1 in extractors
        assert extractor2 in extractors
    
    def test_register_for_event_type(self):
        """Test registering extractors for specific event types."""
        registry = ExtractorRegistry()
        extractor1 = MockExtractor(["type1"])
        extractor2 = MockExtractor(["type2"])
        
        registry.register_for_event_type("type1", extractor1)
        registry.register_for_event_type("type2", extractor2)
        
        # Create mock events
        class MockEvent:
            def __init__(self, event_type):
                self.event_type = event_type
                
        event1 = MockEvent("type1")
        event2 = MockEvent("type2")
        
        # Test getting extractors for events
        extractors1 = registry.get_extractors_for_event(event1)
        assert len(extractors1) == 1
        assert extractor1 in extractors1
        
        extractors2 = registry.get_extractors_for_event(event2)
        assert len(extractors2) == 1
        assert extractor2 in extractors2
    
    def test_get_extractor_by_name(self):
        """Test getting an extractor by name."""
        registry = ExtractorRegistry()
        extractor = MockExtractor()
        
        registry.register(extractor)
        
        assert registry.get_extractor_by_name("MockExtractor") == extractor
        assert registry.get_extractor_by_name("NonexistentExtractor") is None


class TestExtractionUtils:
    """Tests for the extraction utility functions."""
    
    def test_find_paths_with_key(self):
        """Test finding paths to a specific key in nested data."""
        data = {
            "level1": {
                "target": "value1",
                "level2": {
                    "target": "value2"
                }
            },
            "array": [
                {"target": "value3"},
                {"nested": {"target": "value4"}}
            ]
        }
        
        paths = find_paths_with_key(data, "target")
        assert len(paths) == 4
        assert ["level1", "target"] in paths
        assert ["level1", "level2", "target"] in paths
        assert ["array", "0", "target"] in paths
        assert ["array", "1", "nested", "target"] in paths
    
    def test_find_values_by_key(self):
        """Test finding all values for a specific key in nested data."""
        data = {
            "level1": {
                "target": "value1",
                "level2": {
                    "target": "value2"
                }
            },
            "array": [
                {"target": "value3"},
                {"nested": {"target": "value4"}}
            ]
        }
        
        values = find_values_by_key(data, "target")
        assert len(values) == 4
        assert "value1" in values
        assert "value2" in values
        assert "value3" in values
        assert "value4" in values
    
    def test_flatten_json(self):
        """Test flattening a nested JSON structure."""
        data = {
            "person": {
                "name": "John",
                "age": 30,
                "address": {
                    "street": "123 Main St",
                    "city": "Anytown"
                }
            },
            "hobbies": ["reading", "swimming"]
        }
        
        flattened = flatten_json(data)
        assert flattened["person.name"] == "John"
        assert flattened["person.age"] == 30
        assert flattened["person.address.street"] == "123 Main St"
        assert flattened["person.address.city"] == "Anytown"
        assert flattened["hobbies.0"] == "reading"
        assert flattened["hobbies.1"] == "swimming"
    
    def test_normalize_string(self):
        """Test normalizing string values."""
        assert normalize_string("  Hello  World  ") == "hello world"
        assert normalize_string("UPPERCASE") == "uppercase"
        assert normalize_string("  multiple    spaces  ") == "multiple spaces"
        assert normalize_string(None) == ""
        assert normalize_string(123) == ""
    
    def test_extract_datetime(self):
        """Test extracting datetime from various formats."""
        # ISO format
        dt1 = extract_datetime("2023-01-01T12:00:00")
        assert dt1.year == 2023
        assert dt1.month == 1
        assert dt1.day == 1
        assert dt1.hour == 12
        assert dt1.minute == 0
        assert dt1.second == 0
        
        # With timezone
        dt2 = extract_datetime("2023-01-01T12:00:00Z")
        assert dt2.year == 2023
        assert dt2.month == 1
        assert dt2.day == 1
        assert dt2.hour == 12
        assert dt2.minute == 0
        assert dt2.second == 0
        assert dt2.tzinfo is not None  # Should have timezone info
        
        # Other formats
        dt3 = extract_datetime("2023-01-01 12:00:00")
        assert dt3.year == 2023
        assert dt3.month == 1
        assert dt3.day == 1
        assert dt3.hour == 12
        
        dt4 = extract_datetime("2023-01-01")
        assert dt4.year == 2023
        assert dt4.month == 1
        assert dt4.day == 1
        
        # Invalid values
        assert extract_datetime("not a date") is None
        assert extract_datetime(None) is None
    
    def test_extract_numeric_values(self):
        """Test extracting numeric values from text."""
        assert extract_numeric_values("The temperature is 72.5 degrees") == [72.5]
        assert extract_numeric_values("Values: -10, 20, 30.5") == [-10.0, 20.0, 30.5]
        assert extract_numeric_values("No numbers here") == []
        assert extract_numeric_values(None) == []
    
    def test_merge_dictionaries(self):
        """Test merging dictionaries."""
        dict1 = {"a": 1, "b": {"c": 2, "d": 3}}
        dict2 = {"b": {"c": 4, "e": 5}, "f": 6}
        
        # With overwrite
        merged = merge_dictionaries(dict1, dict2)
        assert merged["a"] == 1
        assert merged["b"]["c"] == 4  # Overwritten
        assert merged["b"]["d"] == 3  # Preserved
        assert merged["b"]["e"] == 5  # Added
        assert merged["f"] == 6  # Added
        
        # Without overwrite
        merged = merge_dictionaries(dict1, dict2, overwrite=False)
        assert merged["a"] == 1
        assert merged["b"]["c"] == 2  # Preserved (not overwritten)
        assert merged["b"]["d"] == 3  # Preserved
        assert merged["b"]["e"] == 5  # Added
        assert merged["f"] == 6  # Added
    
    def test_extract_schema_fields(self):
        """Test extracting fields based on a schema mapping."""
        data = {
            "person": {
                "firstName": "John",
                "lastName": "Doe",
                "details": {
                    "age": 30
                }
            },
            "contact": {
                "email": "john@example.com"
            }
        }
        
        schema = {
            "name": "person.firstName",
            "surname": "person.lastName",
            "age": "person.details.age",
            "phone": ["contact.phone", "contact.mobile"],
            "email": "contact.email"
        }
        
        extracted = extract_schema_fields(data, schema)
        assert extracted["name"] == "John"
        assert extracted["surname"] == "Doe"
        assert extracted["age"] == 30
        assert extracted["email"] == "john@example.com"
        assert "phone" not in extracted  # No matching paths
    
    def test_get_nested_value(self):
        """Test getting a nested value using a dot-notation path."""
        data = {
            "a": {
                "b": {
                    "c": "value"
                }
            }
        }
        
        assert get_nested_value(data, "a.b.c") == "value"
        assert get_nested_value(data, "a.b.d") is None
        assert get_nested_value(data, "a.b.d", "default") == "default"
        assert get_nested_value(None, "a.b.c") is None
        assert get_nested_value(data, "") is None 