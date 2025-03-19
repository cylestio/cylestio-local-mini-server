from typing import Dict, Any, Optional
import datetime
import logging

logger = logging.getLogger(__name__)

def process_system_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process system events like initialization, startup, shutdown.
    
    Args:
        event: Raw system event
        
    Returns:
        Transformed event with system information
    """
    # Start with generic processing
    transformed = _process_generic_event(event)
    
    # Extract system-specific fields
    if "data" in event:
        data = event["data"]
        
        # Extract message if available
        if "message" in data:
            transformed["data"]["system_message"] = data["message"]
        
        # Extract agent_id from data (some system events may include it there)
        if "agent_id" in data:
            transformed["data"]["subject_agent"] = data["agent_id"]
        
        # Extract configuration if available
        if "config" in data:
            transformed["data"]["configuration"] = data["config"]
        
        # Extract model information
        if "model" in data:
            transformed["data"]["model"] = data["model"]
        
        # Extract database information
        if "database_path" in data:
            transformed["data"]["database_path"] = data["database_path"]
        
        # Extract method information for patch events
        if "method" in data:
            transformed["data"]["patched_method"] = data["method"]
    
    # Handle specific event types
    event_type = event.get("event_type")
    if event_type == "monitoring_enabled":
        transformed["data"]["system_status"] = "enabled"
    elif event_type == "monitoring_disabled":
        transformed["data"]["system_status"] = "disabled"
    elif event_type == "LLM_patch" or event_type == "MCP_patch":
        transformed["data"]["patch_type"] = event_type.split("_")[0]
    
    return transformed

def _process_generic_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic processing for system events.
    
    Args:
        event: Raw event
        
    Returns:
        Processed event with common fields extracted
    """
    timestamp = event.get("timestamp")
    if isinstance(timestamp, str):
        timestamp = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    
    transformed = {
        "timestamp": timestamp,
        "level": event.get("level", "INFO"),
        "agent_id": event.get("agent_id"),
        "event_type": event.get("event_type"),
        "channel": event.get("channel", "SYSTEM"),
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