"""
Extractors package for normalizing JSON data.

This package provides extractors that normalize complex JSON data
from event payloads into dedicated relational database tables.
"""

from app.business_logic.extractors.base import (
    BaseExtractor, 
    ExtractorRegistry, 
    extractor_registry
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
from app.business_logic.extractors.common_extractor import CommonExtractor
from app.business_logic.extractors.token_usage_extractor import TokenUsageExtractor
from app.business_logic.extractors.performance_extractor import PerformanceExtractor
from app.business_logic.extractors.security_extractor import SecurityExtractor
from app.business_logic.extractors.model_info_extractor import ModelInfoExtractor
from app.business_logic.extractors.framework_extractor import FrameworkExtractor
from app.business_logic.extractors.model_request_extractor import ModelRequestExtractor
from app.business_logic.extractors.model_response_extractor import ModelResponseExtractor
from app.business_logic.extractors.example_extractor import UserActivityExtractor
from app.business_logic.extractors.llm_call_extractor import LLMCallExtractor
from app.business_logic.extractors.monitor_event_extractor import MonitorEventExtractor

# Export the core extraction framework
__all__ = [
    'BaseExtractor',
    'ExtractorRegistry',
    'extractor_registry',
    'find_paths_with_key',
    'find_values_by_key',
    'flatten_json',
    'normalize_string',
    'extract_datetime',
    'extract_numeric_values',
    'merge_dictionaries',
    'extract_schema_fields',
    'get_nested_value',
    'UserActivityExtractor',
    'LLMCallExtractor',
    'MonitorEventExtractor',
]

# Register all extractors
extractor_registry.register(CommonExtractor())
extractor_registry.register(TokenUsageExtractor())
extractor_registry.register(PerformanceExtractor())
extractor_registry.register(SecurityExtractor())
extractor_registry.register(ModelInfoExtractor())
extractor_registry.register(FrameworkExtractor())
extractor_registry.register(ModelRequestExtractor())
extractor_registry.register(ModelResponseExtractor())
extractor_registry.register(UserActivityExtractor())
extractor_registry.register(LLMCallExtractor())
extractor_registry.register(MonitorEventExtractor())

# Register specific extractors for specific event types
extractor_registry.register_for_event_type("model_request", ModelRequestExtractor())
extractor_registry.register_for_event_type("model_response", ModelResponseExtractor())
extractor_registry.register_for_event_type("framework_patch", FrameworkExtractor())
extractor_registry.register_for_event_type("user_login", UserActivityExtractor())
extractor_registry.register_for_event_type("user_action", UserActivityExtractor())
extractor_registry.register_for_event_type("user_logout", UserActivityExtractor())
extractor_registry.register_for_event_type("LLM_call_start", LLMCallExtractor())
extractor_registry.register_for_event_type("LLM_call_finish", LLMCallExtractor())
extractor_registry.register_for_event_type("LLM_call_blocked", LLMCallExtractor())
extractor_registry.register_for_event_type("monitor_init", MonitorEventExtractor())
extractor_registry.register_for_event_type("monitor_shutdown", MonitorEventExtractor()) 