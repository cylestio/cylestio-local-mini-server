from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
import datetime
import logging

logger = logging.getLogger(__name__)

class BaseTransformer(ABC):
    """
    Base abstract class for all event transformers.
    """
    
    def __init__(self):
        self.event_processors = {}
        self._register_processors()
    
    @abstractmethod
    def _register_processors(self) -> None:
        """
        Register all event processors for this transformer.
        Must be implemented by subclasses.
        """
        pass
    
    def transform(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a raw JSON event into a structured event.
        
        Args:
            raw_event: Raw JSON event data
        
        Returns:
            Transformed event data ready for database insertion
        """
        try:
            # Extract event type
            event_type = raw_event.get("event_type", "UNKNOWN")
            
            # Process with specific processor if available
            if event_type in self.event_processors:
                return self.event_processors[event_type](raw_event)
            
            # Fall back to generic processing
            return self._process_generic(raw_event)
        except Exception as e:
            logger.error(f"Error transforming event: {str(e)}")
            # Return original event with minimal processing to avoid data loss
            return self._process_generic(raw_event)
    
    def _process_generic(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generic processing for events without specific processors.
        
        Args:
            raw_event: Raw JSON event data
        
        Returns:
            Minimally processed event data
        """
        # Extract basic fields
        try:
            timestamp = raw_event.get("timestamp")
            timestamp = self.normalize_timestamp(timestamp)
            
            transformed = {
                "timestamp": timestamp,
                "level": raw_event.get("level", "INFO"),
                "agent_id": raw_event.get("agent_id"),
                "event_type": raw_event.get("event_type", "UNKNOWN"),
                "channel": raw_event.get("channel", "UNKNOWN"),
                "direction": raw_event.get("direction"),
                "session_id": raw_event.get("session_id"),
                "data": raw_event.get("data", {}),
            }
            
            # Extract caller information if available
            if "caller" in raw_event:
                caller = raw_event["caller"]
                transformed["caller_file"] = caller.get("file")
                transformed["caller_line"] = caller.get("line")
                transformed["caller_function"] = caller.get("function")
            
            return transformed
        except Exception as e:
            logger.error(f"Error in generic processing: {str(e)}")
            # Return original data with minimal required fields
            return {
                "timestamp": datetime.datetime.now(),
                "level": "ERROR",
                "agent_id": raw_event.get("agent_id", "unknown"),
                "event_type": raw_event.get("event_type", "ERROR"),
                "channel": "ERROR",
                "data": raw_event
            }
            
    @staticmethod
    def normalize_timestamp(timestamp):
        """
        Convert a timestamp to a datetime object if it's not already one.
        
        Args:
            timestamp: The timestamp to normalize (string, datetime, or other format)
            
        Returns:
            A datetime object, or None if conversion fails
        """
        if timestamp is None:
            return datetime.datetime.now()
            
        if isinstance(timestamp, datetime.datetime):
            return timestamp
            
        if isinstance(timestamp, str):
            try:
                # Handle common ISO format variations
                if 'Z' in timestamp:
                    # Replace Z with +00:00 for proper UTC handling
                    timestamp = timestamp.replace('Z', '+00:00')
                elif 'T' in timestamp and '+' not in timestamp and not any(c in timestamp[10:] for c in ['-', '+']):
                    # Add timezone if missing
                    timestamp = timestamp + '+00:00'
                    
                return datetime.datetime.fromisoformat(timestamp)
            except ValueError:
                try:
                    # Try more flexible parsing as fallback
                    import dateutil.parser
                    return dateutil.parser.parse(timestamp)
                except (ImportError, ValueError):
                    # If dateutil is not available or parsing fails
                    logger.warning(f"Could not parse timestamp: {timestamp}")
                    return datetime.datetime.now()
        
        # For numeric timestamps (assuming unix timestamps)
        try:
            if isinstance(timestamp, (int, float)):
                # Determine if this is seconds or milliseconds based on magnitude
                timestamp_value = float(timestamp)  # Ensure it's a number
                if timestamp_value > 1e10:  # Likely milliseconds
                    return datetime.datetime.fromtimestamp(timestamp_value / 1000)
                else:  # Likely seconds
                    return datetime.datetime.fromtimestamp(timestamp_value)
        except (ValueError, OverflowError, OSError, TypeError):
            logger.warning(f"Could not convert numeric timestamp: {timestamp}")
        
        # If all else fails
        logger.warning(f"Using current time for unparseable timestamp: {timestamp}")
        return datetime.datetime.now() 