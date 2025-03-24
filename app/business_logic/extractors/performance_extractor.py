"""
PerformanceExtractor module.

This module extracts performance metrics from events that include duration or latency data.
"""

import logging
from typing import Optional

from app.models.performance_metric import PerformanceMetric
from app.business_logic.extractors.base import BaseExtractor

# Set up logging
logger = logging.getLogger(__name__)


class PerformanceExtractor(BaseExtractor):
    """Extractor for performance metric data.
    
    Extracts duration, latency and other performance metrics from
    various event types that include timing information.
    """
    
    def can_process(self, event) -> bool:
        """Check if this event contains performance data.
        
        Args:
            event: The event to check
            
        Returns:
            True if this event type might contain performance data
        """
        if not event.data:
            return False
        
        # Event types that typically contain performance data
        perf_event_types = {
            "model_response", 
            "LLM_call_finish",
            "call_finish"
        }
        
        # Also check for direct duration field in the event
        if event.duration_ms is not None and event.duration_ms > 0:
            return True
            
        return event.event_type in perf_event_types
    
    async def process(self, event, db_session) -> None:
        """Extract performance data from the event.
        
        Args:
            event: The event to process
            db_session: Database session for persistence
        """
        performance_metric = await self._extract_performance_metrics(event)
        
        if performance_metric:
            db_session.add(performance_metric)
    
    async def _extract_performance_metrics(self, event) -> Optional[PerformanceMetric]:
        """Extract performance metrics from various event formats.
        
        Handles different JSON structures based on event type.
        
        Args:
            event: The event to extract from
            
        Returns:
            PerformanceMetric object or None if no data found
        """
        try:
            # Get event data
            data = event.data
            duration_ms = None
            
            # First check if duration is directly in the event
            if event.duration_ms is not None and event.duration_ms > 0:
                duration_ms = event.duration_ms
                
            # Otherwise extract from data field based on event type
            elif event.event_type == "model_response":
                if "performance" in data and "duration_ms" in data["performance"]:
                    duration_str = data["performance"]["duration_ms"]
                    # Handle both string and float formats
                    duration_ms = float(duration_str) if isinstance(duration_str, str) else duration_str
                    
            elif event.event_type == "call_finish":
                if "duration" in data:
                    duration_ms = float(data["duration"]) * 1000  # Convert to ms
            
            elif event.event_type == "LLM_call_finish":
                # Some LLM providers include performance data
                if "performance" in data:
                    perf_data = data["performance"]
                    if isinstance(perf_data, dict) and "duration_ms" in perf_data:
                        duration_ms = float(perf_data["duration_ms"])
            
            # If we found duration data, create the object
            if duration_ms is not None and duration_ms > 0:
                return PerformanceMetric(
                    event_id=event.id,
                    duration_ms=duration_ms,
                    timestamp=event.timestamp
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Error extracting performance metrics from event {event.id}: {str(e)}")
            return None 