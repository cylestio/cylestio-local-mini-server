from typing import Dict, Any, Optional
import datetime
import logging
import re

logger = logging.getLogger(__name__)

def process_tool_call_start(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process tool call start events.
    
    Args:
        event: Raw tool call start event
        
    Returns:
        Transformed event with extracted tool call data
    """
    # Start with generic processing
    transformed = _process_generic_event(event)
    transformed["direction"] = "outgoing"
    
    # Extract tool-specific fields
    if "data" in event:
        data = event["data"]
        
        # Extract function name and arguments
        if "function" in data:
            transformed["data"]["tool_name"] = data["function"]
        
        # Extract arguments
        if "args" in data:
            args = data["args"]
            try:
                # Try to parse arguments if they're a string
                if isinstance(args, str):
                    # Handle common patterns like "(arg1, arg2, ...)"
                    args_str = args.strip()
                    
                    # Extract tool arguments using regex patterns
                    tool_name_match = re.search(r"'([^']+)'", args_str)
                    if tool_name_match:
                        transformed["data"]["tool_function"] = tool_name_match.group(1)
                    
                    # Try to extract JSON-like data for args
                    json_match = re.search(r"{([^}]+)}", args_str)
                    if json_match:
                        json_args = json_match.group(0)
                        transformed["data"]["tool_args"] = json_args
            except Exception as e:
                logger.error(f"Error parsing tool arguments: {str(e)}")
                transformed["data"]["raw_args"] = args
        
        # Extract keywords
        if "kwargs" in data:
            transformed["data"]["tool_kwargs"] = data["kwargs"]
    
    return transformed

def process_tool_call_finish(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process tool call finish events.
    
    Args:
        event: Raw tool call finish event
        
    Returns:
        Transformed event with extracted tool response data
    """
    # Start with generic processing
    transformed = _process_generic_event(event)
    transformed["direction"] = "incoming"
    
    # Extract tool-specific fields
    if "data" in event:
        data = event["data"]
        
        # Extract duration
        if "duration" in data:
            transformed["duration_ms"] = float(data["duration"]) * 1000  # Convert to ms
        
        # Extract function name
        if "function" in data:
            transformed["data"]["tool_name"] = data["function"]
        
        # Extract result
        if "result" in data:
            result = data["result"]
            transformed["data"]["tool_result"] = result
            
            # Check if the result indicates an error
            if isinstance(result, str) and ("error" in result.lower() or "exception" in result.lower()):
                transformed["data"]["is_error"] = True
                transformed["level"] = "ERROR"
            elif isinstance(result, dict) and "error" in result:
                transformed["data"]["is_error"] = True
                transformed["level"] = "ERROR"
            elif isinstance(result, str) and "isError=False" in result:
                transformed["data"]["is_error"] = False
            else:
                transformed["data"]["is_error"] = False
    
    return transformed

def _process_generic_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic processing for tool events.
    
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
        "channel": event.get("channel", "MCP"),
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