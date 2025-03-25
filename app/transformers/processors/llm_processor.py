from typing import Dict, Any, Optional
import datetime
import logging
import json

logger = logging.getLogger(__name__)

def process_llm_call_start(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process LLM call start events.
    
    Args:
        event: Raw LLM call start event
        
    Returns:
        Transformed event with extracted LLM request data
    """
    # Start with generic processing
    transformed = _process_generic_event(event)
    transformed["direction"] = "outgoing"
    
    # Extract LLM-specific fields
    if "data" in event:
        data = event["data"]
        
        # Extract prompt information
        if "prompt" in data:
            try:
                # Some prompts may be strings, others may be JSON
                prompt = data["prompt"]
                if isinstance(prompt, str):
                    try:
                        # Try to parse as JSON
                        prompt_json = json.loads(prompt)
                        transformed["data"]["parsed_prompt"] = prompt_json
                    except:
                        # Not valid JSON, keep as string
                        transformed["data"]["parsed_prompt"] = prompt
                else:
                    # Already an object
                    transformed["data"]["parsed_prompt"] = prompt
            except Exception as e:
                logger.error(f"Error parsing prompt: {str(e)}")
        
        # Extract alert information
        if "alert" in data:
            transformed["data"]["alert_level"] = data["alert"]
        
        # Extract model information
        if "model" in data:
            transformed["data"]["model"] = data["model"]
    
    return transformed

def process_llm_call_finish(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process LLM call finish events.
    
    Args:
        event: Raw LLM call finish event
        
    Returns:
        Transformed event with extracted LLM response data
    """
    # Start with generic processing
    transformed = _process_generic_event(event)
    transformed["direction"] = "incoming"
    
    # Extract LLM-specific fields
    if "data" in event:
        data = event["data"]
        
        # Extract performance data
        if "duration" in data:
            transformed["duration_ms"] = float(data["duration"]) * 1000  # Convert to ms
        
        # Extract response
        if "response" in data:
            transformed["data"]["response_text"] = data["response"]
        
        # Extract token usage
        if "usage" in data and data["usage"]:
            usage = data["usage"]
            if usage and isinstance(usage, dict):
                transformed["data"]["prompt_tokens"] = usage.get("prompt_tokens")
                transformed["data"]["completion_tokens"] = usage.get("completion_tokens")
                transformed["data"]["total_tokens"] = usage.get("total_tokens")
        
        # Extract model information
        if "model" in data:
            transformed["data"]["model"] = data["model"]
        
        # Extract alert information
        if "alert" in data:
            transformed["data"]["alert_level"] = data["alert"]
    
    return transformed

def _process_generic_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic processing for LLM events.
    
    Args:
        event: Raw event
        
    Returns:
        Processed event with common fields extracted
    """
    # Import here to avoid circular imports
    from app.transformers.base import BaseTransformer
    
    timestamp = event.get("timestamp")
    timestamp = BaseTransformer.normalize_timestamp(timestamp)
    
    transformed = {
        "timestamp": timestamp,
        "level": event.get("level", "INFO"),
        "agent_id": event.get("agent_id"),
        "event_type": event.get("event_type"),
        "channel": event.get("channel", "LLM"),
        "session_id": event.get("session_id"),
        "data": event.get("data", {}).copy() if event.get("data") else {},
    }
    
    # Extract caller information if available
    if "caller" in event:
        caller = event["caller"]
        transformed["caller_file"] = caller.get("file")
        transformed["caller_line"] = caller.get("line")
        transformed["caller_function"] = caller.get("function")
    
    return transformed 