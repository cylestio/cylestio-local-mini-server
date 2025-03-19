from typing import Dict, Any, Optional
import datetime
import logging
import json

logger = logging.getLogger(__name__)

def process_security_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process security-related events like blocked calls or alerts.
    
    Args:
        event: Raw security event
        
    Returns:
        Transformed event with security information
    """
    # Start with generic processing
    transformed = _process_generic_event(event)
    
    # Mark as a security event
    transformed["level"] = event.get("level", "WARNING")
    
    # Extract security-specific fields
    if "data" in event:
        data = event["data"]
        
        # Extract reason for security event
        if "reason" in data:
            transformed["data"]["security_reason"] = data["reason"]
        
        # Extract the affected content if available
        if "prompt" in data:
            try:
                # Some prompts may be strings, others may be JSON
                prompt = data["prompt"]
                if isinstance(prompt, str):
                    try:
                        # Try to parse as JSON
                        prompt_json = json.loads(prompt)
                        transformed["data"]["affected_content"] = prompt_json
                    except:
                        # Not valid JSON, keep as string
                        transformed["data"]["affected_content"] = prompt
                else:
                    # Already an object
                    transformed["data"]["affected_content"] = prompt
            except Exception as e:
                logger.error(f"Error parsing affected content: {str(e)}")
        
        # Extract alert information
        if "alert" in data:
            transformed["data"]["alert_level"] = data["alert"]
            
            # If alert is "dangerous" or "critical", mark as high severity
            if data["alert"] in ["dangerous", "critical"]:
                transformed["level"] = "ERROR"
                transformed["data"]["severity"] = "high"
            else:
                transformed["data"]["severity"] = "medium"
    
    return transformed

def _process_generic_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic processing for security events.
    
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
        "level": event.get("level", "WARNING"),
        "agent_id": event.get("agent_id"),
        "event_type": event.get("event_type"),
        "channel": event.get("channel", "SECURITY"),
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