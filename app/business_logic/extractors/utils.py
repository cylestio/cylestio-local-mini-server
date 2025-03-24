"""
Extraction utilities module.

This module provides utility functions for JSON data extraction
and manipulation used by the extractors.
"""

from typing import Dict, Any, List, Union, Optional, Type, Tuple, Set, Callable
from datetime import datetime
import logging
import re
import json

logger = logging.getLogger(__name__)


def find_paths_with_key(data: Dict[str, Any], target_key: str) -> List[List[str]]:
    """Find all paths to a specific key in a nested JSON structure.
    
    Args:
        data: The data dictionary to search
        target_key: The key to search for
        
    Returns:
        List of paths (as lists of keys) to the target key
    """
    results = []
    
    def search(current_data, current_path):
        if isinstance(current_data, dict):
            for key, value in current_data.items():
                if key == target_key:
                    results.append(current_path + [key])
                if isinstance(value, (dict, list)):
                    search(value, current_path + [key])
        elif isinstance(current_data, list):
            for i, item in enumerate(current_data):
                if isinstance(item, (dict, list)):
                    search(item, current_path + [str(i)])
    
    search(data, [])
    return results


def find_values_by_key(data: Dict[str, Any], target_key: str) -> List[Any]:
    """Find all values for a specific key in a nested JSON structure.
    
    Args:
        data: The data dictionary to search
        target_key: The key to search for
        
    Returns:
        List of values for the target key
    """
    results = []
    
    def search(current_data):
        if isinstance(current_data, dict):
            for key, value in current_data.items():
                if key == target_key:
                    results.append(value)
                if isinstance(value, (dict, list)):
                    search(value)
        elif isinstance(current_data, list):
            for item in current_data:
                if isinstance(item, (dict, list)):
                    search(item)
    
    search(data)
    return results


def flatten_json(data: Dict[str, Any], delimiter: str = '.') -> Dict[str, Any]:
    """Flatten a nested JSON structure into a flat dictionary with delimited keys.
    
    Args:
        data: The nested data dictionary to flatten
        delimiter: The delimiter to use in the flattened keys
        
    Returns:
        A flattened dictionary
    """
    flattened = {}
    
    def flatten(current_data, prefix=''):
        if isinstance(current_data, dict):
            for key, value in current_data.items():
                new_prefix = f"{prefix}{delimiter}{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    flatten(value, new_prefix)
                else:
                    flattened[new_prefix] = value
        elif isinstance(current_data, list):
            for i, item in enumerate(current_data):
                new_prefix = f"{prefix}{delimiter}{i}"
                if isinstance(item, (dict, list)):
                    flatten(item, new_prefix)
                else:
                    flattened[new_prefix] = item
    
    flatten(data)
    return flattened


def normalize_string(value: str) -> str:
    """Normalize a string value for consistent processing.
    
    Converts to lowercase, removes extra whitespace, etc.
    
    Args:
        value: The string to normalize
        
    Returns:
        The normalized string
    """
    if not value or not isinstance(value, str):
        return ""
    
    # Convert to lowercase and strip whitespace
    normalized = value.lower().strip()
    
    # Replace multiple spaces with a single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized


def extract_datetime(value: Any) -> Optional[datetime]:
    """Extract and parse a datetime from various formats.
    
    Args:
        value: The value to parse as a datetime
        
    Returns:
        Parsed datetime or None if parsing fails
    """
    if not value:
        return None
        
    if isinstance(value, datetime):
        return value
        
    if isinstance(value, (int, float)):
        # Assume it's a timestamp
        try:
            return datetime.fromtimestamp(value)
        except (ValueError, OverflowError):
            pass
    
    if isinstance(value, str):
        # Try multiple formats
        formats = [
            # ISO format
            lambda v: datetime.fromisoformat(v.replace('Z', '+00:00')),
            # Common formats
            lambda v: datetime.strptime(v, '%Y-%m-%d %H:%M:%S'),
            lambda v: datetime.strptime(v, '%Y-%m-%dT%H:%M:%S'),
            lambda v: datetime.strptime(v, '%Y-%m-%d'),
            lambda v: datetime.strptime(v, '%Y/%m/%d %H:%M:%S'),
        ]
        
        for format_parser in formats:
            try:
                return format_parser(value)
            except ValueError:
                continue
    
    logger.debug(f"Failed to parse datetime value: {value}")
    return None


def extract_numeric_values(text: str) -> List[float]:
    """Extract all numeric values from a text string.
    
    Args:
        text: The text to extract numbers from
        
    Returns:
        List of extracted numeric values
    """
    if not text or not isinstance(text, str):
        return []
    
    # Find all numeric patterns (including decimals)
    pattern = r'-?\d+(?:\.\d+)?'
    matches = re.findall(pattern, text)
    
    # Convert matches to float
    return [float(match) for match in matches]


def merge_dictionaries(dict1: Dict[str, Any], dict2: Dict[str, Any], 
                      overwrite: bool = True) -> Dict[str, Any]:
    """Merge two dictionaries recursively.
    
    Args:
        dict1: The first dictionary
        dict2: The second dictionary to merge into the first
        overwrite: Whether to overwrite values in dict1 with values from dict2
        
    Returns:
        The merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = merge_dictionaries(result[key], value, overwrite)
        elif key not in result or overwrite:
            # Add or overwrite the value
            result[key] = value
    
    return result


def extract_schema_fields(data: Dict[str, Any], schema_fields: Dict[str, Union[str, List[str]]]) -> Dict[str, Any]:
    """Extract fields from data based on a schema mapping.
    
    Args:
        data: The data dictionary to extract from
        schema_fields: Mapping of output field names to input field paths
        
    Returns:
        Dictionary with extracted fields according to the schema
    """
    result = {}
    
    for field_name, path in schema_fields.items():
        if isinstance(path, list):
            # Try multiple paths
            for p in path:
                value = get_nested_value(data, p)
                if value is not None:
                    result[field_name] = value
                    break
        else:
            # Single path
            value = get_nested_value(data, path)
            if value is not None:
                result[field_name] = value
    
    return result


def get_nested_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Get a value from a nested dictionary using a dot-notation path.
    
    Args:
        data: The data dictionary to extract from
        path: Dot-notation path to the value
        default: Default value to return if the path doesn't exist
        
    Returns:
        The extracted value or the default if not found
    """
    if not data or not path:
        return default
        
    parts = path.split('.')
    current = data
    
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
            
    return current 